import hashlib
import hmac
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.db import Claim, RunState, Segment, claim_dict, init_db, ping, session, utcnow
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
from app.settings import settings

sessions: set[str] = set()
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    collapse_pending_queue()
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


class ManualBody(BaseModel):
    text: str = Field(min_length=12, max_length=4000)


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
    get_listener().ensure_checker()
    return {"ok": True}


@app.get("/api/estado")
def estado(request: Request) -> dict:
    authorized(request)
    running_flag()
    with session() as db:
        state = db.get(RunState, 1)
        segments = list(db.scalars(select(Segment).order_by(Segment.id.desc()).limit(80)))
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
    return {
        "running": bool(state.running) if state else False,
        "youtube_url": state.youtube_url if state else settings.youtube_default,
        "last_error": state.last_error if state else "",
        "cookies_loaded": cookies_loaded(),
        "ie_mcp": ie_mcp.enabled(),
        "queue": {"done": len(done), "pending": len(queue), "erro": len(errors)},
        "presets": {
            "bandnews_sp": PRESETS["bandnews_sp"],
        },
        "segments": [
            {
                "id": row.id,
                "text": row.text,
                "created_at": row.created_at.isoformat() if row.created_at else "",
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
        get_listener().start(url)
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
        claim_id = enqueue_manual(body.text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": claim_id}


@app.post("/api/zerar")
def zerar(request: Request) -> dict:
    authorized(request)
    get_listener().halt()
    with session() as db:
        db.execute(delete(Claim))
        db.execute(delete(Segment))
        state = db.get(RunState, 1)
        if state:
            state.running = 0
            state.last_error = ""
            state.youtube_url = settings.youtube_default
            state.updated_at = utcnow()
        db.commit()
    return {"ok": True}


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
        verdict = verify_claim(quote, normalized)
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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
