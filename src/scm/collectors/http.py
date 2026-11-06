import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "SupplyChainIntelligenceMVP/0.1 (public-source research; local development)"


class AccessBlocked(RuntimeError):
    pass


class SafeFetcher:
    """Single-host, rate-limited requests, bounded redirects, robots-first; no bypasses."""

    def __init__(self, client=None, interval=1.0, retries=2):
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(20, connect=10), headers={"User-Agent": USER_AGENT}, follow_redirects=False
        )
        self.interval = interval
        self.retries = retries
        self.last_request = {}
        self.robots = {}
        self.robots_audit = {}

    def _request(self, url, allowed_host):
        for _ in range(4):
            p = urlsplit(url)
            if (
                p.scheme != "https"
                or p.hostname != allowed_host
                or p.username
                or p.password
                or p.port not in [None, 443]
            ):
                raise AccessBlocked("Cross-host redirect or unsupported URL; manual source review required")
            response = None
            for attempt in range(self.retries + 1):
                wait = self.interval - (time.monotonic() - self.last_request.get(allowed_host, 0))
                if wait > 0:
                    time.sleep(wait)
                self.last_request[allowed_host] = time.monotonic()
                try:
                    # Streaming enforces size bound before loading potentially unbounded data.
                    with self.client.stream("GET", url) as raw:
                        body = bytearray()
                        for chunk in raw.iter_bytes():
                            body.extend(chunk)
                            if len(body) > 4_000_000:
                                raise AccessBlocked("Response exceeds 4MB limit")
                        response = httpx.Response(
                            raw.status_code, headers=raw.headers, content=bytes(body), request=raw.request
                        )
                    if response.status_code in [429, 500, 502, 503, 504] and attempt < self.retries:
                        retry_after = response.headers.get("retry-after", "")
                        delay = float(retry_after) if retry_after.isdigit() else 2**attempt
                        if delay > 30:
                            raise AccessBlocked("Retry-After exceeds bounded run; defer collection")
                        time.sleep(delay)
                        continue
                    break
                except httpx.TransportError:
                    if attempt == self.retries:
                        raise
                    time.sleep(2**attempt)
            if response.status_code in [301, 302, 303, 307, 308]:
                url = urljoin(url, response.headers.get("location", ""))
                continue
            return response
        raise AccessBlocked("Too many redirects")

    def get(self, url):
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        host = parsed.hostname
        if origin not in self.robots:
            response = self._request(origin + "/robots.txt", host)
            parser = RobotFileParser()
            if response.status_code == 200:
                if (
                    "<html" in response.text.lower()
                    or "text/html" in response.headers.get("content-type", "").lower()
                ):
                    raise AccessBlocked("robots.txt returned HTML/challenge; fail closed")
                parser.parse(response.text.splitlines())
                status = "200 parsed"
            elif response.status_code in [404, 410]:
                parser.parse(["User-agent: *", "Allow: /"])
                status = f"{response.status_code} no robots file (RFC 9309)"
            else:
                raise AccessBlocked(f"robots.txt HTTP {response.status_code}; fail closed")
            self.robots[origin] = parser
            self.robots_audit[origin] = status
        parser = self.robots[origin]
        if not parser.can_fetch(USER_AGENT, url):
            raise AccessBlocked("robots.txt disallows requested URL")
        delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*")
        rate = parser.request_rate(USER_AGENT) or parser.request_rate("*")
        if delay:
            self.interval = max(self.interval, delay)
        if rate and rate.requests:
            self.interval = max(self.interval, rate.seconds / rate.requests)
        response = self._request(url, host)
        if response.status_code in [401, 403, 429]:
            raise AccessBlocked(f"HTTP {response.status_code}; access restriction, not bypassed")
        response.raise_for_status()
        text = response.text.lower()
        if ("captcha" in text or "verify you are human" in text or "just a moment..." in text) and len(
            text
        ) < 40000:
            raise AccessBlocked("Possible CAPTCHA/challenge; manual access review required")
        return response

    def close(self):
        self.client.close()
