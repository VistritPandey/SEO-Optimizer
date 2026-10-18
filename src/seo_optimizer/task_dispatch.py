"""Authenticated Cloud Tasks delivery into the combined Cloud Run web service."""

import logging
import os
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from seo_optimizer.settings import Settings
from seo_optimizer.store import Store

LOGGER = logging.getLogger(__name__)
WORK_PATH = "/api/v1/internal/work"
WAKE_PATH = "/api/v1/internal/wake"


def task_config(settings: Settings) -> tuple[str, str, str]:
    return (
        os.getenv("OPT_TASKS_QUEUE", ""),
        os.getenv("OPT_TASKS_ACCOUNT", ""),
        os.getenv("OPT_TASKS_AUDIENCE", settings.public_url).rstrip("/"),
    )


def dispatch(settings: Settings, delay: int = 0) -> None:
    from google.cloud import tasks_v2

    queue, account, audience = task_config(settings)
    if not queue or not account or not audience.startswith("https://"):
        raise ValueError("Cloud Tasks queue, account and HTTPS audience are required")
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": audience + WORK_PATH,
            "headers": {"Content-Type": "application/json"},
            "body": b"{}",
            "oidc_token": {"service_account_email": account, "audience": audience},
        },
        "dispatch_deadline": timedelta(seconds=1200),
        "schedule_time": datetime.now(UTC) + timedelta(seconds=max(0, delay)),
    }
    with tasks_v2.CloudTasksClient() as client:
        client.create_task(request={"parent": queue, "task": task}, timeout=15)


def authorize(request: Request, settings: Settings) -> None:
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.id_token import verify_oauth2_token

    queue, account, audience = task_config(settings)
    if not queue or not account:
        raise HTTPException(503, "Task delivery is not configured")
    bearer = request.headers.get("authorization", "")
    if not bearer.startswith("Bearer "):
        raise HTTPException(401, "Task identity required")
    try:
        claims = verify_oauth2_token(  # type: ignore[no-untyped-call]
            bearer[7:], GoogleRequest(), audience=audience
        )
    except (ValueError, GoogleAuthError):
        raise HTTPException(403, "Invalid task identity") from None
    if claims.get("email") != account or claims.get("email_verified") is not True:
        raise HTTPException(403, "Task identity not permitted")


def install(app: FastAPI, storage: Store, settings: Settings) -> None:
    # One process in the combined container; the queue additionally serializes deliveries.
    lock = threading.Lock()

    @app.post(WORK_PATH, include_in_schema=False)
    def work(request: Request) -> dict[str, bool]:
        authorize(request, settings)
        if not lock.acquire(blocking=False):
            raise HTTPException(429, "Worker is busy")
        try:
            from seo_optimizer.worker import Worker

            worked = Worker(storage, settings).tick()
            if storage.has_pending_jobs():
                dispatch(settings, delay=30)
            return {"worked": worked}
        finally:
            lock.release()

    @app.post(WAKE_PATH, include_in_schema=False)
    def wake(request: Request) -> dict[str, bool]:
        authorize(request, settings)
        dispatch(settings)
        return {"scheduled": True}

    @app.middleware("http")
    async def wake_after_mutation(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        if (
            os.getenv("OPT_TASKS_QUEUE")
            and request.method in {"POST", "PUT", "PATCH", "DELETE"}
            and response.status_code < 300
            and request.url.path.startswith(("/api/v1/", "/webhooks/"))
            and not request.url.path.startswith("/api/v1/internal/")
        ):
            try:
                if await run_in_threadpool(storage.has_pending_jobs):
                    await run_in_threadpool(dispatch, settings)
            except Exception:
                # Keep the successful user's operation. Hourly reconciliation recovers the queue.
                LOGGER.exception("Task dispatch failed; persisted jobs await reconciliation")
        return response
