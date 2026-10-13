# Research, strategy and supported publication

Each project owns a versioned workspace containing source material, dated query/page
measurements, and engine-specific citation observations. Open **Research workspace** from the
project overview. Its expandable brief shows the source, factual support, dependencies and
success metric before a content job is queued. Customer pages never expose private skill text.

The `/api/v1/projects/{id}/workspace` GET/PUT interface imports or exports the same Pydantic
contract. Records are stored per tenant and project. Unknown fact references, duplicate IDs,
overlapped query/page/market/device windows, future observations and impossible click counts
are rejected. PUT replaces the complete workspace; export first when merging another dataset.

## What the strategy loop does

`GET /api/v1/projects/{id}/strategy` returns an evidence-backed backlog. The ordering uses
observed impressions, owner-confirmed relevance, and supported readiness. It is an explained
queue heuristic, not a prediction of ranking, traffic, difficulty or revenue. Irrelevant and
zero-impression queries do not trigger publication. Without search observations, demand stays
unknown and the report records the missing input.

A ready brief requires a business goal, a mapped public route, reviewed original owner material,
and current trusted facts supporting each complete passage. Competitor or primary-source
material can be stored for research but cannot masquerade as original business evidence. The
current publisher copies supported original passages into an existing static HTML main. It
preserves existing copy; it does not create an unrestricted article or change application code.

Enable `auto_fix`, `allow_content_publication`, `auto_content_refresh`, and configure isolated
`check_commands` to run the loop autonomously. A completed audit queues strategy; strategy queues
one supported refresh. The worker rechecks the latest brief before changing source, checks the
staged page, publishes through the existing Git policy and confirms the passage in the served
page. Identical brief jobs are deduplicated. A repeat content job does not duplicate a passage.
Changed managed passages require fresh editorial evidence rather than a blind overwrite.

Manual jobs use `POST /api/v1/projects/{id}/strategy` and
`POST /api/v1/projects/{id}/content/{opportunity_id}`. The dashboard exposes the same supported
publication action. Missing permission, facts, source or checks blocks the job with a dependency.

## Real search observations

`POST /api/v1/projects/{id}/search-console?start=YYYY-MM-DD&end=YYYY-MM-DD` reads the configured
URL-prefix property with the encrypted `search_console_access_token` credential. Configure that
credential through the scoped credentials API. It needs an owner-supplied OAuth access token;
the model API key cannot read Search Console. OAuth consent and token refresh are external.

The connector collects finalized web query/page/country/device slices, at most 1,000 top rows,
within a bounded measurement window. Imports remain unknown in business relevance until the
owner confirms it. Reimporting identical record IDs replaces those rows; overlapping distinct
windows are rejected. The underlying API also has top-row coverage limits, so an empty result
cannot establish zero total demand. This connector passed controlled-transport tests; a real
Search Console account is not connected in this workspace.
[Google Search Console API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query),
verified October 12, 2026.

## Citation experiments

Import engine transcripts in `citations`, retaining experiment, query, market, model/engine
version, baseline/treatment/holdout arm, sampling time, answer and cited URLs. Mark simulated
inputs `synthetic`; real and simulated samples are never aggregated together. Retrieval-disabled
responses cannot establish search citations. Accuracy remains unreviewed until checked against
the source supporting the cited passage.

`POST /api/v1/projects/{id}/citations` accepts `query`, `experiment`, `market`, and `arm`.
With a configured Google provider it collects an actual Interactions API answer with search
steps and URL annotations. The collector was exercised with the supplied provider key. It
observes the **search-grounded API**, not consumer AI Overview placements. Other engine
observations currently use explicit imports; automated Bing dashboard ingestion is not promised.
[Google grounding documentation](https://ai.google.dev/gemini-api/docs/google-search),
verified October 12, 2026.

Opaque grounding redirects stay unresolved. They produce citation-rate bounds and an unknown
point estimate when necessary, rather than a fabricated absence. Repeated observations describe
sampling variability; a before/after difference does not prove the source change caused it.
Clicks, rankings, citations, conversions and field performance remain separate measurements.

## Compute and publication boundaries

A native tool loop can finish once staged proposals pass trusted verification. Publication then
still runs independent policy/build checks and served-page verification. This avoids paying for
a redundant final response that simply repeats already verified patches.

The worker can reuse a prior model assessment only when the source revision, served observations,
workspace, policy, provider configuration, knowledge and fact/material validity are unchanged.
Evidence is recollected first. Assessments with additional model findings are re-evaluated so
caching cannot silently resolve those findings. Changed inputs invalidate the cache; irrelevant
mapped repository changes still bypass inference at the earlier incremental gate.

Technical model repairs preserve body copy. Changing body claims requires the supported content
job; citing a fact ID alone is insufficient. A navigation repair needs observed 404/410 evidence
and an observed public replacement. Vision remains optional and cannot prove indexing or uplift.

The recorded local demonstration used a real Git repository, HTTP site, dashboard, Docker check,
local commit and post-publication inspection. Its notebook and query counts are explicitly
synthetic. Publication is verified; search traffic and conversion gains are unverified.
