# Ecommerce search

Checks: commerce.facts, commerce.variants, commerce.navigation, commerce.merchants. Sources: google-product, google-variants, google-ecommerce, google-schema, google-canonical, google-ai in the [registry](../sources.json).

## Offers and variants

Use authoritative current catalog facts to identify each offer, product variant, market, currency, price, availability and validity period. Compare visible data, applicable Product/ProductGroup markup and authorized feed observations. Do not copy a parent product price onto every variant or mark unavailable stock as available.

Product snippets, merchant listings and Merchant Center feeds have different requirements. A markup validator confirms structure, not account approval, actual availability or a rich result. Do not conflate an external feed mismatch with a source-code defect when the repository is not the feed authority.

Map actual variant selection, supported URLs, group identities and canonical behavior before edits. A single-page variant selector and distinct variant pages require different treatment; do not force one URL design. Verify that selected offers and markup remain consistent.

## Categories and filters

Keep valuable category and product pages discoverable through useful internal links. Determine which faceted/filter pages have distinct value and which are duplicate combinations before adjusting crawling or canonicals. Blanket noindex for all filters can hide useful pages; enabling every filter can create unnecessary discovery work. Use explicit inventory and business intent.

Verify actual category-to-product navigation, status/redirects, canonicals and representative combinations. Pagination or selection controls must preserve human use and relevant accessible links. No framework rewrite is implied by a coverage finding.

## Merchant facts and accounts

Returns, shipping, business information and offers must match actual policies and markets. Treat feeds/account state as separate evidence with separate authorization. Missing permissions produce dependencies; never invent account enrollment, shipping promises or policies. Useful local/shop details can support AI experiences but do not guarantee selection.
