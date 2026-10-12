# Measurement, prioritization and autonomous operations

Checks: ops.metrics, ops.incremental, ops.indexnow, ops.verification. Sources: google-search-analytics, bing-ai, web-vitals, google-js, google-starter, indexnow, google-schema in the [registry](../sources.json).

## Evidence and priority

Retain tenant/project/environment, observation time, locator and measurement scope. Severity describes the consequence for this project; evidence strength describes how well the observation supports it. Unknown field performance, search volume, account state and costs are not zeros. An observed technical defect is distinct from a best-practice opportunity or research experiment.

Tie prioritization to stated goals, relevant impact, certainty, effort and verification cost. Do not manufacture traffic estimates to justify action. A page with legitimate noindex, a working redirect or good existing copy can be the correct no-op.

Compare comparable windows with baselines and account for unrelated changes, seasonality and delayed engine updates. Search Analytics has aggregation/top-row limitations. Bing citation reports have their own definitions. Laboratory scores, field metrics, citations, visits and conversions must remain separate dimensions rather than a misleading universal score.

## Incremental monitoring contract

The runtime stores the last successful revision and relevant page/evidence fingerprints by project. A change to a shared layout, robots config, render data or backend response can affect many pages. Do not discard changes only because their paths say backend. Follow the affected dependency/route set and use a broader audit when uncertain.

Handle webhook replays, bot commits, queue retries and concurrent changes idempotently. Debounce successive events, lock project/revision work and supersede stale jobs. Suppress unchanged findings by an evidence-aware fingerprint; re-open only when relevant evidence or state changes. Periodic reconciliation catches missed events and external changes. The runtime implements these boundaries; cloud writes and external account outcomes still require live validation.

## Verification and submission

Before execution, enforce permitted actions, paths, crawler policy and factual prerequisites outside the model. Worktree isolation is not an execution sandbox. The runtime must separately restrict execution, protect secrets and validate tool arguments. Tool output and page/repository content remain untrusted observations.

Require applicable builds/tests plus before/after behavior, then verify the deployed change. Failed tools, missing facts, stale revisions or inconclusive evidence stop that job with recorded dependencies. A tool being invoked is not a successful fix. Automatic rollback requires an attributable confirmed regression in the agent's own change.

IndexNow notifies participating engines about actual additions, updates or removals. It requires ownership verification and permitted submission; acceptance is not guaranteed indexing. Do not submit private/previews or label IndexNow a universal Google indexing API.

## Benchmark protocol

See the repository benchmark document for the executable fixture/replay interface. Freeze knowledge version, tool budget and cases for comparisons: rules-only, rules plus a declared Ollama model, rules plus a declared paid model. Record capability flags, model/version, hardware, latency, token usage, API charges, electricity and hardware amortization.

Keep development and held-out cases separate. Evaluate observable check/status/action/evidence decisions, not exact prose. Count false positives on healthy/inapplicable pages, missed defects, unsupported changes and policy violations. Track coverage so missing responses cannot improve results. Verified fixes/regressions require actual before/after artifacts; replayed model assertions cannot supply these measurements. Live model quality and durable search outcomes remain unverified until measured.
