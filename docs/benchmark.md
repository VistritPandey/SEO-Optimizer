# Benchmark protocol

## Freeze the comparison

Compare three declared arms: the implemented rules baseline; rules plus one named Ollama
model; rules plus one named paid-provider model. Use the same knowledge version, cases,
observations, tools, step/time budget and allowed actions. Give the models only AuditRequest
inputs and relevant references. The two model arms and actual tool execution are not implemented
yet; saved-output replay establishes the measurement interface.

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

Verified fixes, regressions and cost per verified fix remain null in Phase 1. To measure them,
the later runtime must retain the actual patch, relevant before/after observations, test output,
checked revision and deployed verification. Never derive them from a model's own claim.

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
affected-page coverage, duplicate suppression, stale-job behavior and tool failures. These
event integrations are future tests, not claimed by the current suite.

Finally, use a dedicated GitHub test project, real deployed URLs and declared model settings.
Observe jobs without live mutations before enabling the configured action policy. Keep live
outcomes distinct from synthetic evaluation reports.
