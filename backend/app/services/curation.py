from __future__ import annotations

import json
import re
import httpx

from app.config import settings
from app.services.schemas import NewsItem
from app.services.collector import COMPANY_ALIASES

SECTOR_TERMS = {
    'fintech', 'pagamento', 'pagamentos', 'benefício', 'beneficios', 'benefícios', 'pat',
    'banco', 'conta digital', 'cartão', 'pix', 'open finance', 'crédito', 'credito'
}


def _normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower()).strip()


def _heuristic_relevant(company: str, title: str) -> tuple[bool, str]:
    t = _normalize(title)
    aliases = [a.lower() for a in COMPANY_ALIASES.get(company, [company])]
    has_alias = any(a in t for a in aliases)
    has_sector = any(term in t for term in SECTOR_TERMS)

    if has_alias and has_sector:
        return True, 'heuristic:alias+sector'
    if has_alias:
        return True, 'heuristic:alias'
    return False, 'heuristic:missing_alias'


def _llm_judge(company: str, item: NewsItem) -> tuple[bool, str]:
    base_url = settings.llm_base_url.strip()
    api_key = settings.llm_api_key.strip()
    model = settings.llm_model.strip() or 'meta-llama/llama-3.1-8b-instruct'

    if not base_url or not api_key:
        return _heuristic_relevant(company, item.title)

    aliases = COMPANY_ALIASES.get(company, [company])
    prompt = {
        'company': company,
        'aliases': aliases,
        'title': item.title,
        'url': item.url,
        'source': item.source,
        'task': 'Decida se a notícia é realmente sobre a empresa/concorrente informado, evitando notícias genéricas de mercado que não citam a empresa de forma clara.'
    }

    try:
        with httpx.Client(timeout=25) as c:
            r = c.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://local.hermes',
                    'X-Title': 'noticias-diarias-onnitech',
                },
                json={
                    'model': model,
                    'temperature': 0,
                    'messages': [
                        {
                            'role': 'system',
                            'content': (
                                'Você é um classificador estrito de pertinência de notícias. '
                                'Retorne APENAS JSON: {"relevant": true|false, "reason": "..."}. '
                                'Marque false quando a empresa não estiver claramente citada/associada.'
                            )
                        },
                        {'role': 'user', 'content': json.dumps(prompt, ensure_ascii=False)}
                    ]
                }
            )
            if r.status_code >= 300:
                return _heuristic_relevant(company, item.title)
            content = r.json()['choices'][0]['message']['content'].strip()
            m = re.search(r'\{.*\}', content, re.S)
            raw = m.group(0) if m else content
            data = json.loads(raw)
            relevant = bool(data.get('relevant', False))
            reason = str(data.get('reason', 'llm:no-reason'))[:140]
            return relevant, f'llm:{reason}'
    except Exception:
        return _heuristic_relevant(company, item.title)


def curate_items(items: list[NewsItem]) -> tuple[list[NewsItem], list[str]]:
    approved: list[NewsItem] = []
    rejected_notes: list[str] = []

    for it in items:
        ok, reason = _llm_judge(it.company, it)
        if ok:
            approved.append(it)
        else:
            rejected_notes.append(f'{it.company}: removida por curadoria ({reason}) -> {it.title[:120]}')

    return approved, rejected_notes
