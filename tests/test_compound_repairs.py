"""Several defects may share a file; every scope and behavior guard still applies."""

import pytest

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.execution import apply_changes
from seo_optimizer.llm import pending_repairs

ORIGINAL = (
    "<html><head><title>Cedar lamps</title></head><body><main>"
    '<a href="/missing" class="link">Collection</a></main></body></html>'
)
UPDATED = ORIGINAL.replace(
    "</title>", '</title><meta name="description" content="Cedar lamps">'
).replace("/missing", "/shop/")


def fixture(tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "web/index.html").write_text(ORIGINAL)
    spec = ProjectSpec(
        name="Workshop",
        website_url="https://example.test/",
        allowed_paths=["web"],
        route_map={"/": "web/index.html"},
        check_commands=[["python", "verify.py"]],
    )
    change = FileChange(
        path="web/index.html",
        before=ORIGINAL,
        after=UPDATED,
        reason="Repair confirmed metadata and navigation",
        check_id="tech.links",
        related_check_ids=["tech.metadata"],
        evidence_ids=["page"],
    )
    return spec, change


def test_combined_static_head_and_link_repairs_remain_one_file_proposal(tmp_path):
    spec, change = fixture(tmp_path)
    files = apply_changes(tmp_path, spec, [change], {"page"}, change.check_ids)
    assert files == {"web/index.html": UPDATED}
    from seo_optimizer.application_models import AgentDecision

    request = {
        "repair_targets": [{"check_id": id, "evidence_ids": ["page"]} for id in change.check_ids]
    }
    assert pending_repairs(request, AgentDecision(changes=[change]), []) == []


@pytest.mark.parametrize(
    "attack",
    [
        "copy",
        "script",
        "handler",
        "privacy",
        "unknown",
        "undeclared",
        "no_checks",
        "executable_head",
    ],
)
def test_combined_repairs_do_not_expand_write_authority(tmp_path, attack):
    spec, change = fixture(tmp_path)
    allowed = set(change.check_ids)
    if attack == "copy":
        change.after = change.after.replace("Collection", "Invented reviews")
    elif attack == "script":
        change.after = change.after.replace("</body>", "<script>steal()</script></body>")
    elif attack == "handler":
        change.after = change.after.replace('class="link"', 'class="link" onclick="steal()"')
    elif attack == "privacy":
        spec.page_intents = {"/": False}
    elif attack == "unknown":
        change.related_check_ids.append("not.a.confirmed.check")
    elif attack == "undeclared":
        change.related_check_ids = []
    elif attack == "no_checks":
        spec.check_commands = []
    elif attack == "executable_head":
        change.after = change.after.replace("</head>", "<style>body{display:none}</style></head>")
    with pytest.raises(ValueError):
        apply_changes(tmp_path, spec, [change], {"page"}, allowed)
    assert (tmp_path / "web/index.html").read_text() == ORIGINAL


def test_whole_file_metadata_proposal_is_judged_by_actual_changed_bytes(tmp_path):
    spec, change = fixture(tmp_path)
    change.check_id, change.related_check_ids = "tech.metadata", []
    change.after = UPDATED.replace("/shop/", "/missing")
    assert apply_changes(tmp_path, spec, [change], {"page"}, {"tech.metadata"})
