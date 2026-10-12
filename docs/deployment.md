# Deployment and operation

## Local

Run `uv sync --locked --extra browser` and `uv run playwright install chromium` for browser/vision
collection. Start `uv run seo-optimizer serve` and `uv run seo-optimizer worker` as separate processes.
The UI is on port 8000. Registration creates a separate account/workspace. SQLite, encrypted
credentials and snapshots live under the ignored `.data` directory. A random local key is generated
with file mode 0600. Keep it: changing the key makes existing credentials unreadable.

Use `uv run seo-optimizer demo` for a real local Git repository and a one-time demo account.
Start the printed HTTP website command before running its worker. The demo is not available in
production mode. Local repository roots are explicitly restricted through OPT_REPO_ROOTS.

## Hosted web and worker

The web control plane can use Vercel; api/index.py is its ASGI entrypoint. Configure
OPT_ENV=production, a PostgreSQL OPT_DATABASE_URL, an OPT_SECRET_KEY with at least 32 random
characters, OPT_DATA_DIR=/tmp/optimizer and the HTTPS OPT_PUBLIC_URL. Set registration policy
explicitly. The key must remain stable and match the worker's key when sharing a database.
No SQLite or filesystem queue is used for production persistence.

The portable worker runs on an always-on host. Either share the same PostgreSQL database/key,
or use outbound HTTPS with OPT_CONTROL_URL and the scoped token generated in workspace Settings:

```sh
uv run seo-optimizer worker --remote
```

A local remote worker can reach its own Ollama endpoint while the dashboard stays hosted. No
public tunnel into Ollama is required. Tokens are account-scoped and can be rotated. Each server
process is replaceable; jobs, leases, deduplication keys, findings and reports are durable in SQL.

The Dockerfile packages a non-root web/worker image. compose.yaml provides PostgreSQL and both
services. Supply OPT_POSTGRES_PASSWORD and OPT_SECRET_KEY securely. Place HTTPS in front of
the container web service: production session cookies require HTTPS. External hosting credentials
are needed to publish; deployment configurations are provided without pretending a live deployment
has occurred.

## GitHub

Connect a selected owner/repository with a repository-scoped token, or provide an App ID,
installation ID and its private key through the authenticated credentials API. Credentials are
encrypted and excluded from ordinary API exports. App credentials are supplied per workspace;
the service does not let users guess an installation ID to use another customer's server key.

For code publication, grant Contents read/write and Pull requests read/write; reading Checks,
commit statuses and Deployments is required for verification. Configure a push webhook at the
project's displayed endpoint and set its matching secret through the credentials API. Signatures,
repository identity and target branch are checked before work is queued. Duplicate pushes reuse a
job, stale revisions are superseded, and known automated merge revisions do not create fix loops.

Native Vercel-to-GitHub deployment records can confirm the merged SHA. The worker waits for the
configured environment's successful deployment, then fetches the configured website. A confirmed
failed fix can trigger a guarded rollback only if the branch still points to the worker's merged
revision. An unavailable site is inconclusive and is not treated as proof for a rollback.

## Execution policy

Project policy controls paths, routes, public/private intent, crawler preferences, facts, model
capabilities, automatic fixes and merging. Static HTML metadata has deterministic verification.
Framework metadata and content changes require configured build/test commands in an isolated
Docker sandbox. Containers use no network, a read-only filesystem/mount, limited resources,
non-root UID, dropped capabilities and no host credentials. Use a prebuilt verification image with
the project's dependencies already available; writable build output belongs under /tmp.

The default web image does not ship a Docker daemon or expose a host socket. A worker performing
builds must be provisioned with a dedicated verification executor. The code refuses to run project
commands directly on the host. Missing execution prerequisites block publication with a recorded
dependency; successful local metadata fixes need no shell-based build step.

Content publication is off by default, independently of automatic metadata fixes. Enable it only
with current owner-verified facts, allowed content paths and applicable sandbox checks. Models can
stage exact replacements or new content; grounding, path limits, stale context and project policy
are checked before filesystem changes. Model declarations cannot authorize a merge or prove facts.

## Operations

Health endpoint: /healthz. Authenticated API specification: route shapes are available from
/api/v1/openapi.json; interactive docs are disabled in production. Project/report data requires an
account session or scoped bearer token. Cookie mutations require CSRF verification. Passwords use
scrypt; login attempts are throttled and credentials are encrypted at rest.

Run one worker per required throughput allocation. Lease recovery and per-project exclusion prevent
overlapping jobs. Check/deployment waits release leases. Transient transport failures retry up to
three times; failed prerequisites block the job. Pausing a project cancels queued execution. Monitor
queued age, blocked jobs, lease expiries and actual provider usage; preserve database backups and
the encryption key together. Jobs record verification, revisions, PRs, rollback and unknown metrics.

New installations create schema version 1. Existing schema changes must use explicit reviewed
migrations before upgrading a deployed database. No live schema or secret rotation is performed by
the application's install command.
