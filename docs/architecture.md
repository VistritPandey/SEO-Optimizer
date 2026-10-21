# Autonomous SEO agent architecture

Your Optimiser is an autonomous SEO agent that follows relevant website changes through investigation, permitted repairs, project checks and deployed-page verification. Hosted source changes remain pull requests for owner review.

The package separates knowledge/contracts/evaluation from the web application and worker.
`contracts.py`, `knowledge.py`, `policy.py`, `audit.py` and `evaluation.py` work without a web
server or provider credential. The private knowledge and UI resources ship inside the wheel.

## Control plane

FastAPI serves Jinja templates and versioned `/api/v1` management/worker endpoints. Templates
use the same tenant-scoped store as APIs. A future frontend can replace templates without
changing worker execution. Signed sessions, CSRF validation and scoped bearer tokens establish
account identity. Project IDs supplied by callers never grant ownership.

SQLAlchemy stores accounts, encrypted project secrets, policies, findings, jobs and leases.
SQLite supports local use; production requires PostgreSQL. Startup records schema version 1
and uses an advisory lock for concurrent PostgreSQL initialization. Future deployed schema
changes require explicit migrations. No global mutable project configuration is used.

The queue claims work with compare-and-swap updates and excludes a second active job for a
project. Waiting checks/deployments release leases. Expired leases recover; stale workers cannot
finish another worker's job. Periodic reconciliation schedules missed work even without webhooks.
Remote workers authenticate outbound over HTTPS with one account's revocable scoped token.
They receive only that account's claimed project and encrypted-at-rest credentials.

## Execution

1. Verify GitHub webhook signatures, repository/branch and revision; enqueue durable work.
2. Snapshot the selected revision; supersede stale pushes and map changed files to affected URLs.
3. Fetch bounded same-origin responses through resolved, checked IP addresses. Optionally collect
   rendered DOM/screenshots or official performance diagnostics. Record collection failures.
4. Run deterministic checks. Select relevant skill references and invoke a configured provider
   when needed. Page/repository text is untrusted evidence, not executable agent instructions.
5. Validate structured findings, source/evidence references and policy. Tools can inspect known
   routes, confined files/diffs, run configured checks or stage exact patch proposals.
6. Independently check actual patches: paths, private intent, stale/ambiguous replacements,
   file limits, script/body preservation and configured publication policy. Build commands run
   only in an isolated Docker sandbox with explicit project commands and prebuilt dependencies.
7. Commit each changed file separately. Publish a GitHub PR, check its exact head/current base,
   wait for required checks, merge when authorized and wait for the merged deployment SHA.
8. Re-fetch affected pages, verify specific fixes and detect new observed defects. Confirmed
   failures permit a guarded revert while no newer branch change exists. Inconclusive evidence
   blocks verification and never fabricates success or proof of a regression.

Local repository integration follows the same inspection/verification path with isolated clones
and a clean, unchanged checked-out target branch. Repository hooks and global Git config are
disabled. Hosted workers cannot accept arbitrary server filesystem paths.

## Providers and authority

Adapters support Ollama chat, OpenAI Responses, Anthropic Messages and Google generation.
Tool calling, schema output and vision are separate capabilities. All responses are locally
validated, with bounded explicit regeneration for invalid JSON when schema mode is configured.
Tool failure, missing keys, unsupported capabilities or invalid decisions cannot publish a patch.
Model time, step/token/file limits bound work. Monetary guards stop further steps when
reported usage and configured prices show the budget is exhausted; they do not cap upstream
billing retroactively. Missing usage/prices stay unknown. Unknown token/cost data
stays unknown. Shared production workers accept official model endpoints; custom/local endpoints
belong on account-scoped local workers.

Policy grants action categories independently of prompts. Models cannot authorize merges,
change privacy/training preferences, attest their own fixes or invent owner facts. Content
truth requires authoritative evidence beyond structural validation. Repository permissions never
imply business-profile, merchant or search-account access. These remain explicit dependencies.

## Measurement

Each finding records evidence and sources separately from severity. Per-page target verification
avoids blaming a new patch for a pre-existing defect on another page. Repeated findings retain
memory; successful re-audits resolve findings only on observed URLs. Reports record coverage,
actual usage, checks, PR/revisions and deployed verification, with missing outcomes exposed.
Performance lab snapshots, field metrics, citations, rankings, visits and conversions are separate.
An observed technical repair is not proof of search uplift.
