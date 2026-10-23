"""Conservative source repair validation for new Git hosts, before creating a PR."""

import json
import re
from pathlib import PurePosixPath

from seo_optimizer.connectors.transport import ConnectorError

SEO_TAG = re.compile(
    r"<title\b[^>]*>.*?</title\s*>|<meta\b(?=[^>]*\b(?:name|property)\s*=\s*[\"\'](?:description|og:[a-z_:]+|twitter:[a-z_:]+)[\"\'])[^>]*>",
    re.I | re.S,
)


def validate_source_change(path: str, before: str, after: str) -> None:
    if not before or not after or len(after) > 100000 or before == after:
        raise ConnectorError("policy", "Source repair must be bounded and change observed content")
    suffix = PurePosixPath(path).suffix
    if suffix == ".html":
        if SEO_TAG.sub("", before) != SEO_TAG.sub("", after):
            raise ConnectorError("policy", "This Git connector permits HTML metadata repairs only")
        if len(re.findall(r"<title\b", after, re.I)) != 1:
            raise ConnectorError("policy", "Repaired HTML must have exactly one title")
        if re.search(r"<(?:script|iframe)\b", "".join(SEO_TAG.findall(after)), re.I):
            raise ConnectorError("policy", "Metadata cannot contain executable markup")
    elif suffix == ".json":
        try:
            old = json.loads(before)
            new = json.loads(after)
        except ValueError:
            raise ConnectorError("policy", "Source JSON must parse") from None
        keys = {"title", "description", "seo", "metadata", "openGraph", "twitter"}

        def protected(value: object, path: str = "") -> dict[str, object]:
            found: dict[str, object] = {}
            if isinstance(value, dict):
                for key, nested in value.items():
                    target = path + "/" + key
                    if re.search(
                        r"robots|index|status|canonical|rating|review|price|hours|training",
                        key,
                        re.I,
                    ):
                        found[target] = nested
                    else:
                        found.update(protected(nested, target))
            return found

        if protected(old) != protected(new):
            raise ConnectorError("policy", "Protected crawler or business fields cannot change")
        if (
            not isinstance(old, dict)
            or not isinstance(new, dict)
            or {k: v for k, v in old.items() if k not in keys}
            != {k: v for k, v in new.items() if k not in keys}
        ):
            raise ConnectorError("policy", "Only JSON metadata fields may change")
    else:
        raise ConnectorError(
            "unsupported",
            (
                "This repository adapter needs HTML or JSON metadata. Framework code repairs"
                " use the existing GitHub worker until framework validation is connected to "
                "this host."
            ),
        )


def validate_metadata_claims(before: str, after: str, claims: set[str], path: str) -> None:
    """A valid diff still cannot introduce claims unsupported by source text or owner facts."""
    from html import unescape
    from html.parser import HTMLParser
    from typing import Any

    class Meta(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.values: list[str] = []
            self.title = False

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "title":
                self.title = True
            if tag == "meta":
                content = dict(attrs).get("content")
                if content:
                    self.values.append(content)

        def handle_endtag(self, tag: str) -> None:
            if tag == "title":
                self.title = False

        def handle_data(self, data: str) -> None:
            if self.title:
                self.values.append(data)

    values: list[str] = []
    if path.endswith(".html"):
        parser = Meta()
        parser.feed(after)
        values = parser.values
    else:

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    walk(nested)
            elif isinstance(value, list):
                for nested in value:
                    walk(nested)
            elif isinstance(value, str):
                values.append(value)

        walk(json.loads(after))
    available = unescape(before + " " + re.sub(r"<[^>]*>", " ", before)).casefold()
    if path.endswith(".json"):
        available += json.dumps(json.loads(before), ensure_ascii=False).casefold()
    established = {value.casefold() for value in claims}
    structural = {"website", "article", "summary", "summary_large_image"}
    if any(
        value.strip()
        and value.casefold() not in available
        and value.casefold() not in established | structural
        for value in values
    ):
        raise ConnectorError(
            "policy", "Source metadata needs observed text or trusted project facts"
        )
