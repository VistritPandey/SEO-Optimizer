"""Framework link repairs preserve behavior and require observed destinations."""

import pytest

from seo_optimizer.application_models import FileChange, ProjectSpec
from seo_optimizer.contracts import Evidence, utc_now
from seo_optimizer.execution import apply_changes
from seo_optimizer.model_guard import validate_model_body
from seo_optimizer.navigation import literal_link_changes

SOURCE = (
    'import Link from "next/link";\nexport default function Page() {'
    'return <main><Link href="/missing" className="link">About us</Link></main>;}'
)


@pytest.mark.parametrize(
    "after",
    [
        SOURCE.replace("/missing", "/about").replace("About us", "Invented reviews"),
        SOURCE.replace('href="/missing"', 'href="/about" onClick={stealData}'),
        SOURCE.replace('href="/missing"', 'href={"/about"}'),
        SOURCE.replace("/missing", "//other.test/about"),
        SOURCE.replace("/missing", "javascript:stealData()"),
        SOURCE.replace("/missing", "/about\\payload"),
        SOURCE.replace("/missing", "/about").replace("return", "runPayload();return"),
        SOURCE,
    ],
)
def test_navigation_guard_rejects_behavior_copy_dynamic_or_external_edits(after):
    with pytest.raises(ValueError, match="Navigation"):
        literal_link_changes(SOURCE, after)


@pytest.mark.parametrize(
    "broken,observed,private",
    [(404, True, False), (200, True, False), (404, False, False), (404, True, True)],
)
def test_framework_link_patch_is_grounded_and_admitted_without_content_permission(
    tmp_path, broken, observed, private
):
    path = tmp_path / "web/page.tsx"
    path.parent.mkdir()
    path.write_text(SOURCE)
    spec = ProjectSpec(
        name="Example site",
        website_url="https://example.test/",
        allowed_paths=["web"],
        route_map={"/": "web/page.tsx"},
        page_intents={"/about": not private},
        check_commands=[["python", "verify.py"]],
        allow_content_publication=False,
    )
    change = FileChange(
        path="web/page.tsx",
        before='href="/missing"',
        after='href="/about"',
        reason="Restore observed navigation",
        check_id="tech.links",
        evidence_ids=["root"],
    )

    def page(id, url, data):
        return Evidence(
            id=id,
            tenant_id="t",
            project_id="p",
            environment="production",
            kind="http",
            url=url,
            observation="Observed response",
            collected_at=utc_now(),
            data=data,
        )

    evidence = [
        page(
            "root",
            "https://example.test/",
            {"status_code": 200, "link_status": {"https://example.test/missing": broken}},
        )
    ]
    if observed:
        evidence.append(page("about", "https://example.test/about", {"status_code": 200}))
    if broken == 404 and observed and not private:
        validate_model_body(tmp_path, spec, change, evidence)
        files = apply_changes(tmp_path, spec, [change], {"root"}, {"tech.links"})
        assert files[change.path] == SOURCE.replace("/missing", "/about")
        path.write_text(SOURCE)
        spec.check_commands = []
        with pytest.raises(ValueError, match="build verification"):
            apply_changes(tmp_path, spec, [change], {"root"}, {"tech.links"})
    else:
        with pytest.raises(ValueError, match="Navigation"):
            validate_model_body(tmp_path, spec, change, evidence)
        assert path.read_text() == SOURCE
