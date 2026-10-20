"""Conservative literal anchor edits, independent of model intent or prose."""

import re

TAGS = re.compile(r"<(?:a|Link)\b[^<>]*>")
HREF = re.compile(r"(?<![\w-])href\s*=\s*(['\"])([^'\"<>\r\n]*)\1")


def literal_link_changes(original: str, updated: str) -> list[tuple[str, str]]:
    """Permit only root-relative quoted href changes; preserve all other bytes."""

    def extract(text: str) -> tuple[str, list[str]]:
        links = []

        def tag(match: re.Match[str]) -> str:
            value = match.group()
            attrs = list(HREF.finditer(value))
            if len(attrs) != 1:
                return value
            attr = attrs[0]
            links.append(attr[2])
            return value[: attr.start(2)] + "__OPTIMISER_HREF__" + value[attr.end(2) :]

        return TAGS.sub(tag, text), links

    before, old_links = extract(original)
    after, new_links = extract(updated)
    if before != after or len(old_links) != len(new_links):
        raise ValueError("Navigation repair must preserve all code, copy and other attributes")
    changed = [(a, b) for a, b in zip(old_links, new_links, strict=True) if a != b]
    if not changed or any(
        not value.startswith("/") or value.startswith("//") or re.search(r"[\s{}\\]", value)
        for pair in changed
        for value in pair
    ):
        raise ValueError("Navigation repair requires static same-site root-relative hrefs")
    return changed
