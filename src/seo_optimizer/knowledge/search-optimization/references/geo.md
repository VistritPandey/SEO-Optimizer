# AI discovery, answers and experiments

Checks: geo.crawlers, geo.google-llms, geo.google-faq, geo.entities, geo.experiment, geo.visibility, geo.google-inclusion. Sources are engine-specific: google-ai, google-updates, google-ai-control, google-ai-report, openai-bots, anthropic-bots, microsoft-content, bing-ai; experimental sources geo-paper and geo-survey. See the [registry](../sources.json).

## Terminology and engine scope

GEO and LLM answer visibility describe related goals rather than a single standardized ranking system. This package treats local search separately instead of assigning a universal meaning to LEO. Identify the exact engine, surface, query, geography and date before applying advice.

Google's 2026 guidance grounds AI visibility in its Search systems. Confirm crawlability, eligible indexed content and owner inclusion preferences. Its guide says special AI files such as llms.txt do not affect Google visibility; do not require them, promise uplift or delete a file intentionally used by another service. Google deprecated FAQ rich results in May 2026. Useful FAQ answers remain useful content; their existence is not a deprecated display promise.

Google does not require fixed-size content chunks, special AI prose or special schema for AI inclusion. Microsoft guidance recommends clear structure and supported facts for answer reuse; retain that publisher context rather than treating every suggested layout as a universal Google requirement. Structured data should describe real visible content and applicable rich-result types.

## Independent crawler policy

OpenAI distinguishes OAI-SearchBot search discovery, GPTBot training and ChatGPT-User user-directed access. Anthropic distinguishes Claude-SearchBot, ClaudeBot and Claude-User. Verify current bot documentation before edits. Allowing search does not require allowing training. Preserve declared opt-outs and provider-specific user access behavior; do not generalize robots semantics across providers.

A bots policy assessment compares effective configuration with owner intent. A user-agent string alone is not verification that a request is from the actual provider. Missing owner policy, property access or network evidence produces a dependency, not an invented configuration change.

## Content and measurement

Keep business entities, names, offers and factual answers consistent across visible content and eligible markup. Make answers useful to people and support important assertions with real evidence. Distinguish being discovered, retrieved, cited, accurately represented and clicked; citation count is not an ordinary search rank.

Use official report definitions when available. Google documents an AI performance report and inclusion control; Bing provides AI citation insights. Do not infer API endpoints from dashboard availability. Retain sample/aggregation caveats and do not invent a universal AI visibility score.

The foundational GEO study measured tactics in particular query/source/model conditions. Its reported gains are not guaranteed organic discovery, future ranking or revenue gains. Later research emphasizes pipeline stages and run-to-run variation. Treat citation rewrites, additional sourced evidence or presentation changes as bounded experiments only when they also preserve truthful, useful content.

An experiment needs a fixed engine/version, queries and paraphrases, repeated baseline/control/treatment observations, hold-out queries, attribution checks and a stopping rule. Retain cases where the engine does not activate search. Record link correctness and factual representation, not just brand mentions. Never insert prompt-injection instructions or inauthentic mentions to manipulate an answering system.
