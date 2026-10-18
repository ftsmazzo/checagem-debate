"""Cliente do MCP Inteligência Eleitoral (somente leitura, rápido)."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from app.settings import settings

_ID = 0


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


def _rpc(method: str, params: dict | None = None, timeout: float = 20) -> dict:
    body: dict[str, Any] = {"jsonrpc": "2.0", "id": _next_id(), "method": method}
    if params is not None:
        body["params"] = params
    with httpx.Client(timeout=timeout) as client:
        response = client.post(settings.ie_mcp_url, headers=_headers(), json=body)
        response.raise_for_status()
        payload = response.json()
    if payload.get("error"):
        raise RuntimeError(str(payload["error"])[:400])
    return payload.get("result") or {}


def _ensure_session() -> None:
    _rpc(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "checagem-debate", "version": "1.0"},
        },
        timeout=12,
    )
    try:
        with httpx.Client(timeout=8) as client:
            client.post(
                settings.ie_mcp_url,
                headers=_headers(),
                json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            )
    except Exception:
        pass


def call_tool(name: str, arguments: dict, timeout: float = 18) -> Any:
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


def _safe(name: str, arguments: dict) -> dict:
    try:
        data = call_tool(name, arguments)
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
    """Puxa só o essencial do acervo IE, com orçamento curto."""
    if not enabled():
        return {"enabled": False, "itens": []}

    query = _topic(f"{claim} {quote}")
    jobs = [
        ("fato_fake", {"query": query, "limite": 4}),
        (
            "acervo_nacional",
            {
                "query": query,
                "nm_candidato": "Lula",
                "ano_eleicao": 2022,
                "limite": 3,
            },
        ),
    ]
    lower = query.lower()
    if any(word in lower for word in ("bolsa", "benefício", "beneficio", "auxílio", "auxilio")):
        jobs.append(("bolsa_familia", {}))
    if any(word in lower for word in ("voto", "urna", "eleito", "turno")):
        jobs.append(("votacao", {"ano": 2022, "cargo": "presidente", "turno": 2}))

    try:
        _ensure_session()
    except Exception as exc:
        return {
            "enabled": True,
            "itens": [],
            "aviso": f"IE indisponível agora: {exc}"[:200],
        }

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_safe, name, args): name for name, args in jobs[:4]
        }
        for future in as_completed(futures, timeout=22):
            try:
                results.append(future.result())
            except Exception:
                continue

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
        "fonte": "Inteligência Eleitoral MCP",
        "aviso": (
            "Cifra TSE/IBGE/gov do acervo IE conta como evidência. "
            "Texto de estratégia/plano da campanha Flávio é só referência narrativa."
        ),
        "itens": useful[:6],
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
