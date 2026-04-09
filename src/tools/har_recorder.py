"""
Agent-OS HAR (HTTP Archive) Recorder

Records browser network traffic in HAR 1.2 format for debugging,
performance analysis, and request replay. Fully compliant with
the HTTP Archive Specification v1.2.

Memory-safe: caps response body capture at 1 MB per entry.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent-os.har-recorder")

# Maximum response body size to store in HAR (bytes)
MAX_BODY_CAPTURE_BYTES = 1 * 1024 * 1024  # 1 MB


class _PendingRequest:
    """Tracks an in-flight request awaiting its paired response."""

    __slots__ = (
        "started_dt", "started_ts", "method", "url", "http_version",
        "headers", "query_string", "post_data", "headers_size", "body_size",
    )

    def __init__(self) -> None:
        self.started_dt: str = ""
        self.started_ts: float = 0.0
        self.method: str = ""
        self.url: str = ""
        self.http_version: str = "HTTP/1.1"
        self.headers: List[Dict[str, str]] = []
        self.query_string: List[Dict[str, str]] = []
        self.post_data: Optional[Dict[str, Any]] = None
        self.headers_size: int = -1
        self.body_size: int = 0


class HARRecorder:
    """Records network traffic in HAR 1.2 format.

    Attaches Playwright request/response listeners to capture full
    request/response pairs including timing data from
    ``response.request.timing``.

    Usage::

        recorder = HARRecorder(browser)
        await recorder.start_recording("main")
        # ... navigate, interact ...
        await recorder.stop_recording("main")
        result = await recorder.save_recording("my_trace.har")
    """

    def __init__(self, browser: Any) -> None:
        """Initialise the recorder.

        Args:
            browser: An ``AgentBrowser`` instance whose pages will be observed.
        """
        self.browser = browser
        self._recording: bool = False
        self._page_id: Optional[str] = None
        self._entries: List[Dict[str, Any]] = []
        self._pages: List[Dict[str, Any]] = []
        self._start_time: Optional[float] = None
        self._recording_dir = Path(os.path.expanduser("~/.agent-os/recordings"))
        self._pending: Dict[str, _PendingRequest] = {}  # request key → pending
        self._request_listener = None
        self._response_listener = None
        self._failed_listener = None

    # ── Public API ───────────────────────────────────────────

    async def start_recording(self, page_id: str = "main") -> Dict[str, Any]:
        """Start recording network traffic in HAR 1.2 format.

        Attaches request and response listeners to the target page.
        Any previously recorded data is cleared.

        Args:
            page_id: Which tab/page to record.

        Returns:
            Dict with ``status`` and recording metadata.
        """
        if self._recording:
            return {
                "status": "error",
                "error": "Recording already in progress. Stop it first with har-stop.",
            }

        page = self.browser._pages.get(page_id, self.browser.page)
        if page is None:
            return {"status": "error", "error": f"Page '{page_id}' not found."}

        # Reset state
        self._entries.clear()
        self._pages.clear()
        self._pending.clear()
        self._start_time = time.time()
        self._page_id = page_id
        self._recording = True

        # Create page entry for HAR
        self._pages.append({
            "startedDateTime": _iso8601(self._start_time),
            "id": page_id,
            "title": "",  # filled at save time
            "pageTimings": {
                "onContentLoad": -1,
                "onLoad": -1,
            },
        })

        # Attach listeners
        self._request_listener = self._make_request_listener(page_id)
        self._response_listener = self._make_response_listener(page_id)
        self._failed_listener = self._make_failed_listener(page_id)

        page.on("request", self._request_listener)
        page.on("response", self._response_listener)
        page.on("requestfailed", self._failed_listener)

        logger.info("HAR recording started on page '%s'", page_id)
        return {
            "status": "recording",
            "page_id": page_id,
            "started_at": _iso8601(self._start_time),
        }

    async def stop_recording(self, page_id: str = "main") -> Dict[str, Any]:
        """Stop recording network traffic.

        Detaches listeners and returns the number of captured entries.

        Args:
            page_id: Which tab/page to stop recording.

        Returns:
            Dict with ``status``, ``entry_count``, and ``duration_seconds``.
        """
        if not self._recording:
            return {
                "status": "error",
                "error": "No recording in progress. Start one first with har-start.",
            }

        page = self.browser._pages.get(page_id, self.browser.page)

        # Detach listeners
        if page and self._request_listener:
            try:
                page.remove_listener("request", self._request_listener)
            except Exception:
                pass
        if page and self._response_listener:
            try:
                page.remove_listener("response", self._response_listener)
            except Exception:
                pass
        if page and self._failed_listener:
            try:
                page.remove_listener("requestfailed", self._failed_listener)
            except Exception:
                pass

        duration = time.time() - (self._start_time or time.time())
        entry_count = len(self._entries)
        self._recording = False

        # Flush any still-pending requests (no response received)
        self._flush_pending()

        logger.info(
            "HAR recording stopped on page '%s': %d entries in %.2fs",
            page_id, entry_count, duration,
        )
        return {
            "status": "stopped",
            "page_id": page_id,
            "entry_count": entry_count,
            "duration_seconds": round(duration, 2),
        }

    async def save_recording(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Save recorded traffic as a ``.har`` file.

        Writes the HAR 1.2 JSON to ``~/.agent-os/recordings/``.

        Args:
            filename: Custom filename. Auto-generated with timestamp if ``None``.

        Returns:
            Dict with ``status``, ``file_path``, ``file_size``, and ``entry_count``.
        """
        if not self._entries and not self._pending:
            return {
                "status": "error",
                "error": "No recorded entries to save. Start and stop a recording first.",
            }

        # Flush pending (requests that never got a response)
        self._flush_pending()

        # Try to grab page title for the page entry
        if self._pages and self._page_id:
            page = self.browser._pages.get(self._page_id, self.browser.page)
            if page:
                try:
                    self._pages[0]["title"] = await page.title()
                except Exception:
                    pass

        har: Dict[str, Any] = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "Agent-OS",
                    "version": "3.0",
                },
                "browser": {
                    "name": "Agent-OS Browser Engine",
                    "version": "3.0",
                },
                "pages": self._pages,
                "entries": self._entries,
            }
        }

        # Generate filename
        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"har_{ts}.har"
        if not filename.endswith(".har"):
            filename += ".har"

        # Ensure directory
        self._recording_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._recording_dir / filename

        try:
            with open(file_path, "w", encoding="utf-8") as fh:
                json.dump(har, fh, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.error("Failed to write HAR file: %s", exc)
            return {"status": "error", "error": str(exc)}

        file_size = file_path.stat().st_size
        entry_count = len(self._entries)

        logger.info("HAR saved: %s (%d bytes, %d entries)", file_path, file_size, entry_count)
        return {
            "status": "success",
            "file_path": str(file_path),
            "file_size": file_size,
            "entry_count": entry_count,
        }

    async def get_recording_status(self) -> Dict[str, Any]:
        """Return current recording state.

        Returns:
            Dict with ``recording``, ``entry_count``, ``duration_seconds``,
            ``page_id``, and ``started_at`` (ISO 8601).
        """
        if not self._recording:
            return {
                "status": "idle",
                "recording": False,
                "entry_count": len(self._entries),
            }

        duration = time.time() - (self._start_time or time.time())
        return {
            "status": "recording",
            "recording": True,
            "entry_count": len(self._entries),
            "pending_requests": len(self._pending),
            "duration_seconds": round(duration, 2),
            "page_id": self._page_id,
            "started_at": _iso8601(self._start_time) if self._start_time else None,
        }

    # ── Listeners (factory methods) ──────────────────────────

    def _make_request_listener(self, page_id: str):
        """Create a request event listener bound to *page_id*."""
        def _on_request(request) -> None:
            self._capture_request(request, page_id)
        return _on_request

    def _make_response_listener(self, page_id: str):
        """Create a response event listener bound to *page_id*."""
        async def _on_response(response) -> None:
            await self._capture_response(response, page_id)
        return _on_response

    def _make_failed_listener(self, page_id: str):
        """Create a requestfailed listener — marks request as errored."""
        def _on_failed(request) -> None:
            key = _request_key(request)
            pending = self._pending.pop(key, None)
            if pending is None:
                return
            entry = _build_entry(
                pending=pending,
                status=0,
                status_text=request.failure or "Failed",
                resp_headers=[],
                resp_body_size=0,
                content_mime="",
                content_text="",
                timing=None,
                page_id=page_id,
            )
            self._entries.append(entry)
        return _on_failed

    # ── Capture logic ────────────────────────────────────────

    def _capture_request(self, request: Any, page_id: str) -> None:
        """Capture request details and store as pending."""
        if not self._recording:
            return

        now = time.time()
        req_headers = _headers_to_list(request.headers)

        pending = _PendingRequest()
        pending.started_dt = _iso8601(now)
        pending.started_ts = now
        pending.method = request.method
        pending.url = request.url
        pending.http_version = _http_version_from_headers(req_headers)
        pending.headers = req_headers
        pending.query_string = _parse_query_string(request.url)
        pending.post_data = _extract_post_data(request)
        pending.headers_size = _estimate_headers_size(request.method, request.url, req_headers)
        pending.body_size = _body_size(request)

        key = _request_key(request)
        self._pending[key] = pending

    async def _capture_response(self, response: Any, page_id: str) -> None:
        """Capture response details and pair with pending request."""
        if not self._recording:
            return

        key = _request_key(response.request)
        pending = self._pending.pop(key, None)
        if pending is None:
            # Response arrived without a captured request — build from scratch
            pending = _PendingRequest()
            pending.started_dt = _iso8601(time.time())
            pending.started_ts = time.time()
            pending.method = response.request.method
            pending.url = response.request.url
            pending.headers = _headers_to_list(response.request.headers)
            pending.query_string = _parse_query_string(response.request.url)
            pending.post_data = _extract_post_data(response.request)
            pending.headers_size = -1
            pending.body_size = 0

        # Response headers
        resp_headers = _headers_to_list(response.headers)

        # Response body (capped)
        content_text = ""
        content_mime = response.headers.get("content-type", "")
        resp_body_size = 0
        try:
            resp_body_size = int(response.headers.get("content-length", 0))
        except (ValueError, TypeError):
            pass

        # Only capture body text for text-like responses < 1 MB
        if _is_text_content(content_mime) and resp_body_size <= MAX_BODY_CAPTURE_BYTES:
            try:
                body_bytes = await response.body()
                resp_body_size = len(body_bytes)
                if resp_body_size <= MAX_BODY_CAPTURE_BYTES:
                    content_text = body_bytes.decode("utf-8", errors="replace")
                else:
                    content_text = f"[Body truncated: {resp_body_size} bytes exceeds 1 MB limit]"
            except Exception:
                pass

        # Timing
        timing = None
        try:
            timing = response.request.timing
        except Exception:
            pass

        entry = _build_entry(
            pending=pending,
            status=response.status,
            status_text=response.status_text,
            resp_headers=resp_headers,
            resp_body_size=resp_body_size,
            content_mime=content_mime,
            content_text=content_text,
            timing=timing,
            page_id=page_id,
        )
        self._entries.append(entry)

    def _flush_pending(self) -> None:
        """Flush all pending requests as entries with no response."""
        for key, pending in list(self._pending.items()):
            entry = _build_entry(
                pending=pending,
                status=0,
                status_text="(no response)",
                resp_headers=[],
                resp_body_size=0,
                content_mime="",
                content_text="",
                timing=None,
                page_id=self._page_id or "main",
            )
            self._entries.append(entry)
        self._pending.clear()


# ─── Helpers ──────────────────────────────────────────────────

def _iso8601(ts: float) -> str:
    """Convert epoch seconds to ISO 8601 with timezone."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _request_key(request: Any) -> str:
    """Generate a unique key for request/response pairing."""
    # Playwright exposes request.navigation for navigation requests;
    # non-navigation requests share the same URL but differ by timing.
    # We use url + method + id() as a robust key.
    return f"{request.method}:{request.url}:{id(request)}"


def _headers_to_list(headers: Dict[str, str]) -> List[Dict[str, str]]:
    """Convert a headers dict to HAR headers list format."""
    return [{"name": k, "value": str(v)} for k, v in headers.items()]


def _parse_query_string(url: str) -> List[Dict[str, str]]:
    """Parse URL query string into HAR queryString format."""
    from urllib.parse import urlparse, parse_qs
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        result = []
        for name, values in qs.items():
            for value in values:
                result.append({"name": name, "value": value})
        return result
    except Exception:
        return []


def _extract_post_data(request: Any) -> Optional[Dict[str, Any]]:
    """Extract POST data from a request in HAR format."""
    try:
        post_data = request.post_data
        if post_data is None:
            return None

        mime = request.headers.get("content-type", "application/octet-stream")
        result: Dict[str, Any] = {
            "mimeType": mime,
            "text": post_data,
        }

        # Try to parse form data
        if "application/x-www-form-urlencoded" in mime:
            from urllib.parse import parse_qs
            parsed = parse_qs(post_data, keep_blank_values=True)
            params = []
            for name, values in parsed.items():
                for value in values:
                    params.append({"name": name, "value": value})
            result["params"] = params

        return result
    except Exception:
        return None


def _http_version_from_headers(headers: List[Dict[str, str]]) -> str:
    """Guess HTTP version from headers."""
    for h in headers:
        if h["name"].lower() == ":status":
            return "h2"
    return "HTTP/1.1"


def _estimate_headers_size(method: str, url: str, headers: List[Dict[str, str]]) -> int:
    """Estimate request headers size in bytes."""
    try:
        from urllib.parse import urlparse
        path = urlparse(url).path or "/"
        first_line = f"{method} {path} HTTP/1.1\r\n"
        header_lines = "".join(f"{h['name']}: {h['value']}\r\n" for h in headers)
        return len(first_line.encode("utf-8")) + len(header_lines.encode("utf-8")) + 2
    except Exception:
        return -1


def _body_size(request: Any) -> int:
    """Estimate request body size."""
    try:
        pd = request.post_data
        if pd:
            return len(pd.encode("utf-8"))
    except Exception:
        pass
    return 0


def _is_text_content(content_type: str) -> bool:
    """Check if a Content-Type indicates text content."""
    ct = content_type.lower()
    text_types = (
        "text/", "application/json", "application/xml", "application/javascript",
        "application/xhtml", "application/x-www-form-urlencoded", "application/svg",
        "image/svg+xml",
    )
    return any(t in ct for t in text_types)


def _parse_timing(timing: Optional[Dict]) -> Dict[str, float]:
    """Convert Playwright timing to HAR timings format.

    Playwright timing keys:
        startTime, domainLookupStart, domainLookupEnd,
        connectStart, connectEnd, requestStart, responseStart, responseEnd

    HAR timings keys:
        blocked, dns, connect, send, wait, receive, ssl
    """
    if not timing:
        return {"blocked": -1, "dns": -1, "connect": -1, "send": -1,
                "wait": -1, "receive": -1, "ssl": -1}

    def _diff(a: str, b: str) -> float:
        va = timing.get(a, -1)
        vb = timing.get(b, -1)
        if va < 0 or vb < 0:
            return -1
        return round(vb - va, 2)

    dns = _diff("domainLookupStart", "domainLookupEnd")
    connect = _diff("connectStart", "connectEnd")
    send = _diff("requestStart", "responseStart")
    receive = _diff("responseStart", "responseEnd")

    # SSL time is included in connect if HTTPS
    ssl = -1
    if timing.get("secureConnectionStart", -1) >= 0:
        ssl = _diff("secureConnectionStart", "connectEnd")

    # blocked = time before DNS starts
    blocked = -1
    if timing.get("startTime", -1) >= 0 and timing.get("domainLookupStart", -1) >= 0:
        blocked = round(timing["domainLookupStart"] - timing["startTime"], 2)

    total = round(
        max(0, timing.get("responseEnd", 0) - timing.get("startTime", 0)),
        2,
    )

    return {
        "blocked": blocked,
        "dns": dns,
        "connect": connect,
        "send": send if send >= 0 else 0,
        "wait": send if send >= 0 else -1,
        "receive": receive if receive >= 0 else 0,
        "ssl": ssl,
    }


def _build_entry(
    pending: _PendingRequest,
    status: int,
    status_text: str,
    resp_headers: List[Dict[str, str]],
    resp_body_size: int,
    content_mime: str,
    content_text: str,
    timing: Optional[Dict],
    page_id: str,
) -> Dict[str, Any]:
    """Build a single HAR entry dict."""
    har_timings = _parse_timing(timing)

    # Total time
    total_time = sum(
        max(0, v) for v in har_timings.values() if isinstance(v, (int, float)) and v >= 0
    )

    # Response headers size estimate
    resp_headers_size = sum(
        len(h["name"]) + len(h["value"]) + 4 for h in resp_headers
    ) + len("HTTP/1.1  \r\n") + 4

    return {
        "startedDateTime": pending.started_dt,
        "time": round(total_time, 2),
        "request": {
            "method": pending.method,
            "url": pending.url,
            "httpVersion": pending.http_version,
            "headers": pending.headers,
            "queryString": pending.query_string,
            "postData": pending.post_data,
            "headersSize": pending.headers_size,
            "bodySize": pending.body_size,
        },
        "response": {
            "status": status,
            "statusText": status_text,
            "httpVersion": pending.http_version,
            "headers": resp_headers,
            "content": {
                "size": resp_body_size,
                "mimeType": content_mime or "application/octet-stream",
                "text": content_text,
            },
            "headersSize": resp_headers_size,
            "bodySize": resp_body_size,
        },
        "cache": {},
        "timings": har_timings,
        "pageref": page_id,
    }
