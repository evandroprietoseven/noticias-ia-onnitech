from __future__ import annotations

from datetime import datetime, timedelta
from dateutil import parser as dateparser
from urllib.parse import quote_plus, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.services.schemas import NewsItem
from app.services.utils import make_fingerprint


COMPANY_ALIASES: dict[str, list[str]] = {
    'Onnitech': ['Onnitech'],
    'Onnibank': ['Onnibank', 'Onni Bank'],
    'Onnipro': ['Onnipro', 'Onni Pro'],
    'Ringgo': ['Ringgo'],
    'Bs Cash': ['Bs Cash', 'BsCash'],
    'Mentore Bank': ['Mentore Bank', 'Mentorebank'],
    'Somapay': ['Somapay', 'Soma Pay'],
    'Pagcorp': ['Pagcorp', 'Pag Corp'],
    'Caju': ['Caju', 'Caju Benefícios', 'Caju Beneficios'],
    'Flash Benefícios': ['Flash Benefícios', 'Flash Beneficios', 'Flash'],
    'Alelo': ['Alelo'],
    'Clara Pagamentos': ['Clara Pagamentos', 'Clara', 'Clara Brasil'],
    'Paytrack': ['Paytrack'],
}

KEYWORD_CLUSTERS = [
    'fintech OR banco digital OR instituição de pagamento OR instituicao de pagamento',
    'meios de pagamento OR pagamentos OR adquirência OR adquirencia OR POS OR maquininha',
    'benefícios corporativos OR beneficios corporativos OR PAT OR vale alimentação OR vale refeição OR cartão multibenefícios',
    'conta digital OR cartão corporativo OR gestao de despesas OR travel and expense',
    'PIX OR Open Finance OR crédito OR credito OR antecipação de recebíveis OR BNPL',
]

BING_TIME_PATTERN = re.compile(r'(\d+)\s*(min|hora|dia|semana|m[eê]s|ano)', re.IGNORECASE)


def _google_news_rss_url(query: str) -> str:
    return f'https://news.google.com/rss/search?q={quote_plus(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419'


def _build_queries(company: str) -> list[str]:
    aliases = COMPANY_ALIASES.get(company, [company])
    alias_expr = ' OR '.join([f'"{a}"' for a in aliases])

    queries = []
    for kw in KEYWORD_CLUSTERS:
        queries.append(f'({alias_expr}) ({kw}) Brasil')

    # query mais ampla para capturar novidades corporativas relevantes
    queries.append(f'({alias_expr}) (fintech OR pagamentos OR benefícios OR beneficios OR banco digital) Brasil')

    # fontes adicionais solicitadas
    queries.append(f'({alias_expr}) site:finsidersbrasil.com.br')
    queries.append(f'({alias_expr}) (site:linkedin.com/company OR site:linkedin.com/posts)')
    queries.append(f'({alias_expr}) (site:instagram.com)')
    return queries


def _normalize_dt(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _parse_bing_relative_date(text: str, now: datetime) -> datetime | None:
    # exemplos: "7 dia(s)", "3 mês(eses)", "5 hora(s)"
    if not text:
        return None
    m = BING_TIME_PATTERN.search(text.replace('(s)', '').replace('(eses)', ''))
    if not m:
        return None

    n = int(m.group(1))
    unit = m.group(2).lower()

    if unit.startswith('min'):
        return now - timedelta(minutes=n)
    if unit.startswith('hora'):
        return now - timedelta(hours=n)
    if unit.startswith('dia'):
        return now - timedelta(days=n)
    if unit.startswith('semana'):
        return now - timedelta(days=7 * n)
    if unit.startswith('m'):
        return now - timedelta(days=30 * n)
    if unit.startswith('ano'):
        return now - timedelta(days=365 * n)
    return None


def _collect_google_news(company: str, now: datetime, cutoff: datetime) -> tuple[list[NewsItem], list[str]]:
    issues: list[str] = []
    out: list[NewsItem] = []

    def _parse_query(query: str) -> tuple[list[NewsItem], str | None]:
        url = _google_news_rss_url(query)
        feed = feedparser.parse(url)
        if getattr(feed, 'bozo', False):
            return [], f'{company}: falha parsing Google RSS'

        query_items: list[NewsItem] = []
        for e in feed.entries[:25]:
            dt_raw = getattr(e, 'published', None) or getattr(e, 'updated', None)
            if not dt_raw:
                continue
            try:
                published = _normalize_dt(dateparser.parse(dt_raw))
            except Exception:
                continue
            if not published or published < cutoff:
                continue

            title = (getattr(e, 'title', '') or '').strip()
            link = (getattr(e, 'link', '') or '').strip()
            if not title or not link:
                continue

            domain = urlparse(link).netloc.lower()
            if 'finsidersbrasil.com.br' in domain:
                source = 'Finsiders Brasil'
            elif 'linkedin.com' in domain:
                source = 'LinkedIn'
            elif 'instagram.com' in domain:
                source = 'Instagram'
            else:
                source = 'Google News RSS'

            raw_summary = (
                getattr(e, 'summary', None)
                or getattr(e, 'description', None)
                or ''
            )
            summary_txt = BeautifulSoup(raw_summary, 'lxml').get_text(' ', strip=True)

            query_items.append(NewsItem(
                company=company,
                title=title,
                url=link,
                source=source,
                published_at=published,
                summary=summary_txt[:320],
                fingerprint=make_fingerprint(title, link),
            ))

        return query_items, None

    queries = _build_queries(company)
    max_workers = min(8, max(1, len(queries)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_parse_query, q) for q in queries]
        for future in as_completed(futures):
            query_items, maybe_issue = future.result()
            out.extend(query_items)
            if maybe_issue:
                issues.append(maybe_issue)

    return out, issues


def _collect_bing_news(company: str, now: datetime, cutoff: datetime) -> tuple[list[NewsItem], list[str]]:
    issues: list[str] = []
    out: list[NewsItem] = []

    aliases = COMPANY_ALIASES.get(company, [company])
    alias_expr = ' OR '.join(aliases)
    query = f'({alias_expr}) fintech pagamentos beneficios corporativos banco digital Brasil'
    url = f'https://www.bing.com/news/search?q={quote_plus(query)}&setlang=pt-br'

    try:
        r = httpx.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'}, follow_redirects=True)
        if r.status_code >= 400:
            issues.append(f'{company}: Bing status {r.status_code}')
            return out, issues

        soup = BeautifulSoup(r.text, 'lxml')
        cards = soup.select('.news-card')
        if not cards:
            return out, issues

        for c in cards[:30]:
            # Em muitos casos o título clicável vem em a.t_t
            a = c.select_one('a.t_t') or c.select_one('.title a') or c.select_one('a[href]')
            if not a:
                continue

            title = a.get_text(' ', strip=True)
            link = (a.get('href') or '').strip()
            if not title or not link or not link.startswith('http'):
                continue

            src_node = c.select_one('.source')
            src_txt = src_node.get_text(' ', strip=True) if src_node else ''
            published = _parse_bing_relative_date(src_txt, now)
            if not published:
                continue
            published = _normalize_dt(published)
            if published < cutoff:
                continue

            snippet_node = c.select_one('.snippet') or c.select_one('.snippet a')
            snippet = snippet_node.get_text(' ', strip=True) if snippet_node else ''

            out.append(NewsItem(
                company=company,
                title=title,
                url=link,
                source='Bing News',
                published_at=published,
                summary=snippet[:320],
                fingerprint=make_fingerprint(title, link),
            ))

    except Exception as e:
        issues.append(f'{company}: falha Bing ({e.__class__.__name__})')

    return out, issues


def fetch_company_news(company: str, now: datetime) -> tuple[list[NewsItem], list[str]]:
    issues: list[str] = []
    cutoff = now - timedelta(days=60)

    g_items, g_issues = _collect_google_news(company, now, cutoff)
    b_items, b_issues = _collect_bing_news(company, now, cutoff)

    items = g_items + b_items
    issues.extend(g_issues)
    issues.extend(b_issues)

    return items, issues
