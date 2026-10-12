# SEO Optimizer

Private search-optimization knowledge and Python evaluation tools for an autonomous service.
Phase 1 contains the decision system and offline verification suite. It does not contain a
production crawler, live model adapter, GitHub integration, deployment worker or dashboard.

## What is implemented

- A concise service-owned skill with eight focused references, 39 checks and 29 attributed
  primary/official research sources, reviewed on October 12, 2026.
- Pydantic contracts and 14 exported JSON Schemas for project context, observations,
  findings, tools, provider capabilities, evaluation inputs and reports.
- Strict local output validation, evidence/source integrity checks, policy declarations,
  and tenant/project/environment boundaries.
- A deterministic offline HTTP-evidence baseline for five checks: title absence,
  accidental exclusion, conflicting HTML canonicals, observed broken internal links,
  and inconsistent product offers. Other catalog checks are guidance, not implemented scanners.
- 41 benchmark cases in development and held-out partitions, synthetic reference
  decisions, and ten adversarial responses. Tests prohibit socket access.

The private skill lives under `src/seo_optimizer/knowledge/search-optimization/` and ships
as a package resource. It is not installed as a global assistant skill. No public application
or customer-facing instruction endpoint exists in this milestone.

## Run locally

Python 3.12 and `uv` are required. Dependency versions are locked in `uv.lock`.

```sh
uv sync --locked
uv run seo-optimizer validate
uv run pytest -q
uv run ruff check src tests
uv run mypy
```

Package validation is offline: it validates contracts, local links, coverage and attribution
relationships. It does not re-fetch sources or certify that external guidance has stayed current.

Export schemas after contract changes:

```sh
uv run seo-optimizer schemas --output schemas
```

Replay the authored examples:

```sh
uv run seo-optimizer evaluate --cases tests/fixtures/cases.json --responses tests/fixtures/reference-responses.json --split all --output reports/reference-replay.json
```

Those responses are synthetic answer examples. Their passing scores demonstrate the replay
interface, not the quality of Ollama or any paid model. Real normalized response records use
the same interface; actual model adapters have not been implemented.

Run the limited scanner and expose its coverage:

```sh
uv run seo-optimizer rules --cases tests/fixtures/cases.json --output reports/rules-responses.json
uv run seo-optimizer evaluate --cases tests/fixtures/cases.json --responses reports/rules-responses.json --split all --output reports/rules-baseline.json
```

The second command intentionally returns exit code 2 because checks without implemented
scanners remain skipped. It never silently calls them healthy. The baseline accepts one HTTP
page per request; it parses supplied fixture evidence and does not fetch destinations itself.
Offer observations supplied by a collector must represent the same selected variant and market.

Challenge the validator with deliberately bad outputs:

```sh
uv run seo-optimizer evaluate --cases tests/fixtures/cases.json --responses tests/fixtures/adversarial-responses.json --split all --output reports/adversarial-replay.json
```

This command intentionally returns exit code 1: the ten supplied outputs must be rejected;
cases without a supplied response are skipped.

Evaluation exit codes: **0** = all selected cases passed; **1** = invalid input or failed cases;
**2** = no failures but incomplete selected-case coverage. Reports preserve missing values as
JSON null, including unavailable cost and live fix measurements.

## Working with the contracts

The provider receives an `AuditRequest` containing project scope, observations and requested
checks. `BenchmarkCase.to_request()` removes answers, split metadata and author descriptions
before a model request. Do not expose reference responses or held-out expectations to the model.

`Provider` and `ToolExecutor` are interfaces; `SavedResponseProvider` is an offline replay adapter.
Tool results are normalized observations, not executable instructions. Provider capability flags
are declared metadata until verified with an actual provider. JSON Schema support is optional;
strict local parsing and cross-record validation are mandatory either way.

The structural policy validator cannot inspect an actual patch, prove a factual sentence,
authenticate a tenant, sandbox execution or attest tool output. The future runtime must perform
those independent checks before shipping. Declared effects and automatic-action flags are
requests, not authority. Real mutation and before/after verification are deliberately absent.

Read [architecture boundaries](docs/architecture.md), the [benchmark protocol](docs/benchmark.md),
and the [delivery report](reports/delivery.md) before planning the next integration stage.

## Next testing stage

Use a dedicated test repository/branch, its public deployed URL and build/test commands, a
specific model identifier and reachable Ollama endpoint, and a list of permitted changes.
Live GitHub testing additionally needs selected-repository App permissions and a webhook
secret configured outside source control. Search Console, business listings and merchant
accounts each require separate authorized access when those checks become operational.

Configure credentials through the deployment secret manager or a local ignored environment
file; do not paste credentials into chat, fixtures, reports or Git-tracked files. Temporary Git
repositories, a local fixture server and replayed webhook events will precede live writes.
