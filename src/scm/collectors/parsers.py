from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
import feedparser


def parse_date(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
    except ValueError:
        try:
            result = parsedate_to_datetime(str(value))
        except (ValueError, TypeError):
            return None
    # Date-only timestamps are preserved at midnight UTC, an explicit convention.
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def parse_article(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    h1 = soup.find('h1')
    title_meta = soup.find('meta', property='og:title')
    title = h1.get_text(' ', strip=True) if h1 else (title_meta.get('content', '') if title_meta else '')
    published = None
    for attrs in [{'property': 'article:published_time'}, {'name': 'date'}, {'name': 'DC.date.issued'}, {'name': 'datePublished'}]:
        tag = soup.find('meta', attrs=attrs)
        if tag:
            published = parse_date(tag.get('content'))
            if published:
                break
    if published is None:
        for tag in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(tag.string or tag.get_text())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and '@graph' in item:
                        items.extend(item['@graph'])
                    if isinstance(item, dict) and item.get('datePublished'):
                        published = parse_date(item['datePublished'])
                        if published:
                            break
            except (ValueError, TypeError):
                continue
    if published is None:
        tag = soup.find('time', datetime=True)
        published = parse_date(tag['datetime']) if tag else None
    content = soup.find('article') or soup.find('main')
    # A generic shell is not treated as a full article.
    if content is None:
        raise ValueError('No article/main content container')
    for tag in content.select('script, style, nav, footer, header, form, aside'):
        tag.decompose()
    paragraphs = [p.get_text(' ', strip=True) for p in content.find_all(['p', 'li'])]
    body = '\n'.join(p for p in paragraphs if len(p) > 35)
    if not title or len(body) < 100:
        raise ValueError('No usable article title/body; possible JS shell or listing')
    return {'title': title, 'body': body[:200000], 'url': url, 'published_at': published}


def discover_links(html, base_url, pattern, limit=5):
    soup = BeautifulSoup(html, 'html.parser')
    seen = set()
    links = []
    main = soup.find('main') or soup
    for anchor in main.find_all('a', href=True):
        url = urljoin(base_url, anchor['href']).split('#')[0]
        if urlsplit(url).hostname != urlsplit(base_url).hostname or url.rstrip('/') == base_url.rstrip('/'):
            continue
        if not re.search(pattern, url) or url in seen:
            continue
        seen.add(url)
        links.append(url)
        if len(links) >= limit:
            break
    return links


def parse_feed(content):
    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        raise ValueError('Invalid RSS/Atom feed')
    entries = []
    for entry in feed.entries[:10]:
        if entry.get('link'):
            entries.append({'url': entry.link, 'published_at': parse_date(entry.get('published')), 'title': entry.get('title', '')})
    return entries
