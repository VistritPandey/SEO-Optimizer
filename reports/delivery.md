# Phase 1 delivery

Knowledge review date: October 12, 2026. Package version: 0.1.0.
Knowledge version: 1.0.0; contract version: 1.0.

## Implemented

The private search-optimization skill has eight routed decision references, 39 checks and
29 attributed sources. Check applicability, evidence, action prerequisites, verification and
no-op conditions are explicit. Research is classified separately from engine requirements.

Python provides 14 exported JSON Schemas, strict output parsing, cross-record evidence/source
validation, project/environment isolation checks, provider/tool interfaces, saved-output replay,
a five-check offline HTTP baseline and an evaluation CLI. The wheel includes the private
knowledge resources and validates in an isolated installed environment.

The benchmark contains 41 cases: 31 development and ten held-out. Reference responses are
authored examples; adversarial responses are deliberately invalid outputs. No real model has
been benchmarked.

## Verification results

| Verification | Result | Interpretation |
|---|---|---|
| Socket-blocked pytest suite | 93 passed; 0 failed; 0 skipped | Contracts, parsing, policies, provenance, CLI behavior, baseline decisions and schema compatibility |
| Ruff | Passed | Source and test lint checks |
| mypy strict | Passed | Eight Python source modules |
| Skill format validator | Passed | Skill frontmatter and completion checks |
| Knowledge package validator | Passed | All eight modules, source/check integrity and reachable local references |
| Build and isolated wheel install | Passed | Packaged knowledge and contracts work outside the source checkout |
| Synthetic reference replay | 41 passed; 0 failed; 0 skipped | Replay interface/rubric examples; not a real model score |
| Deterministic rules baseline | 19 passed; 0 failed; 22 skipped | Supported checks matched raw fixture expectations; remaining checks have no scanner |
| Adversarial replay | 10 rejected; 31 skipped | Ten intentionally bad outputs failed evaluation as required |

Machine-readable evidence is in `reference-replay.json`, `rules-baseline.json`,
`adversarial-replay.json` and `tests.xml` in this directory. Full evaluation reports contain
expected/observed decisions, failures, coverage and explicit unverified items. Skipped cases
never count as successes. Unknown runtime/cost values remain null.

## Unverified or deferred

- Live provider capability, inference quality, tool-loop reliability and measured model costs.
- Actual repository auditing beyond the five supplied-evidence checks; real browser/vision collection.
- Authenticated public SaaS access, database isolation, worker queue and execution sandbox.
- GitHub authentication/events/writes, branch merges, deployed verification and rollback.
- Business-profile, merchant-account and search-report integrations.
- Verified code fixes, regressions, causal search uplift, visits, conversions and cost per fix.

The validator checks structural policy declarations, not an actual patch's behavior or the truth
of every sentence. Those remain separate runtime responsibilities. The Phase 1 package performs
no production mutation and makes no claim of verified live improvements.

## Inputs for the next testing stage

1. A dedicated GitHub test repository and target branch, plus the framework and root folder.
2. A deployed website URL and build/test/start commands, with production/private/preview URL intent.
3. The exact Ollama model name, accessible worker-side endpoint, hardware and available memory;
   optional paid-provider/model selections for a later comparison.
4. Verified business/product facts and goals, crawler preferences and allowed change categories/paths.
5. Selected-repository GitHub App permissions and a webhook secret configured outside source control
   when the live connector is implemented; separate access for search/listing/merchant data if needed.

Do not send secret values in chat. Configure them through an ignored local environment file or
deployment secret manager. First test temporary Git commits/branch merges, a local fixture site and
event replay; enable live mutations only after that integration stage meets the configured policy.
