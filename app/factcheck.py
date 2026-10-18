import json
import re

import httpx

from app.settings import settings

ALLOWED = {
    "sustentado",
    "contradito",
    "exagerado",
    "sem_evidencia",
    "inconclusivo",
}
NEEDS_SOURCE = {"sustentado", "contradito", "exagerado"}

DEBATE_RULES = """
Regras do debate Band de 18/10/2026, mediado por Adriana Araújo e Eduardo Oinegue:
- Bloco 1: cada mediador faz uma pergunta. Flávio responde primeiro (2 min). Confronto de 30 min, 15 para cada um. Lula pergunta primeiro.
- Bloco 2: Adriana faz uma pergunta aos dois. Flávio responde primeiro (2 min). Confronto de 15 min. Flávio pergunta primeiro. Pergunta 1min30, resposta e tréplica 4 min, réplica 2 min.
- Bloco 3: Eduardo faz a mesma pergunta aos dois. Lula responde primeiro (2 min). Confronto de 15 min. Lula pergunta primeiro, com os mesmos tempos do bloco 2.
- Considerações finais: 2 min cada. Lula começa. Flávio encerra.
Pergunta de Adriana ou Eduardo não é fala de candidato. Use o nome dito no áudio. Se o trecho não identificar Lula, não atribua a ele.
"""

EXTRACT_SYSTEM = """Você extrai afirmações verificáveis de um trecho de debate presidencial em português.
""" + DEBATE_RULES + """
Responda só JSON neste formato:
{"claims":[{"quote":"trecho curto ouvido","claim":"afirmação reescrita de forma checável","speaker":"lula|outro|incerto"}]}

Regras:
- Entre só frase com fato checável: número, data, obra, lei, cargo, comparação quantitativa.
- speaker=lula apenas quando o trecho deixa claro que quem afirma é Luiz Inácio Lula da Silva. Se a autoria estiver ambígua, use incerto.
- Não invente frase que não esteja no trecho.
- Ignore opinião, ataque pessoal e pergunta de mediador.
- Se não houver afirmação checável, devolva {"claims":[]}."""

VERIFY_SYSTEM = """Você checa uma afirmação pública atribuída a Lula no debate presidencial de 18/10/2026.
""" + DEBATE_RULES + """
Faça mais de uma busca se a primeira for vaga. Procure o número, o período e a definição (por exemplo o que conta como creche).
Responda só JSON:
{"status":"sustentado|contradito|exagerado|sem_evidencia|inconclusivo","confidence":0.4,"summary":"até 500 caracteres","missing":"o que impediu cravar, ou vazio","sources":[{"title":"nome da página","url":"https://...","note":"o que a página mostra"}]}

Regras:
- status sustentado: a fonte publicamente acessível apoia o núcleo da frase, no recorte de tempo e lugar certos.
- status contradito: a fonte publicamente acessível mostra que o núcleo da frase não se sustenta.
- status exagerado: a direção pode estar certa, mas o número, o prazo ou o recorte está maior do que a fonte mostra.
- status sem_evidencia: a busca não achou fonte suficiente. Não chute.
- status inconclusivo: as fontes divergem ou a frase depende de definição (qual governo, qual município, o que conta como creche).
- Toda url tem de ser https e tem de ter aparecido na busca. Não invente url.
- Prefira IBGE, INEP, Portal da Transparência, gov.br, TSE e séries oficiais. Agência de checagem entra como fonte secundária e deve ser nomeada.
- Não use a palavra fake. Não escreva texto de campanha.
- Se a frase não diz o período, registre isso em missing e não marque sustentado só porque algum número parecido existe em outro ano."""


def parse_json(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("resposta sem JSON")
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("JSON raiz não é objeto")
    return data


def sanitize_verdict(payload: dict) -> dict:
    status = str(payload.get("status") or "").strip().lower()
    if status not in ALLOWED:
        status = "inconclusivo"
    sources = []
    for item in payload.get("sources") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if not url.startswith("https://"):
            continue
        sources.append(
            {
                "title": str(item.get("title") or url)[:180],
                "url": url[:500],
                "note": str(item.get("note") or "")[:300],
            }
        )
    if status in NEEDS_SOURCE and not sources:
        status = "sem_evidencia"
    try:
        confidence = float(payload.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    return {
        "status": status,
        "confidence": confidence,
        "summary": str(payload.get("summary") or "")[:800],
        "missing": str(payload.get("missing") or "")[:400],
        "sources": sources[:5],
    }


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.openrouter_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.referer,
        "X-Title": "Checagem do debate",
    }


def chat_completion(model: str, system: str, user: str, timeout: float) -> dict:
    if not settings.openrouter_key:
        raise RuntimeError("OPENROUTER_API_KEY ausente")
    body = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=_headers(),
            json=body,
        )
        response.raise_for_status()
        return response.json()


def message_text(payload: dict) -> str:
    content = payload["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content)


def chat_json(model: str, system: str, user: str, timeout: float) -> dict:
    return parse_json(message_text(chat_completion(model, system, user, timeout)))


def citation_urls(payload: dict) -> list[str]:
    found = []
    for item in payload.get("citations") or []:
        if isinstance(item, str):
            found.append(item)
        elif isinstance(item, dict):
            found.append(str(item.get("url") or ""))
    message = ((payload.get("choices") or [{}])[0].get("message") or {})
    for note in message.get("annotations") or []:
        if not isinstance(note, dict):
            continue
        cite = note.get("url_citation") or note
        if isinstance(cite, dict):
            found.append(str(cite.get("url") or ""))
    return found


def attach_citations(data: dict, urls: list[str]) -> dict:
    sources = [item for item in (data.get("sources") or []) if isinstance(item, dict)]
    known = {str(item.get("url") or "").strip() for item in sources}
    for url in urls:
        clean = str(url or "").strip()
        if not clean.startswith("https://") or clean in known:
            continue
        sources.append({"title": clean, "url": clean, "note": "página usada na busca"})
        known.add(clean)
    merged = dict(data)
    merged["sources"] = sources
    return merged


def extract_claims(transcript: str) -> list[dict]:
    data = chat_json(
        settings.extract_model,
        EXTRACT_SYSTEM,
        transcript[-6000:],
        timeout=45,
    )
    found = []
    for item in data.get("claims") or []:
        if not isinstance(item, dict):
            continue
        speaker = str(item.get("speaker") or "incerto").strip().lower()
        if speaker != "lula":
            continue
        quote = str(item.get("quote") or "").strip()
        claim = str(item.get("claim") or "").strip()
        if len(claim) < 12 or len(quote) < 8:
            continue
        found.append({"quote": quote[:500], "claim": claim[:400]})
    return found[:4]


def verify_claim(quote: str, claim: str) -> dict:
    payload = chat_completion(
        settings.fact_model,
        VERIFY_SYSTEM,
        f"Frase ouvida:\n{quote}\n\nAfirmação a checar:\n{claim}",
        timeout=90,
    )
    data = attach_citations(parse_json(message_text(payload)), citation_urls(payload))
    return sanitize_verdict(data)
