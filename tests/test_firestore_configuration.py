"""Named database selection must agree across settings and SDK construction."""

import os

import pytest
from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore

from seo_optimizer.firestore_store import FirestoreStore
from seo_optimizer.settings import Settings, validate_firestore_database


def test_environment_selects_named_database(tmp_path, monkeypatch):
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.setattr("seo_optimizer.settings.load_dotenv", lambda: None)
    monkeypatch.setenv("OPT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPT_STORAGE", "firestore")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-your-optimiser")
    monkeypatch.setenv("OPT_FIRESTORE_DATABASE", "optimiser-test")
    settings = Settings.from_env()
    assert settings.firestore_database == "optimiser-test"
    monkeypatch.setenv("OPT_FIRESTORE_DATABASE", "projects/example/databases/other")
    with pytest.raises(ValueError, match="OPT_FIRESTORE_DATABASE"):
        Settings.from_env()


@pytest.mark.parametrize("emulator", [False, True])
@pytest.mark.parametrize("database", ["(default)", "optimiser-test"])
def test_sdk_targets_selected_database_without_network(tmp_path, monkeypatch, emulator, database):
    if emulator:
        monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8089")
    else:
        monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    real_client = firestore.Client

    def client(**kwargs):
        kwargs.setdefault("credentials", AnonymousCredentials())
        return real_client(**kwargs)

    monkeypatch.setattr(firestore, "Client", client)
    store = FirestoreStore(
        Settings(
            tmp_path,
            "",
            "test-secret",
            firebase_project="demo-your-optimiser",
            firestore_database=database,
        )
    )
    assert store.db._database_string == f"projects/demo-your-optimiser/databases/{database}"
    store.close()


@pytest.mark.parametrize(
    "value", ["", "abc", "Uppercase", "a" * 64, "test/db", "f47ac10b-58cc-0372-8567-0e02b2c3d479"]
)
def test_database_ids_reject_paths_and_invalid_names(value):
    with pytest.raises(ValueError, match="OPT_FIRESTORE_DATABASE"):
        validate_firestore_database(value)
