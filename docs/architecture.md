# Architecture boundaries for the next milestone

## Current implementation

The Python package separates contracts, knowledge loading, structural policy validation,
provider/tool interfaces, a limited rule baseline and evaluation. None imports a web framework,
provider SDK or GitHub client. Private knowledge resources are included in the Python wheel.

`ProjectContext` carries tenant/project identifiers, website types, environments, exact URL
intent, dated business facts, goals, crawler preferences and allowed actions/paths. Each piece
of evidence carries its tenant/project/environment. Assessment validation rejects cross-scope
references. These checks are internal invariants, not a replacement for authenticated access.

`AuditRequest` deliberately excludes benchmark expectations. Findings refer to supplied
observations and attributed checks. Severity and evidence strength are distinct fields. A
missing prerequisite is represented by an unresolved finding with named dependencies.

`ProviderCapabilities` treats tool calling, JSON Schema output and vision independently.
No capability or model endpoint is assumed. All raw responses receive strict Pydantic validation,
then knowledge/policy checks. Schemas express structural constraints; cross-record semantics
and several model validators still require the Python validation layer.

## Hosting and UI

Use FastAPI with server-rendered templates and minimal browser JavaScript for the first UI.
Keep versioned management APIs separate from templates so a later Next.js frontend can use
the same service. Authentication supplies the tenant; user-submitted identifiers must not
establish ownership. Require tenant-scoped storage and queries before accepting public users.

Host management routes and short webhook handlers independently from the portable worker.
Vercel or another host can serve suitable dashboard/API workloads; do not put an unbounded
repository/build/model loop in a request handler. Deployment selection and persistence/auth
implementation belong to the next milestone, not this knowledge deliverable.

A local worker authenticates outbound to claim durable jobs and calls nearby Ollama. An
always-on cloud worker can later use the same contracts with other provider adapters. No public
exposure of a local model endpoint is needed. A disconnected worker leaves jobs queued.

## Future execution flow

1. Accept and verify a GitHub event; durably enqueue scoped work and acknowledge promptly.
2. Resolve the last successfully analyzed revision and changed page dependencies.
3. Collect affected response/DOM/source observations; reconcile periodically for missed events.
4. Run deterministic checks, then invoke relevant skill references for reasoning that needs AI.
5. Validate structured decisions and independent factual/policy prerequisites.
6. Apply permitted changes in isolated workspaces and an actual execution sandbox.
7. Verify the patch, current revision, relevant checks and deployment before declaring success.

The queue needs idempotency, bounded retries, revision supersession and per-project locking.
Bot-generated events must not create fix loops. Findings need evidence-aware fingerprints so
an unchanged problem does not create repeated work. Shared templates, configuration and
backend render/response changes invalidate affected page evidence.

## Authority and verification

Project policy grants action categories once; the runtime need not seek approval for each
permitted, verified action. Model text cannot grant additional authority. Never treat a model's
declared patch effects, referenced fact IDs or claimed tool success as independent proof.

Tenant isolation, secret protection, network restrictions, sandboxing, argument validation,
content claim verification, actual patch inspection, GitHub permissions and deployed checks
remain mandatory runtime work. Business-profile/merchant permissions are separate from repo
permissions. Missing facts or integration access stop the affected job with a dependency.

Keep the knowledge package private in application/worker distribution. Do not expose its
instruction content through future customer management APIs. Backend API versioning will
initially mirror schema version 1.0, but no HTTP endpoints are implemented in Phase 1.
