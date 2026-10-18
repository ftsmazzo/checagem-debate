import base64
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import Claim, RunState, Segment, session, utcnow
from app.factcheck import extract_claims, verify_claim
from app.settings import settings

YOUTUBE_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}
NOISE = (
    "obrigado por assistir",
    "legendas pela comunidade",
    "inscreva-se no canal",
    "amara.org",
)


def assert_youtube(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in YOUTUBE_HOSTS:
        raise ValueError("use um link do YouTube")
    return url.strip()


def _fingerprint(text: str) -> str:
    folded = " ".join(text.casefold().split())
    return hashlib.sha256(folded.encode("utf-8")).hexdigest()


class DebateListener:
    def __init__(self) -> None:
        self.audio_stop = threading.Event()
        self.audio_thread: threading.Thread | None = None
        self.check_thread: threading.Thread | None = None
        self.procs: list[subprocess.Popen] = []
        self.lock = threading.Lock()
        self.context = ""
        self.chunk_dir = Path("/tmp/debate-chunks")

    def start(self, url: str) -> None:
        url = assert_youtube(url)
        if not settings.openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY ausente no serviço")
        with self.lock:
            if self.audio_thread and self.audio_thread.is_alive():
                return
            self.audio_stop.clear()
            self._set_state(True, url, "")
            self.ensure_checker()
            self.audio_thread = threading.Thread(target=self._audio_loop, args=(url,), daemon=True)
            self.audio_thread.start()

    def halt(self) -> None:
        self.audio_stop.set()
        self._kill()
        self._set_state(False, None, "")

    def ensure_checker(self) -> None:
        if self.check_thread and self.check_thread.is_alive():
            return
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()

    def _set_state(self, running: bool | None, url: str | None, error: str | None) -> None:
        with session() as db:
            state = db.get(RunState, 1)
            if running is not None:
                state.running = 1 if running else 0
            if url is not None:
                state.youtube_url = url
            if error is not None:
                state.last_error = error[:1500]
            state.updated_at = utcnow()
            db.commit()

    def _kill(self) -> None:
        for proc in list(self.procs):
            if proc.poll() is None:
                proc.kill()
        self.procs.clear()

    def _audio_loop(self, url: str) -> None:
        self.chunk_dir.mkdir(parents=True, exist_ok=True)
        while not self.audio_stop.is_set():
            try:
                self._run_once(url)
            except Exception as exc:
                self._set_state(None, None, f"áudio: {exc}")
            if self.audio_stop.wait(8):
                break
        self._set_state(False, None, None)

    def _run_once(self, url: str) -> None:
        for old in self.chunk_dir.glob("c*.mp3"):
            old.unlink(missing_ok=True)
        ytdlp = subprocess.Popen(
            [
                "yt-dlp",
                "--no-warnings",
                "--no-progress",
                "--no-part",
                "-f",
                "ba/bestaudio/best",
                "--extractor-args",
                "youtube:player_client=android,web",
                "-o",
                "-",
                url,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        pattern = str(self.chunk_dir / "c%05d.mp3")
        ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "libmp3lame",
                "-b:a",
                "64k",
                "-f",
                "segment",
                "-segment_time",
                str(settings.chunk_seconds),
                "-reset_timestamps",
                "1",
                pattern,
            ],
            stdin=ytdlp.stdout,
            stderr=subprocess.PIPE,
        )
        if ytdlp.stdout:
            ytdlp.stdout.close()
        self.procs = [ytdlp, ffmpeg]
        errors: list[str] = []
        threading.Thread(target=_drain, args=(ytdlp.stderr, errors), daemon=True).start()
        threading.Thread(target=_drain, args=(ffmpeg.stderr, errors), daemon=True).start()
        seen: set[str] = set()
        while not self.audio_stop.is_set():
            if ytdlp.poll() is not None and ffmpeg.poll() is not None:
                detail = " ".join(errors)[-500:] or f"yt-dlp saiu com código {ytdlp.returncode}"
                self._set_state(None, None, detail)
                return
            ready = _stable_chunks(self.chunk_dir, seen)
            for path in ready:
                seen.add(path.name)
                self._transcribe_file(path)
            time.sleep(1)
        self._kill()

    def _transcribe_file(self, path: Path) -> None:
        try:
            text = transcribe_mp3(path)
        finally:
            path.unlink(missing_ok=True)
        folded = text.casefold().strip()
        if len(folded) < 8 or any(noise in folded for noise in NOISE):
            return
        with session() as db:
            db.add(Segment(text=text))
            db.commit()
        self.context = (self.context + "\n" + text)[-8000:]
        self._enqueue_from_context()

    def _enqueue_from_context(self) -> None:
        try:
            claims = extract_claims(self.context)
        except Exception as exc:
            self._set_state(None, None, f"extração: {exc}")
            return
        with session() as db:
            for item in claims:
                row = Claim(
                    quote=item["quote"],
                    normalized=item["claim"],
                    fingerprint=_fingerprint(item["claim"]),
                    speaker="lula",
                    origin="live",
                    status="pendente",
                )
                db.add(row)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()

    def _check_loop(self) -> None:
        while True:
            with session() as db:
                row = db.scalars(
                    select(Claim).where(Claim.status == "pendente").order_by(Claim.id).limit(1)
                ).first()
                if row is None:
                    claim_id = None
                else:
                    claim_id = row.id
                    quote = row.quote
                    normalized = row.normalized
            if claim_id is None:
                time.sleep(1)
                continue
            try:
                verdict = verify_claim(quote, normalized)
                status = verdict["status"]
                summary = verdict["summary"]
                missing = verdict["missing"]
                confidence = verdict["confidence"]
                sources = json.dumps(verdict["sources"], ensure_ascii=False)
            except Exception as exc:
                status = "erro"
                summary = str(exc)[:800]
                missing = ""
                confidence = 0
                sources = "[]"
                self._set_state(None, None, f"checagem: {exc}")
            with session() as db:
                current = db.get(Claim, claim_id)
                if current and current.status == "pendente":
                    current.status = status
                    current.summary = summary
                    current.missing = missing
                    current.confidence = confidence
                    current.sources_json = sources
                    db.commit()


def enqueue_manual(text: str) -> int:
    cleaned = " ".join(text.split())
    if len(cleaned) < 12:
        raise ValueError("escreva a frase completa")
    with session() as db:
        row = Claim(
            quote=cleaned[:500],
            normalized=cleaned[:400],
            fingerprint=_fingerprint("manual:" + cleaned),
            speaker="lula",
            origin="manual",
            status="pendente",
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.scalars(
                select(Claim).where(Claim.fingerprint == _fingerprint("manual:" + cleaned))
            ).first()
            return existing.id if existing else 0
        claim_id = row.id
    _ensure_checker()
    return claim_id


def _ensure_checker() -> None:
    get_listener().ensure_checker()


def transcribe_mp3(path: Path) -> str:
    payload = {
        "model": settings.stt_model,
        "language": "pt",
        "input_audio": {
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
            "format": "mp3",
        },
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.referer,
        "X-Title": "Checagem do debate",
    }
    with httpx.Client(timeout=60) as client:
        response = client.post(
            "https://openrouter.ai/api/v1/audio/transcriptions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        return str(response.json().get("text") or "").strip()


def _drain(pipe, bucket: list[str]) -> None:
    if pipe is None:
        return
    for line in iter(pipe.readline, b""):
        bucket.append(line.decode("utf-8", "replace").strip())
        if len(bucket) > 12:
            del bucket[:-12]


def _stable_chunks(folder: Path, seen: set[str]) -> list[Path]:
    files = sorted(folder.glob("c*.mp3"))
    if len(files) < 2:
        return []
    ready = []
    for path in files[:-1]:
        if path.name in seen or path.stat().st_size < 1000:
            continue
        ready.append(path)
    return ready


_listener: DebateListener | None = None


def get_listener() -> DebateListener:
    global _listener
    if _listener is None:
        _listener = DebateListener()
    return _listener


def running_flag() -> bool:
    thread = get_listener().audio_thread
    alive = bool(thread and thread.is_alive() and not get_listener().audio_stop.is_set())
    if not alive:
        with session() as db:
            state = db.get(RunState, 1)
            if state and state.running:
                state.running = 0
                state.updated_at = utcnow()
                db.commit()
    return alive


def chunk_dir_override(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    get_listener().chunk_dir = Path(path)
