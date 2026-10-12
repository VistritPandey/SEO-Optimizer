# Delivery and verification

Delivered application version: **1.0.0**. Knowledge review: **October 12, 2026**.
Knowledge version: 1.0.0; contract version: 1.0.

## Delivered software

The repository includes the private research-backed skill, contracts/evaluation, live collectors,
native provider adapters, autonomous portable worker, tenant-scoped persistence, local Git and
GitHub integration, server-rendered dashboard, versioned APIs, deployment configuration and CI.

The private package contains eight focused references, 39 checks, 30 attributed sources and
21 exported JSON Schemas. Checks declare applicability, required evidence, permitted actions,
verification and no-op conditions. The application exposes findings and results; it does not
serve the skill instructions to customers or install them as a global assistant skill.

The operational loop supports signed pushes, incremental route audits, periodic reconciliation,
policy-checked exact edits, isolated verification, individual file commits, PR checks, rebase
merging, deployment-SHA confirmation, re-fetching and guarded rollback. Local repository fixes
follow the same evidence/verification flow. Queues, retries, leases, tenant boundaries, missing
inputs and repeated findings are handled by application code independently of model prompts.

Broader content publication is off by default, limited to static HTML/Markdown, and requires
current owner fact references plus configured checks. Content permission does not authorize
application-code changes. Private routes, indexing intent, scripts/styles/controls and crawler
preferences have independent checks. Factual meaning still requires authoritative material;
structural validation cannot prove every sentence true.

## Passed verification

| Check | Result | Scope |
|---|---|---|
| Pytest | **145 passed; 0 failed; 0 skipped** | Contracts, policy, tenant isolation, credentials, CSRF, webhook replay, native adapters, leases, remote workers, publication and recovery |
| Lint, formatting and strict types | Passed | Source, tests and hosting entrypoint; 22 typed source modules |
| Knowledge and skill validators | Passed | Source/check relationships, module routing, local references and skill format |
| Build and isolated wheel | Passed | Installed package, knowledge, schemas, SQLite initialization, authenticated templates and CSS/JS outside source imports |
| Real Git/HTTP integration | Passed | Temporary repository commits, verified title repair, merge, live response and repeated-audit idempotence |
| Real local demo | Passed | One actual missing-title fix committed, merged and verified on its served website |
| Real Chromium collection | Passed | Pinned local HTTP requests, rendered DOM and PNG evidence |
| Real Chromium dashboard | Passed | Login, project results/settings, desktop/mobile layout and no JavaScript errors |
| Real pinned HTTPS request | Passed | Original Host/TLS name retained while connecting to a checked IP |
| Actual Ollama schema smoke | Passed | One structured response from installed gemma4:12b |
| Actual Ollama tool smoke | Passed | Native tool call, successful controlled observation and grounded final JSON |
| Synthetic reference replay | 41 passed | Authored rubric examples; no model-quality claim |
| Limited rules replay | 19 passed; 22 skipped | Supported raw-evidence checks; skipped checks remain unassessed |
| Adversarial replay | 10 rejected; 31 skipped | Deliberately malformed/unsupported responses failed as required |

The test suite blocks network access except explicitly permitted loopback integration tests.
It requires no GitHub credentials or paid inference. One dependency deprecation warning comes
from the installed Starlette TestClient/httpx interface; no tests fail because of it.

Machine-readable evidence: `tests.xml`, `wheel-smoke.json`, `local-integration.json`,
`browser-smoke.json`, `ui-smoke.json`, `http-smoke.json`, `reference-replay.json`,
`rules-baseline.json`, `adversarial-replay.json` and the Ollama reports in this directory.

## Failed model-quality trials

Failures are retained rather than converted to successes or removed from coverage.
The installed model was gemma4:12b on an Apple M4. These were development fixtures, not
held-out inference or real search-outcome trials.

| Trial | Passed | Failed | Interpretation |
|---|---:|---:|---|
| Initial model-only fixture run | 2 | 3 | Incorrect action choices and malformed output |
| Restricted assessment-only run | 1 | 4 | Unresolved findings omitted required dependencies |
| Rules plus Ollama hybrid | 14 | 3 | Rules handled 12 cases without inference; model passed 2 of its 5 cases |

The hybrid protocol and response records expose actual inference counts. Its 14/17 result is
**not** a 14/17 model-only score. Rule routing saved 12 inference calls. The small local model
has demonstrated schema/tool capability but is **not qualified for unsupervised publication**
by these quality trials. Invalid decisions block publishing. Rules remain the application's
default provider; stronger/configured models need their own benchmark results.

API cost was zero for local inference; electricity and hardware costs remain unknown. Total
cost per verified model fix is unverified. Actual repository remediation by an LLM, live vision
reasoning quality and paid-provider quality/cost were not measured.

## Skipped and unverified external outcomes

- **Hosting:** Vercel and container configuration is authored; no cloud deployment was performed
  without deployment credentials. PostgreSQL production concurrency and a real Docker build
  sandbox remain unverified in this environment; SQLite and sandbox refusal/policy gates are tested.
- **GitHub:** Signatures, native API protocols, commit/PR/check gates, merge recovery and guarded
  rollback are tested with controlled transports. Real App authentication, cloud writes, merges
  and deployment records require a connected test repository.
- **Performance/accounts:** The PageSpeed adapter and missing-field/quota handling are tested
  with controlled responses. Real PageSpeed quota access, field observations, Search Console,
  business listings, merchant feeds and AI-citation accounts are unverified or unconfigured.
- **Search outcomes:** Rankings, indexing, citations, traffic, conversions and causal uplift
  cannot be inferred from a successful code fix. The dashboard retains these as unknown.
- **Coverage:** The catalog is broader than the executable rules. Remaining checks need model
  interpretation or external evidence; no claim is made that 39 complete deterministic scanners
  or every external account connector has been delivered.

These are explicit access/measurement boundaries of the delivered software, not passing tests.

## Running demo and live-project configuration

The current local dashboard runs at **http://127.0.0.1:8787** and the demo website at
**http://127.0.0.1:8081**. The worker runs separately. Local demo login details are saved in
ignored `.data/demo-login.txt`, mode 0600. They are never committed.

For a live project configure:

1. The exact GitHub `owner/repository`, target branch and permitted folders/route mapping.
2. Its deployed URL and environment, public/private URL intent, real build/test commands and a
   prebuilt sandbox image. Enable rebase merging; supply required repository check names.
3. The provider/model ID, capabilities and reachable worker-side endpoint. The installed local
   endpoint is `http://127.0.0.1:11434`; gemma4:12b requires quality improvements or replacement.
4. Current owner-verified business/product facts and original source material, goals, crawler
   preferences, publication policy and usage budgets.
5. Repository-scoped GitHub App/token access and a matching signed push webhook secret entered
   through authenticated settings. The deployment integration must report the merged SHA to
   GitHub. Configure PostgreSQL, a stable encryption key, HTTPS and hosting access separately.
6. Separate authorized search/listing/merchant/report access for checks that require those facts.

See `../docs/deployment.md` for deployment commands and policy prerequisites. Configure secrets
in the app or an ignored environment/host secret manager, never in Git-tracked files or chat.
