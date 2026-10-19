# Public website release — 19 October 2026

The redesigned Your Optimiser website is deployed to the existing combined Cloud Run service.
Revision **your-optimiser-00004-x2x** is ready and receives 100% of traffic. The application image is
`site-f88b4c0`; the cloud build completed successfully. Runtime secrets, named Firestore database,
Cloud Tasks identity and the health-gated ingress were preserved.

## Available now

- Operational URL: https://your-optimiser-m4yk3u7p3a-uc.a.run.app
- Canonical product URL: https://youroptimiser.com
- Eight public pages: home, workflow, SEO/AI search, continuous SEO guide, security, contact,
  privacy and terms.
- Customer-focused content, an interactive fictional repair and healthy-update example,
  consistent logos/icons, sharing previews, self-hosted fonts and restrained Motion animations.
- The existing Remotion walkthrough remains silent and captioned. Its player and compressed
  poster load only when requested.
- Distinct page metadata, canonical links, sitemap, robots directives, factual JSON-LD and a
  public `llms.txt` index. Private workspaces remain authenticated and noindex.
- GitHub installation now starts through authenticated, one-use, tenant-bound OAuth state.
  This supports the App's existing authorisation-during-installation setting.

## Verification

| Check | Observed result | Evidence |
| --- | --- | --- |
| Python suite | 270 passed, 10 skipped; one dependency deprecation warning | `uv run --no-sync pytest -q` |
| Static checks | Ruff passes; mypy passes for 37 source files | Local checks |
| Frontend checks | TypeScript passes; 2 proxy-policy tests pass; production build succeeds | Local checks and successful Cloud Build |
| Dependency audit | No known npm vulnerabilities reported | `npm audit` after lockfile update |
| Public HTML, local | 9 check groups pass, including www redirect | [Local report](public-site-qa.json) |
| Public HTML, deployed | 8 check groups pass; public www redirect deferred to DNS/TLS readiness | [Live report](public-site-live.json) |
| Browser, deployed | 6 workflow/responsive groups pass; no browser errors or axe A/AA violations across eight pages | [Browser report](public-browser-qa.json) |
| Combined container | 7 check groups pass, including public pages, non-root runtime, Chromium and process recovery | [Container report](combined-container.json) |
| Mobile Lighthouse, local production frontend | Performance 96; accessibility 100; best practices 100; SEO 100 | [Interactive report](public-site-lighthouse.report.html) |
| Lighthouse measurements | LCP 2.8 s; CLS 0; total blocking time 0 ms | [Raw report](public-site-lighthouse.report.json) |
| Live health and protection | Health 200; unauthenticated project/install/proxy requests 401; video/poster HEAD 200 | Direct HTTP checks after deployment |

The 10 skipped Python tests require the local Firestore emulator. They are not counted as passes.
The container report predates the final installation-state fix; the fix was covered by the final
Python/proxy suites and deployed endpoint checks. CI was extended with public-site/browser checks;
this release does not claim a new remote GitHub Actions result. These QA checks used no model calls,
customer accounts or GitHub writes.

Screenshots from the deployed public site: [desktop](public-site/desktop.png),
[mobile](public-site/mobile.png), [workflow](public-site/how-it-works.png),
[privacy](public-site/privacy.png).

## Domain status and remaining external work

At verification, the apex domain's A and AAAA records point to Google's mapping addresses and
Cloud Run reports the domain as routable. **Google's managed certificate is still pending**;
HTTPS requests to the custom domain do not yet succeed. The operational Cloud Run URL works.

The `www` mapping is provisioned but its public DNS record is still absent. Add this record at
the registrar:

| Host | Type | Value |
| --- | --- | --- |
| `www` | CNAME | `ghs.googlehosted.com.` |

The application's www-to-apex permanent redirect passes locally. Its public DNS/TLS path must
be checked once the alias resolves and both certificates are ready. Firebase authorises both
domains; the GitHub App's homepage, callback and webhook URLs already use the apex domain.
No private key or root environment file was included in the build source.

## Explicitly unverified

This release establishes and tests website foundations. Search indexing, ranking gains, AI
citations, conversions and field Core Web Vitals have not been demonstrated. Lighthouse is a
local lab measurement. `llms.txt` is an informational index, not evidence of visibility gains.
The fictional interactive example illustrates the workflow; it is not a fresh live AI run.

Real Firebase sign-in, a customer GitHub installation, repository PR/deployment, assistive-technology
review and legal approval of the drafted policies remain outside these public-site checks.
Privacy/security requests currently use the documented manual private-channel request process.
