import hashlib
import re
from urllib.parse import urlparse
from rapidfuzz import fuzz


def strip_emojis(text: str) -> str:
    # Remove emojis/common pictographs while preserving pt-BR accents and punctuation.
    if not text:
        return ''
    emoji_re = re.compile(
        '['
        '\U0001F300-\U0001F5FF'  # symbols & pictographs
        '\U0001F600-\U0001F64F'  # emoticons
        '\U0001F680-\U0001F6FF'  # transport/map
        '\U0001F700-\U0001F77F'
        '\U0001F780-\U0001F7FF'
        '\U0001F800-\U0001F8FF'
        '\U0001F900-\U0001F9FF'  # supplemental symbols
        '\U0001FA00-\U0001FAFF'
        '\U00002700-\U000027BF'  # dingbats
        '\U00002600-\U000026FF'  # misc symbols
        ']+',
        flags=re.UNICODE,
    )
    out = emoji_re.sub('', text)
    out = out.replace('️', '').replace('✨', '').replace('🔥', '').replace('💳', '')
    return re.sub(r'\s+', ' ', out).strip()


def normalize_title(title: str) -> str:
    t = strip_emojis(title).lower().strip()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'[^a-z0-9à-ÿ ]', '', t)
    return t


def make_fingerprint(title: str, url: str) -> str:
    domain = urlparse(url).netloc.lower().replace('www.', '')
    key = f"{normalize_title(title)}|{domain}"
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def similar_title(a: str, b: str) -> bool:
    return fuzz.token_set_ratio(normalize_title(a), normalize_title(b)) >= 88
