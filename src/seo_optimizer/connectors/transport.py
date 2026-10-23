"Bounded provider transport: no redirects, no automatic retries of writes, no secret errors."

import base64
import json
import re
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from seo_optimizer.connectors.models import ConnectionInput
from seo_optimizer.crawler import Crawler


class ConnectorError(ValueError):
    def __init__(self, code: str, message: str, retry_after: int = 0):
        super().__init__(message)
        self.code, self.retry_after = code, retry_after


def segment(value: str) -> str:
    from urllib.parse import quote

    if not value or len(value) > 500 or any(x in value for x in ["..", "\\", "\x00", "?", "#"]):
        raise ConnectorError("configuration", "Invalid provider resource identifier")
    return quote(value, safe="")


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", value):
        raise ConnectorError("configuration", "Invalid provider account identifier")
    return value


class Transport:
    def __init__(
        self,
        connection: ConnectionInput,
        client: httpx.Client | None = None,
        allow_private: bool = False,
    ):
        self.connection = connection
        self.client = client or httpx.Client(timeout=25, follow_redirects=False)
        self.owned = client is None
        self.allow_private = allow_private
        self.calls = 0

    def close(self) -> None:
        if self.owned:
            self.client.close()

    def secret(self, name: str = "access_token") -> str:
        value = self.connection.credentials.get(name, "")
        if not value:
            raise ConnectorError("credentials_required", f"Configure the {name} credential")
        return value

    def bearer(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self.secret()}

    def basic(self, username: str, password: str) -> dict[str, str]:
        raw = f"{self.secret(username)}:{self.secret(password)}"
        return {"Authorization": "Basic " + base64.b64encode(raw.encode()).decode()}

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        body: Any = None,
        params: dict[str, Any] | None = None,
        read_only: bool = True,
        dynamic: bool = False,
        raw: bool = False,
        form: dict[str, str] | None = None,
        multipart: bool = False,
    ) -> Any:
        self.calls += 1
        if self.calls > 30:
            raise ConnectorError("budget", "Connector request budget exhausted")
        target = httpx.URL(url)
        extensions: dict[str, Any] = {}
        request_headers = {"User-Agent": "YourOptimiser/1.0", **(headers or {})}
        if dynamic:
            # Pin self-hosted CMS addresses. Credentials never follow redirects or cross origins.
            checker = Crawler(self.connection.resource, self.allow_private, self.client)
            addresses = checker.check_url(url)
            if self.owned or not isinstance(self.client._transport, httpx.MockTransport):
                target = target.copy_with(host=addresses[0])
                request_headers["Host"] = httpx.URL(url).netloc.decode()
                extensions["sni_hostname"] = httpx.URL(url).host
        elif urlparse(url).scheme != "https":
            raise ConnectorError("configuration", "Provider endpoints require HTTPS")
        for attempt in range(2 if read_only else 1):
            try:
                with self.client.stream(
                    method,
                    target,
                    headers=request_headers,
                    json=body,
                    params=params,
                    data=None if multipart else form,
                    files={k: (None, v) for k, v in (form or {}).items()} if multipart else None,
                    extensions=extensions,
                    follow_redirects=False,
                ) as response:
                    content = bytearray()
                    for part in response.iter_bytes():
                        content.extend(part)
                        if len(content) > 2_000_000:
                            raise ConnectorError(
                                "response_limit", "Provider response exceeded 2 MB"
                            )
                    if response.status_code == 429:
                        retry = response.headers.get("Retry-After", "1")
                        seconds = min(int(retry), 300) if retry.isdigit() else 30
                        if read_only and attempt == 0 and seconds <= 2:
                            time.sleep(seconds)
                            continue
                        raise ConnectorError("rate_limited", "Provider rate limit reached", seconds)
                    if response.status_code in {401, 403}:
                        raise ConnectorError(
                            "reconnect_required",
                            "Provider rejected access; reconnect or check permissions",
                        )
                    if response.status_code in {409, 412}:
                        raise ConnectorError(
                            "conflict", "Provider content changed; collect a fresh proposal"
                        )
                    if not 200 <= response.status_code < 300:
                        raise ConnectorError(
                            "provider_error", f"Provider returned HTTP {response.status_code}"
                        )
                    if raw:
                        return bytes(content).decode("utf-8")
                    try:
                        value = json.loads(content) if content else {}
                    except (ValueError, UnicodeError):
                        raise ConnectorError(
                            "invalid_response", "Provider returned invalid JSON"
                        ) from None
                    if not isinstance(value, (dict, list)):
                        raise ConnectorError(
                            "invalid_response", "Provider returned an invalid document"
                        )
                    if isinstance(value, dict) and value.get("errors"):
                        raise ConnectorError(
                            "provider_error", "Provider rejected the requested operation"
                        )
                    return value
            except httpx.HTTPError:
                raise ConnectorError(
                    "transport_failed" if read_only else "write_uncertain",
                    "Provider connection failed"
                    if read_only
                    else "Write outcome is uncertain; inspect provider before retrying",
                ) from None
        raise ConnectorError("rate_limited", "Provider rate limit reached")
