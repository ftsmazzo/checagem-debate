from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.settings import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote: Mapped[str] = mapped_column(Text)
    normalized: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    speaker: Mapped[str] = mapped_column(String(32), default="lula")
    origin: Mapped[str] = mapped_column(String(16), default="live")
    status: Mapped[str] = mapped_column(String(32), default="pendente")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    missing: Mapped[str] = mapped_column(Text, default="")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RunState(Base):
    __tablename__ = "run_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    running: Mapped[int] = mapped_column(Integer, default=0)
    youtube_url: Mapped[str] = mapped_column(Text, default="")
    last_error: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


engine = None
Session = None


def init_db() -> None:
    global engine, Session
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL ausente")
    engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=5)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with Session() as session:
        state = session.get(RunState, 1)
        if state is None:
            session.add(RunState(id=1, running=0, youtube_url=settings.youtube_default))
            session.commit()


def session():
    if Session is None:
        raise RuntimeError("banco ainda não iniciado")
    return Session()


def ping() -> None:
    with session() as db:
        db.execute(select(1))


def claim_dict(row: Claim) -> dict:
    import json

    try:
        sources = json.loads(row.sources_json or "[]")
    except json.JSONDecodeError:
        sources = []
    return {
        "id": row.id,
        "quote": row.quote,
        "normalized": row.normalized,
        "speaker": row.speaker,
        "origin": row.origin,
        "status": row.status,
        "confidence": row.confidence,
        "summary": row.summary,
        "missing": row.missing,
        "sources": sources,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }
