from dataclasses import dataclass
from datetime import datetime

@dataclass
class NewsItem:
    company: str
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str
    fingerprint: str
