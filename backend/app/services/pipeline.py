from datetime import datetime, date, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.companies import ALL_COMPANIES
from app.services.collector import fetch_company_news
from app.services.summarizer import summarize_ptbr
from app.services.storage import dedupe_similar, filter_max_two_occurrences, register_report_usage, upsert_articles
from app.services.reporting import generate_markdown, generate_html, generate_pdf
from app.services.delivery import deliver_telegram, deliver_email
from app.services.curation import curate_items
from app.services.utils import strip_emojis, similar_title


def _cleanup_old_outputs() -> None:
    out_dir = Path(__file__).resolve().parents[2] / 'data' / 'outputs'
    if not out_dir.exists():
        return
    cutoff = datetime.now() - timedelta(days=30)
    for p in out_dir.glob('*'):
        if p.is_file() and datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
            p.unlink(missing_ok=True)


def _prioritize_news_over_instagram(items: list):
    by_company: dict[str, list] = {}
    for it in items:
        by_company.setdefault(it.company, []).append(it)

    out = []
    for company_items in by_company.values():
        non_instagram = [x for x in company_items if x.source != 'Instagram']
        if non_instagram:
            out.extend(non_instagram)
        else:
            out.extend(company_items)
    return out


def run_pipeline() -> dict:
    _cleanup_old_outputs()
    now = datetime.now()
    run_at = now.isoformat()
    issues: list[str] = []
    collected = []

    max_workers = min(8, max(1, len(ALL_COMPANIES)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_company_news, company, now): company for company in ALL_COMPANIES}
        for future in as_completed(futures):
            items, errs = future.result()
            collected.extend(items)
            issues.extend(errs)

    deduped = dedupe_similar(collected)
    curated, curation_rejections = curate_items(deduped)
    prioritized = _prioritize_news_over_instagram(curated)
    filtered = filter_max_two_occurrences(prioritized, date.today())

    for i in filtered:
        i.title = strip_emojis(i.title)
        ai_summary = strip_emojis(summarize_ptbr(i.title, company=i.company, source=i.source)).strip()
        base_summary = strip_emojis(i.summary or '').strip()

        base_is_redundant = (not base_summary) or similar_title(i.title, base_summary)
        if ai_summary and not similar_title(i.title, ai_summary):
            i.summary = ai_summary
        elif not base_is_redundant:
            i.summary = base_summary
        else:
            i.summary = 'Sem subtítulo disponível na fonte.'

    upsert_articles(filtered)
    register_report_usage(filtered, date.today())

    md_path = generate_markdown(run_at, filtered, issues)
    html_path = generate_html(md_path)
    pdf_path = generate_pdf(html_path)

    telegram_status = deliver_telegram(pdf_path)
    email_status = deliver_email(html_path, pdf_path)

    return {
        'run_at': run_at,
        'items_found': len(collected),
        'items_after_dedupe': len(deduped),
        'items_after_curation': len(curated),
        'items_curated_out': len(curation_rejections),
        'items_in_report': len(filtered),
        'issues': issues,
        'curation_notes': curation_rejections[:30],
        'markdown': md_path,
        'html': html_path,
        'pdf': pdf_path,
        'telegram_status': telegram_status,
        'email_status': email_status,
    }
