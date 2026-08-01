"""AutoFlow AI - HTTP transport (generated from metadata).

Provider-agnostic HTTP client with default headers/query params,
JSON encoding, timeouts, and optional streaming. Uses ``requests``
when available; falls back to stdlib ``urllib`` so imports never fail.
"""

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

try:
    import requests  # type: ignore
    HAS_REQUESTS = True
except ImportError:  # pragma: no cover - optional dependency
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


class HTTPTransport:
    """HTTP client used by connector implementations."""

    def __init__(self, base_url: str = "",
                 default_headers: Optional[Dict[str, str]] = None,
                 timeout: float = 30.0,
                 verify: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_headers = dict(default_headers or {})
        self.default_query: Dict[str, str] = {}
        self.timeout = timeout
        self.verify = verify

    def set_default_header(self, name: str, value: str) -> None:
        self.default_headers[name] = value

    def set_default_query_param(self, name: str, value: str) -> None:
        self.default_query[name] = value

    def _url(self, url: str) -> str:
        if url.startswith("http") or not self.base_url:
            return url
        return f"{self.base_url}/{url.lstrip('/')}"

    def _query(self, params: Optional[dict]) -> str:
        merged = dict(self.default_query)
        merged.update(params or {})
        if not merged:
            return ""
        return "?" + urllib.parse.urlencode(
            {k: (v if isinstance(v, str) else json.dumps(v))
             for k, v in merged.items()})

    def request(self, method: str, url: str,
                params: Optional[dict] = None,
                headers: Optional[dict] = None,
                json_body: Any = None,
                data: Any = None,
                timeout: Optional[float] = None,
                auth_header: bool = True,
                stream: bool = False) -> Any:
        """Perform an HTTP request and return parsed JSON (or dict)."""
        full_url = self._url(url) + self._query(params)
        req_headers = dict(self.default_headers)
        req_headers.update(headers or {})
        req_headers.setdefault("Accept", "application/json")
        if json_body is not None and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"
        body = None
        if json_body is not None:
            body = json.dumps(json_body, default=str).encode()
        elif data is not None:
            body = urllib.parse.urlencode(data).encode()
        timeout = timeout or self.timeout

        if HAS_REQUESTS:
            response = requests.request(
                method=method, url=full_url, headers=req_headers, data=body,
                timeout=timeout, verify=self.verify, stream=stream,
            )
            response.raise_for_status()
            if stream:
                return {"status_code": response.status_code,
                        "stream": response.iter_content(chunk_size=8192)}
            try:
                return response.json()
            except ValueError:
                return {"status_code": response.status_code,
                        "text": response.text}

        # stdlib fallback
        req = urllib.request.Request(full_url, data=body, headers=req_headers,
                                     method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                raw = resp.read()
                try:
                    return json.loads(raw.decode())
                except ValueError:
                    return {"status_code": resp.status, "text": raw.decode()}
        except urllib.error.HTTPError as exc:
            try:
                return json.loads(exc.read().decode())
            except Exception:  # noqa: BLE001
                return {"status_code": exc.code, "error": str(exc)}
