"""Audit the served public website, not source-code strings. No credentials or model calls."""

import argparse
import json
import struct
import traceback
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import httpx

CANONICAL = "https://youroptimiser.com"
PAGES = (
    "/",
    "/how-it-works",
    "/seo-and-ai-search",
    "/guides/continuous-seo",
    "/security",
    "/contact",
    "/privacy",
    "/terms",
    "/blog",
    "/blog/what-is-an-autonomous-seo-agent",
    "/blog/seo-checklist-after-a-website-update",
    "/blog/seo-and-geo-what-to-fix-first",
)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.title = ""
        self.headings = []
        self.links = []
        self.ids = set()
        self.meta = {}
        self.canonical = ""
        self.schemas = []
        self._title = False
        self._json = False
        self._script = ""
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        value = dict(attrs)
        if value.get("id"):
            self.ids.add(value["id"])
        if tag == "title":
            self._title = True
        if tag == "h1":
            self.headings.append(tag)
        if tag == "a" and value.get("href"):
            self.links.append(value["href"])
        if tag == "meta":
            key = value.get("name") or value.get("property")
            if key:
                self.meta[key] = value.get("content", "")
        if tag == "link" and value.get("rel") == "canonical":
            self.canonical = value["href"]
        if tag == "script" and value.get("type") == "application/ld+json":
            self._json = True
            self._script = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False
        if tag == "script" and self._json:
            self.schemas.append(json.loads(self._script))
            self._json = False

    def handle_data(self, data):
        if self._title:
            self.title += data
        if self._json:
            self._script += data


def check_public_site(base_url, passed=None, verify_www=True):
    if passed is None:
        passed = []
    documents, titles = {}, set()
    with httpx.Client(base_url=base_url, timeout=45, follow_redirects=False) as client:
        for path in PAGES:
            response = client.get(path)
            assert response.status_code == 200, f"{path}: HTTP {response.status_code}"
            document = Document(response.text)
            documents[path] = document
            assert len(document.headings) == 1, f"{path}: expected one H1"
            assert document.title and document.title not in titles, f"{path}: duplicate/empty title"
            titles.add(document.title)
            assert document.meta.get("description"), f"{path}: missing description"
            assert "noindex" not in document.meta.get("robots", ""), f"{path}: not indexable"
            assert document.canonical.rstrip("/") == (CANONICAL + path).rstrip("/"), (
                f"{path}: incorrect canonical {document.canonical}"
            )
            assert document.meta.get("og:image", "").startswith(CANONICAL), (
                f"{path}: missing absolute social image"
            )
            assert document.meta.get("twitter:card") == "summary_large_image"
        passed.append(
            f"{len(PAGES)} public pages: served HTML, one H1, unique titles, descriptions, "
            "canonical and social metadata"
        )

        for path in ("/login", "/dashboard"):
            response = client.get(path)
            assert response.status_code == 200
            document = Document(response.text)
            assert "noindex" in document.meta.get("robots", "")
            assert "noindex" in response.headers.get("x-robots-tag", "")
            assert "index" not in document.meta.get("googlebot", "").replace("noindex", "")
        passed.append("Sign-in and workspace pages carry noindex in HTML and HTTP headers")

        sitemap = client.get("/sitemap.xml")
        assert sitemap.status_code == 200
        assert "application/xml" in sitemap.headers.get("content-type", "")
        assert "noindex" not in sitemap.headers.get("x-robots-tag", "")
        bot_sitemap = client.get("/sitemap.xml", headers={"User-Agent": "Googlebot"})
        assert bot_sitemap.status_code == 200
        assert bot_sitemap.content == sitemap.content
        root = ElementTree.fromstring(sitemap.content)
        locations = {element.text.rstrip("/") for element in root.findall("{*}url/{*}loc")}
        assert locations == {(CANONICAL + path).rstrip("/") for path in PAGES}
        robots = client.get("/robots.txt")
        assert robots.status_code == 200 and f"Sitemap: {CANONICAL}/sitemap.xml" in robots.text
        policy = RobotFileParser()
        policy.parse(robots.text.splitlines())
        assert policy.can_fetch("Googlebot", CANONICAL + "/sitemap.xml")
        assert all(policy.can_fetch("Googlebot", CANONICAL + path) for path in PAGES)
        assert not policy.can_fetch("Googlebot", CANONICAL + "/api/v1/projects")
        passed.append(
            "Sitemap includes public canonical pages only; "
            "robots allows them and excludes API crawling"
        )

        index = client.get("/llms.txt")
        assert index.status_code == 200 and "text/plain" in index.headers["content-type"]
        assert all(CANONICAL + path in index.text for path in PAGES)
        assert "not a ranking mechanism" in index.text
        passed.append("LLM product index is readable, links to public facts and states its limits")

        schemas = documents["/"].schemas
        assert schemas
        graph = schemas[0]["@graph"]
        assert {item["@type"] for item in graph} == {
            "Organization",
            "WebSite",
            "SoftwareApplication",
        }
        application = next(item for item in graph if item["@type"] == "SoftwareApplication")
        assert application["offers"]["price"] == "0" and application["url"] == CANONICAL
        assert not any("aggregateRating" in item for item in graph)
        passed.append(
            "Structured data describes the real product and free offer "
            "without fabricated reviews or FAQ rich-result markup"
        )

        for path, size in (
            ("/icon.png", (64, 64)),
            ("/apple-icon.png", (180, 180)),
            ("/opengraph-image", (1200, 630)),
        ):
            response = client.get(path)
            assert response.status_code == 200 and response.content.startswith(b"\x89PNG")
            assert struct.unpack(">II", response.content[16:24]) == size
        passed.append(
            "Favicon, Apple touch icon and branded social image have correct PNG dimensions"
        )

        visited = set(PAGES)
        for source, document in documents.items():
            for href in document.links:
                target = urlparse(urljoin(CANONICAL + source, href))
                if target.hostname != "youroptimiser.com":
                    continue
                path = target.path or "/"
                if path not in visited:
                    response = client.head(path) if path.endswith(".mp4") else client.get(path)
                    assert response.status_code == 200, f"Broken link {source} → {href}"
                    visited.add(path)
                if target.fragment and path in documents:
                    assert target.fragment in documents[path].ids, f"Missing anchor {href}"
        passed.append("Every internal navigation link and in-page anchor resolves")

        assert client.get("/this-page-does-not-exist").status_code == 404
        if verify_www:
            redirect = client.get("/privacy", headers={"Host": "www.youroptimiser.com"})
            assert (
                redirect.status_code == 308
                and redirect.headers["location"] == CANONICAL + "/privacy"
            )
            passed.append(
                "www host normalises to the canonical apex domain with a permanent redirect"
            )
        assert client.get("/api/backend/projects").status_code == 401
        passed.append("Unknown pages return 404 and workspace API access stays protected")
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3002")
    parser.add_argument("--report", type=Path, default=Path("reports/public-site-qa.json"))
    parser.add_argument(
        "--skip-host-redirect",
        action="store_true",
        help="Skip Host-header checks behind an external proxy; record as unverified",
    )
    args = parser.parse_args()
    report = {
        "environment": args.base_url,
        "passed": [],
        "failed": [],
        "model_calls": 0,
        "unverified": [
            "Search indexing and rankings",
            "AI citation outcomes",
            "Field Core Web Vitals",
            "Real customer sign-in and GitHub lifecycle",
        ],
    }
    try:
        check_public_site(args.base_url, report["passed"], verify_www=not args.skip_host_redirect)
    except (AssertionError, httpx.HTTPError, ValueError, ElementTree.ParseError) as error:
        frame = traceback.extract_tb(error.__traceback__)[-1]
        report["failed"].append(str(error) or f"{type(error).__name__} at line {frame.lineno}")
    if args.skip_host_redirect:
        report["unverified"].append("Public www redirect: verify after alias DNS and TLS are ready")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return int(bool(report["failed"]))


if __name__ == "__main__":
    raise SystemExit(main())
