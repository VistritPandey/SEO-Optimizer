# Public website and domain

The hosted product's canonical URL is **https://youroptimiser.com**. Brand identity and the
public route list live in `frontend/lib/site.ts`. Customer project URLs remain project settings;
they are not rewritten to the product domain.

## Public experience

The landing page explains the product with a fictional store example, an interactive repair and
healthy-update path, the free plan, FAQs and an original practical guide. The supporting pages
cover the workflow, SEO and AI search, repository controls, contact, privacy and terms. Customer
results, reviews and rankings have not been invented. Hosted pull requests require owner review.

The cream/green identity uses the generated logo at appropriate browser, touch and header sizes,
with a branded 1200 × 630 sharing image. Fonts are self-hosted by Next's font loader; visitors do
not fetch Google Fonts at runtime. Motion supplies small transitions and honours reduced-motion
preferences. Content remains in the initial HTML. The existing silent Remotion walkthrough and
captions are preserved; video and its compressed poster mount only when the viewer opens it.

## Search and AI discovery

- Each public page has a distinct title, description, canonical URL and sharing metadata.
- `sitemap.xml` lists the eight public pages; it excludes sign-in, workspaces and APIs. It does
  not manufacture a new modification date on every request.
- `robots.txt` permits public crawling by default and excludes API/webhook paths. It does not
  add a new training opt-out or weaken authentication. Login/workspace pages have noindex metadata
  and headers; private access still requires authentication.
- Organization, WebSite and SoftwareApplication JSON-LD describe the visible product and real
  free offer. There are no fabricated ratings, business locations or FAQ rich-result promises.
- `llms.txt` is a factual index for readers and tools. It grants no private access and makes no
  ranking promise. [Google's AI search guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
  says it does not improve Google visibility.

These changes establish technical and content foundations. Indexing, rankings, AI citations,
conversion improvements and field Core Web Vitals require subsequent external observations.

## Domain and external configuration

Root `.env` has `SITE_URL=https://youroptimiser.com` for future deployments. The deployment script
sets the API's public and frontend origins while retaining the Cloud Run service URL as the
Cloud Tasks OIDC audience. Do not change that audience to an unrelated host.

The apex domain is mapped to `your-optimiser` in Cloud Run `us-central1`. Its four IPv4 records
point to Google's mapping addresses. Google manages the HTTPS certificate. Check mapping
readiness and certificate issuance before treating the custom domain as live.

The `www` mapping is also provisioned. Its DNS record must be present at the domain registrar:

| Host | Type | Value |
| --- | --- | --- |
| `www` | CNAME | `ghs.googlehosted.com.` |

Once routed, `www` returns a permanent redirect to the apex domain and preserves the path.
The Cloud Run hostname remains available for operations and delivery callbacks; public pages
identify the custom domain as canonical.

Firebase's authorised domain list includes `youroptimiser.com` and `www.youroptimiser.com`;
existing domains belonging to other applications were preserved. GitHub App homepage, redirect
and webhook settings were inspected against the new domain:

```text
Homepage: https://youroptimiser.com
Callback: https://youroptimiser.com/api/v1/github/callback
Webhook:  https://youroptimiser.com/webhooks/github
```

The dashboard begins installation through an authenticated endpoint that supplies one-use,
tenant-bound OAuth state. It supports GitHub's "Request user authorization (OAuth) during
installation" option. A separate account-connection action remains available. Plain public install
links do not bind a GitHub account to a workspace; begin from the dashboard when that association
is needed. Installation IDs in redirect query parameters are never treated as authorisation.

## Policies and support

The policies describe the implemented hosted behaviour: Firebase identity, tenant-scoped
Firestore storage, server-side credentials, third-party AI processing, GitHub access, manual
data requests and retained history. They do not claim a compliance certification, invented legal
entity, fixed deletion deadline, data residency guarantee or universal provider training policy.
The operator should review these statements as provider settings and legal obligations evolve.

No support mailbox has been invented. The current contact page sends general questions to the
existing GitHub issue tracker. Privacy/security users request a private channel using a generic
public issue and are told not to submit sensitive details until a private channel is provided.
The operator handles those requests manually. Replace this process with a verified business
support channel when available.

## Verification

Against a running production frontend or combined container:

```sh
uv run python scripts/test_public_site.py --base-url http://127.0.0.1:3002
uv run python scripts/test_public_browser.py --base-url http://127.0.0.1:3002
```

The first command checks served HTML, metadata, canonical URLs, private noindex boundaries,
structured data, crawl files, asset dimensions, internal links, redirects and response codes.
The second runs the broken and healthy examples, video controls, FAQs, 390px layout checks,
reduced motion and axe WCAG A/AA scans across the eight public pages. It needs the frontend's
development dependencies and `uv run playwright install chromium`. These checks make zero model
calls and do not create customer accounts or GitHub writes.

The frontend CI job runs both checks after a production build. The combined-container job also
runs served-page checks. Reports distinguish automated checks from manual accessibility review,
real customer sign-in and GitHub lifecycle verification. Lighthouse reports are local mobile lab
measurements; they are not field-performance or ranking evidence.
