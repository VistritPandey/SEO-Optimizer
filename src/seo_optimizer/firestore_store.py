"""Firestore adapter with transactional leases and tenant checks at every boundary.

Large JSON fields use immutable, content-addressed chunk documents. Server SDK access
bypasses Firestore rules; user-facing reads always go through the authenticated API.
"""

import hashlib
import json
import os
import secrets
import time
from typing import Any, TypeVar, cast

from google.api_core.exceptions import Aborted
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from seo_optimizer.application_models import ProjectCreate, ProjectSecrets, ProjectSpec
from seo_optimizer.growth import Workspace, validate_workspace
from seo_optimizer.settings import Settings
from seo_optimizer.store import (
    FindingRecord,
    Job,
    Project,
    Store,
    User,
    identifier,
    token_hash,
)

T = TypeVar("T", User, Project, Job, FindingRecord)
ACTIVE = {"queued", "running", "waiting_checks", "waiting_deployment"}


class FirestoreStore(Store):
    def __init__(self, settings: Settings, client: Any = None):
        self.settings = settings
        if client is None:
            if os.getenv("FIRESTORE_EMULATOR_HOST"):
                from google.auth.credentials import AnonymousCredentials

                client = firestore.Client(
                    project=settings.firebase_project,
                    database=settings.firestore_database,
                    credentials=AnonymousCredentials(),  # type: ignore[no-untyped-call]
                )
            else:
                client = firestore.Client(
                    project=settings.firebase_project, database=settings.firestore_database
                )
        self.db = client

    def health(self) -> None:
        self.db.collection("optimizer_health").document("schema-v1").get()

    def close(self) -> None:
        self.db.close()

    def _pack(self, value: dict[str, Any]) -> dict[str, Any]:
        packed = dict(value)
        for name in ("spec", "last_report", "payload", "result", "events", "details", "body"):
            if name not in packed:
                continue
            encoded = json.dumps(packed[name], ensure_ascii=True, separators=(",", ":"))
            if len(encoded) <= 100_000:
                continue
            if len(encoded) > 10_000_000:
                raise ValueError("Stored record exceeds ten megabytes")
            digest = hashlib.sha256(encoded.encode()).hexdigest()
            chunks = [encoded[i : i + 100_000] for i in range(0, len(encoded), 100_000)]
            for index, chunk in enumerate(chunks):
                self.db.collection("optimizer_blobs").document(f"{digest}-{index}").set(
                    {"text": chunk}
                )
            packed[name] = {"_chunks": digest, "count": len(chunks)}
        return packed

    def _unpack(self, value: dict[str, Any]) -> dict[str, Any]:
        unpacked = dict(value)
        for name, body in value.items():
            if isinstance(body, dict) and set(body) == {"_chunks", "count"}:
                chunks = []
                for index in range(body["count"]):
                    snapshot = (
                        self.db.collection("optimizer_blobs")
                        .document(f"{body['_chunks']}-{index}")
                        .get()
                    )
                    if not snapshot.exists:
                        raise ValueError("Stored evidence chunk is missing")
                    chunks.append(snapshot.to_dict()["text"])
                encoded = "".join(chunks)
                if hashlib.sha256(encoded.encode()).hexdigest() != body["_chunks"]:
                    raise ValueError("Stored evidence integrity mismatch")
                unpacked[name] = json.loads(encoded)
        return unpacked

    def _record(self, model: type[T], snapshot: Any) -> T | None:
        return model(**self._unpack(snapshot.to_dict())) if snapshot.exists else None

    def _get(self, collection: str, id: str, model: type[T]) -> T | None:
        return self._record(model, self.db.collection(collection).document(id).get())

    def _query(self, collection: str, **filters: Any) -> list[Any]:
        query = self.db.collection(collection)
        for name, value in filters.items():
            query = query.where(filter=FieldFilter(name, "==", value))
        return list(query.stream())

    def state(self, key: str) -> tuple[dict[str, Any], int]:
        snapshot = self.db.collection("optimizer_state").document(token_hash(key)).get()
        if not snapshot.exists:
            return {}, 0
        record = snapshot.to_dict()
        body = self._unpack(record)["body"]
        return json.loads(self.settings.cipher.decrypt(body.encode())), int(record["version"])

    def save_state(self, key: str, value: dict[str, Any], expected: int) -> bool:
        ref = self.db.collection("optimizer_state").document(token_hash(key))
        body = self.settings.cipher.encrypt(json.dumps(value).encode()).decode()
        packed = self._pack({"body": body, "version": expected + 1})

        @firestore.transactional
        def save(transaction: Any) -> bool:
            snapshot = ref.get(transaction=transaction)
            version = snapshot.to_dict()["version"] if snapshot.exists else 0
            if version != expected:
                return False
            transaction.set(ref, packed)
            return True

        try:
            return bool(save(self.db.transaction()))
        except ValueError as error:
            if isinstance(error.__cause__, Aborted):
                return False
            raise

    def create_user(self, email: str, password_hash: str) -> tuple[User, str]:
        token, id = secrets.token_urlsafe(40), identifier()
        value = dict(
            id=id,
            email=email.lower(),
            password_hash=password_hash,
            token_hash=token_hash(token),
            created_at=time.time(),
        )
        ref = self.db.collection("optimizer_users").document(id)
        unique = self.db.collection("optimizer_email").document(token_hash(email.lower()))

        @firestore.transactional
        def create(transaction: Any) -> None:
            if unique.get(transaction=transaction).exists:
                raise ValueError("Email is already registered")
            transaction.create(ref, value)
            transaction.create(unique, {"user_id": id})

        create(self.db.transaction())
        return User(**value), token

    def user(
        self, *, email: str | None = None, id: str | None = None, token: str | None = None
    ) -> User | None:
        if id is not None:
            return self._get("optimizer_users", id, User)
        if email is not None:
            snapshot = (
                self.db.collection("optimizer_email").document(token_hash(email.lower())).get()
            )
            return self.user(id=snapshot.to_dict()["user_id"]) if snapshot.exists else None
        if token is not None:
            records = self._query("optimizer_users", token_hash=token_hash(token))
            return self._record(User, records[0]) if records else None
        return None

    def rotate_token(self, tenant: str) -> str:
        token = secrets.token_urlsafe(40)
        self.db.collection("optimizer_users").document(tenant).update(
            {"token_hash": token_hash(token)}
        )
        return token

    def throttle(self, key: str) -> bool:
        for _ in range(20):
            value, version = self.state("throttle:" + token_hash(key))
            now = time.time()
            if value.get("until", 0) < now:
                value = {"count": 0, "until": now + 900}
            value["count"] += 1
            if self.save_state("throttle:" + token_hash(key), value, version):
                return bool(value["count"] <= 10)
        return False

    def create_project(self, tenant: str, value: ProjectCreate) -> Project:
        id, now = identifier(), time.time()
        ref = self.db.collection("optimizer_projects").document(id)
        account_ref = self.db.collection("optimizer_project_counts").document(tenant)
        limit = self.settings.free_projects if self.settings.hosted else 20
        if len(self.projects(tenant)) >= limit:
            raise ValueError("Project limit reached")
        self.reserve_job(tenant, id + ":initial:" + id)
        body = self._pack(
            dict(
                id=id,
                tenant_id=tenant,
                spec=value.spec.model_dump(mode="json"),
                credentials=self.encode_credentials(value.credentials),
                updated_at=now,
                next_audit=now + value.spec.reconcile_seconds,
                last_revision="",
                last_report={},
            )
        )

        @firestore.transactional
        def create(transaction: Any) -> None:
            snapshot = account_ref.get(transaction=transaction)
            count = snapshot.to_dict()["count"] if snapshot.exists else 0
            if count >= limit:
                raise ValueError("Project limit reached")
            transaction.set(account_ref, {"count": count + 1})
            transaction.create(ref, body)

        create(self.db.transaction())
        self.enqueue(tenant, id, "audit", "initial:" + id, {})
        project = self.project(tenant, id)
        assert project is not None
        return project

    def projects(self, tenant: str) -> list[Project]:
        records = [
            cast(Project, self._record(Project, snap))
            for snap in self._query("optimizer_projects", tenant_id=tenant)
        ]
        return sorted(records, key=lambda item: item.updated_at, reverse=True)

    def project(self, tenant: str, id: str) -> Project | None:
        value = self.webhook_project(id)
        return value if value is not None and value.tenant_id == tenant else None

    def webhook_project(self, id: str) -> Project | None:
        return self._get("optimizer_projects", id, Project)

    def update_project(
        self, tenant: str, id: str, spec: ProjectSpec, credentials: ProjectSecrets | None = None
    ) -> None:
        if self.project(tenant, id) is None:
            raise KeyError("Project not found")
        value: dict[str, Any] = {"spec": spec.model_dump(mode="json"), "updated_at": time.time()}
        if credentials is not None:
            value["credentials"] = self.encode_credentials(credentials)
        self.db.collection("optimizer_projects").document(id).update(self._pack(value))

    def workspace(self, tenant: str, project_id: str) -> Workspace:
        if self.project(tenant, project_id) is None:
            raise ValueError("Project not found")
        snapshot = self.db.collection("optimizer_workspaces").document(project_id).get()
        return (
            Workspace.model_validate(self._unpack(snapshot.to_dict())["body"])
            if snapshot.exists
            else Workspace()
        )

    def save_workspace(self, tenant: str, project_id: str, value: Workspace) -> None:
        project = self.project(tenant, project_id)
        if project is None:
            raise ValueError("Project not found")
        validate_workspace(ProjectSpec.model_validate(project.spec), value)
        self.db.collection("optimizer_workspaces").document(project_id).set(
            self._pack(
                {
                    "tenant_id": tenant,
                    "body": value.model_dump(mode="json"),
                    "updated_at": time.time(),
                }
            )
        )

    def enqueue(
        self, tenant: str, project_id: str, kind: str, key: str, payload: dict[str, Any]
    ) -> Job:
        if self.project(tenant, project_id) is None:
            raise KeyError("Project not found")
        id = token_hash(project_id + ":" + key)
        ref = self.db.collection("optimizer_jobs").document(id)
        existing = self.job(tenant, id)
        if existing:
            return existing
        self.reserve_job(tenant, project_id + ":" + key)
        now = time.time()
        body = self._pack(
            dict(
                id=id,
                tenant_id=tenant,
                project_id=project_id,
                kind=kind,
                status="queued",
                dedupe_key=key,
                payload=payload,
                result={},
                events=[],
                attempts=0,
                available_at=now,
                lease_until=0,
                worker_id="",
                created_at=now,
                updated_at=now,
            )
        )

        @firestore.transactional
        def create(transaction: Any) -> None:
            if not ref.get(transaction=transaction).exists:
                transaction.create(ref, body)

        create(self.db.transaction())
        value = self.job(tenant, id)
        assert value is not None
        return value

    def jobs(self, tenant: str, project_id: str | None = None) -> list[Job]:
        filters = {"tenant_id": tenant}
        if project_id:
            filters["project_id"] = project_id
        query = self.db.collection("optimizer_jobs")
        for name, value in filters.items():
            query = query.where(filter=FieldFilter(name, "==", value))
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(100)
        return [cast(Job, self._record(Job, snap)) for snap in query.stream()]

    def job(self, tenant: str, id: str) -> Job | None:
        value = self._get("optimizer_jobs", id, Job)
        return value if value is not None and value.tenant_id == tenant else None

    def has_pending_jobs(self) -> bool:
        query = (
            self.db.collection("optimizer_jobs")
            .where(filter=FieldFilter("status", "in", list(ACTIVE)))
            .limit(1)
        )
        return next(iter(query.stream()), None) is not None

    def claim(self, worker: str, tenant: str | None = None) -> Job | None:
        query = self.db.collection("optimizer_jobs").where(
            filter=FieldFilter("status", "in", list(ACTIVE))
        )
        if tenant:
            query = query.where(filter=FieldFilter("tenant_id", "==", tenant))
        query = (
            query.where(filter=FieldFilter("available_at", "<=", time.time()))
            .where(filter=FieldFilter("lease_until", "<=", time.time()))
            .order_by("available_at")
            .limit(100)
        )
        candidates = list(query.stream())
        for candidate in candidates:
            ref = candidate.reference
            project_id = candidate.to_dict()["project_id"]
            lease_ref = self.db.collection("optimizer_leases").document(project_id)

            @firestore.transactional
            def claim_one(
                transaction: Any, ref: Any = ref, lease_ref: Any = lease_ref
            ) -> dict[str, Any] | None:
                now = time.time()
                lease = lease_ref.get(transaction=transaction)
                snapshot = ref.get(transaction=transaction)
                body = snapshot.to_dict()
                if (
                    body["status"] not in ACTIVE
                    or body["available_at"] > now
                    or body["lease_until"] > now
                    or (lease.exists and lease.to_dict()["until"] > now)
                ):
                    return None
                changes = dict(
                    status="running",
                    worker_id=worker,
                    lease_until=now + 900,
                    attempts=body["attempts"] + (body["status"] in {"queued", "running"}),
                    updated_at=now,
                )
                transaction.update(ref, changes)
                transaction.set(
                    lease_ref,
                    {
                        "job_id": body["id"],
                        "worker": worker,
                        "until": now + 900,
                        "tenant_id": body["tenant_id"],
                        "project_id": body["project_id"],
                    },
                )
                return {**body, **changes}

            try:
                body = claim_one(self.db.transaction())
            except ValueError as error:
                if isinstance(error.__cause__, Aborted):
                    continue  # Another worker won; contention is not a failed SEO job.
                raise
            if body is not None:
                return Job(**self._unpack(body))
        return None

    def progress(self, tenant: str, id: str, worker: str, message: str) -> None:
        job = self.job(tenant, id)
        if job is None:
            raise ValueError("Job not found")
        ref = self.db.collection("optimizer_jobs").document(id)
        lease_ref = self.db.collection("optimizer_leases").document(job.project_id)

        @firestore.transactional
        def record(transaction: Any) -> None:
            snapshot = ref.get(transaction=transaction)
            lease = lease_ref.get(transaction=transaction)
            body, now = snapshot.to_dict(), time.time()
            if (
                body["tenant_id"] != tenant
                or body["worker_id"] != worker
                or body["status"] != "running"
                or body["lease_until"] <= now
                or not lease.exists
                or lease.to_dict().get("job_id") != id
                or lease.to_dict().get("worker") != worker
                or lease.to_dict().get("tenant_id") != tenant
                or lease.to_dict().get("until", 0) <= now
            ):
                raise ValueError("Job lease no longer owned")
            transaction.update(
                ref,
                {
                    "events": [*body["events"][-99:], {"time": now, "message": message[:200]}],
                    "updated_at": now,
                },
            )

        record(self.db.transaction())

    def finish(
        self,
        tenant: str,
        id: str,
        worker: str,
        status: str,
        result: dict[str, Any],
        delay: float = 0,
    ) -> None:
        ref = self.db.collection("optimizer_jobs").document(id)
        job = self.job(tenant, id)
        if job is None:
            raise ValueError("Job not found")
        lease_ref = self.db.collection("optimizer_leases").document(job.project_id)
        project_ref = self.db.collection("optimizer_projects").document(job.project_id)
        packed_result = self._pack({"result": result})
        project_audit = (
            job.kind not in {"followup", "pull_request"} or result.get("stage") == "verified"
        )
        packed_report = (
            self._pack({"last_report": result["report"]})
            if result.get("report") and project_audit
            else {}
        )

        @firestore.transactional
        def finish_one(transaction: Any) -> None:
            snapshot = ref.get(transaction=transaction)
            lease = lease_ref.get(transaction=transaction)
            project = project_ref.get(transaction=transaction)
            body, now = snapshot.to_dict(), time.time()
            if (
                body["tenant_id"] != tenant
                or body["worker_id"] != worker
                or body["status"] != "running"
                or body["lease_until"] <= now
                or not lease.exists
                or lease.to_dict().get("job_id") != id
            ):
                raise ValueError("Job lease no longer owned")
            events = [
                *body["events"][-99:],
                {"time": now, "message": result.get("summary", status)},
            ]
            transaction.update(
                ref,
                {
                    **packed_result,
                    "status": status,
                    "lease_until": 0,
                    "available_at": now + delay,
                    "updated_at": now,
                    "events": events,
                },
            )
            transaction.delete(lease_ref)
            if project.exists and project.to_dict()["tenant_id"] == tenant:
                changes: dict[str, Any] = {**packed_report, "updated_at": now}
                if (
                    project_audit
                    and result.get("revision")
                    and status
                    in {
                        "complete",
                        "waiting_checks",
                        "waiting_deployment",
                    }
                ):
                    changes["last_revision"] = result["revision"]
                transaction.update(project_ref, changes)

        finish_one(self.db.transaction())
        self.index_pr(tenant, job.project_id, id, status, result)

    def remember_findings(
        self, tenant: str, project_id: str, findings: list[dict[str, Any]], audited_urls: list[str]
    ) -> int:
        if self.project(tenant, project_id) is None:
            raise ValueError("Project not found")
        now, fresh = time.time(), 0
        existing = {item.fingerprint: item for item in self.findings(tenant, project_id)}
        seen = set()
        for finding in findings:
            key = token_hash(
                json.dumps(
                    {name: finding.get(name) for name in ("check_id", "url", "status")},
                    sort_keys=True,
                )
            )
            seen.add(key)
            old = existing.get(key)
            fresh += old is None or not old.active
            body = dict(
                id=project_id + "-" + key,
                tenant_id=tenant,
                project_id=project_id,
                fingerprint=key,
                details=finding,
                active=True,
                first_seen=old.first_seen if old else now,
                last_seen=now,
            )
            self.db.collection("optimizer_findings").document(body["id"]).set(self._pack(body))
        for key, old in existing.items():
            if key not in seen and old.details.get("url") in audited_urls:
                self.db.collection("optimizer_findings").document(old.id).update({"active": False})
        return fresh

    def findings(self, tenant: str, project_id: str) -> list[FindingRecord]:
        return [
            cast(FindingRecord, self._record(FindingRecord, snap))
            for snap in self._query("optimizer_findings", tenant_id=tenant, project_id=project_id)
        ]

    def reconcile(self, tenant: str | None = None) -> int:
        query = self.db.collection("optimizer_projects").where(
            filter=FieldFilter("next_audit", "<=", time.time())
        )
        if tenant:
            query = query.where(filter=FieldFilter("tenant_id", "==", tenant))
        scheduled = 0
        for snapshot in query.stream():
            project = cast(Project, self._record(Project, snapshot))
            spec = ProjectSpec.model_validate(project.spec)
            if spec.enabled:
                try:
                    self.enqueue(
                        project.tenant_id,
                        project.id,
                        "audit",
                        f"reconcile:{int(project.next_audit)}",
                        {},
                    )
                    scheduled += 1
                except ValueError:
                    pass  # Quota is exhausted; the next monthly window can retry.
            snapshot.reference.update({"next_audit": time.time() + spec.reconcile_seconds})
        return scheduled
