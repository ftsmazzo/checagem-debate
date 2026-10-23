import base64
import hashlib
import json
import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.db import Claim, RunState, Segment, session, store_verdict, utcnow
from app.factcheck import extract_claims, verify_claim
from app.settings import settings

YOUTUBE_HOSTS = {"www.youtube.com", "youtube.com", "m.youtube.com", "youtu.be"}
STREAM_HOSTS = YOUTUBE_HOSTS | {
    "playerservices.streamtheworld.com",
    "live.streamtheworld.com",
}
PRESETS = {
    "bandnews_sp": (
        "https://playerservices.streamtheworld.com/api/livestream-redirect/"
        "BANDNEWSFM_SPAAC.m3u8?dist=bandsite"
    ),
    "cbn_sp": (
        "https://playerservices.streamtheworld.com/api/livestream-redirect/"
        "CBN_SPAAC.m3u8"
    ),
}
NOISE = (
    "obrigado por assistir",
    "legendas pela comunidade",
    "inscreva-se no canal",
    "amara.org",
)


def resolve_stream(url: str) -> str:
    cleaned = (url or "").strip()
    if cleaned in PRESETS:
        return PRESETS[cleaned]
    if cleaned.startswith("preset:"):
        key = cleaned.split(":", 1)[1]
        if key not in PRESETS:
            raise ValueError("fonte desconhecida")
        return PRESETS[key]
    parsed = urlparse(cleaned)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("use um link https")
    if "globo" in host:
        raise ValueError(
            "O GloboPlay não abre por link. Deixe o debate tocando e use Ouvir a aba do GloboPlay."
        )
    if host in STREAM_HOSTS or host.endswith(".streamtheworld.com") or cleaned.endswith(".m3u8") or ".m3u8?" in cleaned:
        return cleaned
    if host in YOUTUBE_HOSTS:
        return cleaned
    raise ValueError("use BandNews FM, um m3u8 ou um link do YouTube")


def assert_youtube(url: str) -> str:
    return resolve_stream(url)


def explain_audio_error(detail: str, has_cookies: bool = False) -> str:
    text = " ".join(detail.split())
    if "not a bot" in text or "Sign in to confirm" in text:
        if has_cookies:
            return (
                "O YouTube recusou o IP desta VPS. "
                "Troque a fonte para BandNews FM SP, que transmite o debate sem o bloqueio."
            )
        return (
            "O YouTube bloqueou o servidor. "
            "Use a fonte BandNews FM SP em vez do YouTube."
        )
    if "Invalid data found when processing input" in text:
        return "O áudio da live não chegou. " + text[-400:]
    return text[-500:]


def youtube_cookie_text(raw: str) -> str:
    text = (raw or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1]
    if "\n" not in text and "\\n" in text:
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t")
    kept = ["# Netscape HTTP Cookie File"]
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        domain = line.split("\t", 1)[0].lstrip(".").lower()
        if domain == "youtube.com" or domain.endswith(".youtube.com"):
            kept.append(line)
    if len(kept) == 1:
        return ""
    return "\n".join(kept) + "\n"


def cookie_args() -> list[str]:
    path = Path(settings.cookies_path or "/tmp/youtube-cookies.txt")
    filtered = youtube_cookie_text(settings.youtube_cookies)
    if filtered:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(filtered, encoding="utf-8")
        os.chmod(path, 0o600)
    if path.is_file() and "youtube.com" in path.read_text(encoding="utf-8", errors="ignore"):
        return ["--cookies", str(path)]
    return []


def cookies_loaded() -> bool:
    return bool(cookie_args())


def is_youtube(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in YOUTUBE_HOSTS


def _fingerprint(text: str) -> str:
    folded = " ".join(text.casefold().split())
    folded = re.sub(r"[^a-z0-9à-ü\s]", "", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    # Agrupa paráfrases quase iguais (mesma notícia repetida no áudio).
    key = folded[:160]
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


CHECK_WORKERS = 3


class DebateListener:
    def __init__(self) -> None:
        self.audio_stop = threading.Event()
        self.audio_thread: threading.Thread | None = None
        self.check_threads: list[threading.Thread] = []
        self.procs: list[subprocess.Popen] = []
        self.lock = threading.Lock()
        self.context = ""
        self.chunk_dir = Path("/tmp/debate-chunks")
        self.persist = True
        self.pending_text = ""
        self.ephemeral: list[dict] = []
        self._ephemeral_seq = 0
        self.browser_on = False
        self.browser_thread: threading.Thread | None = None
        self.browser_queue: queue.Queue[Path] = queue.Queue(maxsize=8)

    def start(self, url: str, persist: bool = True) -> None:
        url = resolve_stream(url)
        if not settings.openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY ausente no serviço")
        with self.lock:
            if self.browser_on:
                raise RuntimeError("Pare a escuta da aba antes de ouvir um link.")
            alive = self.audio_thread and self.audio_thread.is_alive()
            if alive and self.persist != persist:
                raise RuntimeError("Pare a escuta antes de trocar entre gravar e só ouvir.")
            if alive:
                return
            self.persist = persist
            self.pending_text = ""
            if not persist:
                self.ephemeral = []
            self.audio_stop.clear()
            self._set_state(True, url, "")
            self.audio_thread = threading.Thread(target=self._audio_loop, args=(url,), daemon=True)
            self.audio_thread.start()
        # Fora do lock: ensure_checker também usa self.lock (Lock não é reentrante).
        self.ensure_checker()

    def begin_browser(self, persist: bool = True) -> None:
        if not settings.openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY ausente no serviço")
        with self.lock:
            if self.audio_thread and self.audio_thread.is_alive():
                raise RuntimeError("Pare a escuta do link antes de ouvir a aba.")
            if self.browser_on and self.browser_thread and self.browser_thread.is_alive():
                self.persist = persist
                return
            self.persist = persist
            self.pending_text = ""
            if not persist:
                self.ephemeral = []
            self.browser_on = True
            self.audio_stop.clear()
            self.browser_thread = threading.Thread(target=self._browser_loop, daemon=True)
            self.browser_thread.start()
        self._set_state(True, None, "")
        self.ensure_checker()

    def ingest_browser(self, data: bytes) -> None:
        if not self.browser_on:
            raise RuntimeError("A escuta da aba não está ligada.")
        self.chunk_dir.mkdir(parents=True, exist_ok=True)
        path = self.chunk_dir / f"aba-{time.time_ns()}.webm"
        path.write_bytes(data)
        try:
            self.browser_queue.put_nowait(path)
        except queue.Full:
            path.unlink(missing_ok=True)
            raise RuntimeError("A transcrição da aba está atrasada. Esse trecho ficou de fora.")

    def halt(self) -> None:
        self.audio_stop.set()
        self.browser_on = False
        self._kill()
        self._flush_turn()
        self._set_state(False, None, "")

    def _browser_loop(self) -> None:
        while not self.audio_stop.is_set():
            try:
                path = self.browser_queue.get(timeout=0.4)
            except queue.Empty:
                continue
            mp3 = path.with_suffix(".mp3")
            try:
                _webm_to_mp3(path, mp3)
                self._transcribe_file(mp3)
            except Exception as exc:
                self._set_state(None, None, f"aba: {exc}")
                mp3.unlink(missing_ok=True)
            finally:
                path.unlink(missing_ok=True)

    def preview(self) -> list[dict]:
        with self.lock:
            return list(self.ephemeral)

    def ensure_checker(self) -> None:
        with self.lock:
            self.check_threads = [t for t in self.check_threads if t.is_alive()]
            while len(self.check_threads) < CHECK_WORKERS:
                thread = threading.Thread(target=self._check_loop, daemon=True)
                thread.start()
                self.check_threads.append(thread)

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
                if is_youtube(url):
                    self._run_youtube(url)
                else:
                    self._run_hls(url)
            except Exception as exc:
                self._set_state(None, None, f"áudio: {exc}")
            if self.audio_stop.wait(8):
                break
        self._set_state(False, None, None)

    def _run_hls(self, url: str) -> None:
        for old in self.chunk_dir.glob("c*.mp3"):
            old.unlink(missing_ok=True)
        pattern = str(self.chunk_dir / "c%05d.mp3")
        ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-reconnect",
                "1",
                "-reconnect_streamed",
                "1",
                "-reconnect_delay_max",
                "5",
                "-i",
                url,
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
            stderr=subprocess.PIPE,
        )
        self.procs = [ffmpeg]
        errors: list[str] = []
        threading.Thread(target=_drain, args=(ffmpeg.stderr, errors), daemon=True).start()
        self._consume_chunks(ffmpeg, errors, youtube=False)

    def _run_youtube(self, url: str) -> None:
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
                "youtube:player_client=default,web",
                *cookie_args(),
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
        self._consume_chunks(ffmpeg, errors, youtube=True, ytdlp=ytdlp)

    def _consume_chunks(
        self,
        ffmpeg: subprocess.Popen,
        errors: list[str],
        youtube: bool,
        ytdlp: subprocess.Popen | None = None,
    ) -> None:
        seen: set[str] = set()
        while not self.audio_stop.is_set():
            ended = ffmpeg.poll() is not None
            if ytdlp is not None:
                ended = ended and ytdlp.poll() is not None
            if ended:
                raw = " ".join(errors) or f"processo saiu com código {ffmpeg.returncode}"
                detail = explain_audio_error(raw, has_cookies=bool(cookie_args())) if youtube else raw[-500:]
                self._set_state(None, None, detail)
                if youtube and "BandNews" in detail:
                    self.audio_stop.set()
                return
            for path in _stable_chunks(self.chunk_dir, seen):
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
        with self.lock:
            self.pending_text = f"{self.pending_text} {text}".strip()
            size = len(self.pending_text)
            ended = self.pending_text.endswith((".", "!", "?"))
            ready = size >= 700 or (size >= 400 and ended)
        if ready:
            self._flush_turn()

    def _flush_turn(self) -> None:
        with self.lock:
            text = " ".join(self.pending_text.split())
            self.pending_text = ""
        if len(text) < 8:
            return
        if not self.persist:
            with self.lock:
                self._ephemeral_seq += 1
                self.ephemeral.insert(
                    0,
                    {
                        "id": self._ephemeral_seq,
                        "text": text,
                        "created_at": utcnow().isoformat(),
                    },
                )
                del self.ephemeral[40:]
            self.context = (self.context + "\n" + text)[-8000:]
            return
        with session() as db:
            state = db.get(RunState, 1)
            db.add(Segment(text=text, debate_id=state.active_debate_id if state else None))
            db.commit()
        self.context = (self.context + "\n" + text)[-8000:]
        self._enqueue_from_context()

    def _enqueue_from_context(self) -> None:
        with session() as db:
            pending_n = db.scalar(
                select(func.count()).select_from(Claim).where(
                    Claim.status.in_(("pendente", "processando"))
                )
            ) or 0
            if pending_n >= 12:
                # Não entope a fila enquanto as checagens atuais não terminam.
                return
        try:
            claims = extract_claims(self.context)
        except Exception as exc:
            self._set_state(None, None, f"extração: {exc}")
            return
        with session() as db:
            state = db.get(RunState, 1)
            debate_id = state.active_debate_id if state else None
            for item in claims:
                row = Claim(
                    quote=item["quote"],
                    normalized=item["claim"],
                    fingerprint=_fingerprint(item["speaker"] + ":" + item["claim"]),
                    speaker=item["speaker"],
                    origin="live",
                    debate_id=debate_id,
                    status="pendente",
                )
                db.add(row)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()

    def _claim_next(self) -> tuple[int, str, str, bool] | None:
        """Pega a pendente mais nova sem colidir com outro worker."""
        with session() as db:
            manual = db.scalars(
                select(Claim)
                .where(Claim.status == "pendente", Claim.origin == "manual")
                .order_by(Claim.id.asc())
                .limit(1)
            ).first()
            live = None
            if manual is None:
                live = db.scalars(
                    select(Claim)
                    .where(Claim.status == "pendente", Claim.origin != "manual")
                    .order_by(Claim.id.desc())
                    .limit(1)
                ).first()
            row = manual or live
            if row is None:
                return None
            pending_n = db.scalar(
                select(func.count()).select_from(Claim).where(
                    Claim.status.in_(("pendente", "processando"))
                )
            ) or 0
            claim_id = row.id
            quote = row.quote
            normalized = row.normalized
            # Update otimista: se outro worker já pegou, rowcount=0.
            result = db.execute(
                update(Claim)
                .where(Claim.id == claim_id, Claim.status == "pendente")
                .values(status="processando")
            )
            db.commit()
            if result.rowcount != 1:
                return None
            fast = pending_n >= 4
            return claim_id, quote, normalized, fast

    def _check_loop(self) -> None:
        while True:
            claimed = None
            try:
                claimed = self._claim_next()
            except Exception as exc:
                self._set_state(None, None, f"fila: {exc}")
                time.sleep(2)
                continue
            if claimed is None:
                time.sleep(1)
                continue
            claim_id, quote, normalized, fast = claimed
            try:
                verdict = verify_claim(quote, normalized, fast=fast)
            except Exception as exc:
                verdict = {
                    "status": "erro",
                    "summary": str(exc)[:800],
                    "missing": "",
                    "confidence": 0,
                    "sources": [],
                    "theme": "",
                }
                self._set_state(None, None, f"checagem: {exc}")
            with session() as db:
                current = db.get(Claim, claim_id)
                if current and current.status in {"pendente", "processando"}:
                    store_verdict(current, verdict)
                    db.commit()


def enqueue_manual(text: str, speaker: str = "avulsa") -> int:
    cleaned = " ".join(text.split())
    if len(cleaned) < 12:
        raise ValueError("escreva a frase completa")
    if len(cleaned) > 4000:
        cleaned = cleaned[:4000]
    who = (speaker or "avulsa").strip().lower()
    if who not in {"lula", "flavio", "avulsa"}:
        raise ValueError("pessoa desconhecida")
    fingerprint = _fingerprint(f"manual:{who}:{cleaned}")
    with session() as db:
        row = Claim(
            quote=cleaned[:500],
            normalized=cleaned[:400],
            fingerprint=fingerprint,
            speaker=who,
            origin="manual",
            debate_id=None,
            status="pendente",
        )
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.scalars(select(Claim).where(Claim.fingerprint == fingerprint)).first()
            return existing.id if existing else 0
        claim_id = row.id
    _ensure_checker()
    return claim_id


def _ensure_checker() -> None:
    get_listener().ensure_checker()


def collapse_pending_queue() -> dict:
    """Libera a fila: descarta paráfrases repetidas e mantém as mais novas."""
    kept = 0
    dropped = 0
    with session() as db:
        rows = list(
            db.scalars(
                select(Claim).where(Claim.status == "pendente").order_by(Claim.id.desc())
            )
        )
        manuals = [row for row in rows if row.origin == "manual"]
        live_rows = [row for row in rows if row.origin != "manual"]
        seen: set[str] = set()
        for row in manuals:
            kept += 1
        for row in live_rows:
            words = re.findall(r"[a-z0-9à-ü]{4,}", (row.normalized or "").casefold())
            key = " ".join(sorted(set(words))[:10])
            if key and key in seen:
                row.status = "erro"
                row.summary = "duplicata na fila — mesma afirmação já estava em checagem"
                row.confidence = 0
                dropped += 1
                continue
            if key:
                seen.add(key)
            if kept >= len(manuals) + 8:
                row.status = "erro"
                row.summary = "fila limpa — prioridade para as frases mais recentes"
                row.confidence = 0
                dropped += 1
                continue
            kept += 1
        state = db.get(RunState, 1)
        if state:
            state.last_error = ""
            state.updated_at = utcnow()
        db.commit()
    _ensure_checker()
    return {"kept": kept, "dropped": dropped}


def _webm_to_mp3(src: Path, dest: Path) -> None:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "64k",
            str(dest),
        ],
        capture_output=True,
        timeout=40,
    )
    if result.returncode != 0 or not dest.is_file() or dest.stat().st_size < 400:
        detail = result.stderr.decode("utf-8", "replace")[-300:]
        raise RuntimeError(detail or "ffmpeg não leu o áudio da aba")


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
