# Frozen repository model comparison

Five arms ran against the same anonymous repository commit, owner facts, runtime, knowledge,
policy, tool/response limits and owner-controlled outcome checks. Runtime integrity was verified
after all arms completed. This is one development repair case with four targets and separate
healthy-site and documentation-only merge controls; it is not held-out generalization.

| Arm | Verified repairs | Healthy control | Docs merge | Repair seconds | Extra paths |
|---|---:|---|---|---:|---:|
| rules | 0/4 | passed | passed | 3.2 | 0 |
| local-minimal | 0/4 | timed out | passed | 268.5 | 0 |
| local-full | 0/4 | timed out | passed | 185.2 | 0 |
| paid-minimal | 0/4 | passed | passed | 52.3 | 0 |
| paid-full | 4/4 | passed | passed | 71.5 | 0 |

Local model: `gemma4:12b` through Ollama; paid model: `gemini-3.8-flash` through the
official Google SDK. The local model ran on Apple M4 / 16 GiB with a 16,384-token context.
The host was shared with development work, so timing is not an isolated throughput test.

The full harness adds the private skill, relevant references, rule evidence and focused check
retrieval. Both model arms keep the same source, fact, path, private-page, crawler, behavior
and publication guards. Minimal runs retain required contract/check identifiers but no check
guidance or deterministic finding hints. Native requests and completed tool results are real.

Rules detected the fixture defects but currently lack automatic repairs for these four targets.
Their zero repair score describes remediation coverage. Local request timeouts are failed
completion attempts, not evidence of an incorrect published edit. Completed usage prior to a
timeout is retained as partial telemetry; total usage for a timed-out response is unknown.

The paid full harness published two justified files and verified all four served outcomes.
Its minimal runner inspected evidence but published no repairs. This supports the harness
on this case; it does not establish broad superiority or local/paid equivalence.

Known API charges are zero for rules/local operation. Electricity and hardware costs remain
unknown. Paid rates were not configured, so billed cost and cost per verified fix remain
unknown. The report does not manufacture a cost advantage from missing measurements.

[Full observations](model-repair-comparison.json) retain model usage, native tool events,
patches, build output, served verification and independent control revisions/diffs.
[Earlier development observations](benchmark-development-history.json) retain failed and
invalidated trials. The final frozen run is the authoritative comparison.

Live GitHub writes, search-account ingestion, consumer-engine citation uplift, rankings,
traffic and conversions remain unverified. More independent projects and repeated held-out
cases are needed before routing every repair to a local model or predicting search impact.
