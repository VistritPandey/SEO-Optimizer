# Benchmark protocol

## Freeze the comparison

Compare three declared arms: the implemented rules baseline; rules plus one named Ollama
model; rules plus one named paid-provider model. Use the same knowledge version, cases,
observations, tools, step/time budget and allowed actions. Give the models only AuditRequest
inputs and relevant references. Native provider/tool adapters and live fixture evaluation are implemented. The CLI
`--arm hybrid` runs the supported rule checks first and passes only remaining checks to the
model; `--arm model-only` isolates model decisions. Protocol files record actual inference
counts so rules-only routes cannot inflate claims of model quality.
Saved-output replay remains available for controlled, offline grading.

Record exact model/version, capability verification, sampling parameters, context budget,
provider errors, host hardware and collection time. Repeat real inference trials and retain
failures. Evaluate each provider/model run separately; mixing models in an aggregate report is
rejected. A later hybrid/fallback benchmark needs its own explicitly defined arm.

## Dataset and separation

The initial set contains 41 cases, including 31 development cases and ten held-out cases.
Healthy, private and inapplicable examples prevent a model from winning by inventing issues.
Cases cover raw HTML and status observations, source policy, business facts, AI search myths,
local details, offers/variants, language alternatives, change relevance and failed tools.

Development is the default CLI partition. Use held-out cases only after freezing the skill/model
configuration; all-partition synthetic replay is a mechanics check, not an untouched scientific
test. Authoring these cases and expectations makes them visible to developers. Strong model
claims require additional blinded real-project examples not used to tune the guide.

Reference responses are authored decisions with no measured model runtime or cost. They are
not a model baseline. Adversarial responses deliberately include malformed JSON, invented
evidence, cross-tenant outputs, unsupported actions, source errors, escaping paths, research
certainty claims, screenshot-only automation and incomplete tool results.

## Decision grading

A case passes when its check/status decisions, action category, automatic-action choice and
required evidence match expectations, and all structural policy/provenance checks pass.
Summary wording is not graded. Duplicate outputs, unrelated source IDs, unknown observations
and cross-scope records cannot hide behind a fluent explanation.

Detection precision/recall compare defect check IDs; unresolved and experimental findings are
separate decisions. Wrongly grounded detections do not count as true positives. Decision pass
rate captures action/policy failures that detection alone misses. Unnecessary actions count
non-noop actions on unexpected findings. Coverage exposes missing responses; no response is
skipped, not passed. An actual provider/run error is failed, not skipped.

The simple rule baseline accepts one HTTP page per request and implements only five of the
39 catalog checks. Unsupported cases remain skipped. Report both its measured detection
performance on supported cases and its overall coverage; do not call skipped checks healthy.
The baseline cannot retrieve a destination response or corroborate a screenshot on its own.

## Measurements and unknowns

ResponseRecord accepts observed runtime and token usage plus API, electricity and amortized
hardware costs. Set an inapplicable but measured cost component to zero; leave unknown
components null. Total cost stays unknown unless all components for all evaluated cases are
available. Runtime means include only cases with measurements, with their count exposed.
Imported measurements are not independently attested by replay.

Decision-only fixtures leave verified fixes, regressions and cost per verified fix null.
The operational runtime retains the actual patch, relevant before/after observations, test output,
checked revision and deployed verification. Use that evidence for operational measurements;
never derive them from a model's own claim.

Search effects need a separate longitudinal study. Track crawl/index status, relevant query
performance, citations/link fidelity, visits and conversions independently. Repeat AI queries
with paraphrases and controls; retain engine/version and whether search activated. Account for
delays, stochastic outputs, seasonality and unrelated changes. A technical fix or a citation
increase is not proof of downstream traffic or revenue improvement.

## Gate for live testing

Before live access: package validation, schema exports, socket-blocked tests, lint/type checks,
installed-wheel validation and expected rejection of adversarial replays must pass.

Next, simulate events against a temporary Git repository: initialize files, commit changes,
create/merge a branch, replay push/deployment events and serve a local fixture website. Assert
affected-page coverage, duplicate suppression, stale-job behavior and tool failures. The current suite exercises real temporary commits/merges and local HTTP verification, signed
webhook replay, remote-worker scope, native provider protocols and recovery/rollback gates.
GitHub API mutations are controlled transport tests; real cloud writes require configured access.

Finally, use a dedicated GitHub test project, real deployed URLs and declared model settings.
Observe jobs without live mutations before enabling the configured action policy. Keep live
outcomes distinct from synthetic evaluation reports.

## Recorded local model runs

The delivered reports retain successful schema/tool smoke tests and unsuccessful model-only
fixture trials. These used the installed gemma4:12b model on an Apple M4, with explicit output
and context limits. Development cases were used; no held-out inference was performed.
A smoke test proves a particular capability invocation, not general autonomous reasoning quality.
Unsuccessful fixture decisions remain failures and cannot qualify the model for production.
Paid inference has since completed two controlled repository repairs with the current Google
SDK, plus a repeated model audit and a merged-documentation control. Those records are in
`reports/agent-demo-repair.json` and `videos/public/agent-run.json`. They used a different task,
configuration and development history from the Ollama decision runs. They are **not** a fair
open-versus-paid comparison or a general model-quality result.


## Measure the contribution of the stack

The comparison question is whether the private skill, evidence selection, tools, rules and
verification improve outcomes enough to make a smaller local model useful. A comparison of
only two models with the full stack cannot isolate that contribution.

Use five arms for the repository-repair evaluation:

| Arm | Reasoning and information | What it establishes |
|---|---|---|
| Rules alone | Supported rules, collected evidence and deterministic repair | Baseline coverage and when inference is unnecessary |
| Open model, minimal runner | Task, facts, output contract and safe file/check primitives | Local model performance without SEO skill/rule hints |
| Open model, full stack | Same primitive access plus versioned skill, rule findings and relevant knowledge tools | Improvement from the optimization stack |
| Paid model, minimal runner | The identical minimal setup | Paid model performance without SEO skill/rule hints |
| Paid model, full stack | The identical full setup | Improvement from the stack and the remaining model gap |

All arms retain the same independent policy and outcome checker. Removing safety gates is
neither necessary nor useful for measuring reasoning quality. "Minimal" means removing SEO
instructions and rule hints, not preventing a model from producing an executable proposal.
A paid-provider transport SDK is an adapter, not an additional source of SEO expertise.

The current `benchmark-live --arm model-only` still supplies the service skill and relevant
references. It is an **assessment-only arm with the skill**, not the proposed minimal runner.
The operational demo measures actual repairs but currently contains one developed scenario.
Neither implements the complete five-arm, held-out repository benchmark yet.

## Repository tasks, controls and measurements

Freeze the knowledge, fixtures, source/evidence hashes, provider settings and evaluator before
collecting comparison results. Each arm starts from a fresh copy of the same commit and the
same observations and owner facts. Expected edits and checker internals are withheld from the
model; configured check results are available through the shared tool interface. Do not modify
the hidden outcome checker after looking at held-out results.

Include several families rather than cloning a single title-repair case:

- Static HTML and framework metadata, rendered content and genuine response directives.
- Shared-layout changes, route-level changes, irrelevant changes and feature-branch merges.
- Products, variants, facets, price/availability contradictions and multilingual equivalents.
- Content briefs and edits requiring original owner material, factual support and search intent.
- Healthy pages, adequate copy, private previews and independently configured training opt-outs.
- Missing facts, forbidden paths, prompt injection, failed tools/builds and changed base revisions.

Use repeated runs in randomized order. Run every model with equal action, step, token and time
limits in the common supported capability set. Report equivalent sampling settings, any provider
settings that cannot be matched, model digests/versions and local hardware. Do not quietly give
one model a larger context or extra retries. Failed runs count in the primary result.
The demo's configured 150,000-token/16-call limits and earlier default Ollama configurations
must not be compared as if they were equivalent trials.

Judge observable behavior:

| Measure | Evidence |
|---|---|
| Detection precision, recall and coverage | Independently established defects, healthy controls and unresolved decisions |
| Verified fix rate | Staged checks plus source, rendered-page and behavior checks after publication |
| Unnecessary changes | Adequate/private content or unrelated files changed without justification |
| Regression rate | Independent behavior, factual, privacy and crawler-policy failures |
| Recovery | Corrected proposals after failed checks; no premature publishing |
| Efficiency | Inference requests, tool calls, cumulative tokens, wall time and applicable cache measurements |
| Cost per verified fix | Observed API billing plus measured local energy/hardware components; otherwise unknown |

Both providers can receive the full stack and still perform poorly. Skill and tool effectiveness
are hypotheses to test, not assumptions that qualify any model for unattended publication.
A useful outcome may be a local model qualified for particular repairs, with rule routing and
paid fallback for unresolved cases. Fallback must be evaluated as its own system, including
its failed attempts and total cost.

## Separate software quality from search results

Repository evaluation measures decisions, repairs and preserved behavior. It cannot measure
whether a site becomes more likely to be indexed, ranked, cited or visited.

A subsequent live-site study records dated crawl/index observations, query performance,
AI-answer citations and factual representation, traffic and conversions separately. Define the
engine, query/locale set, control pages or topics, repeated observations and the evaluation
window before treatment. Confirm available authorized account data and connector/API coverage.
GEO/LEO labels do not replace those engine-specific definitions. Leave unavailable measurements
unknown and retain observations where retrieval/search did not activate.

## Executable repository comparison

The `benchmark-repairs` command now runs actual native inference and local repository repairs
on the anonymous store fixture. It records the frozen Git commit/content hash, trusted facts,
shared limits, individual failures, per-target verification, published file scope, healthy
control, merged documentation branch control, observed time, and available usage/cost fields.
Rules alone currently have no repair implementation for these four target defects. A zero
rules repair score describes coverage, not an incorrect application of an implemented rule.

```sh
uv run seo-optimizer benchmark-repairs \
  --output .data/repair-benchmark/run.json \
  --local-model gemma4:12b --paid-model gemini-3.8-flash
```

Run with the browser extra and its installed Chromium plus the configured Docker verification
image. A model API key is read from the ignored `.env`; no GitHub credentials are required.
One frozen repair case is a development diagnostic, not a held-out model-quality estimate.
Published file precision and verified repair recall can be observed on it, but repairs within
one case are correlated. Repeat across independent projects and cases before generalizing.

`--arms` selects a subset. `--resume` adds previously unrun arms to the same saved fixture,
commit, origin and facts. It reserves the original server port before resetting the generated
repository; an active run cannot be resumed safely. Deferred retry jobs are terminalized for
scenario isolation and their failed attempt is retained. A control's own healthy baseline is
established independently so failed earlier inference cannot turn a docs-only merge into an
unrelated website audit. Only generated benchmark repositories are reset or cleaned.

`--controls-only --resume --arms ARM` repeats controls while retaining the recorded repair and
invalidated prior control observations. This is for documented experiment contamination; it
must not erase valid model failures or be used to hide unfavorable trials. Control retest
artifacts include their before/after Git revisions and actual diff.

The initial live experiment exercised `gemma4:12b` through Ollama and `gemini-3.8-flash` through
the official SDK. Local timeouts remain failures. Local API charges of zero do not include
hardware, electricity, or opportunity cost. Paid token usage without declared rates does not
establish a billed amount or cost per verified fix. Runtime observed during development is not
an isolated hardware throughput comparison.

The subsequent runtime improvement can finish inference after trusted staged-tool verification,
then still run independent publication checks. An unchanged-input assessment cache avoids
repeat inference when safe. Requalify all arms on the same runtime/knowledge revision after
such changes; do not silently pool samples from different implementations. The current
recorded repair and content demonstrations separately qualify these new boundaries.

## Reproducible workflow coverage

Run `uv run python scripts/verify_workflows.py --sandbox --output reports/workflow-validation.json`
with Docker available. This runs the Python suite and derives the report from individual JUnit
results. Missing catalog scenarios remain unverified; skipped tests never count as passes.

All 39 catalog paths have a rich-context scenario. Semantic paths also exercise unresolved
inputs, grounded findings, and locally validated scripted reviews. These fixture reviews test
contracts and routing, not an actual model's ability to make the right judgment. An artificial
site providing every input does not establish complete evidence for a connected customer site.

Six repair scenarios use the native provider adapter with scripted replies and real temporary
Git repositories, HTTP collection, Docker checks, publication and fresh served observations:
description, conflicting canonical, accidental public-page noindex, broken navigation, and
configured crawler policy, and combined metadata/navigation defects in one file. Healthy repeat audits must leave Git unchanged. A seventh scenario
rejects an owner check and must publish nothing. These scenarios replay inference responses;
they do not use live GitHub or measure provider quality. Existing production validation is
recorded separately in `reports/agent-validation.json`.

Verification retains rule-established defects separately from semantic findings. A semantic
repair cannot become a verified fix merely because a crawl reports no new contradiction.
Unconfirmed repairs retain evidence dependencies and do not trigger rollback without an
observed regression. Supported original-passage publication has its own served-text check.
