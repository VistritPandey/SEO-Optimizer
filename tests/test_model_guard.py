from pathlib import Path

import pytest

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.contracts import Evidence, utc_now
from seo_optimizer.model_guard import validate_model_body


def test_body_claims_cannot_bypass_gate_with_known_fact_ids(tmp_path):
    (tmp_path / "web").mkdir()
    path = tmp_path / "web/index.html"
    path.write_text(
        "<html><head><title>Guide</title></head><body><main>Observed text</main></body></html>"
    )
    spec = ProjectSpec(name="Guide", website_url="https://example.test/", allowed_paths=["web"])
    change = FileChange(
        path="web/index.html",
        before="Observed text",
        after="Invented five-star reviews",
        check_id="content.factual",
        reason="Unsupported claim",
        evidence_ids=["source"],
        fact_ids=["known-fact"],
    )
    with pytest.raises(ValueError, match="claim-verified"):
        validate_model_body(tmp_path, spec, change, [])


@pytest.mark.parametrize(
    "destination,status", [("/shop/", 404), ("/unknown/", 404), ("/shop/", 200), ("/private/", 404)]
)
def test_navigation_repair_requires_observed_failure_and_public_target(
    tmp_path, destination, status
):
    (tmp_path / "web").mkdir()
    (tmp_path / "web/index.html").write_text(
        '<body><main><a href="/broken/">Shop</a></main></body>'
    )
    spec = ProjectSpec(
        name="Guide",
        website_url="https://example.test/",
        allowed_paths=["web"],
        route_map={"/": "web/index.html"},
        page_intents={"/private/": False},
    )
    change = FileChange(
        path="web/index.html",
        before='href="/broken/"',
        after=f'href="{destination}"',
        check_id="tech.links",
        reason="Link repair",
        evidence_ids=["source"],
    )

    def page(url, data):
        return Evidence(
            id=url,
            tenant_id="t",
            project_id="p",
            environment="production",
            kind="http",
            url=url,
            collected_at=utc_now(),
            observation="Controlled response",
            data=data,
        )

    evidence = [
        page(
            "https://example.test/",
            {"status_code": 200, "link_status": {"https://example.test/broken/": status}},
        ),
        page("https://example.test/shop/", {"status_code": 200}),
        page("https://example.test/private/", {"status_code": 200}),
    ]
    if destination == "/shop/" and status == 404:
        validate_model_body(tmp_path, spec, change, evidence)
    else:
        with pytest.raises(ValueError, match="Navigation"):
            validate_model_body(tmp_path, spec, change, evidence)


def test_recorded_real_repair_passes_body_guard(tmp_path):
    import json

    report = json.loads((Path(__file__).parents[1] / "videos/public/agent-run.json").read_text())
    for proposal in report["repair"]["result"]["proposals"]:
        if proposal["path"] == "web/index.html":
            # Source and proposal from the anonymous recording, with observed broken navigation.
            path = tmp_path / proposal["path"]
            path.parent.mkdir(parents=True)
            source = next(
                t["result"]["text"]
                for t in report["repair"]["result"]["report"]["tool_trace"]
                if t["name"] == "read_file" and t["arguments"]["path"] == proposal["path"]
            )
            path.write_text(source)
            from urllib.parse import urlparse

            origin = next(
                f["url"] for f in report["baseline"]["findings"] if f["check_id"] == "tech.links"
            )
            spec = ProjectSpec(
                name="Recording",
                website_url=origin,
                allowed_paths=["web"],
                route_map={"/": "web/index.html"},
            )
            site = (
                "https://" + urlparse(origin).netloc
                if origin.startswith("https:")
                else "http://" + urlparse(origin).netloc
            )
            pages = [
                Evidence(
                    id="observed",
                    tenant_id="t",
                    project_id="p",
                    environment="production",
                    kind="http",
                    url=origin,
                    collected_at=utc_now(),
                    observation="Recorded missing route",
                    data={
                        "status_code": 200,
                        "link_status": {site + "/collections/lighting/": 404},
                    },
                ),
                Evidence(
                    id="target",
                    tenant_id="t",
                    project_id="p",
                    environment="production",
                    kind="http",
                    url=site + "/shop/",
                    collected_at=utc_now(),
                    observation="Recorded collection",
                    data={"status_code": 200},
                ),
            ]
            validate_model_body(tmp_path, spec, FileChange.model_validate(proposal), pages)
