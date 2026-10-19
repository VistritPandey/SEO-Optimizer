# Deploy the whole app to one Cloud Run service

The root `deploy.sh` builds the Next.js frontend and Python API into one container, with one
public URL. An internal reverse proxy routes pages, API calls, GitHub callbacks and webhooks.
Cloud Tasks sends authenticated requests back to this service to execute one worker step at a
time. Work stays inside the request lifetime; no always-running worker or five-minute empty
Cloud Run Job is needed. An hourly Scheduler request reconciles periodic audits and recovers
persisted work after dispatch failures. Waiting jobs schedule another task after 30 seconds.

Firestore and Firebase Auth remain managed services. Customer source checks run through the
separate Cloud Build verification identity, without application database or secret access.
The application and its dependencies share one project; this is one Cloud Run service, not
one component with an embedded database.

## First deployment

Install `uv`, the Google Cloud CLI and Firebase CLI. Sign in with `gcloud auth login` and
`firebase login`. Use an explicit billing-enabled Google Cloud project that you control.
In that same project's Firebase console, register a web app and enable email/password and/or
Google sign-in. Create a GitHub App with the permissions/events described in
[the hosted setup guide](hosted-setup.md#provisioning).

```sh
cp deploy/single-service.env.example .env.deploy
# Fill PROJECT_ID, OPT_FIRESTORE_DATABASE, Firebase web config, and GitHub App config.
./deploy.sh --dry-run
./deploy.sh
```

`.env.deploy` is ignored by Git and cloud/container upload rules. The script also reads the
existing root `.env` and `frontend/.env.local` as fallbacks. `.env.deploy` overrides those files;
exported shell variables take precedence. Values are parsed as dotenv data, never executed as
shell code, and variable interpolation is disabled. `--config /path/to/config` selects another
configuration file. `--dry-run` validates the configuration and prints a plan without cloud calls
or resource changes; `uv` can install locked local dependencies on first use.

The script requires the intended project explicitly; it does not choose the current gcloud
project. The Firebase project ID must match it. It creates the necessary APIs, service accounts,
Artifact Registry, database if absent, Firestore rules/indexes, source-check bucket, task queue,
secrets, Cloud Run service and hourly Scheduler wake-up. The first image build includes Chromium
and its Linux libraries, so allow several minutes. Cloud Build handles the target platform;
Docker does not need to run on your laptop.

Set `OPT_FIRESTORE_DATABASE` to the exact **database ID** you created in Firestore, for example
`your-optimiser`. This is a backend setting, not a Firebase Realtime Database URL; it does not
belong in `frontend/.env.local`. The frontend uses Firebase for authentication and calls the
backend for application data. Deployment requires an explicit ID, prints it in `--dry-run`,
reuses that database if present, and creates it in `REGION` only if absent. Existing database
locations are preserved. It never falls back to `(default)` when configuration is missing.

The deployment generates a temporary Firebase configuration containing only that database,
so application reads/writes, rules and indexes all target the same ID. The repository's
`firebase.json` is for local emulators; the deploy script does not use it for production.
Other databases' rules and indexes are not deployed. Named database selection follows the
[Firestore database guide](https://firebase.google.com/docs/firestore/manage-databases) and
[Firebase CLI configuration](https://firebase.google.com/docs/cli#configuration_for_multiple_cloud_firestore_databases).
Changing the ID selects a different data store; existing records are not migrated automatically.

The deploying account needs permission to enable services, configure IAM, create these resources,
use the deployment/build identities and deploy Firebase rules. Authentication, billing or IAM
failures stop with the relevant command's error. The script does not activate billing or create
an unrelated cloud project. Index creation can take time; wait for indexes to become ready before
exercising project jobs. No actual cloud deployment was performed while testing this script.

## Secrets and the final URLs

Provide the initial managed model key, GitHub OAuth secret and GitHub App PEM private key through
the ignored configuration/environment or pre-create their named Secret Manager resources.
`GOOGLE_API_KEY` in the existing root `.env` supplies the default managed Google key.
`GITHUB_PRIVATE_KEY_FILE` can point to a local PEM outside the repository. The session/encryption
key and GitHub webhook secret are generated securely if absent for a new secret.

Secret values are sent on standard input to Secret Manager. They are not build arguments,
container files, printed commands or configuration reports. The service receives Secret Manager
references. Existing secrets are reused, never overwritten on redeploy. Keep the encryption key
and data backed up together; changing that key prevents reading existing encrypted credentials.
Rotate existing credentials explicitly in Secret Manager, then redeploy.

On first deployment the script uses Cloud Run's deterministic service/project-number/region URL;
on redeploy it uses the service's existing URL. `SITE_URL` optionally sets an already-routed HTTPS
custom domain. The final output includes the website, GitHub OAuth callback and webhook URLs.
Update the GitHub App configuration with those URLs and the generated webhook secret (retrieve
it from Secret Manager). Add the website hostname to Firebase Auth's authorized domains.
The script cannot configure an external GitHub App or its installation for you.

The script checks the live homepage and API health before reporting success. That smoke check
is not a full sign-in or real agent repair test. Before inviting users, verify sign-in, repository
selection, a relevant merge, the agent's PR, review/merge, deployment detection and served-page
verification using your own test project. Existing hosted projects require owner review/merge.
Disconnect/revocation, job failures and task retries also need a live qualification run.

## Cost and runtime defaults

The default service has one CPU, 2 GiB memory, zero minimum instances, one maximum instance,
eight concurrent HTTP requests and a 1,250-second timeout. The task queue permits one delivery
at a time with a 1,200-second deadline; the worker retains its project leases and bounded work.
Queue retries are bounded, and a failed follow-up dispatch returns an error so delivery can retry.
The API preserves successfully queued work if the initial dispatch fails; hourly reconciliation
recovers it. Tasks contain no repository credentials or customer-controlled commands.

At low traffic the service can scale to zero. Cold starts are expected. Model calls, Cloud Build,
storage, logging and network usage still contribute to billing. Budgets alert; they do not impose
a hard spending cap. Keep the existing project/job quotas and verification budgets. A single
instance shares resources between browsing and agent work; this is an initial beta tradeoff.
If needed, `CPU=2`, `MEMORY=4Gi` and `MAX_INSTANCES=2` or `3` are supported configuration choices.
The Cloud Tasks queue still serializes worker deliveries.

Deployment updates the configured service, secrets references, queue policy, Scheduler job and
repository-owned Firestore rules/indexes in the selected database. Use a dedicated application
database: do not select a database whose existing rules must be preserved. The application
identity's Datastore IAM role is project-wide; a named database selects storage and is not an
IAM security boundary. Prefer a dedicated project when other applications require isolation.
The script does not provision a
load balancer, VPC connector, GPU or paid subscription system.

## Local verification

`tests/test_deploy_gcp.py` exercises first deploy/redeploy planning through fake cloud commands,
secret preservation, explicit project selection, shell injection resistance, public-only build
arguments and fail-fast resource inspection. `tests/test_task_dispatch.py` checks OIDC identity
boundaries, queued execution, follow-up dispatch and persistence after a dispatch failure.
The combined container is also built and smoke-tested locally before delivery. Live IAM,
Firebase/GitHub authorization and Cloud Tasks delivery require the selected real project.
