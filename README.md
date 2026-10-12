# SEO Optimizer

A Python application that observes websites and repositories, proposes grounded improvements,
verifies them, and publishes permitted changes autonomously. Run the dashboard locally or host
it on Vercel; keep the portable worker beside Ollama or use a cloud model provider.

## Start locally

Requires Python 3.12, `uv` and Git.

```sh
uv sync --locked
uv run seo-optimizer serve
```

Open http://127.0.0.1:8000, create an account and connect a website. Start the worker in a second
terminal:

```sh
uv run seo-optimizer worker
```

The default rules provider needs no model account. Ollama, OpenAI, Anthropic and Google use
native adapters with independently configured tool calling, JSON Schema and vision capabilities.
Select an actual model ID; declared capabilities still need verification against that model.
Keys are entered through authenticated project settings and encrypted at rest.

For a complete local example, run `uv run seo-optimizer demo`. It creates a real Git repository,
a queued project and a one-time account password. Start the printed fixture-site command before
running the worker. Local repositories must be inside `OPT_REPO_ROOTS`; the default is `.data`.
The demo repair changes a missing title using the page's actual H1, commits, merges and checks
its served response. Repeated audits do not create another fix commit.

Optional rendered/visual collection:

```sh
uv sync --locked --extra browser
uv run playwright install chromium
```

Enable `browser_enabled` in project configuration. Vision is optional and never establishes
indexing, ranking or field performance by itself. Enable `measure_performance` for an optional
public-URL mobile PageSpeed diagnostic; configure its key in project settings if required by quota.

## What ships

- A responsive server-rendered dashboard, account sessions, CSRF protection, encrypted project
  credentials, scoped API/worker tokens and tenant-scoped SQL persistence.
- A durable queue with leases, per-project exclusion, bounded retries, duplicate event suppression,
  incremental route auditing, periodic reconciliation and persistent finding memory.
- Bounded same-origin HTTP collection with validated/pinned addresses; optional rendered DOM,
  screenshots and official performance diagnostics. Missing evidence stays unknown.
- Native provider adapters, bounded tool execution, local output validation, token/cost accounting
  and conservative application-enforced patch checks.
- Local Git and GitHub App/token integration: isolated snapshots, one file per commit, pull
  requests, required-check gates, guarded merging, deployment-SHA confirmation and verification.
  A confirmed regression permits guarded rollback only while no newer branch change exists.
- A private skill with eight focused references, 39 checks and 30 primary/official research sources
  reviewed October 12, 2026; 21 exported JSON Schemas and offline evaluation tooling.
- Deployment configuration for Vercel and containers, CI checks, temporary Git/HTTP integration
  tests, provider-protocol tests and reproducible benchmark reports.

The 39-check catalog covers technical SEO, experience, strategy/content, AI search, local,
ecommerce, international and operations. It is a decision system: it does not imply 39 complete
deterministic scanners or direct access to external search/business accounts. Runtime reports
show which checks were assessed, need a model, need data or do not apply. The observed health
score covers assessed checks; it is not a ranking or universal AI-visibility score.

Metadata fixes are autonomous within project policy. Framework edits require isolated build
checks. Broader content publication additionally requires supported claims, owner-verified
facts and explicit publication policy. External business listings, merchant feeds, search analytics
and causal search uplift require their own authorized evidence; missing access is a dependency.

## Validate and evaluate

```sh
uv run seo-optimizer validate
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv build
uv run seo-optimizer schemas --output schemas
```

Ordinary tests block network access. Local Git/HTTP integration tests explicitly allow loopback
only. No GitHub credentials or paid model access is needed for the suite.

```sh
uv run seo-optimizer evaluate --cases tests/fixtures/cases.json --responses tests/fixtures/reference-responses.json --split all --output reports/reference-replay.json
uv run seo-optimizer rules --cases tests/fixtures/cases.json --output reports/rules-responses.json
uv run seo-optimizer evaluate --cases tests/fixtures/cases.json --responses reports/rules-responses.json --split all --output reports/rules-baseline.json
uv run seo-optimizer benchmark-live --cases tests/fixtures/cases.json --model YOUR_INSTALLED_MODEL --provider ollama --arm hybrid --limit 17 --output reports/my-model.json
```

Synthetic reference replay tests the rubric, not model quality. The limited rules replay leaves
unsupported cases skipped. Hybrid evaluation runs rules first and calls the selected model only for unsupported checks;
its protocol records how many cases actually used inference. `--arm model-only` measures the
model without rules. A live benchmark retains malformed outputs and wrong decisions as
failures. Evaluation exits: 0 all passed; 1 failed/invalid; 2 incomplete with no failures.
Unknown costs remain null; a local model's zero API cost does not imply zero electricity or
hardware cost. Held-out cases remain separate from development runs.

Read [deployment](docs/deployment.md), [architecture](docs/architecture.md),
[benchmark methodology](docs/benchmark.md) and the [verified delivery report](reports/delivery.md).
The delivery report identifies passed, failed, skipped and unverified work separately.

## Hosting and live projects

The web process handles short requests; the worker handles repositories, builds and inference.
Production requires PostgreSQL, a stable secret key and HTTPS. Vercel uses `api.index:app`;
its ephemeral filesystem is never the production queue. The local worker connects outbound
with `OPT_CONTROL_URL` and a scoped token, keeping Ollama private. See `.env.example`.

For live project testing, configure the repository/branch, deployed URL/environment, allowed
paths and route map, real build/test commands and verification image, exact model endpoint/ID,
verified facts and crawler policy. Supply repository-scoped GitHub access and a signed push
webhook secret through the app. Deployments must report the merged SHA to GitHub. Configure
hosting and provider secrets outside tracked files; do not paste secrets into reports or chat.
