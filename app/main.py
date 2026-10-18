import hashlib
import hmac
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db import Claim, RunState, Segment, claim_dict, init_db, ping, session
from app.listener import (
    PRESETS,
    cookies_loaded,
    enqueue_manual,
    get_listener,
    resolve_stream,
    running_flag,
)
from app.settings import settings

sessions: set[str] = set()
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
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
    return {"ok": True}


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
    return {"ok": True}


@app.get("/api/estado")
def estado(request: Request) -> dict:
    authorized(request)
    running_flag()
    with session() as db:
        state = db.get(RunState, 1)
        segments = list(db.scalars(select(Segment).order_by(Segment.id.desc()).limit(80)))
        claims = list(db.scalars(select(Claim).order_by(Claim.id.desc()).limit(40)))
    return {
        "running": bool(state.running) if state else False,
        "youtube_url": state.youtube_url if state else settings.youtube_default,
        "last_error": state.last_error if state else "",
        "cookies_loaded": cookies_loaded(),
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


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
