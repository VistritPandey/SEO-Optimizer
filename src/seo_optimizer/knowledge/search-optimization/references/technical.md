# Technical SEO decisions

Use when routes, metadata, responses, templates, content delivery or deployment configuration change. Checks: tech.indexability through tech.migration. Provenance: google-essentials, google-starter, google-js, google-canonical in the [registry](../sources.json).

## Establish intent and the actual response

Map source changes to URLs and environments. An HTTP 200 is not enough to establish indexability, and a crawler simulation cannot confirm a URL is in an engine's index. Record response status, redirect chain, relevant headers, robots rules, initial HTML and rendered DOM separately. Use Search Console observations for Google-selected canonicals/indexing when available.

A robots.txt Disallow restricts crawling, rather than serving as a reliable removal-from-index instruction. A crawler blocked by robots may not see a page's noindex instruction. Diagnose the combination; do not simply remove every block. X-Robots-Tag and HTML robots directives must agree with explicitly public/private intent. Preserve authenticated routes, internal tools and previews. The environment default is not sufficient authority to expose a private URL.

## Metadata and canonical decisions

An absent title on a successfully served public page is actionable when page purpose and visible facts are known. Write a descriptive title, not a keyword list. An adequate title is a no-op even if it exceeds a favorite character count. Meta descriptions influence presentation but engines may generate a different snippet; absence alone is not a proven ranking loss.

Check canonical declarations in raw HTML, rendered HTML and response Link headers. Contradictory declarations warrant investigation; a canonical is a signal rather than a command. Verify page equivalence and the preferred URL before editing. Do not canonicalize distinct products, languages or service pages to a single generic page. Canonical absence is not automatically a defect; Google can choose canonicals without it.

## Links, statuses and rendering

Require observed destination responses before marking a link broken. Redirects and fragment navigation can be valid; external destinations and temporary network failures need different treatment. A navigation control without a real discoverable href deserves a DOM and interaction inspection. Preserve accessible navigation and user behavior when changing it.

404/410 removals, 401 authentication and genuine redirects are not inherently SEO failures. Detect redirect loops, irrelevant destinations and successful responses serving error content against the intended route map. A blanket redirect of missing URLs to the homepage can create soft errors and lose user intent.

Compare initial response to rendered content and resource failures. A browser able to render content does not prove all crawlers can. Preserve server-rendered content when useful and repair the verified cause rather than rewriting a framework. Do not introduce separate deceptive content for bots.

## Sitemaps and migrations

A sitemap helps discovery but is not an indexing guarantee or mandatory for every small site. Entries should represent public preferred URLs with meaningful modification dates. Never set lastmod to now on every run without actual changes.

For migrations, establish old/new equivalents before changing redirects, links, canonicals and sitemaps. Keep intentional removals distinct from moved pages. Validate a representative before/after route inventory and defer index/traffic conclusions to subsequent engine observations. Shared templates and backend response changes can affect many URLs.

Verification: fetch actual responses, inspect DOM, exercise routes, compare intended visibility and retain relevant tests. Browser inspection is a simulation, labeled accordingly.
