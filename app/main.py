import hashlib
import threading
import hmac
import re
import secrets
import unicodedata
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

from app.db import (
    FIRST_DEBATE_SLUG,
    SCORE_BASE,
    SCORE_SPEAKERS,
    Claim,
    Debate,
    RunState,
    Segment,
    claim_dict,
    init_db,
    mentira_percent,
    ping,
    session,
    utcnow,
)
from app.listener import (
    PRESETS,
    collapse_pending_queue,
    cookies_loaded,
    enqueue_manual,
    get_listener,
    resolve_stream,
    running_flag,
)
from app import ie_mcp
from app.transcript import group_turns

sessions: set[str] = set()
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    collapse_pending_queue()
    threading.Thread(target=ie_mcp.probe, name="ie-probe", daemon=True).start()
    yield


app = FastAPI(title="Checagem do debate", lifespan=lifespan)


def _password_ok(given: str) -> bool:
    expected = settings.app_password
    if not expected or not given:
        return False
    return hmac.compare_digest(
        hashlib.sha256(given.encode()).digest(),
        hashlib.sha256(expected.encode()).digest(),
    )


def authorized(request: Request) -> None:
    token = request.cookies.get("sessao", "")
    if token not in sessions:
        raise HTTPException(status_code=401, detail="faça login")


class LoginBody(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class StartBody(BaseModel):
    youtube_url: str = Field(default="", max_length=400)
    gravar: bool = True


class ManualBody(BaseModel):
    text: str = Field(min_length=12, max_length=4000)
    speaker: str = Field(default="avulsa", max_length=16)


class DebateBody(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    slug: str = Field(default="", max_length=80)


SPEAKER_LABEL = {"lula": "Lula", "flavio": "Flávio Bolsonaro"}
RESOLVED = ("sustentado", "contradito", "exagerado", "sem_evidencia", "inconclusivo")


@app.get("/health")
def health() -> dict:
    ping()
    key = settings.openrouter_key
    openrouter = {"key_len": len(key), "key_suffix": key[-4:] if len(key) >= 4 else ""}
    if key:
        try:
            import httpx

            response = httpx.get(
                "https://openrouter.ai/api/v1/auth/key",
                headers={"Authorization": f"Bearer {key}"},
                timeout=15,
            )
            openrouter["auth_status"] = response.status_code
            if response.status_code == 200:
                openrouter["auth_ok"] = True
            else:
                openrouter["auth_ok"] = False
                openrouter["auth_detail"] = (response.text or "")[:120]
        except Exception as exc:
            openrouter["auth_ok"] = False
            openrouter["auth_detail"] = str(exc)[:120]
    else:
        openrouter["auth_ok"] = False
        openrouter["auth_detail"] = "chave ausente"
    return {"ok": True, "openrouter": openrouter, "fact_model": settings.fact_model}


@app.post("/api/login")
def login(body: LoginBody, response: Response) -> dict:
    if not _password_ok(body.password):
        raise HTTPException(status_code=401, detail="senha incorreta")
    token = secrets.token_urlsafe(32)
    sessions.add(token)
    response.set_cookie(
        "sessao",
        token,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=60 * 60 * 18,
    )
    # Não bloqueia o login se o checker estiver ocupado; workers sobem no iniciar/checar.
    try:
        get_listener().ensure_checker()
    except Exception:
        pass
    return {"ok": True}


@app.get("/api/estado")
def estado(request: Request) -> dict:
    authorized(request)
    running_flag()
    with session() as db:
        state = db.get(RunState, 1)
        segments_total = int(db.scalar(select(func.count()).select_from(Segment)) or 0)
        recent = list(db.scalars(select(Segment).order_by(Segment.id.desc()).limit(240)))
        recent.reverse()
        segments = list(
            reversed(
                group_turns(
                    [
                        {"id": row.id, "text": row.text, "created_at": row.created_at}
                        for row in recent
                    ]
                )[-24:]
            )
        )
        # Resolvidas primeiro (o usuário precisa ver o veredito), depois a fila.
        done = list(
            db.scalars(
                select(Claim)
                .where(
                    Claim.status.in_(
                        (
                            "sustentado",
                            "contradito",
                            "exagerado",
                            "sem_evidencia",
                            "inconclusivo",
                        )
                    )
                )
                .order_by(Claim.id.desc())
                .limit(30)
            )
        )
        queue = list(
            db.scalars(
                select(Claim)
                .where(Claim.status.in_(("pendente", "processando")))
                .order_by(Claim.id.desc())
                .limit(12)
            )
        )
        errors = list(
            db.scalars(
                select(Claim).where(Claim.status == "erro").order_by(Claim.id.desc()).limit(5)
            )
        )
        claims = done + queue + errors
        manual_n = int(
            db.scalar(
                select(func.count())
                .select_from(Claim)
                .where(Claim.status.in_(("pendente", "processando")), Claim.origin == "manual")
            )
            or 0
        )
        live_n = int(
            db.scalar(
                select(func.count())
                .select_from(Claim)
                .where(Claim.status.in_(("pendente", "processando")), Claim.origin != "manual")
            )
            or 0
        )
        active = _debate_brief(db, state.active_debate_id if state else None)
        archive = db.scalars(select(Debate).where(Debate.slug == FIRST_DEBATE_SLUG)).first()
        archive_segments = 0
        archive_claims = 0
        if archive is not None:
            archive_segments = int(
                db.scalar(
                    select(func.count()).select_from(Segment).where(Segment.debate_id == archive.id)
                )
                or 0
            )
            archive_claims = int(
                db.scalar(
                    select(func.count()).select_from(Claim).where(Claim.debate_id == archive.id)
                )
                or 0
            )
    return {
        "running": bool(state.running) if state else False,
        "youtube_url": state.youtube_url if state else settings.youtube_default,
        "last_error": state.last_error if state else "",
        "cookies_loaded": cookies_loaded(),
        "ie_mcp": ie_mcp.snapshot(),
        "queue": {
            "done": len(done),
            "pending": len(queue),
            "erro": len(errors),
            "manuais": manual_n,
            "ao_vivo": live_n,
        },
        "segments_total": segments_total,
        "persist": get_listener().persist,
        "ephemeral": get_listener().preview(),
        "active_debate": active,
        "archive": None
        if archive is None
        else {
            "slug": archive.slug,
            "title": archive.title,
            "held_on": archive.held_on.isoformat() if archive.held_on else "",
            "segments": archive_segments,
            "claims": archive_claims,
        },
        "presets": {
            "bandnews_sp": PRESETS["bandnews_sp"],
        },
        "segments": [
            {
                "id": row["id"],
                "text": row["text"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                "parts": row["parts"],
            }
            for row in segments
        ],
        "claims": [claim_dict(row) for row in claims],
    }


@app.post("/api/iniciar")
def iniciar(body: StartBody, request: Request) -> dict:
    authorized(request)
    try:
        url = resolve_stream(body.youtube_url or settings.youtube_default)
        get_listener().start(url, persist=body.gravar)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/parar")
def parar(request: Request) -> dict:
    authorized(request)
    get_listener().halt()
    return {"ok": True}


@app.post("/api/checar")
def checar(body: ManualBody, request: Request) -> dict:
    authorized(request)
    try:
        claim_id = enqueue_manual(body.text, speaker=body.speaker)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": claim_id}


@app.post("/api/zerar")
def zerar(request: Request) -> dict:
    """Limpa só a fila de checagens. A transcrição nunca é apagada daqui."""
    authorized(request)
    get_listener().halt()
    with session() as db:
        db.execute(
            delete(Claim).where(Claim.status.in_(("pendente", "processando", "erro")))
        )
        state = db.get(RunState, 1)
        if state:
            state.running = 0
            state.last_error = ""
            state.youtube_url = settings.youtube_default
            state.updated_at = utcnow()
        db.commit()
    return {"ok": True, "segments_kept": True}


@app.get("/api/transcricao")
def transcricao(
    request: Request,
    download: bool = Query(default=False),
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=5000, ge=1, le=20000),
):
    """Recupera a transcrição completa gravada no banco (ordem cronológica)."""
    authorized(request)
    with session() as db:
        total = int(db.scalar(select(func.count()).select_from(Segment)) or 0)
        query = select(Segment).order_by(Segment.id.asc()).limit(limit)
        if after_id:
            query = (
                select(Segment)
                .where(Segment.id > after_id)
                .order_by(Segment.id.asc())
                .limit(limit)
            )
        rows = list(db.scalars(query))
    turns = group_turns(
        [
            {"id": row.id, "text": row.text, "created_at": row.created_at}
            for row in rows
        ]
    )
    payload = {
        "total": total,
        "count": len(rows),
        "turns": len(turns),
        "next_after_id": rows[-1].id if rows else after_id,
        "segments": [
            {
                "id": turn["id"],
                "text": turn["text"],
                "created_at": turn["created_at"].isoformat() if turn["created_at"] else "",
                "parts": turn["parts"],
            }
            for turn in turns
        ],
        "text": "\n\n".join(turn["text"] for turn in turns),
    }
    if download:
        body = "\n\n".join(
            f"[{turn['created_at'].isoformat() if turn['created_at'] else ''}] {turn['text']}"
            for turn in turns
        )
        return PlainTextResponse(
            body or "(transcrição vazia)",
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="transcricao-debate.txt"'
            },
        )
    return payload


@app.post("/api/reprocessar")
def reprocessar(request: Request) -> dict:
    authorized(request)
    return collapse_pending_queue()


@app.post("/api/checar-agora")
def checar_agora(request: Request) -> dict:
    """Processa a pendente mais nova na hora."""
    authorized(request)
    from app.factcheck import verify_claim

    with session() as db:
        row = db.scalars(
            select(Claim)
            .where(Claim.status == "pendente", Claim.origin == "manual")
            .order_by(Claim.id.asc())
            .limit(1)
        ).first()
        if row is None:
            row = db.scalars(
                select(Claim)
                .where(Claim.status == "pendente")
                .order_by(Claim.id.desc())
                .limit(1)
            ).first()
        if row is None:
            return {"ok": True, "done": False, "message": "fila vazia"}
        claim_id = row.id
        quote = row.quote
        normalized = row.normalized
        row.status = "processando"
        db.commit()
    try:
        verdict = verify_claim(quote, normalized, fast=True)
        status = verdict["status"]
        summary = verdict["summary"]
        missing = verdict["missing"]
        confidence = verdict["confidence"]
        sources = __import__("json").dumps(verdict["sources"], ensure_ascii=False)
    except Exception as exc:
        status = "erro"
        summary = str(exc)[:800]
        missing = ""
        confidence = 0
        sources = "[]"
    with session() as db:
        current = db.get(Claim, claim_id)
        if current:
            current.status = status
            current.summary = summary
            current.missing = missing
            current.confidence = confidence
            current.sources_json = sources
            db.commit()
    get_listener().ensure_checker()
    return {"ok": True, "done": True, "id": claim_id, "status": status, "summary": summary[:240]}


def _slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")
    return (text or "debate")[:80]


def _debate_brief(db, debate_id: int | None) -> dict | None:
    if not debate_id:
        return None
    row = db.get(Debate, debate_id)
    if row is None:
        return None
    return {
        "id": row.id,
        "slug": row.slug,
        "title": row.title,
        "held_on": row.held_on.isoformat() if row.held_on else "",
    }


def _debate_public(row: Debate, active_id: int | None) -> dict:
    return {
        "id": row.id,
        "slug": row.slug,
        "title": row.title,
        "held_on": row.held_on.isoformat() if row.held_on else "",
        "active": row.id == active_id,
    }


@app.get("/api/debates")
def listar_debates(request: Request) -> dict:
    authorized(request)
    with session() as db:
        state = db.get(RunState, 1)
        active_id = state.active_debate_id if state else None
        rows = list(db.scalars(select(Debate).order_by(Debate.id.desc())))
        return {"debates": [_debate_public(row, active_id) for row in rows]}


@app.post("/api/debates")
def criar_debate(body: DebateBody, request: Request) -> dict:
    authorized(request)
    slug = _slugify(body.slug or body.title)
    with session() as db:
        if db.scalars(select(Debate).where(Debate.slug == slug)).first():
            raise HTTPException(status_code=400, detail="já existe um debate com esse nome")
        row = Debate(slug=slug, title=body.title.strip(), held_on=date.today(), rules="")
        db.add(row)
        db.flush()
        state = db.get(RunState, 1)
        if state:
            state.active_debate_id = row.id
            state.updated_at = utcnow()
        db.commit()
        return _debate_public(row, row.id)


@app.get("/api/debates/{slug}/placar")
def placar(slug: str, request: Request) -> dict:
    authorized(request)
    with session() as db:
        debate = db.scalars(select(Debate).where(Debate.slug == slug)).first()
        if debate is None:
            raise HTTPException(status_code=404, detail="debate não encontrado")
        cards = []
        for speaker in SCORE_SPEAKERS:
            grouped = db.execute(
                select(Claim.status, func.count())
                .where(
                    Claim.debate_id == debate.id,
                    Claim.speaker == speaker,
                    Claim.status.in_(RESOLVED),
                )
                .group_by(Claim.status)
            ).all()
            counts = {status: 0 for status in RESOLVED}
            for status, total in grouped:
                if status in counts:
                    counts[status] = int(total)
            rows = list(
                db.scalars(
                    select(Claim)
                    .where(
                        Claim.debate_id == debate.id,
                        Claim.speaker == speaker,
                        Claim.status.in_(RESOLVED),
                    )
                    .order_by(Claim.id.desc())
                    .limit(40)
                )
            )
            shown = [claim_dict(row) for row in rows]
            cards.append(
                {
                    "speaker": speaker,
                    "nome": SPEAKER_LABEL[speaker],
                    "counts": counts,
                    "base": sum(counts[status] for status in SCORE_BASE),
                    "mentira_percent": mentira_percent(counts),
                    "claims": shown,
                }
            )
        return {
            "debate": {
                "slug": debate.slug,
                "title": debate.title,
                "held_on": debate.held_on.isoformat() if debate.held_on else "",
            },
            "candidates": cards,
            "formula": "contradito / (sustentado + contradito + exagerado)",
        }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(STATIC / "dashboard.html")


@app.get("/checar")
def checar_pagina() -> FileResponse:
    return FileResponse(STATIC / "checar.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
