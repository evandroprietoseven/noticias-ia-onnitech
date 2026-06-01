from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class Article(Base):
    __tablename__ = 'articles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1200), unique=True)
    source: Mapped[str] = mapped_column(String(200))
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    title_fingerprint: Mapped[str] = mapped_column(String(256), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ReportArticle(Base):
    __tablename__ = 'report_articles'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_date: Mapped[datetime] = mapped_column(Date, index=True)
    article_fingerprint: Mapped[str] = mapped_column(String(256), index=True)

    __table_args__ = (
        UniqueConstraint('report_date', 'article_fingerprint', name='uq_report_article_once_per_day'),
    )
