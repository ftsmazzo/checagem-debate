from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, create_engine, inspect, select, text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.settings import settings

FIRST_DEBATE_SLUG = "2026-10-18-band"
SCORE_SPEAKERS = ("lula", "flavio")
SCORE_BASE = ("sustentado", "contradito", "exagerado")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Debate(Base):
    __tablename__ = "debates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    held_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    rules: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    debate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote: Mapped[str] = mapped_column(Text)
    normalized: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    speaker: Mapped[str] = mapped_column(String(32), default="lula")
    origin: Mapped[str] = mapped_column(String(16), default="live")
    debate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pendente")
    confidence: Mapped[float] = mapped_column(Float, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    missing: Mapped[str] = mapped_column(Text, default="")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    theme: Mapped[str] = mapped_column(String(40), default="")
    correction: Mapped[str] = mapped_column(Text, default="")
    listed: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CorrectionReport(Base):
    __tablename__ = "correction_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RunState(Base):
    __tablename__ = "run_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    running: Mapped[int] = mapped_column(Integer, default=0)
    youtube_url: Mapped[str] = mapped_column(Text, default="")
    last_error: Mapped[str] = mapped_column(Text, default="")
    active_debate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


engine = None
Session = None


def init_db() -> None:
    global engine, Session
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL ausente")
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    _add_missing_columns(engine)
    with Session() as db:
        state = db.get(RunState, 1)
        if state is None:
            db.add(RunState(id=1, running=0, youtube_url=settings.youtube_default))
            db.commit()
        _seed_first_debate(db)


def _add_missing_columns(bound) -> None:
    insp = inspect(bound)
    tables = set(insp.get_table_names())
    wanted = {
        "segments": [("debate_id", "INTEGER")],
        "claims": [
            ("debate_id", "INTEGER"),
            ("theme", "VARCHAR(40) DEFAULT ''"),
            ("correction", "TEXT DEFAULT ''"),
            ("listed", "INTEGER DEFAULT 1"),
        ],
        "run_state": [("active_debate_id", "INTEGER")],
    }
    alters: list[str] = []
    for table, columns in wanted.items():
        if table not in tables:
            continue
        names = {item["name"] for item in insp.get_columns(table)}
        for column, kind in columns:
            if column not in names:
                alters.append(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
    if not alters:
        return
    with bound.begin() as conn:
        for statement in alters:
            conn.execute(text(statement))


def _seed_first_debate(db) -> None:
    debate = db.scalars(select(Debate).where(Debate.slug == FIRST_DEBATE_SLUG)).first()
    created = debate is None
    if debate is None:
        debate = Debate(
            slug=FIRST_DEBATE_SLUG,
            title="Band — 18/10",
            held_on=date(2026, 10, 18),
            rules="Lula e Flávio Bolsonaro. Mediação de Adriana Araújo e Eduardo Oinegue.",
        )
        db.add(debate)
        db.flush()
    elif debate.title.startswith("Primeiro debate"):
        debate.title = "Band — 18/10"
    if created:
        db.execute(update(Segment).where(Segment.debate_id.is_(None)).values(debate_id=debate.id))
        db.execute(update(Claim).where(Claim.debate_id.is_(None)).values(debate_id=debate.id))
    state = db.get(RunState, 1)
    if state is not None and state.active_debate_id is None:
        state.active_debate_id = debate.id
    db.commit()


def mentira_percent(counts: dict) -> float | None:
    """contradito / (sustentado + contradito + exagerado). Sem essa base, não há percentual."""
    base = sum(int(counts.get(key) or 0) for key in SCORE_BASE)
    if base <= 0:
        return None
    return round(100 * int(counts.get("contradito") or 0) / base, 1)


def placar_resumo(counts: dict) -> dict:
    """Participação de falso ou distorcido entre os carimbos fechados.

    Promessa e carimbo em aberto ficam de fora do percentual.
    """
    from app.factcheck import CLOSED, OPEN

    closed = {key: int(counts.get(key) or 0) for key in CLOSED}
    classified = sum(closed.values())
    false_n = closed["contradito"] + closed["distorcido"]
    percent = None if classified <= 0 else int(false_n * 100 / classified + 0.5)
    return {
        "verdadeiras": closed["sustentado"],
        "ressalva": closed["sustentado_ressalva"],
        "parcial": closed["nao_e_bem_assim"],
        "exageradas": closed["exagerado"],
        "sem_provas": closed["sem_prova"],
        "distorcidas": closed["distorcido"],
        "falsas": closed["contradito"],
        "falsas_ou_distorcidas": false_n,
        "classificadas": classified,
        "sem_veredito": sum(int(counts.get(key) or 0) for key in OPEN),
        "promessas": int(counts.get("promessa") or 0),
        "percentual": percent,
    }


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
        "debate_id": row.debate_id,
        "status": row.status,
        "confidence": row.confidence,
        "summary": row.summary,
        "missing": row.missing,
        "sources": sources,
        "theme": getattr(row, "theme", "") or "",
        "correction": getattr(row, "correction", "") or "",
        "listed": int(getattr(row, "listed", 1) or 0),
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def store_verdict(row: Claim, verdict: dict) -> None:
    import json

    row.status = str(verdict.get("status") or "erro")[:32]
    row.summary = str(verdict.get("summary") or "")
    row.missing = str(verdict.get("missing") or "")
    row.confidence = float(verdict.get("confidence") or 0)
    row.sources_json = json.dumps(verdict.get("sources") or [], ensure_ascii=False)
    row.theme = str(verdict.get("theme") or "")[:40]
