from pydantic import HttpUrl

from seo_optimizer.application_models import ProjectSpec
from seo_optimizer.scanner import affected_urls
from seo_optimizer.worker import infer_route_map


def test_explicit_website_scope_skips_unrelated_backend_but_checks_dependencies():
    spec = ProjectSpec(
        name="Site",
        website_url=HttpUrl("https://example.test"),
        allowed_paths=["src/app", "src/components", "public"],
        route_map={"/": "src/app/page.tsx", "/shop": "src/app/shop/page.tsx"},
    )
    assert affected_urls(spec, ["backend/service.py"]) == []
    assert affected_urls(spec, ["src/server/jobs.py"]) == []
    assert affected_urls(spec, ["src/app/shop/page.tsx"]) == ["https://example.test/shop"]
    assert affected_urls(spec, ["src/components/Menu.tsx"]) is None
    assert affected_urls(spec, ["next.config.ts"]) is None


def test_next_routes_handle_src_groups_and_skip_unresolved_dynamic_api_paths(tmp_path):
    files = [
        "src/app/page.tsx",
        "src/app/(store)/shop/page.tsx",
        "src/app/[slug]/page.tsx",
        "src/pages/contact.tsx",
        "src/pages/api/health.ts",
        "src/pages/_app.tsx",
    ]
    for name in files:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("export default function Page() { return null }")
    spec = ProjectSpec(
        name="Site", website_url=HttpUrl("https://example.test"), allowed_paths=["src"]
    )
    assert infer_route_map(tmp_path, spec) == {
        "/": "src/app/page.tsx",
        "/shop": "src/app/(store)/shop/page.tsx",
        "/contact": "src/pages/contact.tsx",
    }
