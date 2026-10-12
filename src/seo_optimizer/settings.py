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
        if production and (len(secret) < 32 or not database.startswith("postgresql")):
            raise ValueError("Production requires OPT_SECRET_KEY and a PostgreSQL database URL")
        data_dir.mkdir(parents=True, exist_ok=True)
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
        )
