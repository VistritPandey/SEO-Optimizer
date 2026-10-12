"""Bounded, same-origin HTTP collection with address checks and optional browser evidence."""

import ipaddress
import re
import socket
import time
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urljoin, urlparse
from uuid import uuid4

import httpx
from pydantic import HttpUrl

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.audit import PageParser
from seo_optimizer.contracts import Evidence, utc_now


class CrawlError(RuntimeError):
    pass


class Crawler:
    def __init__(
        self, base_url: str, allow_private: bool = False, client: httpx.Client | None = None
    ):
        self.base_url = base_url
        self.host = urlparse(base_url).hostname
        self.allow_private = allow_private
        self.client = client or httpx.Client(
            timeout=15, follow_redirects=False, headers={"User-Agent": "SEOOptimizer/1.0"}
        )
        self.owns_client = client is None
        self.requests = 0
        self.deadline: float | None = None

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    def check_url(self, url: str) -> list[str]:
        parts = urlparse(url)
        if (
            parts.scheme not in {"http", "https"}
            or parts.username
            or parts.password
            or parts.hostname != self.host
        ):
            raise CrawlError("URL is outside the configured website")
        if parts.port and parts.port not in {80, 443} and not self.allow_private:
            raise CrawlError("Nonstandard website ports are disabled")
        try:
            addresses = {
                str(item[4][0])
                for item in socket.getaddrinfo(parts.hostname or "", parts.port or 443)
            }
        except socket.gaierror as error:
            raise CrawlError("Website hostname did not resolve") from error
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if (
                ip.is_link_local
                or ip.is_multicast
                or ip.is_unspecified
                or (not ip.is_global and not self.allow_private)
            ):
                raise CrawlError("Website resolves to a restricted network address")
        return sorted(addresses, key=lambda value: ipaddress.ip_address(value).version)

    def fetch(self, url: str) -> httpx.Response:
        for _ in range(6):
            if self.deadline is not None:
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    raise CrawlError("Crawl time budget exhausted")
                self.client.timeout = httpx.Timeout(min(15, remaining))
            addresses = self.check_url(url)
            self.requests += 1
            if self.requests > 250:
                raise CrawlError("Crawl request budget exhausted")
            # Resolve again for every hop. No model-supplied off-origin fetches.
            original = httpx.URL(url)
            pinned = original.copy_with(host=addresses[0])
            with self.client.stream(
                "GET",
                pinned,
                headers={"Host": original.netloc.decode()},
                extensions={"sni_hostname": original.host},
            ) as streamed:
                body = bytearray()
                for chunk in streamed.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 2_000_000:
                        raise CrawlError("Page response exceeded the size limit")
                response = httpx.Response(
                    streamed.status_code,
                    headers={
                        key: value
                        for key, value in streamed.headers.items()
                        if key.lower()
                        not in {"content-encoding", "content-length", "transfer-encoding"}
                    },
                    content=bytes(body),
                    request=httpx.Request("GET", url),
                )
            if response.status_code not in {301, 302, 303, 307, 308}:
                return response
            url = urljoin(url, response.headers.get("location", ""))
        raise CrawlError("Redirect chain exceeded the limit")

    def collect(
        self, tenant: str, project: str, spec: ProjectSpec, seeds: list[str] | None = None
    ) -> list[Evidence]:
        if self.deadline is None:
            self.deadline = time.monotonic() + min(120, spec.max_job_seconds / 2)
        queue = deque(seeds or [str(spec.website_url)])
        visited: set[str] = set()
        evidence: list[Evidence] = []
        robots, sitemap = "", ""
        for path in ("robots.txt", "sitemap.xml"):
            try:
                response = self.fetch(urljoin(self.base_url, "/" + path))
                if response.status_code == 200:
                    if path == "robots.txt":
                        robots = response.text
                    else:
                        sitemap = response.text
            except (httpx.HTTPError, CrawlError):
                pass
        while queue and len(evidence) < spec.max_pages:
            if time.monotonic() >= self.deadline:
                break
            url = urldefrag(queue.popleft())[0]
            if url in visited:
                continue
            visited.add(url)
            try:
                response = self.fetch(url)
            except (httpx.HTTPError, CrawlError) as error:
                evidence.append(
                    Evidence(
                        id=str(uuid4()),
                        tenant_id=tenant,
                        project_id=project,
                        environment=spec.environment,
                        kind="http",
                        url=HttpUrl(url),
                        observation="Page collection failed",
                        collected_at=utc_now(),
                        data={"collection_error": type(error).__name__},
                    )
                )
                continue
            if "html" not in response.headers.get("content-type", "text/html"):
                continue
            parser = PageParser()
            parser.feed(response.text)
            links: dict[str, int] = {}
            for href in parser.links[:30]:
                linked = urldefrag(urljoin(str(response.url), href))[0]
                if urlparse(linked).hostname != self.host or href.startswith("#"):
                    continue
                if urlparse(linked).path.lower().endswith((".png", ".jpg", ".pdf", ".zip")):
                    continue
                if linked not in visited:
                    queue.append(linked)
                if linked not in links:
                    try:
                        links[linked] = self.fetch(linked).status_code
                    except (httpx.HTTPError, CrawlError):
                        pass
            data: dict[str, Any] = {
                "status_code": response.status_code,
                "html": response.text,
                "headers": {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower() in {"x-robots-tag", "link", "content-type"}
                },
                "link_status": links,
                "robots_txt": robots,
                "sitemap_xml": sitemap,
                "final_url": str(response.url),
            }
            evidence.append(
                Evidence(
                    id=str(uuid4()),
                    tenant_id=tenant,
                    project_id=project,
                    environment=spec.environment,
                    kind="http",
                    url=HttpUrl(url),
                    observation="Collected live HTTP page and same-origin link responses",
                    collected_at=utc_now(),
                    data=data,
                )
            )
        return evidence


def capture_browser(
    url: str, crawler: Crawler, tenant: str, project: str, environment: str, output: Path
) -> list[Evidence]:
    from playwright.sync_api import sync_playwright

    crawler.check_url(url)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel="chromium")
        context = browser.new_context(
            viewport={"width": 1280, "height": 900}, service_workers="block"
        )

        def route(request: Any) -> None:
            try:
                if request.request.method != "GET":
                    request.abort()
                    return
                response = crawler.fetch(request.request.url)
                request.fulfill(
                    status=response.status_code,
                    headers=dict(response.headers),
                    body=response.content,
                )
            except (CrawlError, httpx.HTTPError):
                request.abort()

        context.route("**/*", route)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        html = page.content()
        screenshot = output / "page.png"
        page.screenshot(path=str(screenshot), full_page=True)
        context.close()
        browser.close()
    return [
        Evidence(
            id=str(uuid4()),
            tenant_id=tenant,
            project_id=project,
            environment=environment,
            kind="dom",
            url=HttpUrl(url),
            collected_at=utc_now(),
            observation="Observed rendered browser DOM",
            data={"html": html},
        ),
        Evidence(
            id=str(uuid4()),
            tenant_id=tenant,
            project_id=project,
            environment=environment,
            kind="screenshot",
            url=HttpUrl(url),
            collected_at=utc_now(),
            screenshot=str(screenshot),
            observation="Captured desktop viewport screenshot",
        ),
    ]


def page_excerpt(html: str) -> str:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()[:3000]
