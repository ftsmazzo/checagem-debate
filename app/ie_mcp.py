"""Cliente do MCP Inteligência Eleitoral (somente leitura)."""

from __future__ import annotations

import json
import re
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


def _rpc(method: str, params: dict | None = None, timeout: float = 45) -> dict:
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
        timeout=30,
    )
    try:
        body = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        with httpx.Client(timeout=15) as client:
            client.post(settings.ie_mcp_url, headers=_headers(), json=body)
    except Exception:
        pass


def call_tool(name: str, arguments: dict, timeout: float = 45) -> Any:
    _ensure_session()
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
    return cleaned[:220]


def gather_context(quote: str, claim: str) -> dict:
    """Puxa fato/fake, plano, cifras e urna relevantes para a frase."""
    if not enabled():
        return {"enabled": False, "itens": []}

    query = _topic(f"{claim} {quote}")
    results: list[dict] = []

    results.append(_safe("fato_fake", {"query": query, "limite": 6}))
    results.append(
        _safe(
            "acervo_nacional",
            {
                "query": query,
                "nm_candidato": "Lula",
                "ano_eleicao": 2022,
                "limite": 4,
            },
        )
    )
    results.append(_safe("plano_governo", {"query": query, "limite": 3}))

    lower = query.lower()
    if any(word in lower for word in ("bolsa", "benefício", "beneficio", "auxílio", "auxilio")):
        results.append(_safe("bolsa_familia", {}))
        results.append(_safe("cadunico", {}))
    if any(word in lower for word in ("pib", "economia", "renda")):
        results.append(_safe("pib", {}))
    if any(word in lower for word in ("população", "populacao", "habitante", "morador")):
        results.append(_safe("populacao", {}))
    if any(word in lower for word in ("voto", "urna", "eleito", "turno", "percentual")):
        results.append(
            _safe(
                "votacao",
                {"ano": 2022, "cargo": "presidente", "turno": 2},
            )
        )
    if any(word in lower for word in ("estratégia", "estrategia", "narrativa", "ataque")):
        results.append(_safe("estrategias", {"query": query, "limite": 4}))

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
            "Material de campanha e cifras oficiais do acervo IE. "
            "Cifra TSE/IBGE/gov vale como evidência. "
            "Texto de estratégia ou plano da campanha Flávio é referência narrativa, "
            "não prova independente sobre Lula."
        ),
        "itens": useful[:8],
    }


def format_context(bundle: dict) -> str:
    if not bundle.get("enabled"):
        return ""
    if not bundle.get("itens"):
        return (
            "\n\nAcervo Inteligência Eleitoral: consultado, sem trecho útil para esta frase."
        )
    compact = {
        "aviso": bundle.get("aviso"),
        "itens": bundle.get("itens"),
    }
    text = json.dumps(compact, ensure_ascii=False)
    return "\n\nContexto Inteligência Eleitoral (MCP):\n" + text[:7000]
