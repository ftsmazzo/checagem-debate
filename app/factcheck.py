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
- Reescreva a claim com sujeito, verbo e número/periodo claros. Exemplo ruim: "fiz creches". Exemplo bom: "o governo Lula entregou 10 creches no Brasil".
- Não invente frase que não esteja no trecho.
- Ignore opinião, ataque pessoal e pergunta de mediador.
- Se não houver afirmação checável, devolva {"claims":[]}."""

VERIFY_SYSTEM = """Você é um checador de fatos para o debate presidencial brasileiro de 18/10/2026.
""" + DEBATE_RULES + """
Use a busca na web. Faça buscas adicionais se a primeira for vaga: número + período + definição do termo.
Responda só JSON:
{"status":"sustentado|contradito|exagerado|sem_evidencia|inconclusivo","confidence":0.4,"summary":"até 500 caracteres","missing":"o que impediu cravar, ou vazio","sources":[{"title":"nome da página","url":"https://...","note":"o que a página mostra"}]}

Regras:
- status sustentado: pelo menos uma fonte https pública apoia o núcleo da frase no recorte certo de tempo e lugar.
- status contradito: fonte https pública mostra que o núcleo não se sustenta.
- status exagerado: a direção pode estar certa, mas número, prazo ou recorte está maior do que a fonte.
- status sem_evidencia: a busca não achou fonte suficiente. Não chute.
- status inconclusivo: fontes divergem ou a frase depende de definição (qual governo, município, o que conta como creche).
- Prefira IBGE, INEP, Portal da Transparência, gov.br, TSE, Senado, Câmara e séries oficiais. Agência de checagem (Lupa, Aos Fatos, Estadão Verifica) é secundária e deve ser nomeada.
- Toda url tem de ser https e tem de ter saído da busca ou das citações. Não invente url.
- Se a frase não diz o período, registre em missing e não marque sustentado só porque um número parecido existe em outro ano.
- Não use a palavra fake. Não escreva texto de campanha.
- confidence alto (>=0.7) só com fonte oficial ou duas fontes independentes apontando o mesmo sentido."""

SEARCH_BRIEF_SYSTEM = """Você pesquisa fontes públicas sobre uma afirmação atribuída a Lula no debate de 18/10/2026.
Responda só JSON:
{"findings":"resumo factual em até 700 caracteres","queries":["busca1","busca2"],"sources":[{"title":"nome","url":"https://...","note":"o que a página diz"}]}
Não invente url. Prefira fontes oficiais brasileiras."""


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
    if status in NEEDS_SOURCE and len(sources) < 2 and confidence > 0.65:
        confidence = 0.65
    return {
        "status": status,
        "confidence": confidence,
        "summary": str(payload.get("summary") or "")[:800],
        "missing": str(payload.get("missing") or "")[:400],
        "sources": sources[:8],
    }


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.openrouter_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.referer,
        "X-Title": "Checagem do debate",
    }


def _openrouter_error(status: int, model: str, detail: str) -> RuntimeError:
    text = detail or "falha na chamada"
    if status == 401 or "user not found" in text.lower():
        return RuntimeError(
            "A chave OPENROUTER_API_KEY no servidor está inválida, expirada ou revogada. "
            "Crie em https://openrouter.ai/keys (tem de começar com sk-or-v1-) e "
            "reinicie o serviço depois de colar no EasyPanel."
        )
    return RuntimeError(f"OpenRouter {status} no modelo {model}: {text}")


def chat_completion(
    model: str,
    system: str,
    user: str,
    timeout: float,
    plugins: list[dict] | None = None,
) -> dict:
    if not settings.openrouter_key:
        raise RuntimeError("OPENROUTER_API_KEY ausente")
    if not settings.openrouter_key.startswith("sk-or-"):
        raise RuntimeError(
            "OPENROUTER_API_KEY inválida: use a chave do OpenRouter (sk-or-v1-...), "
            "não a chave do site da Perplexity (pplx-...)."
        )
    body: dict = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if plugins:
        body["plugins"] = plugins
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=_headers(),
            json=body,
        )
        if response.is_error:
            detail = ""
            try:
                err = response.json().get("error") or {}
                detail = str(err.get("message") or err)
            except Exception:
                detail = response.text[:300]
            raise _openrouter_error(
                response.status_code, model, detail or response.reason_phrase
            )
        return response.json()


def message_text(payload: dict) -> str:
    content = payload["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content)


def chat_json(
    model: str,
    system: str,
    user: str,
    timeout: float,
    plugins: list[dict] | None = None,
) -> dict:
    return parse_json(
        message_text(chat_completion(model, system, user, timeout, plugins=plugins))
    )


def citation_sources(payload: dict) -> list[dict]:
    found = []
    for item in payload.get("citations") or []:
        if isinstance(item, str) and item.startswith("https://"):
            found.append({"title": item, "url": item, "note": "citação da busca"})
        elif isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            if url.startswith("https://"):
                found.append(
                    {
                        "title": str(item.get("title") or url)[:180],
                        "url": url,
                        "note": str(item.get("note") or item.get("content") or "")[:300],
                    }
                )
    message = ((payload.get("choices") or [{}])[0].get("message") or {})
    for note in message.get("annotations") or []:
        if not isinstance(note, dict):
            continue
        cite = note.get("url_citation") or note
        if not isinstance(cite, dict):
            continue
        url = str(cite.get("url") or "").strip()
        if not url.startswith("https://"):
            continue
        found.append(
            {
                "title": str(cite.get("title") or url)[:180],
                "url": url,
                "note": str(cite.get("content") or "")[:300],
            }
        )
    return found


def attach_citations(data: dict, extra: list[dict]) -> dict:
    sources = [item for item in (data.get("sources") or []) if isinstance(item, dict)]
    known = {str(item.get("url") or "").strip() for item in sources}
    for item in extra:
        url = str(item.get("url") or "").strip()
        if not url.startswith("https://") or url in known:
            continue
        sources.append(
            {
                "title": str(item.get("title") or url)[:180],
                "url": url[:500],
                "note": str(item.get("note") or "")[:300],
            }
        )
        known.add(url)
    merged = dict(data)
    merged["sources"] = sources
    return merged


def web_plugins() -> list[dict]:
    return [
        {
            "id": "web",
            "engine": "perplexity",
            "max_results": 8,
            "search_prompt": (
                "Resultados de busca em {date}. Priorize fontes oficiais brasileiras "
                "(gov.br, IBGE, INEP, TSE, Portal da Transparência) e cite com links https."
            ),
        }
    ]


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


def _search_brief(quote: str, claim: str) -> dict:
    try:
        payload = chat_completion(
            settings.search_model,
            SEARCH_BRIEF_SYSTEM,
            f"Frase ouvida:\n{quote}\n\nAfirmação:\n{claim}",
            timeout=90,
        )
        data = attach_citations(
            parse_json(message_text(payload)), citation_sources(payload)
        )
        return {
            "findings": str(data.get("findings") or "")[:900],
            "sources": data.get("sources") or [],
            "raw": message_text(payload)[:2500],
        }
    except Exception:
        return {"findings": "", "sources": [], "raw": ""}


def verify_claim(quote: str, claim: str) -> dict:
    brief = _search_brief(quote, claim)
    brief_block = ""
    if brief["findings"] or brief["sources"]:
        brief_block = (
            "\n\nPesquisa prévia (Sonar Pro Search):\n"
            + (brief["findings"] or brief["raw"] or "(sem resumo)")
            + "\nFontes já vistas:\n"
            + json.dumps(brief["sources"][:8], ensure_ascii=False)
        )
    payload = chat_completion(
        settings.fact_model,
        VERIFY_SYSTEM,
        f"Frase ouvida:\n{quote}\n\nAfirmação a checar:\n{claim}{brief_block}",
        timeout=120,
        plugins=web_plugins(),
    )
    data = attach_citations(parse_json(message_text(payload)), citation_sources(payload))
    data = attach_citations(data, brief["sources"])
    return sanitize_verdict(data)
