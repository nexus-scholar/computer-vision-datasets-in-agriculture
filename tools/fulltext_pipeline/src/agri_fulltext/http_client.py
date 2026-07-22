from __future__ import annotations

import email.utils
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests


class PoliteSession(requests.Session):
    """Sequential, host-aware throttling with bounded Retry-After handling."""

    DEFAULT_INTERVALS = {
        "api.unpaywall.org": 0.25,
        "api.openalex.org": 0.15,
        "content.openalex.org": 0.15,
        "api.semanticscholar.org": 1.05,
        "api.crossref.org": 0.2,
        "pmc.ncbi.nlm.nih.gov": 0.35,
        "www.ebi.ac.uk": 0.2,
        "europepmc.org": 0.5,
        "arxiv.org": 3.0,
    }

    def __init__(self, max_retries: int = 2):
        super().__init__()
        self.max_retries = max(0, max_retries)
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()

    def request(self, method, url, **kwargs):  # type: ignore[override]
        host = (urlsplit(str(url)).hostname or "").lower()
        interval = self.DEFAULT_INTERVALS.get(host, 0.5)
        with self._lock:
            elapsed = time.monotonic() - self._last_request.get(host, 0.0)
            if elapsed < interval:
                time.sleep(interval - elapsed)
            self._last_request[host] = time.monotonic()
        last_response = None
        for attempt in range(self.max_retries + 1):
            response = super().request(method, url, **kwargs)
            last_response = response
            if response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                return response
            delay = _retry_after_seconds(response.headers.get("Retry-After"))
            response.close()
            time.sleep(delay if delay is not None else min(2 ** (attempt + 1), 30))
        assert last_response is not None
        return last_response


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None
