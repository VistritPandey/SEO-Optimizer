"""Explicit local/hosted settings; secrets never enter project exports."""

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_url: str
    secret_key: str
    production: bool = False
    allow_private_network: bool = True
    allow_local_repositories: bool = True
    registration_enabled: bool = True
    public_url: str = "http://127.0.0.1:8000"
    allowed_repo_roots: tuple[Path, ...] = ()

    storage_backend: str = "sql"
    firebase_project: str = ""
    hosted: bool = False
    frontend_url: str = "http://localhost:3000"
    managed_model: str = "gemini-3.8-flash"
    managed_key: str = ""
    github_app_id: str = ""
    github_app_slug: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    github_private_key: str = ""
    github_webhook_secret: str = ""
    free_projects: int = 3
    free_jobs_per_month: int = 100

    @property
    def cipher(self) -> Fernet:
        return Fernet(base64.urlsafe_b64encode(hashlib.sha256(self.secret_key.encode()).digest()))

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        production = os.getenv("OPT_ENV", "development") == "production"
        data_dir = Path(os.getenv("OPT_DATA_DIR", ".data")).resolve()
        secret = os.getenv("OPT_SECRET_KEY", "")
        database = os.getenv("OPT_DATABASE_URL", "")
        backend = os.getenv("OPT_STORAGE", "sql")
        hosted = os.getenv("OPT_HOSTED", "0") == "1"
        firebase_project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        if backend not in {"sql", "firestore"}:
            raise ValueError("OPT_STORAGE must be sql or firestore")
        if production and (
            len(secret) < 32 or (backend == "sql" and not database.startswith("postgresql"))
        ):
            raise ValueError("Production requires a stable secret and PostgreSQL or Firestore")
        if (backend == "firestore" or hosted) and not firebase_project:
            raise ValueError("GOOGLE_CLOUD_PROJECT is required for hosted identity/storage")
        if production and os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
            raise ValueError("Auth emulator is forbidden in production")
        data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        data_dir.chmod(0o700)
        if not secret:
            key_file = data_dir / "secret.key"
            try:
                descriptor = os.open(key_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                with os.fdopen(descriptor, "w") as handle:
                    handle.write(secrets.token_urlsafe(48))
            except FileExistsError:
                pass
            secret = key_file.read_text().strip()
        roots = tuple(
            Path(value).resolve()
            for value in os.getenv("OPT_REPO_ROOTS", str(data_dir)).split(os.pathsep)
            if value
        )
        return cls(
            data_dir=data_dir,
            database_url=database or f"sqlite:///{data_dir / 'control.db'}",
            secret_key=secret,
            production=production,
            allow_private_network=os.getenv("OPT_ALLOW_PRIVATE_NETWORK", "0" if production else "1")
            == "1",
            allow_local_repositories=not production,
            registration_enabled=os.getenv("OPT_REGISTRATION", "1") == "1",
            public_url=os.getenv("OPT_PUBLIC_URL", "http://127.0.0.1:8000"),
            allowed_repo_roots=roots,
            storage_backend=backend,
            firebase_project=firebase_project,
            hosted=hosted,
            frontend_url=os.getenv("OPT_FRONTEND_URL", "http://localhost:3000").rstrip("/"),
            managed_model=os.getenv("OPT_MANAGED_MODEL", "gemini-3.8-flash"),
            managed_key=os.getenv("GOOGLE_API_KEY", "") if hosted else "",
            github_app_id=os.getenv("GITHUB_APP_ID", ""),
            github_app_slug=os.getenv("GITHUB_APP_SLUG", ""),
            github_client_id=os.getenv("GITHUB_CLIENT_ID", ""),
            github_client_secret=os.getenv("GITHUB_CLIENT_SECRET", ""),
            github_private_key=os.getenv("GITHUB_PRIVATE_KEY", "").replace("\\n", "\n"),
            github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
            free_projects=int(os.getenv("OPT_FREE_PROJECTS", "3")),
            free_jobs_per_month=int(os.getenv("OPT_FREE_JOBS", "100")),
        )
