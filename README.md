# Your Optimiser

<img src="frontend/public/brand/mark.png" alt="Your Optimiser" width="64" height="64" />

**SEO care that keeps up with your website.**

[Website](https://youroptimiser.com) · [How it works](https://youroptimiser.com/how-it-works) · [GitHub](https://github.com/YourOptimiser/SEO-Optimizer)

Your Optimiser checks website changes, identifies supported SEO issues, prepares focused
fixes and verifies the served result. Healthy updates do not need an edit. GitHub is the
hosted repository integration; your team reviews proposed pull requests.

## How it works

1. Connect a repository and the website it serves. Choose the branch and pages to monitor.
2. The agent inspects relevant changes and collects current page evidence.
3. Confirmed issues become findings with evidence and proposed changes. Missing facts remain
   dependencies rather than invented content.
4. Source edits must pass project permissions and configured verification.
5. After an approved change is deployed, the agent checks the live page and records the outcome.

Coverage includes technical SEO, content, AI-search discovery, local business facts, ecommerce
and international targeting. Checks distinguish directly observed defects from questions that
need external data. Search rankings, citations and traffic are not guaranteed.

[Try the interactive example](https://youroptimiser.com/#how) · [Watch the silent walkthrough](https://youroptimiser.com/demo.mp4)

## Run locally

From a checkout, with Git installed:

```sh
./run.sh
```

Windows PowerShell:

```powershell
.\run.ps1
```

The launcher installs the Python runtime and dependencies, then guides you through connecting
a local project, choosing an inference endpoint and scheduling checks. Automatic edits start
disabled. Your credentials stay in your installation; they do not belong in Git.

The open-source version can run locally with your own configuration. The hosted application
has its own account, usage limits and service terms. Future paid hosted plans will be offered
separately; they do not change the repository's software licence.

[Local setup](docs/local-setup.md) · [Single-service Cloud Run deployment](docs/single-service-deploy.md) · [Hosted configuration](docs/hosted-setup.md)

## Development

Python 3.12, uv and a Next.js frontend. Knowledge, contracts and evaluation work independently
of the dashboard.

```sh
uv sync --locked --all-extras
uv run pytest -q
uv run ruff check src tests scripts api
uv run ruff format --check src tests scripts api
uv run mypy
npm ci --prefix frontend
npm run typecheck --prefix frontend
npm test --prefix frontend
```

Offline tests need no model key or GitHub credentials. Optional Firestore integration tests
require the emulator. With Docker running, `uv run python scripts/verify_workflows.py --sandbox`
also exercises real isolated checks, temporary Git publication and served-page verification.
The [workflow report](reports/workflow-validation.json) separates scripted decision tests from
actual model quality and live search outcomes. The [real repair run](reports/repair-workflow-verification.json)
records four verified repairs, healthy controls, and earlier failed attempts.
See [architecture](docs/architecture.md), [benchmark protocol](docs/benchmark.md)
and [supported content workflows](docs/research-workspace.md) for engineering details.

## Security and privacy

Project permissions, tenant checks, validated evidence and isolated build execution constrain
agent actions. Untrusted page or repository text cannot grant permissions. Secrets belong in
ignored local configuration or the deployment's secret store. Never commit environment files,
private keys, credentials or personal-site test data.

To request a private reporting channel, use [the contact page](https://youroptimiser.com/contact)
without posting sensitive details publicly. The hosted [privacy notice](https://youroptimiser.com/privacy)
and [terms](https://youroptimiser.com/terms) describe service data handling and limits.
