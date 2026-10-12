# International and multilingual SEO

Checks: intl.hreflang, intl.localization. Sources: google-hreflang, google-helpful in the [registry](../sources.json).

## Equivalent language alternatives

Build an actual locale-to-URL map before changing hreflang. Check supported language/region identifiers, self-references, reciprocal links, final URL accessibility and consistency with the chosen canonical. x-default is useful when applicable, not mandatory for every page. Do not fabricate alternatives or return links.

Language alternatives must represent equivalent user intent, not merely similar keywords. Do not canonicalize all translated content to an English page while claiming each language should remain discoverable. Use the documented alternative mechanisms consistently for the website's implementation.

## Genuine localization

Confirm visible language, currency, product/service availability, policies and regional contact facts. hreflang is not translation or proof of local presence. Use authoritative localized facts and competent translation; missing facts remain unresolved. Avoid a forced redirect that prevents users or crawlers from reaching an intended locale.

A single-language website is a no-op. For actual localized sites, verify reciprocal and self references, equivalent content, navigation and explicit locale behavior. Retain query language and geography when comparing outcomes; do not infer a global uplift from one market.
