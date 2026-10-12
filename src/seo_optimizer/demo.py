"""A real local repository and website for exercising the complete autonomous path."""

import secrets

from seo_optimizer.application_models import ProjectCreate, ProjectSpec
from seo_optimizer.execution import run_git
from seo_optimizer.settings import Settings
from seo_optimizer.store import Store
from seo_optimizer.web import hash_password


def create_demo() -> None:
    settings = Settings.from_env()
    root = settings.data_dir / "demo-repository"
    if settings.production:
        raise ValueError("Demo is for a local development host")
    if (root / ".git").exists():
        print("Demo already exists; use your existing account or create another through the UI.")
        return
    (root / "web").mkdir(parents=True)
    (root / "web/index.html").write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="description" content="Practical guides for a more useful website.">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        "<body><main><h1>Field Notes</h1><p>Practical guides for a more useful website.</p></main></body></html>"
    )
    run_git(root, "init", "-b", "main")
    run_git(root, "add", "web/index.html")
    run_git(
        root,
        "-c",
        "user.name=Optimizer",
        "-c",
        "user.email=optimizer@localhost",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "Add demo page",
    )
    store = Store(settings)
    password = secrets.token_urlsafe(18)
    user, _ = store.create_user("demo@localhost.test", hash_password(password))
    spec = ProjectSpec.model_validate(
        {
            "name": "Field Notes",
            "website_url": "http://127.0.0.1:8081/",
            "local_path": str(root),
            "allowed_paths": ["web"],
            "route_map": {"/": "web/index.html"},
        }
    )
    store.create_project(user.id, ProjectCreate(spec=spec))
    print("Demo account: demo@localhost.test")
    print("One-time local password:", password)
    print(
        "Website command: uv run python -m http.server 8081 --bind 127.0.0.1 --directory",
        root / "web",
    )
    print("Dashboard: uv run seo-optimizer serve")
    print("Worker: uv run seo-optimizer worker")
