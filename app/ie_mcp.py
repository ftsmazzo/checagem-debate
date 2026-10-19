"""Cliente do MCP Inteligência Eleitoral (somente leitura, com teto de tempo)."""

from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.settings import settings

_ID = 0
_LOCK = threading.Lock()
_SESSION_READY = False
_OK = False
_DETAIL = "ainda não testada"
_CHECKED_AT = ""
BUDGET_SECONDS = 8.0
TOOL_TIMEOUT = 4.0


def _next_id() -> int:
    global _ID
    _ID += 1
    return _ID


def enabled() -> bool:
    return bool(settings.ie_mcp_url and settings.ie_mcp_token)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.ie_mcp_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def snapshot() -> dict:
    with _LOCK:
        return {
            "enabled": enabled(),
            "ok": _OK,
            "detail": _DETAIL,
            "checked_at": _CHECKED_AT,
        }


def _mark(ok: bool, detail: str) -> None:
    global _OK, _DETAIL, _CHECKED_AT
    with _LOCK:
        _OK = ok
        _DETAIL = detail[:180]
        _CHECKED_AT = datetime.now(timezone.utc).isoformat()


def _rpc(method: str, params: dict | None = None, timeout: float = 4) -> dict:
    body: dict[str, Any] = {"jsonrpc": "2.0", "id": _next_id(), "method": method}
    if params is not None:
        body["params"] = params
    limits = httpx.Timeout(timeout, connect=2.0)
    with httpx.Client(timeout=limits) as client:
        response = client.post(settings.ie_mcp_url, headers=_headers(), json=body)
        response.raise_for_status()
        payload = response.json()
    if payload.get("error"):
        raise RuntimeError(str(payload["error"])[:400])
    return payload.get("result") or {}


def _ensure_session() -> None:
    global _SESSION_READY
    with _LOCK:
        ready = _SESSION_READY
    if ready:
        return
    _rpc(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "checagem-debate", "version": "1.0"},
        },
        timeout=3,
    )
    try:
        limits = httpx.Timeout(2.0, connect=2.0)
        with httpx.Client(timeout=limits) as client:
            client.post(
                settings.ie_mcp_url,
                headers=_headers(),
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
    except Exception:
        pass
    with _LOCK:
        _SESSION_READY = True


def probe() -> dict:
    """Testa a IE uma vez, sem segurar a fila se o servidor não responder."""
    if not enabled():
        _mark(False, "não configurada")
        return snapshot()
    try:
        _ensure_session()
        _mark(True, "ligada")
    except Exception as exc:
        global _SESSION_READY
        with _LOCK:
            _SESSION_READY = False
        _mark(False, f"sem resposta: {exc}"[:180])
    return snapshot()


def call_tool(name: str, arguments: dict, timeout: float = TOOL_TIMEOUT) -> Any:
    result = _rpc(
        "tools/call",
        {"name": name, "arguments": arguments},
        timeout=timeout,
    )
    chunks = []
    for item in result.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            chunks.append(str(item.get("text") or ""))
    raw = "\n".join(chunks).strip()
    if not raw:
        return {"status": "vazio"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "ok", "texto": raw[:4000]}


def _safe(name: str, arguments: dict, timeout: float = TOOL_TIMEOUT) -> dict:
    try:
        data = call_tool(name, arguments, timeout=timeout)
        if not isinstance(data, dict):
            return {"tool": name, "status": "ok", "dados": data}
        out = dict(data)
        out["tool"] = name
        return out
    except Exception as exc:
        return {"tool": name, "status": "erro", "mensagem": str(exc)[:240]}


def _topic(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned[:180]


def gather_context(quote: str, claim: str) -> dict:
    """Puxa só o essencial do acervo IE, em série e com teto duro de tempo."""
    if not enabled():
        return {"enabled": False, "itens": []}

    query = _topic(f"{claim} {quote}")
    jobs = [
        ("fato_fake", {"query": query, "limite": 3}),
        (
            "acervo_nacional",
            {
                "query": query,
                "nm_candidato": "Lula",
                "ano_eleicao": 2022,
                "limite": 2,
            },
        ),
    ]

    deadline = time.monotonic() + BUDGET_SECONDS
    try:
        _ensure_session()
        _mark(True, "ligada")
    except Exception as exc:
        global _SESSION_READY
        with _LOCK:
            _SESSION_READY = False
        _mark(False, f"sem resposta: {exc}"[:180])
        return {
            "enabled": True,
            "ok": False,
            "itens": [],
            "aviso": f"IE indisponível agora: {exc}"[:200],
        }

    # Uma ferramenta por vez, e para quando o teto de 8s acaba.
    results: list[dict] = []
    for name, args in jobs:
        left = deadline - time.monotonic()
        if left < 1.5:
            break
        results.append(_safe(name, args, timeout=min(TOOL_TIMEOUT, left)))

    useful = []
    for item in results:
        status = str(item.get("status") or "")
        if status in {"erro", "vazio"}:
            continue
        if item.get("itens") == [] and not item.get("linhas") and not item.get("texto"):
            continue
        useful.append(item)

    return {
        "enabled": True,
        "ok": True,
        "fonte": "Inteligência Eleitoral MCP",
        "aviso": (
            "Cifra TSE/IBGE/gov do acervo IE conta como evidência. "
            "Texto de estratégia/plano da campanha Flávio é só referência narrativa."
        ),
        "itens": useful[:4],
    }


def format_context(bundle: dict) -> str:
    if not bundle.get("enabled"):
        return ""
    if not bundle.get("itens"):
        return ""
    compact = {
        "aviso": bundle.get("aviso"),
        "itens": bundle.get("itens"),
    }
    text = json.dumps(compact, ensure_ascii=False)
    return "\n\nContexto Inteligência Eleitoral (MCP):\n" + text[:5000]
