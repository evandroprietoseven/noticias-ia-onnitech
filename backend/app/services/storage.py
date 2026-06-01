from datetime import date, timedelta
from sqlalchemy import select, func
from app.db import SessionLocal
from app.models import Article, ReportArticle
from app.services.schemas import NewsItem
from app.services.utils import similar_title


def upsert_articles(items: list[NewsItem]) -> list[Article]:
    saved: list[Article] = []
    with SessionLocal() as db:
        for n in items:
            existing = db.scalar(select(Article).where(Article.url == n.url))
            if existing:
                saved.append(existing)
                continue
            a = Article(
                company=n.company,
                title=n.title,
                summary=n.summary,
                url=n.url,
                source=n.source,
                published_at=n.published_at,
                title_fingerprint=n.fingerprint,
            )
            db.add(a)
            db.flush()
            saved.append(a)
        db.commit()
    return saved


def filter_max_two_occurrences(items: list[NewsItem], report_day: date) -> list[NewsItem]:
    kept: list[NewsItem] = []
    with SessionLocal() as db:
        cutoff = report_day - timedelta(days=30)
        for item in items:
            count = db.scalar(
                select(func.count(ReportArticle.id)).where(
                    ReportArticle.article_fingerprint == item.fingerprint,
                    ReportArticle.report_date >= cutoff,
                )
            ) or 0
            if count < 2:
                kept.append(item)
    return kept


def register_report_usage(items: list[NewsItem], report_day: date) -> None:
    with SessionLocal() as db:
        existing = {
            x[0]
            for x in db.execute(
                select(ReportArticle.article_fingerprint).where(ReportArticle.report_date == report_day)
            ).all()
        }
        for item in items:
            if item.fingerprint in existing:
                continue
            db.add(ReportArticle(report_date=report_day, article_fingerprint=item.fingerprint))
            existing.add(item.fingerprint)
        db.commit()


def dedupe_similar(items: list[NewsItem]) -> list[NewsItem]:
    by_company: dict[str, list[NewsItem]] = {}
    for i in sorted(items, key=lambda x: x.published_at, reverse=True):
        pool = by_company.setdefault(i.company, [])
        if any(similar_title(i.title, p.title) for p in pool):
            continue
        pool.append(i)

    out: list[NewsItem] = []
    for lst in by_company.values():
        out.extend(lst)
    return sorted(out, key=lambda x: x.published_at, reverse=True)
