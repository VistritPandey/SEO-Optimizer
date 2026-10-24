"OAuth grants scoped to project and provider, one-use state, encrypted refresh credentials."

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from urllib.parse import urlencode

import httpx

from seo_optimizer.connectors.models import ConnectionInput, Platform
from seo_optimizer.connectors.transport import ConnectorError, Transport
from seo_optimizer.store import Store

GOOGLE_SCOPES = {
    Platform.SEARCH_CONSOLE: "https://www.googleapis.com/auth/webmasters.readonly",
    Platform.GA4: "https://www.googleapis.com/auth/analytics.readonly",
    Platform.BUSINESS_PROFILE: "https://www.googleapis.com/auth/business.manage",
}
OAUTH = {
    "shopify": ("", ""),
    "google": (
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
    ),
    "webflow": (
        "https://webflow.com/oauth/authorize",
        "https://api.webflow.com/oauth/access_token",
    ),
    "gitlab": ("https://gitlab.com/oauth/authorize", "https://gitlab.com/oauth/token"),
    "bitbucket": (
        "https://bitbucket.org/site/oauth2/authorize",
        "https://bitbucket.org/site/oauth2/access_token",
    ),
}


def provider(platform: Platform) -> str:
    name = "google" if platform in GOOGLE_SCOPES else platform.value
    if name not in OAUTH:
        raise ConnectorError("unsupported", "Use scoped platform credentials for this connector")
    return name


def credentials(name: str) -> tuple[str, str]:
    prefix = "OPT_CONNECTOR_" + name.upper()
    client = os.getenv(prefix + "_CLIENT_ID", "")
    secret = os.getenv(prefix + "_CLIENT_SECRET", "")
    if not client or not secret:
        raise ConnectorError(
            "oauth_unconfigured",
            "The service operator must configure this platform's OAuth application",
        )
    return client, secret


def availability(platform: Platform) -> dict[str, bool]:
    """Expose connection capabilities without exposing operator credentials."""
    name = "google" if platform in GOOGLE_SCOPES else platform.value
    supported = name in OAUTH
    prefix = "OPT_CONNECTOR_" + name.upper()
    return {
        "oauth_supported": supported,
        "oauth_available": supported
        and bool(os.getenv(prefix + "_CLIENT_ID") and os.getenv(prefix + "_CLIENT_SECRET")),
    }


def begin(store: Store, tenant: str, project: str, platform: Platform) -> str:
    name = provider(platform)
    client, _ = credentials(name)
    from seo_optimizer.connectors.service import ConnectorService

    project_record = store.project(tenant, project)
    if project_record is None:
        raise ConnectorError("not_found", "Project not found")
    connection, _ = ConnectorService(store, project_record).state(platform)
    if not connection.get("config"):
        raise ConnectorError("not_connected", "Save the account resource before authorizing")
    config = ConnectionInput.model_validate(connection["config"])
    authorize_url = OAUTH[name][0]
    if name == "shopify":
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", config.resource):
            raise ConnectorError("configuration", "Use the permanent Shopify shop domain")
        authorize_url = "https://" + config.resource + "/admin/oauth/authorize"
    state = secrets.token_urlsafe(40)
    verifier = secrets.token_urlsafe(48)
    key = "connector-oauth:" + hashlib.sha256(state.encode()).hexdigest()
    redirect = store.settings.public_url.rstrip("/") + "/api/v1/connectors/oauth/callback"
    data = {
        "tenant": tenant,
        "project": project,
        "platform": platform.value,
        "expires": time.time() + 600,
        "verifier": verifier,
        "redirect": redirect,
        "generation": connection.get("generation"),
    }
    if not store.save_state(key, data, 0):
        raise ConnectorError("conflict", "OAuth state could not be reserved")
    params = {
        "client_id": client,
        "redirect_uri": redirect,
        "response_type": "code",
        "state": state,
    }
    if name in {"google", "gitlab"}:
        params.update(
            code_challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("="),
            code_challenge_method="S256",
        )
    if name == "google":
        params.update(
            scope=GOOGLE_SCOPES[platform],
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
    elif name == "gitlab":
        params["scope"] = "api" if config.allow_writes else "read_api"
    elif name == "webflow":
        params["scope"] = "sites:read pages:read cms:read" + (
            " pages:write cms:write" if config.allow_writes else ""
        )
    elif name == "shopify":
        params["scope"] = "read_products,write_products" if config.allow_writes else "read_products"
    return authorize_url + "?" + urlencode(params)


def complete(
    store: Store,
    state: str,
    code: str,
    client: httpx.Client | None = None,
    query: dict[str, str] | None = None,
) -> tuple[str, str, Platform]:
    if len(state) > 200 or not code or len(code) > 4000:
        raise ConnectorError("oauth_state", "Invalid OAuth response")
    key = "connector-oauth:" + hashlib.sha256(state.encode()).hexdigest()
    saved, version = store.state(key)
    if not saved or saved.get("expires", 0) < time.time() or not store.save_state(key, {}, version):
        raise ConnectorError("oauth_state", "OAuth state expired or was already used")
    p = Platform(saved["platform"])
    name = provider(p)
    client_id, secret = credentials(name)
    project = store.project(saved["tenant"], saved["project"])
    if project is None:
        raise ConnectorError("not_found", "Project no longer exists")
    from seo_optimizer.connectors.service import ConnectorService

    service = ConnectorService(store, project, client)
    record, _ = service.state(p)
    if not record.get("config"):
        raise ConnectorError("not_connected", "Configure the account resource before connecting")
    if record.get("generation") != saved.get("generation"):
        raise ConnectorError("oauth_state", "Connection changed during authorization; start again")
    config = ConnectionInput.model_validate(record["config"])
    if name == "shopify":
        supplied = query or {}
        if (
            supplied.get("shop") != config.resource
            or supplied.get("code") != code
            or supplied.get("state") != state
        ):
            raise ConnectorError("oauth_state", "Shopify callback does not match the connection")
        message = urlencode(
            sorted((k, v) for k, v in supplied.items() if k not in {"hmac", "signature"})
        )
        expected = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        stamp = supplied.get("timestamp", "")
        if (
            not stamp.isdigit()
            or abs(time.time() - int(stamp)) > 600
            or not hmac.compare_digest(expected, supplied.get("hmac", ""))
        ):
            raise ConnectorError("signature", "Shopify callback signature is invalid")
    t = Transport(config, client)
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": saved["redirect"],
        "client_id": client_id,
        "client_secret": secret,
    }
    if name in {"google", "gitlab"}:
        form["code_verifier"] = saved["verifier"]
    try:
        token_url = OAUTH[name][1]
        headers = None
        if name == "bitbucket":
            raw = f"{client_id}:{secret}".encode()
            headers = {"Authorization": "Basic " + base64.b64encode(raw).decode()}
            form.pop("client_id")
            form.pop("client_secret")
        if name == "shopify":
            token_url = "https://" + config.resource + "/admin/oauth/access_token"
            tokens = t.request("POST", token_url, body=form, read_only=False)
        elif name == "webflow":
            tokens = t.request("POST", token_url, body=form, read_only=False)
        else:
            tokens = t.request("POST", token_url, headers=headers, form=form, read_only=False)
        if not isinstance(tokens.get("access_token"), str):
            raise ConnectorError("invalid_response", "OAuth did not return an access token")
        config.credentials.update(access_token=tokens["access_token"])
        if tokens.get("refresh_token"):
            config.credentials["refresh_token"] = tokens["refresh_token"]
        if name in {"google", "gitlab", "bitbucket", "shopify"}:
            config.credentials.update(client_id=client_id, client_secret=secret)
        service.configure(config)
    finally:
        t.close()
    return saved["tenant"], saved["project"], p


def refresh_google(config: ConnectionInput, client: httpx.Client | None = None) -> None:
    client_id = config.credentials.get("client_id", "")
    secret = config.credentials.get("client_secret", "")
    if not client_id or not secret:
        client_id, secret = credentials("google")
    t = Transport(config, client)
    try:
        tokens = t.request(
            "POST",
            OAUTH["google"][1],
            form={
                "grant_type": "refresh_token",
                "refresh_token": t.secret("refresh_token"),
                "client_id": client_id,
                "client_secret": secret,
            },
            read_only=False,
        )
        if not isinstance(tokens.get("access_token"), str):
            raise ConnectorError("reconnect_required", "Refresh failed; reconnect Google")
        config.credentials["access_token"] = tokens["access_token"]
    finally:
        t.close()


def refresh_access(config: ConnectionInput, client: httpx.Client | None = None) -> None:
    name = provider(config.platform)
    if name == "google":
        refresh_google(config, client)
        return
    if name not in {"gitlab", "bitbucket", "shopify"}:
        raise ConnectorError("reconnect_required", "This platform requires renewed authorization")
    client_id = config.credentials.get("client_id", "")
    secret = config.credentials.get("client_secret", "")
    if not client_id or not secret:
        client_id, secret = credentials(name)
    t = Transport(config, client)
    form = {
        "grant_type": "refresh_token",
        "refresh_token": t.secret("refresh_token"),
        "client_id": client_id,
        "client_secret": secret,
    }
    try:
        if name == "bitbucket":
            headers = {
                "Authorization": "Basic "
                + base64.b64encode(f"{client_id}:{secret}".encode()).decode()
            }
            form.pop("client_id")
            form.pop("client_secret")
            tokens = t.request("POST", OAUTH[name][1], headers=headers, form=form, read_only=False)
        elif name == "shopify":
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", config.resource):
                raise ConnectorError("configuration", "Shop domain is invalid")
            tokens = t.request(
                "POST",
                "https://" + config.resource + "/admin/oauth/access_token",
                body=form,
                read_only=False,
            )
        else:
            tokens = t.request("POST", OAUTH[name][1], form=form, read_only=False)
        if not isinstance(tokens.get("access_token"), str):
            raise ConnectorError(
                "reconnect_required", "Refresh failed; authorize the platform again"
            )
        config.credentials["access_token"] = tokens["access_token"]
        if tokens.get("refresh_token"):
            config.credentials["refresh_token"] = tokens["refresh_token"]
    finally:
        t.close()
