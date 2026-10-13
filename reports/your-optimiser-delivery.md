# Your Optimiser delivery

The first-run launcher and hosted application are implemented around the Python SEO worker.
Run `./run.sh` locally, or `.\run.ps1` on Windows. Setup asks for the private data folder,
website repository/URL, model, account and schedule. Rules is the dependency-free model default;
Ollama and personal paid keys remain available. Automatic edits begin off, with local publication
and supported content controlled separately by project policy.

The hosted product includes the Next.js landing/free-pricing pages, Firebase identity, Firestore
adapter, guided GitHub App connection, dashboard findings/evidence, research/content actions,
free limits, durable PR indexing/review reservations, reconnect/revocation handling, Cloud Run
provisioning and isolated Cloud Build verification. Server-owned provider/model configuration can
change without a customer-facing provider choice or per-project key rewrite. Central credentials
are not copied into project records or returned to customer worker endpoints.

| Validation | Result |
|---|---|
| Offline Python suite | **228 passed**, 5 emulator cases skipped |
| Actual Firebase/Firestore emulators | **5 passed**, including concurrent claims and recreated-UID isolation |
| Frontend proxy boundary tests | **2 passed** |
| Ruff / format / strict mypy / wheel | Passed; 36 Python source files checked |
| Next formatting / types / production build | Passed on Node 24.12 |
| Private knowledge / schemas | 39 checks, 31 sources; 29 schema contracts |
| Fresh clone launcher | Passed on macOS, without developer dependencies, including paths with spaces and shutdown |
| Browser flows | 7 passed through actual Next, Firebase Auth and Firestore; rules worker, zero model/GitHub requests |
| Fresh actual model repair | **4 defects → 0**, 2 files, 14 tool calls, 8 successful-run model requests |
| Repeat / docs merge | Zero extra inference; periodic cache preservation also tested |
| New video | 72 seconds, 1080p H.264; actual browser capture and recorded model transcript replay |

No final test failures remain. An earlier repair attempt was blocked before publication when its
source-read reference was missing. The interface now binds only actual current source evidence;
missing, stale or cross-tenant reads are rejected both at staging and final validation. SQLite and
Firestore project leases prevent competing workers from publishing overlapping jobs. PR-branch
reports remain separate from verified production observations.

The emulator cases were skipped by the network-disabled default suite and then executed
separately; they are passed, rather than untested. A Starlette TestClient deprecation warning
remains in the Python suite. This warning did not fail validation.

Live production Cloud Run/Firebase IAM/domain configuration, actual GitHub App/PR/CI/deployment,
and live Cloud Build execution are **unverified**. Native Windows/Linux launcher execution and
actual OS cron installation are also unverified. Cron quoting, idempotency and preservation were
tested without modifying the host's crontab. Public account data-retention/deletion policy and
paid subscription/billing remain future launch decisions; paid billing is not activated.

The repair establishes local code and served-page outcomes, not ranking, conversion or consumer
AI-citation gains. HTTP-only commerce comparison retains an unresolved assessment while the
independent sandbox checks fixture price/product facts. Paid price rates were not configured, so
API dollars and total infrastructure cost remain unknown. The initial blocked attempt made six
requests in addition to the eight-request successful run. The earlier frozen five-arm benchmark
is retained as historical evidence; this update does not claim a new open-model quality result.

The exact next integration inputs are recorded in [the machine-readable report](your-optimiser-delivery.json):
an explicit Cloud/Firebase project and frontend domain, Secret Manager resources, the GitHub App
configuration and selected test repository, its default branch/monitored routes/required checks,
a dependency-equipped verification image and its deployed test URL/environment. Local users
instead supply their own repository/website and optional Ollama endpoint/model or paid key.

[Local setup](../docs/local-setup.md) · [Hosted setup](../docs/hosted-setup.md) ·
[Video and provenance](../docs/your-optimiser-video.md) · [README](../README.md)
