"""Content-addressed permitted HTTP response evidence; never rendered as executable HTML."""

import hashlib
import os
import tempfile
from pathlib import Path

from scm.settings import ROOT, utcnow


class RecordingFetcher:
    def __init__(self, fetcher, root=None):
        self.fetcher = fetcher
        self.root = Path(root or ROOT / "runtime/platform/artifacts")
        self.captures = []

    def __getattr__(self, name):
        return getattr(self.fetcher, name)

    def get(self, url):
        response = self.fetcher.get(url)
        content = response.content
        sha = hashlib.sha256(content).hexdigest()
        mode = "live" if self.verification_type == "LIVE_HTTP" else "demo"
        relative = Path(mode) / sha[:2] / (sha + ".bin")
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                raise ValueError("Existing raw response artifact failed integrity check")
        else:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
                tmp.write(content)
                name = tmp.name
            os.replace(name, target)
        self.captures.append(
            {
                "url": url,
                "response_url": str(response.url),
                "sha256": sha,
                "bytes": len(content),
                "content_type": response.headers.get("content-type"),
                "path": relative.as_posix(),
                "captured_at": utcnow().isoformat(),
                "mode": mode,
            }
        )
        return response
