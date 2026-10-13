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
