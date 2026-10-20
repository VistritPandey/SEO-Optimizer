"""Body copy requires a grounded content task; model repairs may correct observed links."""

import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.contracts import Evidence
from seo_optimizer.execution import confined
from seo_optimizer.navigation import literal_link_changes


def validate_model_body(
    root: Path,
    spec: ProjectSpec,
    change: FileChange,
    evidence: list[Evidence],
) -> None:
    target = confined(root, change.path, spec.allowed_paths)
    if target.suffix.lower() == ".md":
        raise ValueError("Original body copy requires a supported content task")
    framework = target.suffix.lower() in {".tsx", ".jsx", ".js", ".ts"}
    if target.suffix.lower() != ".html" and not (framework and change.check_id == "tech.links"):
        return
    original = target.read_text()
    updated = original.replace(change.before, change.after, 1)
    if framework:
        changed_links = literal_link_changes(original, updated)
    else:
        changed_links = html_link_changes(original, updated)
    validate_destinations(spec, change, evidence, changed_links)


def html_link_changes(original: str, updated: str) -> list[tuple[str, str]]:
    old = re.search(r"<body\b[^>]*>.*?</body>", original, re.S | re.I)
    new = re.search(r"<body\b[^>]*>.*?</body>", updated, re.S | re.I)
    if old is None or new is None:
        raise ValueError("HTML model repairs require an inspectable document body")
    if old.group() == new.group():
        return []
    anchor = re.compile(r"<a\b[^>]*>", re.I)
    href = re.compile(r"\bhref\s*=\s*([\'\"])(.*?)\1", re.I)

    def without_links(body: str) -> str:
        return anchor.sub(lambda match: href.sub('href=""', match.group()), body)

    if re.sub(r"\s+", " ", without_links(old.group())) != re.sub(
        r"\s+", " ", without_links(new.group())
    ):
        raise ValueError("Model body copy is not claim-verified; use a supported content task")
    old_links = [href.search(a) for a in anchor.findall(old.group())]
    new_links = [href.search(a) for a in anchor.findall(new.group())]
    if len(old_links) != len(new_links):
        raise ValueError("Model repair alters navigation structure")
    return [
        (before[2], after[2])
        for before, after in zip(old_links, new_links, strict=True)
        if before is not None and after is not None and before[2] != after[2]
    ]


def validate_destinations(
    spec: ProjectSpec, change: FileChange, evidence: list[Evidence], links: list[tuple[str, str]]
) -> None:
    routes = [route for route, path in spec.route_map.items() if path == change.path]
    pages = [e for e in evidence if e.kind == "http" and e.data.get("status_code") == 200]
    intents = {urlparse(route).path or "/": value for route, value in spec.page_intents.items()}
    for before, after in links:
        supported = False
        for route in routes:
            page_url = urljoin(str(spec.website_url), route)
            old_url, new_url = urljoin(page_url, before), urljoin(page_url, after)
            broken = False
            for page in pages:
                statuses = page.data.get("link_status")
                status = statuses.get(old_url) if isinstance(statuses, dict) else None
                if str(page.url) == page_url and type(status) is int and status in {404, 410}:
                    broken = True
            observed = any(str(e.url) == new_url for e in pages)
            public = intents.get(urlparse(new_url).path, spec.environment == "production")
            if broken and observed and public:
                supported = True
                break
        if not supported:
            raise ValueError(
                "Navigation change lacks an observed broken link and public destination"
            )
