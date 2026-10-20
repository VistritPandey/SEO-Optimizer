import pytest

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.contracts import Evidence, utc_now
from seo_optimizer.knowledge import load_knowledge
from seo_optimizer.scanner import context, scan


@pytest.mark.parametrize("intent,expected", [(None, "unresolved"), (True, "defect"), (False, None)])
def test_live_noindex_requires_owner_confirmed_page_intent(intent, expected):
    spec = ProjectSpec(
        name="Website",
        website_url="https://example.test/",
        page_intents={} if intent is None else {"/account": intent},
    )
    evidence = Evidence(
        id="account-response",
        tenant_id="tenant",
        project_id="site",
        environment="production",
        kind="http",
        url="https://example.test/account",
        observation="Collected account landing page",
        collected_at=utc_now(),
        data={
            "status_code": 200,
            "html": '<title>Account</title><meta name="robots" content="noindex">',
        },
    )
    findings, coverage = scan(context("tenant", "site", spec), spec, [evidence], load_knowledge())
    indexing = [finding for finding in findings if finding.check_id == "tech.indexability"]
    if expected is None:
        assert not indexing
    else:
        assert len(indexing) == 1 and indexing[0].status == expected
        if intent is None:
            assert indexing[0].dependencies
            assert not indexing[0].action.automatic
            assert (
                next(
                    item["state"]
                    for item in coverage["coverage"]
                    if item["check_id"] == "tech.indexability"
                )
                == "needs_data"
            )


@pytest.mark.parametrize(
    "tag,defect",
    [
        ('<meta name="description" content="">', True),
        ('<meta name="description" content="   ">', True),
        ('<meta name="description">', True),
        ('<meta content="Observed lamp guide" name="DESCRIPTION">', False),
    ],
)
def test_empty_description_cannot_establish_a_metadata_pass(tag, defect):
    spec = ProjectSpec(name="Website", website_url="https://example.test/")
    evidence = Evidence(
        id="response",
        tenant_id="tenant",
        project_id="site",
        environment="production",
        kind="http",
        url="https://example.test/",
        observation="Fixture response",
        collected_at=utc_now(),
        data={"status_code": 200, "html": "<title>Guide</title>" + tag},
    )
    findings, _ = scan(context("tenant", "site", spec), spec, [evidence], load_knowledge())
    assert any(f.check_id == "tech.metadata" and f.status == "defect" for f in findings) is defect
