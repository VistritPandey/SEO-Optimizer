"""Real Firebase emulators, opt-in; never a production Google project."""

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import HttpUrl

from seo_optimizer.application_models import ProjectCreate, ProjectSecrets, ProjectSpec
from seo_optimizer.settings import Settings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("FIRESTORE_EMULATOR_HOST") != "127.0.0.1:8089",
        reason="Start the documented local Firestore emulator",
    ),
]


@pytest.fixture(params=["(default)", "optimiser-test"])
def store(tmp_path: Path, request):
    from seo_optimizer.firestore_store import FirestoreStore

    value = FirestoreStore(
        Settings(
            tmp_path,
            "",
            "emulator-test-secret-" * 3,
            storage_backend="firestore",
            firebase_project="demo-your-optimiser",
            firestore_database=request.param,
        )
    )
    yield value
    value.close()


def project(store, tenant: str):
    return store.create_project(
        tenant,
        ProjectCreate(
            spec=ProjectSpec(name="Example website", website_url=HttpUrl("https://example.test")),
            credentials=ProjectSecrets(provider_key="example-private-key"),
        ),
    )


def test_firestore_scope_dedupe_chunked_evidence_and_findings(store) -> None:
    tenant, token = store.create_user(f"owner-{uuid4()}@example.test", "password-hash")
    other, _ = store.create_user(f"other-{uuid4()}@example.test", "password-hash")
    assert store.user(token=token).id == tenant.id
    site = project(store, tenant.id)
    assert store.project(other.id, site.id) is None
    assert store.secrets(site).provider_key == "example-private-key"
    first = store.enqueue(tenant.id, site.id, "audit", "same-event", {"example": True})
    assert store.enqueue(tenant.id, site.id, "audit", "same-event", {}).id == first.id
    with pytest.raises(KeyError):
        store.enqueue(other.id, site.id, "audit", "invalid-owner", {})
    job = store.claim("worker", tenant.id)
    assert job is not None
    with pytest.raises(ValueError):
        store.finish(other.id, job.id, "worker", "complete", {})
    store.progress(tenant.id, job.id, "worker", "Collecting evidence")
    assert store.job(tenant.id, job.id).events[-1]["message"] == "Collecting evidence"
    with pytest.raises(ValueError):
        store.progress(other.id, job.id, "worker", "Wrong tenant")
    with pytest.raises(ValueError):
        store.progress(tenant.id, job.id, "other-worker", "Wrong worker")
    assert store.claim("other-worker", tenant.id) is None
    large = {"report": {"pages": 1, "example": "evidence " * 30_000}, "summary": "Complete"}
    store.finish(tenant.id, job.id, "worker", "complete", large)
    assert store.job(tenant.id, job.id).result == large
    assert store.project(tenant.id, site.id).last_report == large["report"]
    findings = [{"check_id": "tech.title", "url": "https://example.test/", "status": "defect"}]
    assert store.remember_findings(tenant.id, site.id, findings, ["https://example.test/"]) == 1
    assert store.remember_findings(tenant.id, site.id, findings, ["https://example.test/"]) == 0
    store.remember_findings(tenant.id, site.id, [], ["https://example.test/"])
    assert not store.findings(tenant.id, site.id)[0].active
    assert store.findings(other.id, site.id) == []
    assert store.save_state("example:" + tenant.id, {"private": "value"}, 0)
    assert not store.save_state("example:" + tenant.id, {}, 0)
    assert store.state("example:" + tenant.id) == ({"private": "value"}, 1)


def test_firestore_only_one_worker_claims_a_project(store) -> None:
    tenant, _ = store.create_user(f"lease-{uuid4()}@example.test", "hash")
    site = project(store, tenant.id)
    store.enqueue(tenant.id, site.id, "audit", "second", {})
    with ThreadPoolExecutor(max_workers=5) as pool:
        claimed = list(pool.map(lambda id: store.claim("worker-" + str(id), tenant.id), range(5)))
    live = [job for job in claimed if job is not None]
    assert len(live) == 1
    store.finish(tenant.id, live[0].id, live[0].worker_id, "complete", {})
    assert store.claim("next-worker", tenant.id) is not None


def test_firestore_hosted_quota_and_project_limit(store) -> None:
    store.settings = replace(store.settings, hosted=True, free_jobs_per_month=3, free_projects=1)
    tenant, _ = store.create_user(f"quota-{uuid4()}@example.test", "hash")
    site = project(store, tenant.id)
    store.enqueue(tenant.id, site.id, "audit", "two", {})
    store.enqueue(tenant.id, site.id, "audit", "three", {})
    with pytest.raises(ValueError, match="Monthly free"):
        store.enqueue(tenant.id, site.id, "audit", "four", {})
    with pytest.raises(ValueError, match="Project limit"):
        project(store, tenant.id)


def test_real_firebase_identity_rejects_unverified_and_invalid_tokens(store, monkeypatch) -> None:
    if os.getenv("FIREBASE_AUTH_EMULATOR_HOST") != "127.0.0.1:9099":
        pytest.skip("Auth emulator not running")
    from firebase_admin import auth, get_app

    from seo_optimizer.hosted import firebase_user

    email = f"identity-{uuid4()}@example.test"
    base = "http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/"
    with httpx.Client() as client:
        result = client.post(
            base + "accounts:signUp?key=example",
            json={"email": email, "password": "example-password-strong", "returnSecureToken": True},
        )
        result.raise_for_status()
        unverified = result.json()
        assert firebase_user(unverified["idToken"], store.settings, store) is None
        application = get_app("your-optimiser-demo-your-optimiser")
        auth.update_user(unverified["localId"], email_verified=True, app=application)
        result = client.post(
            base + "accounts:signInWithPassword?key=example",
            json={"email": email, "password": "example-password-strong", "returnSecureToken": True},
        )
        result.raise_for_status()
        token = result.json()["idToken"]
    account = firebase_user(token, store.settings, store)
    assert account is not None and account.email == email
    assert firebase_user(token, store.settings, store).id == account.id
    assert firebase_user("not-a-token", store.settings, store) is None
    auth.update_user(unverified["localId"], disabled=True, app=application)
    assert firebase_user(token, store.settings, store) is None


def test_recreated_firebase_uid_does_not_inherit_existing_workspace(store):
    if os.getenv("FIREBASE_AUTH_EMULATOR_HOST") != "127.0.0.1:9099":
        pytest.skip("Auth emulator not running")
    from firebase_admin import auth, get_app, initialize_app

    from seo_optimizer.hosted import firebase_user

    name = "your-optimiser-demo-your-optimiser"
    try:
        app = get_app(name)
    except ValueError:
        app = initialize_app(options={"projectId": "demo-your-optimiser"}, name=name)
    email, password = f"recreated-{uuid4()}@example.test", "fixture-password-strong"

    def sign_in():
        with httpx.Client() as client:
            result = client.post(
                "http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=example",
                json={"email": email, "password": password, "returnSecureToken": True},
            )
            result.raise_for_status()
            return result.json()["idToken"]

    first = auth.create_user(email=email, password=password, email_verified=True, app=app)
    token = sign_in()
    owner = firebase_user(token, store.settings, store)
    assert owner is not None
    site = project(store, owner.id)
    auth.delete_user(first.uid, app=app)
    assert firebase_user(token, store.settings, store) is None
    second = auth.create_user(email=email, password=password, email_verified=True, app=app)
    assert first.uid != second.uid
    assert firebase_user(sign_in(), store.settings, store) is None
    assert store.project(owner.id, site.id) is not None
