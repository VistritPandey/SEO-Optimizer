"Explicit support matrix; a connection is never proof of a working production integration."

from typing import Any

from seo_optimizer.connectors.models import Platform

# Fields are provider credentials or account identifiers, never arbitrary API endpoints.
DEFINITIONS: dict[str, dict[str, Any]] = {
    "search_console": dict(
        name="Google Search Console",
        group="Search evidence",
        resource="URL-prefix property or sc-domain:example.com",
        options=[],
        secrets=["access_token", "refresh_token", "client_id", "client_secret"],
        write=False,
        note=(
            "Search analytics, sitemap status and indexed-URL inspection. Average "
            "position is not a fixed rank; top-row coverage is bounded."
        ),
        source="https://developers.google.com/webmaster-tools/v1/api_reference_index",
    ),
    "wordpress": dict(
        name="WordPress",
        group="Publishing",
        resource="Website URL",
        options=["seo_title_field", "seo_description_field", "content_type"],
        secrets=["username", "application_password"],
        write=True,
        note=(
            "Pages and posts; registered REST meta fields only. Configure SEO plugin "
            "field mappings explicitly. Published content keeps its status."
        ),
        source="https://developer.wordpress.org/rest-api/reference/pages/",
    ),
    "woocommerce": dict(
        name="WooCommerce",
        group="Publishing",
        resource="Store URL",
        options=[],
        secrets=["consumer_key", "consumer_secret"],
        write=True,
        note=(
            "Product names, descriptions and short descriptions. Prices, inventory and "
            "reviews are never changed."
        ),
        source="https://woocommerce.github.io/woocommerce-rest-api-docs/",
    ),
    "shopify": dict(
        name="Shopify",
        group="Publishing",
        resource="Shop domain, example.myshopify.com",
        options=[],
        secrets=["access_token", "refresh_token", "client_id", "client_secret"],
        write=True,
        note=(
            "Product SEO title and description via versioned GraphQL. Theme edits and "
            "theme publication are not part of this connector."
        ),
        source="https://shopify.dev/docs/api/admin-graphql/latest/mutations/productUpdate",
    ),
    "webflow": dict(
        name="Webflow",
        group="Publishing",
        resource="Site ID",
        options=["collection_id", "locale_id", "seo_title_field", "seo_description_field"],
        secrets=["access_token", "refresh_token"],
        write=True,
        note=(
            "Static-page SEO metadata and mapped CMS fields. Changes are staged; "
            "publishing the whole site is not automatic."
        ),
        source="https://developers.webflow.com/data/reference/pages-and-components/pages/update-page-settings",
    ),
    "ga4": dict(
        name="Google Analytics 4",
        group="Search evidence",
        resource="Numeric property ID",
        options=[],
        secrets=["access_token", "refresh_token", "client_id", "client_secret"],
        write=False,
        note=(
            "Landing-page sessions, engagement, key events and revenue. Attribution "
            "depends on the property's tracking setup."
        ),
        source="https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1beta/properties/runReport",
    ),
    "vercel": dict(
        name="Vercel",
        group="Deployments",
        resource="Project ID",
        options=["team_id"],
        secrets=["access_token", "webhook_secret"],
        write=False,
        note=(
            "Deployment status and signed events. Only the configured production origin "
            "and environment can trigger verification."
        ),
        source="https://vercel.com/docs/webhooks/webhooks-api",
    ),
    "netlify": dict(
        name="Netlify",
        group="Deployments",
        resource="Site ID",
        options=[],
        secrets=["access_token", "webhook_secret"],
        write=False,
        note=(
            "Deployment status. Use the signed generic deployment event from CI for a "
            "consistent verification payload."
        ),
        source="https://docs.netlify.com/deploy/deploy-notifications/",
    ),
    "deployment": dict(
        name="Other hosting / CI",
        group="Deployments",
        resource="Project identifier",
        options=[],
        secrets=["webhook_secret"],
        write=False,
        note=(
            "Signed deployment events from any host; replay, origin, freshness and "
            "environment checks enforced."
        ),
        source="https://youroptimiser.com/how-it-works",
    ),
    "gitlab": dict(
        name="GitLab",
        group="Repositories",
        resource="Group/project",
        options=["branch"],
        secrets=["access_token", "refresh_token", "client_id", "client_secret", "webhook_secret"],
        write=True,
        note=(
            "File reads, guarded branch commits and merge requests on GitLab.com. "
            "Self-hosted endpoints require a separately reviewed host configuration."
        ),
        source="https://docs.gitlab.com/api/merge_requests/",
    ),
    "bitbucket": dict(
        name="Bitbucket",
        group="Repositories",
        resource="Workspace/repository",
        options=["branch"],
        secrets=["access_token", "refresh_token", "client_id", "client_secret", "webhook_secret"],
        write=True,
        note=(
            "File reads, guarded branch commits and pull requests on Bitbucket Cloud. "
            "Existing PR lifecycle must be completed in Bitbucket."
        ),
        source="https://developer.atlassian.com/cloud/bitbucket/rest/api-group-pullrequests/",
    ),
    "bing": dict(
        name="Bing Webmaster Tools",
        group="Search evidence",
        resource="Verified website URL",
        options=[],
        secrets=["api_key"],
        write=False,
        note=(
            "Query statistics and crawl statistics. AI citation dashboard ingestion is "
            "not claimed without a documented accessible API."
        ),
        source="https://learn.microsoft.com/en-us/bingwebmaster/",
    ),
    "business_profile": dict(
        name="Google Business Profile",
        group="Local search",
        resource="locations/ID",
        options=[],
        secrets=["access_token", "refresh_token", "client_id", "client_secret"],
        write=True,
        note=(
            "Read business details and update regular hours from unexpired trusted "
            "project facts. Google API approval is required."
        ),
        source="https://developers.google.com/my-business/reference/businessinformation/rest/v1/locations/patch",
    ),
    "cloudflare": dict(
        name="Cloudflare",
        group="Crawler evidence",
        resource="Zone ID",
        options=[],
        secrets=["access_token"],
        write=False,
        note=(
            "Sampled request analytics, paths and response statuses. Dataset "
            "availability depends on plan; visits do not establish citations or bot "
            "identity."
        ),
        source="https://developers.cloudflare.com/analytics/graphql-api/",
    ),
    "server_logs": dict(
        name="Server logs",
        group="Crawler evidence",
        resource="Website origin",
        options=[],
        secrets=[],
        write=False,
        note=(
            "Import bounded structured request records. User agents are self-reported; "
            "no user IPs or cookies are stored."
        ),
        source="https://www.cloudflare.com/en-gb/learning/ai/how-to-detect-which-ai-bots-crawl/",
    ),
    "wix": dict(
        name="Wix",
        group="Publishing",
        resource="Site ID",
        options=[],
        secrets=["access_token"],
        write=False,
        note=(
            "Read site SEO tags plus live-page audits. Page-level writes are withheld "
            "until the relevant Wix page/app API can be validated; proposals can be "
            "exported."
        ),
        source="https://dev.wix.com/docs/api-reference/business-management/seo/site-seo-tags-v1/site-seo-tags-object",
    ),
    "squarespace": dict(
        name="Squarespace",
        group="Publishing",
        resource="Website URL",
        options=[],
        secrets=["access_token"],
        write=True,
        note=(
            "Commerce product SEO metadata. General pages and blogs use live-page audits"
            " and exported recommendations; no general page-edit API is assumed."
        ),
        source="https://developers.squarespace.com/commerce-apis/products",
    ),
    "framer": dict(
        name="Framer",
        group="Publishing",
        resource="Framer project ID",
        options=["collection_id", "seo_title_field", "seo_description_field"],
        secrets=["access_token"],
        write=True,
        note=(
            "Official Server API bridge for CMS reads and mapped CMS-field changes. "
            "Requires Node and the bundled framer-api bridge; no automatic production "
            "deployment."
        ),
        source="https://www.framer.com/developers/server-api-quick-start",
    ),
    "sanity": dict(
        name="Sanity",
        group="Publishing",
        resource="Project ID",
        options=["dataset", "document_type", "seo_title_field", "seo_description_field"],
        secrets=["access_token"],
        write=True,
        note=(
            "Mapped document fields with revision preconditions. Only existing draft "
            "documents are writable; publish through the customer's normal review flow."
        ),
        source="https://www.sanity.io/docs/http-reference/mutation",
    ),
    "contentful": dict(
        name="Contentful",
        group="Publishing",
        resource="Space ID",
        options=["environment", "locale", "seo_title_field", "seo_description_field"],
        secrets=["access_token"],
        write=True,
        note=(
            "Mapped entry fields with version preconditions. Updates stay unpublished; "
            "publication is managed through Contentful."
        ),
        source="https://www.contentful.com/developers/docs/references/content-management-api/overview/",
    ),
    "dataforseo": dict(
        name="Keyword & competitor rankings",
        group="Search evidence",
        resource="Target hostname",
        options=["location_code", "language_code"],
        secrets=["username", "password"],
        write=False,
        note=(
            "Paid Google organic SERP observations by query, location and language. One "
            "bounded live task per explicit collection; charges are recorded when "
            "returned."
        ),
        source="https://docs.dataforseo.com/v3/serp-google-organic-overview/",
    ),
    "ai_visibility": dict(
        name="AI answer visibility",
        group="AI visibility",
        resource="Target hostname",
        options=[],
        secrets=["google_key", "openai_key", "anthropic_key", "perplexity_key"],
        write=False,
        note=(
            "Search-enabled API experiments and separately labelled imports of consumer "
            "observations. Never presented as universal rankings or consumer-product "
            "coverage."
        ),
        source="https://youroptimiser.com/seo-and-ai-search",
    ),
}


def catalog() -> list[dict[str, Any]]:
    assert set(DEFINITIONS) == {p.value for p in Platform}
    return [
        {"platform": key, **value, "live_verified": False} for key, value in DEFINITIONS.items()
    ]
