from pydantic import HttpUrl

from seo_optimizer.contracts import Evidence, utc_now
from seo_optimizer.evidence_archive import archive_evidence


def test_archived_evidence_retains_scope_and_observed_canonicals_without_cookies():
    item = Evidence(
        id="http",
        tenant_id="tenant",
        project_id="project",
        environment="production",
        kind="http",
        url=HttpUrl("https://example.test"),
        collected_at=utc_now(),
        observation="Collected response",
        data={
            "status_code": 200,
            "headers": {"set-cookie": "private-session", "X-Robots-Tag": "noindex"},
            "html": '<title>Example</title><link rel="canonical" href="https://example.test/a">'
            '<link rel="canonical" href="https://example.test/b">',
        },
    )
    record = archive_evidence([item])[0]
    assert record["tenant_id"] == "tenant" and record["project_id"] == "project"
    assert record["data"]["canonical_urls"] == ["https://example.test/a", "https://example.test/b"]
    assert "private-session" not in str(record)
    assert record["data"]["headers"] == {"X-Robots-Tag": "noindex"}
    assert Evidence.model_validate(record).id == item.id


def test_budget_keeps_identifiers_and_explicitly_records_missing_details():
    source = Evidence(
        id="source",
        tenant_id="tenant",
        project_id="project",
        environment="production",
        kind="source",
        source_file="web/index.html",
        collected_at=utc_now(),
        observation="Read file",
        data={"text": "example " * 1000},
    )
    record = archive_evidence([source], budget=1)[0]
    assert record["id"] == "source"
    assert record["data"]["dependency"] == "Evidence archive budget reached"
    assert source.data["text"] == "example " * 1000
