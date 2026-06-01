from datetime import datetime
from pathlib import Path
from collections import defaultdict
import markdown as md
from jinja2 import Template
from weasyprint import HTML
from app.services.companies import ONNITECH_GROUP, COMPETITORS
from app.services.schemas import NewsItem

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / 'data' / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)


def _today_stamp() -> str:
    return datetime.now().strftime('%Y%m%d')


def _source_label(item: NewsItem) -> str:
    t = (item.title or '').lower()
    u = (item.url or '').lower()
    s = (item.source or '').lower()

    if 'instagram.com' in t or 'instagram.com' in u or 'instagram' in s:
        return 'Insta'
    if 'linkedin.com' in t or 'linkedin.com' in u or 'linkedin' in s:
        return 'LinkedIn'
    return 'Notícia'


def _line(item: NewsItem) -> str:
    d = item.published_at.strftime('%d/%m/%Y')
    lbl = _source_label(item)
    return (
        f"- [{d}] **{item.title}**  \n"
        f"  {item.summary}  \n"
        f"  Fonte: {lbl} ([link]({item.url}))"
    )


def generate_markdown(run_at: str, items: list[NewsItem], issues: list[str]) -> str:
    by_company = defaultdict(list)
    for i in items:
        by_company[i.company].append(i)

    lines = [
        '# Resumo Diário de Notícias - Grupo Onnitech e Concorrentes',
        '',
        f'Gerado em: {run_at}',
        ''
    ]

    lines += ['## Grupo Onnitech', '']
    for c in ONNITECH_GROUP:
        lines += [f'### {c}']
        comp = sorted(by_company.get(c, []), key=lambda x: x.published_at, reverse=True)
        if not comp:
            lines += ['- Não foram encontradas notícias recentes (últimos 60 dias) para esta empresa.', '']
        else:
            lines += [_line(i) for i in comp] + ['']

    lines += ['## Concorrentes', '']
    for c in COMPETITORS:
        lines += [f'### {c}']
        comp = sorted(by_company.get(c, []), key=lambda x: x.published_at, reverse=True)
        if not comp:
            lines += ['- Não foram encontradas notícias recentes (últimos 60 dias) para esta empresa.', '']
        else:
            lines += [_line(i) for i in comp] + ['']

    if issues:
        lines += ['## Problemas de coleta', '']
        lines += [f'- {x}' for x in issues]

    p = OUT / f'Resumo_Diario_Noticias_Grupo_Onnitech_Concorrentes_{_today_stamp()}.md'
    p.write_text('\n'.join(lines), encoding='utf-8')
    return str(p)


def generate_html(markdown_path: str) -> str:
    m = Path(markdown_path).read_text(encoding='utf-8')
    body = md.markdown(m)
    template = Template('''<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><style>
@page { size: A4; margin: 1.6cm; }
body { font-family: Arial, sans-serif; color: #1a1a1a; margin: 0; font-size: 12px; }
.cover { background: linear-gradient(135deg, #0e3b5a, #0aa37a); color: #fff; padding: 36px; border-radius: 14px; margin-bottom: 24px; }
.cover h1 { margin: 0 0 6px 0; font-size: 28px; }
.cover p { margin: 0; opacity: .95; }
h2 { color: #0e3b5a; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 22px; }
h3 { color: #0aa37a; margin-bottom: 8px; }
a { color: #0b63ce; text-decoration: underline; }
li { margin-bottom: 6px; }
</style></head><body>
<div class="cover"><h1>Resumo Diário de Notícias</h1><p>Grupo Onnitech e Concorrentes</p></div>
{{ body }}
</body></html>''')
    html = template.render(body=body)
    out = Path(markdown_path).with_suffix('.html')
    out.write_text(html, encoding='utf-8')
    return str(out)


def generate_pdf(html_path: str) -> str:
    out = Path(html_path).with_suffix('.pdf')
    HTML(filename=html_path).write_pdf(str(out))
    return str(out)
