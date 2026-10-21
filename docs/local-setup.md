# Run your autonomous SEO agent locally

Your Optimiser monitors relevant website changes, investigates supported SEO issues, prepares permitted source repairs and verifies the result. Local action policy controls which repairs can be published automatically.

Clone/download the application, install Git, then run `./run.sh` (macOS/Linux/WSL) or
`.\run.ps1` (Windows PowerShell). Use a terminal that accepts interactive input.
The launcher bootstraps uv/Python 3.12 and uses the locked, application-only environment.
The local Python dashboard needs no Node.js or cloud account.

## First run

1. Choose a private data folder. The default is a separate folder for this application checkout.
2. Choose your website's Git repository, with at least one commit and a checked-out branch.
3. Supply its deployed URL, or run its development server and supply that localhost URL.
4. Choose rules, a model already installed in Ollama, or a paid provider and model ID.
5. Set your dashboard email and password (12 characters minimum).
6. Choose the website directories to monitor. The defaults cover common static/Next layouts;
   unrelated backend directories can be excluded. Shared rendering dependencies stay explicit.
7. Decide whether verified metadata repairs are permitted. Changes start off; local publication
   requires the separate `auto_merge` policy. Content publication has further evidence gates.
8. Use foreground scheduling, or install a cron wake-up on a system with `crontab`.

The dashboard opens at `http://127.0.0.1:8787`. The worker runs beside it, claims the initial audit
and reconciles hourly. Leave the website server running for live-page evidence.
Use `./run.sh --port 8790` if the default port is occupied. The setting applies to that invocation.

## Local models and paid keys

Install/run Ollama separately, pull a model and leave it running. Setup lists installed models;
it does not download a large model without your selection. Use `--endpoint` for a different
Ollama endpoint. Tool calling, schema output and vision remain separate capabilities in project
policy; a model that lacks a needed capability produces a dependency rather than a fabricated result.

Paid keys use a private prompt, or `--key-env YOUR_VARIABLE`. They are encrypted in the database,
not written in the launcher configuration. Provider costs and local hardware/energy costs remain
unknown unless available usage/rates are configured. See the recorded model comparison rather
than assuming every local model performs equally well.

## Background scheduling

`./run.sh --no-start --schedule cron` installs one namespaced entry every five minutes. It quotes
paths (including spaces and cron's `%` character) and preserves other entries. Each invocation runs
one worker tick; project reconciliation timing and durable leases prevent repeated/overlapping
model audits. Foreground and scheduled workers can coexist. Cron does not host the dashboard.

Remove only that installation's line with `crontab -e` (look for `your-optimiser:<id>`).
On Windows, use Task Scheduler: run PowerShell with `-NoProfile -File` followed by the absolute
`run.ps1` path and `--once`, every five minutes, under your user account. The foreground launcher
also works without an OS scheduler. Native Windows execution and Task Scheduler are not yet
validated in this macOS test environment; the launcher and scheduler instructions are provided.

## Verification and actual publication

Read-only audits work without Docker. Framework/code or content repairs need explicit
`check_commands` and a verification image with dependencies preinstalled. Commands run without
network access in a container with a read-only source mount, dropped capabilities and no host
credentials. Build output belongs in `/tmp`; copy source there inside the check when a build
requires writable files. Never grant the model arbitrary host execution.

For a first project, inspect findings before enabling `auto_fix`. Configure route mappings for
dynamic pages; the worker infers static HTML and basic Next App/Pages routes, skips API endpoints
and leaves unresolved dynamic parameters for the owner. Configure private page intent and
crawler preferences before allowing changes. Existing training opt-outs are preserved.

A local verified change becomes one file per commit and a guarded fast-forward only when
`auto_merge` is enabled and the target checkout is clean, on the expected branch/revision.
Otherwise the result records verified proposals. A GitHub-connected project publishes a PR;
checks, merge permission and served-page verification remain separate stages.

## Troubleshooting and unattended setup

- Missing Git / empty repository: install Git and make the first commit before setup.
- Ollama unavailable / model missing: start Ollama, run `ollama list`, then retry.
- Port in use: use `--port`, or stop the other launcher.
- Site unavailable: start the site's server or supply its deployed URL. A successful launcher
  does not establish that the website can be crawled.
- Missing Docker / build image: install the executor and prepare the image. Publication stays
  blocked until configured checks pass.
- Reinstall: preserve `.your-optimiser.json`, the data directory, database and `secret.key`.
  Removing the configuration starts a new setup; it does not erase your old database.

For automated installation, provide `--no-start --repo PATH --url URL --provider rules
--password-env VARIABLE --data-dir PATH`. The variable contains the password; do not place it
in command arguments. A second `--no-start` launch resumes the saved configuration without
creating another account/project. `scripts/test_clean_install.py` exercises a clean clone with
space-containing paths and an environment without developer dependencies.
