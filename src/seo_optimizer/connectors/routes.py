"Authenticated connector management; untrusted public hooks require independent signatures."

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from seo_optimizer.connectors import jobs, oauth
from seo_optimizer.connectors.models import (
    CollectionRequest,
    ConnectionInput,
    ImportRequest,
    Platform,
    ProposalInput,
)
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.connectors.transport import ConnectorError
from seo_optimizer.store import Store


def install(app: FastAPI, store: Store, owned: Any, csrf: Any, job_json: Any) -> None:
    def service(request: Request, id: str) -> ConnectorService:
        return ConnectorService(store, owned(request, id))

    @app.exception_handler(ConnectorError)
    async def connector_error(request: Request, error: ConnectorError) -> JSONResponse:
        status = (
            409
            if error.code in {"conflict", "busy", "write_uncertain"}
            else 403
            if error.code in {"policy", "signature"}
            else 429
            if error.code == "rate_limited"
            else 404
            if error.code == "not_found"
            else 422
        )
        return JSONResponse(
            {"detail": str(error), "code": error.code},
            status_code=status,
            headers={"Retry-After": str(error.retry_after)} if error.retry_after else {},
        )

    def worker_service(request: Request, id: str) -> ConnectorService:
        value = service(request, id)
        if not request.headers.get("authorization", "").startswith("Bearer "):
            raise HTTPException(403, "Worker state requires scoped API authorization")
        return value

    @app.get("/api/v1/worker/connectors/{id}/{platform}/state")
    def worker_state(request: Request, id: str, platform: Platform) -> Any:
        value, version = worker_service(request, id).state(platform)
        return {"value": value, "version": version}

    @app.put("/api/v1/worker/connectors/{id}/{platform}/state")
    def worker_save_state(
        request: Request, id: str, platform: Platform, value: dict[str, Any]
    ) -> Any:
        s = worker_service(request, id)
        if (
            set(value) != {"value", "expected"}
            or not isinstance(value["value"], dict)
            or type(value["expected"]) is not int
        ):
            raise HTTPException(400, "Invalid connection state contract")
        return {"saved": store.save_state(s.key(platform), value["value"], value["expected"])}

    @app.get("/api/v1/projects/{id}/connectors")
    def list_connections(request: Request, id: str) -> Any:
        return service(request, id).overview()

    @app.put("/api/v1/projects/{id}/connectors/{platform}")
    def configure(request: Request, id: str, platform: Platform, value: ConnectionInput) -> Any:
        s = service(request, id)
        csrf(request)
        if value.platform != platform:
            raise HTTPException(400, "Platform differs from the endpoint")
        return s.configure(value)

    @app.delete("/api/v1/projects/{id}/connectors/{platform}")
    def disconnect(request: Request, id: str, platform: Platform) -> Any:
        s = service(request, id)
        csrf(request)
        s.disconnect(platform)
        return {
            "disconnected": True,
            "note": (
                "Stored platform credentials were removed. Revoke the platform grant in its "
                "settings if required."
            ),
        }

    @app.post("/api/v1/projects/{id}/connectors/{platform}/collect", status_code=202)
    def collect(request: Request, id: str, platform: Platform, value: CollectionRequest) -> Any:
        s = service(request, id)
        csrf(request)
        state, _ = s.state(platform)
        if not state.get("config"):
            raise ConnectorError("not_connected", "Connect the platform first")
        return job_json(
            jobs.enqueue(store, s.project, platform, "collect", value.model_dump(mode="json")),
            hosted=store.settings.hosted,
        )

    @app.post("/api/v1/projects/{id}/connectors/{platform}/proposals", status_code=201)
    def propose(request: Request, id: str, platform: Platform, value: ProposalInput) -> Any:
        s = service(request, id)
        csrf(request)
        return s.propose(platform, value)

    @app.post(
        "/api/v1/projects/{id}/connectors/{platform}/proposals/{proposal_id}/{operation}",
        status_code=202,
    )
    def publish(
        request: Request, id: str, platform: Platform, proposal_id: str, operation: str
    ) -> Any:
        s = service(request, id)
        csrf(request)
        if operation not in {"apply", "rollback", "verify"}:
            raise HTTPException(404, "Operation not found")
        return job_json(
            jobs.enqueue(store, s.project, platform, operation, proposal_id=proposal_id),
            hosted=store.settings.hosted,
        )

    @app.post("/api/v1/projects/{id}/connectors/{platform}/import")
    def import_records(request: Request, id: str, platform: Platform, value: ImportRequest) -> Any:
        s = service(request, id)
        csrf(request)
        return s.import_records(platform, value)

    @app.post("/api/v1/projects/{id}/connectors/{platform}/oauth")
    def authorize(request: Request, id: str, platform: Platform) -> Any:
        s = service(request, id)
        csrf(request)
        return {"url": oauth.begin(store, s.project.tenant_id, id, platform)}

    @app.get("/api/v1/connectors/oauth/callback")
    def callback(request: Request, state: str, code: str = "", error: str = "") -> Any:
        if error:
            raise ConnectorError(
                "oauth_denied", "Platform authorization was not completed; reconnect to try again"
            )
        if len(list(request.query_params.multi_items())) != len(dict(request.query_params)):
            raise ConnectorError("oauth_state", "Duplicate OAuth callback parameters are invalid")
        _, project_id, platform = oauth.complete(
            store, state, code, query=dict(request.query_params)
        )
        return RedirectResponse(
            store.settings.frontend_url.rstrip("/")
            + "/dashboard/connections/"
            + platform.value
            + "?project="
            + project_id,
            status_code=303,
        )

    @app.post("/webhooks/connectors/{tenant}/{id}/{platform}")
    async def event(request: Request, tenant: str, id: str, platform: Platform) -> Any:
        from seo_optimizer.connectors.events import handle, native_deployment, native_repository

        project = store.project(tenant, id)
        if project is None:
            raise HTTPException(404, "Connection not found")
        s = ConnectorService(store, project)
        raw = await request.body()
        if len(raw) > 500000:
            raise HTTPException(413, "Event exceeds its limit")
        headers = dict(request.headers)
        if (
            platform in {Platform.VERCEL, Platform.NETLIFY}
            and "x-optimiser-signature" not in headers
        ):
            return native_deployment(s, platform, headers, raw)
        if (
            platform in {Platform.GITLAB, Platform.BITBUCKET}
            and "x-optimiser-signature" not in headers
        ):
            return native_repository(s, platform, headers, raw)
        return handle(s, platform, headers, raw)
