# Website connectors

Your Optimiser can collect evidence from 22 additional connection types alongside its existing GitHub integration. Open a project and select **Connectors**. Accounts, credentials, policies, evidence and proposals belong to that project and tenant.

The adapters are implemented and exercised with controlled provider responses. A local CMS test exercises the actual HTTP, API, database, worker, publication, live-page verification and restoration path. **Live provider accounts remain unverified until their owners grant access.** A green offline test is not a certification by any platform.

## Coverage

| Connection | Implemented scope | Publication boundary |
| --- | --- | --- |
| Google Search Console | Finalized query/page/country/device/day observations, sitemap status, indexed-URL inspection; URL-prefix and domain properties | Read-only. Average position is aggregated, coverage is bounded, and inspection is not a live test or indexing request. |
| WordPress | Pages or posts, observed titles/content, explicitly registered REST SEO meta fields | Small updates preserve status. Yoast/Rank Math fields need a site-specific writable REST mapping or bridge; no blanket plugin compatibility claim. |
| WooCommerce | Product names, descriptions and short descriptions | No prices, stock, reviews, variations or publication-status changes. |
| Shopify | Product SEO metadata through GraphQL Admin API 2026-10 | No theme edits or automatic theme publication. |
| Webflow | Static-page metadata and explicitly mapped CMS fields | Saves staged changes. Whole-site publication stays in Webflow. |
| GA4 | Organic landing-page sessions, engaged sessions, key events and revenue | Read-only; configured tracking and attribution limit interpretation. |
| Vercel | Deployment reads and native HMAC-SHA1 signed successful production events | A build is not proof that the canonical page is repaired. |
| Netlify | Deployment reads and native HS256 JWS body-digest verification | Successful production deployments trigger project verification. |
| Other hosting / CI | Timestamped HMAC-SHA256 deployment events | Origin, environment, replay, order, freshness and monitored-path checks apply. |
| GitLab.com | Bounded source discovery, file reads, separate branches, commits and merge requests | Initial automatic source repair targets missing HTML titles. Supported manual patches are HTML metadata or JSON metadata. Framework-code CI integration is not claimed. Never auto-merges. |
| Bitbucket Cloud | File reads, branch/parent-pinned multipart commits and pull requests | Same source restrictions as GitLab. Existing PR follow-ups, CI completion and merges stay in Bitbucket. |
| Bing Webmaster Tools | Query statistics and crawl statistics | Read-only. Bing AI citation-report API ingestion is not included without an accessible documented interface. |
| Google Business Profile | Business information reads and regular-hours updates | Changes require matching, unexpired trusted project facts. Google API approval and location permission are required. |
| Cloudflare | Bounded adaptive request groups, paths and response statuses | Data may be sampled or plan-restricted. No crawler identity, training preference or citation is inferred. |
| Server logs | Structured request-record imports | No IPs, cookies, arbitrary fields or query strings. User agents are not verified identities. |
| Wix | Site SEO tags and the existing live-site audit | Read-only in this release. General page edits need validation against the applicable Wix page/app API. Export observations for manual work. |
| Squarespace | Commerce product reads and SEO updates | General pages and blogs use live-site audits and exported observations; no general page-edit API is assumed. |
| Framer | Official `framer-api` 5.1.0 Server API bridge, CMS reads and mapped string-field updates | Does not publish or promote a production deployment. CMS slugs are not treated as evidence of a visible page title. |
| Sanity | Bounded document reads, mapped draft-field updates with revision preconditions | Existing drafts only. Does not create or publish documents. |
| Contentful | Bounded entry reads, localized field mappings and version-checked updates | Saves an unpublished revision; preserves unrelated fields and locales. |
| Keyword & competitor rankings | One bounded DataForSEO organic SERP task for an explicit keyword/location/language | Paid collection is explicit. Records observed positions and returned costs, not inferred competitor rankings. |
| AI answer visibility | Search-enabled API experiments for Google, OpenAI, Anthropic and Perplexity; consumer-observation imports | Explicit model and query required. Citation URLs come from annotations. API experiments, imported consumer observations and crawler visits remain separate. No universal GEO rank. |

The machine-readable definitions and primary-source links are in `src/seo_optimizer/connectors/catalog.py`. The exported contracts are in `schemas/`. Provider schema/plan changes and actual authorization still need live validation.

## First connection

1. Create a project with its canonical deployed URL and platform. A CMS project does not require GitHub access. The first website audit is read-only unless a supported publishing connection is configured.
2. Open **Connectors**, choose the platform, and enter its account/resource identifier.
3. Save scoped credentials or use **Authorize account** when the service operator has registered that platform's OAuth app. Secrets are encrypted with the existing application encryption key and never returned to the dashboard.
4. Collect evidence. Observe job progress under **AI audits & logs** and expand collected records for provenance and coverage limitations.
5. Review supported proposals. Allowing writes and enabling automatic application are separate settings; the project must also allow repairs. Changing account/resource mappings invalidates old proposals.
6. Apply a proposal, inspect provider readback, publish staged changes through the platform's normal workflow when needed, and verify the exact canonical page. A successful API response does not prove indexing, rankings or growth.

Automatic title proposals reuse an observed title or HTML H1. They do not invent descriptions, reviews or commercial claims. Preview/private pages and configured non-indexable routes are excluded from automatic proposals. SEO mappings cannot target crawler directives, publication state, inventory, pricing or review fields.

Repository checks enforce configured source paths and metadata-only changes. Their new-host adapter checks source locally and opens a PR; **build/CI and live deployment remain separate verification steps**. The existing GitHub worker retains its fuller build and PR lifecycle.

## Credentials for production testing

Customer credentials belong in the project's Connectors form, not the frontend environment or repository.

| Platform | Owner-provided access |
| --- | --- |
| Search Console / GA4 | Google OAuth authorization for the chosen verified property; read-only scopes |
| Business Profile | Approved Google Business Profile API project and permission for `locations/ID` |
| WordPress | Website URL, dedicated username and an application password; REST exposure for mapped plugin meta fields |
| WooCommerce | Dedicated consumer key/secret with the required product permissions |
| Shopify | Permanent `myshopify.com` shop domain; merchant OAuth authorization or scoped Admin API token |
| Webflow | Site ID, OAuth grant/token, optional collection and locale IDs, explicit CMS field mappings |
| GitLab / Bitbucket | Repository identifier and a scoped token/OAuth grant; webhook secret for push events |
| Vercel / Netlify | Project/site ID, read token and webhook signing secret |
| Bing | Verified website and Webmaster API key |
| Cloudflare | Zone ID and a read token for the available analytics dataset |
| Wix / Squarespace | Site identifier/URL and scoped platform access token |
| Framer | Project ID, project-bound Server API key, collection ID and CMS field IDs |
| Sanity | Project, dataset, document type, mapped SEO fields and scoped token |
| Contentful | Space, environment, locale, mapped field IDs and management token |
| DataForSEO | API username/password and location/language settings |
| AI experiments | Chosen API engine's key and explicit supported model; results do not measure its consumer app |

For hosted OAuth, register these optional **operator** environment variables in pairs:

- `OPT_CONNECTOR_GOOGLE_CLIENT_ID` and `OPT_CONNECTOR_GOOGLE_CLIENT_SECRET`
- `OPT_CONNECTOR_SHOPIFY_CLIENT_ID` and `OPT_CONNECTOR_SHOPIFY_CLIENT_SECRET`
- `OPT_CONNECTOR_WEBFLOW_CLIENT_ID` and `OPT_CONNECTOR_WEBFLOW_CLIENT_SECRET`
- `OPT_CONNECTOR_GITLAB_CLIENT_ID` and `OPT_CONNECTOR_GITLAB_CLIENT_SECRET`
- `OPT_CONNECTOR_BITBUCKET_CLIENT_ID` and `OPT_CONNECTOR_BITBUCKET_CLIENT_SECRET`

Register the callback as `https://youroptimiser.com/api/v1/connectors/oauth/callback` for this deployment, or the local control-plane public URL plus that path. Configure each provider's allowed scopes/app distribution as required. These are backend settings. `deploy.sh` places supplied optional client secrets in Secret Manager, never Docker build arguments or frontend configuration. They are not required for offline tests or manually scoped tokens.

OAuth state is project-bound, single use, generation-checked and expires after ten minutes. Google and GitLab use PKCE. Shopify additionally checks its callback HMAC, timestamp and shop. Google, GitLab, Bitbucket and Shopify support refresh-token recovery on collection; an uncertain external write is never blindly repeated. Webflow grants without a supported refresh flow require reauthorization when rejected.

## Monitoring and deployment events

Connection clocks are indexed separately from encrypted credentials. Periodic reconciliation queues due collections independently of the full website-audit interval. A busy lease or paused project prevents overlapping work. Paid SERP/API experiments and evidence imports do not run periodically. Missing credentials or runtime dependencies pause automatic retries until the connection is repaired.

A webhook URL is project/tenant scoped: `/webhooks/connectors/{tenant_id}/{project_id}/{platform}`. Obtain the exact URL from the authorized connection record. Set a long random signing secret on the connection and the sending platform. Secrets never belong in the webhook URL.

Vercel and Netlify accept their documented native signatures. GitLab accepts its configured secret-token header; Bitbucket accepts the HMAC-SHA256 header. Push events must match the configured repository and target branch. Irrelevant monitored-path changes are skipped when the event contains usable file changes. A bounded scan is used when changed paths are unavailable.

Generic CI events use this body contract:

```json
{
  "event_id": "deployment-unique-id",
  "resource": "configured-project-identifier",
  "environment": "production",
  "revision": "deployed-commit-or-revision",
  "url": "https://example.com/",
  "occurred_at": "2026-10-23T12:00:00Z",
  "status": "succeeded",
  "changed_paths": ["web/index.html"]
}
```

Compute `hex(HMAC-SHA256(secret, timestamp + "." + exact_request_body))`, send `X-Optimiser-Timestamp` as Unix seconds and `X-Optimiser-Signature: sha256=<digest>`. Timestamp tolerance is five minutes; event observation tolerance is one hour. Body bytes must match exactly. Old observations and previews do not trigger publication verification. The canonical production origin is required. Event IDs and queued-job dedupe prevent repeat work; out-of-order deployments are ignored.

The app queues live verification for eligible publishing proposals when a deployment event arrives. A proposal needs an exact same-origin page URL and supported live criteria. Missing page mappings remain a dependency. A failed live check does not silently restore an entire site's publication or revert somebody else's concurrent changes; provider restoration is a separate guarded action.

## API and portable worker

All management routes require the existing project-owner authentication and CSRF rules:

- `GET /api/v1/projects/{id}/connectors`
- `PUT` or `DELETE /api/v1/projects/{id}/connectors/{platform}`
- `POST .../{platform}/collect` queues a durable job
- `POST .../{platform}/proposals` validates evidence, facts and fields and saves a preview
- `POST .../{platform}/proposals/{proposal_id}/apply`, `/verify`, `/rollback`
- `POST .../{platform}/import` for structured logs or consumer observations
- `POST .../{platform}/oauth` starts authorization

Set `verification_url` on a proposal when the provider does not return its public page URL. It must resolve within the project origin. Unknown evidence, stale facts, unsupported fields, concurrent revisions and private paths stop changes. A timeout after a write records `write_uncertain`; inspect the provider and collect new evidence instead of replaying the write.

Scoped portable workers can exchange connector state through worker-only endpoints. Those endpoints are excluded from the frontend proxy. Existing hosted worker identity restrictions still apply.

For a local Framer worker, run `npm ci --prefix integrations/framer --ignore-scripts` and use Node 22 or later. If installed from a wheel or run outside the repository, set `OPT_FRAMER_BRIDGE` to the bundled bridge's absolute path. The combined image includes it automatically. Credentials reach the bridge through stdin, never command-line arguments.

## Reproducible validation

```sh
uv run pytest tests/test_connector_adapters.py tests/test_connector_service.py tests/test_connector_e2e.py
uv run python scripts/test_workspace_browser.py
node --test integrations/framer/bridge.test.mjs
uv run mypy
uv run ruff check src tests scripts api deploy/combined-entrypoint.py
```

The HTTP CMS fixture is local and fictional. Provider wire tests use `httpx.MockTransport`; Framer tests use a controlled SDK object. No production repository, business listing, paid model, SERP budget or customer CMS is modified by these tests.

For the default and named Firestore databases, start the documented Firebase emulators with project `demo-your-optimiser`, then run:

```sh
FIRESTORE_EMULATOR_HOST=127.0.0.1:8089 \
FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 \
uv run pytest tests/test_firestore_integration.py --allow-hosts=127.0.0.1
```

The release report separates local passes, skipped Docker checks, live-account verification and actual search/AI outcomes. Real account authorization, platform plan restrictions, end-to-end native delivery, live model quality, commercial impact and search visibility require a separate production pilot.
