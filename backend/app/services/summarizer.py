import re
import httpx

from app.config import settings


def _force_third_person(text: str, company: str) -> str:
    company_clean = (company or '').strip() or 'A empresa'
    txt = (text or '').strip()

    # Ajustes específicos para frases típicas de post corporativo em 1ª pessoa.
    txt = re.sub(
        r'(?i)\bnós\s+da\s+[^,.;:]+\s+participamos\b',
        f'{company_clean} participa',
        txt,
    )

    replacements = [
        (r'\bnós\b', company_clean),
        (r'\bnosso\b', f'da {company_clean}'),
        (r'\bnossa\b', f'da {company_clean}'),
        (r'\bnossos\b', f'da {company_clean}'),
        (r'\bnossas\b', f'da {company_clean}'),
        (r'\bestamos\b', f'{company_clean} está'),
        (r'\bparticipamos\b', f'{company_clean} participa'),
    ]
    for pattern, repl in replacements:
        txt = re.sub(pattern, repl, txt, flags=re.IGNORECASE)

    return txt


def summarize_ptbr(title: str, company: str = '', source: str = '') -> str:
    # Preferência: IA curta; fallback determinístico.
    base_url = settings.llm_base_url.strip()
    api_key = settings.llm_api_key.strip()
    model = settings.llm_model.strip() or 'openai/gpt-5.4-nano'

    is_social = source in {'Instagram', 'LinkedIn'}
    system_prompt = 'Resuma em pt-BR em no máximo 2 linhas, sem inventar fatos.'
    if is_social:
        system_prompt += ' Se for publicação da própria empresa, escreva sempre em terceira pessoa, citando a empresa pelo nome e sem usar "nós".'

    if base_url and api_key:
        try:
            with httpx.Client(timeout=20) as c:
                r = c.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers={'Authorization': f'Bearer {api_key}'},
                    json={
                        'model': model,
                        'messages': [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': f'Empresa: {company}\nFonte: {source}\nTítulo: {title}'}
                        ],
                        'temperature': 0.2
                    }
                )
                if r.status_code < 300:
                    txt = r.json()['choices'][0]['message']['content'].strip()
                    if is_social:
                        txt = _force_third_person(txt, company)
                    return txt[:300]
        except Exception:
            pass

    return ''
