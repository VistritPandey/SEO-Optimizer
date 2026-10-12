"""Tenant-scoped storage and a durable compare-and-swap job queue."""

import hashlib
import json
import secrets
import time
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from seo_optimizer.application_models import ProjectCreate, ProjectSecrets, ProjectSpec
from seo_optimizer.settings import Settings


class Base(DeclarativeBase):
    pass


class SchemaVersion(Base):
    __tablename__ = "schema_version"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[float] = mapped_column(Float)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON)
    credentials: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[float] = mapped_column(Float)
    next_audit: Mapped[float] = mapped_column(Float)
    last_revision: Mapped[str] = mapped_column(String(64), default="")
    last_report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("project_id", "dedupe_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), index=True)
    dedupe_key: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[float] = mapped_column(Float)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    worker_id: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[float] = mapped_column(Float)


class FindingRecord(Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("project_id", "fingerprint"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen: Mapped[float] = mapped_column(Float)
    last_seen: Mapped[float] = mapped_column(Float)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    until: Mapped[float] = mapped_column(Float)


def identifier() -> str:
    return str(uuid4())


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class Store:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_engine(
            settings.database_url.replace("postgresql://", "postgresql+psycopg://", 1),
            connect_args={"check_same_thread": False, "timeout": 30}
            if settings.database_url.startswith("sqlite")
            else {},
            pool_pre_ping=True,
        )
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        with self.engine.begin() as connection:
            if connection.dialect.name == "postgresql":
                connection.execute(text("SELECT pg_advisory_xact_lock(701032021)"))
            Base.metadata.create_all(connection)
            version = connection.execute(select(SchemaVersion.version)).scalar_one_or_none()
            if version is None:
                connection.execute(insert(SchemaVersion).values(id=1, version=1))
            elif version != 1:
                raise ValueError("Database schema requires an explicit migration")

    def create_user(self, email: str, password_hash: str) -> tuple[User, str]:
        token = secrets.token_urlsafe(40)
        user = User(
            id=identifier(),
            email=email,
            password_hash=password_hash,
            token_hash=token_hash(token),
            created_at=time.time(),
        )
        with self.sessions.begin() as session:
            session.add(user)
        return user, token

    def user(
        self, *, email: str | None = None, id: str | None = None, token: str | None = None
    ) -> User | None:
        with self.sessions() as session:
            query = select(User)
            if email is not None:
                query = query.where(User.email == email.lower())
            elif id is not None:
                query = query.where(User.id == id)
            elif token is not None:
                query = query.where(User.token_hash == token_hash(token))
            else:
                return None
            return session.scalar(query)

    def rotate_token(self, tenant: str) -> str:
        token = secrets.token_urlsafe(40)
        with self.sessions.begin() as session:
            session.execute(
                update(User).where(User.id == tenant).values(token_hash=token_hash(token))
            )
        return token

    def throttle(self, key: str) -> bool:
        """Persist failed-login attempts; return false when the window is exhausted."""
        digest, now = token_hash(key), time.time()
        with self.sessions.begin() as session:
            value = session.get(LoginAttempt, digest)
            if value is None:
                session.add(LoginAttempt(key=digest, count=1, until=now + 900))
                return True
            if value.until < now:
                value.count, value.until = 1, now + 900
                return True
            value.count += 1
            return value.count <= 10

    def create_project(self, tenant: str, value: ProjectCreate) -> Project:
        with self.sessions.begin() as session:
            if (
                len(list(session.scalars(select(Project.id).where(Project.tenant_id == tenant))))
                >= 20
            ):
                raise ValueError("Project limit reached")
            project = Project(
                id=identifier(),
                tenant_id=tenant,
                spec=value.spec.model_dump(mode="json"),
                credentials=self.settings.cipher.encrypt(
                    value.credentials.model_dump_json().encode()
                ).decode(),
                updated_at=time.time(),
                next_audit=time.time() + value.spec.reconcile_seconds,
                last_revision="",
                last_report={},
            )
            session.add(project)
        self.enqueue(tenant, project.id, "audit", f"initial:{project.id}", {})
        return project

    def projects(self, tenant: str) -> list[Project]:
        with self.sessions() as session:
            return list(
                session.scalars(
                    select(Project)
                    .where(Project.tenant_id == tenant)
                    .order_by(Project.updated_at.desc())
                )
            )

    def project(self, tenant: str, id: str) -> Project | None:
        with self.sessions() as session:
            return session.scalar(
                select(Project).where(Project.id == id, Project.tenant_id == tenant)
            )

    def webhook_project(self, id: str) -> Project | None:
        # Only the signature-authenticated webhook path may use this lookup.
        with self.sessions() as session:
            return session.get(Project, id)

    def secrets(self, project: Project) -> ProjectSecrets:
        return ProjectSecrets.model_validate_json(
            self.settings.cipher.decrypt(project.credentials.encode())
        )

    def update_project(
        self, tenant: str, id: str, spec: ProjectSpec, credentials: ProjectSecrets | None = None
    ) -> None:
        with self.sessions.begin() as session:
            project = session.scalar(
                select(Project).where(Project.id == id, Project.tenant_id == tenant)
            )
            if project is None:
                raise KeyError("Project not found")
            project.spec, project.updated_at = spec.model_dump(mode="json"), time.time()
            if credentials is not None:
                project.credentials = self.settings.cipher.encrypt(
                    credentials.model_dump_json().encode()
                ).decode()

    def enqueue(
        self, tenant: str, project_id: str, kind: str, key: str, payload: dict[str, Any]
    ) -> Job:
        if self.project(tenant, project_id) is None:
            raise KeyError("Project not found")
        now = time.time()
        job = Job(
            id=identifier(),
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
        try:
            with self.sessions.begin() as session:
                session.add(job)
        except IntegrityError:
            with self.sessions() as session:
                existing = session.scalar(
                    select(Job).where(
                        Job.project_id == project_id, Job.dedupe_key == key, Job.tenant_id == tenant
                    )
                )
                if existing is None:
                    raise
                return existing
        return job

    def jobs(self, tenant: str, project_id: str | None = None) -> list[Job]:
        with self.sessions() as session:
            query = select(Job).where(Job.tenant_id == tenant)
            if project_id:
                query = query.where(Job.project_id == project_id)
            return list(session.scalars(query.order_by(Job.created_at.desc()).limit(100)))

    def job(self, tenant: str, id: str) -> Job | None:
        with self.sessions() as session:
            return session.scalar(select(Job).where(Job.id == id, Job.tenant_id == tenant))

    def claim(self, worker: str, tenant: str | None = None) -> Job | None:
        now = time.time()
        with self.sessions.begin() as session:
            live = set(
                session.scalars(
                    select(Job.project_id).where(Job.status == "running", Job.lease_until > now)
                )
            )
            query = select(Job).where(
                Job.available_at <= now,
                Job.status.in_(["queued", "waiting_checks", "waiting_deployment", "running"]),
                Job.lease_until <= now,
                Job.project_id.not_in(live),
            )
            if tenant:
                query = query.where(Job.tenant_id == tenant)
            candidate = session.scalar(query.order_by(Job.created_at).limit(1))
            if candidate is None:
                return None
            attempts = candidate.attempts + (candidate.status in {"queued", "running"})
            changed = session.execute(
                update(Job)
                .where(
                    Job.id == candidate.id, Job.status == candidate.status, Job.lease_until <= now
                )
                .values(
                    status="running",
                    worker_id=worker,
                    lease_until=now + 900,
                    attempts=attempts,
                    updated_at=now,
                )
            )
            if cast(CursorResult[Any], changed).rowcount != 1:
                return None
            session.refresh(candidate)
            return candidate

    def finish(
        self,
        tenant: str,
        id: str,
        worker: str,
        status: str,
        result: dict[str, Any],
        delay: float = 0,
    ) -> None:
        with self.sessions.begin() as session:
            job = session.scalar(
                select(Job).where(
                    Job.id == id,
                    Job.tenant_id == tenant,
                    Job.worker_id == worker,
                    Job.status == "running",
                )
            )
            if job is None:
                raise ValueError("Job lease no longer owned")
            job.status, job.result = status, result
            job.lease_until, job.available_at, job.updated_at = 0, time.time() + delay, time.time()
            job.events = [
                *job.events[-99:],
                {"time": time.time(), "message": result.get("summary", status)},
            ]
            project = session.scalar(
                select(Project).where(Project.id == job.project_id, Project.tenant_id == tenant)
            )
            if project is not None and result.get("report"):
                project.last_report = result["report"]
                project.updated_at = time.time()
                if result.get("revision") and status in {
                    "complete",
                    "waiting_checks",
                    "waiting_deployment",
                }:
                    project.last_revision = result["revision"]

    def remember_findings(
        self, tenant: str, project_id: str, findings: list[dict[str, Any]], audited_urls: list[str]
    ) -> int:
        now, fresh = time.time(), 0
        with self.sessions.begin() as session:
            active = list(
                session.scalars(
                    select(FindingRecord).where(
                        FindingRecord.tenant_id == tenant, FindingRecord.project_id == project_id
                    )
                )
            )
            by_key = {item.fingerprint: item for item in active}
            seen: set[str] = set()
            for finding in findings:
                key = token_hash(
                    json.dumps(
                        {key: finding.get(key) for key in ("check_id", "url", "summary")},
                        sort_keys=True,
                    )
                )
                seen.add(key)
                existing = by_key.get(key)
                if existing:
                    fresh += not existing.active
                    existing.details, existing.active, existing.last_seen = finding, True, now
                else:
                    fresh += 1
                    session.add(
                        FindingRecord(
                            id=identifier(),
                            tenant_id=tenant,
                            project_id=project_id,
                            fingerprint=key,
                            details=finding,
                            active=True,
                            first_seen=now,
                            last_seen=now,
                        )
                    )
            for item in active:
                if item.details.get("url") in audited_urls and item.fingerprint not in seen:
                    item.active = False
        return fresh

    def findings(self, tenant: str, project_id: str) -> list[FindingRecord]:
        with self.sessions() as session:
            return list(
                session.scalars(
                    select(FindingRecord)
                    .where(
                        FindingRecord.tenant_id == tenant, FindingRecord.project_id == project_id
                    )
                    .order_by(FindingRecord.active.desc(), FindingRecord.last_seen.desc())
                )
            )

    def reconcile(self, tenant: str | None = None) -> int:
        now, scheduled = time.time(), 0
        with self.sessions() as session:
            query = select(Project).where(Project.next_audit <= now)
            if tenant:
                query = query.where(Project.tenant_id == tenant)
            due = list(session.scalars(query))
        for project in due:
            spec = ProjectSpec.model_validate(project.spec)
            if spec.enabled:
                self.enqueue(
                    project.tenant_id,
                    project.id,
                    "audit",
                    f"reconcile:{int(project.next_audit)}",
                    {},
                )
                scheduled += 1
            with self.sessions.begin() as session:
                session.execute(
                    update(Project)
                    .where(Project.id == project.id, Project.next_audit == project.next_audit)
                    .values(next_audit=now + spec.reconcile_seconds)
                )
        return scheduled
