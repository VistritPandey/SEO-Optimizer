"CMS reads and small field updates. Publication permissions live in the service layer."

import json
import re
from typing import Any

from seo_optimizer.connectors.models import Collection, CollectionRequest, Platform, Resource
from seo_optimizer.connectors.transport import ConnectorError, Transport, identifier, segment

CMS = {
    Platform.WORDPRESS,
    Platform.WOOCOMMERCE,
    Platform.SHOPIFY,
    Platform.WEBFLOW,
    Platform.SANITY,
    Platform.CONTENTFUL,
    Platform.SQUARESPACE,
    Platform.WIX,
    Platform.FRAMER,
}


def mapped(t: Transport) -> dict[str, str]:
    result = {}
    for key in ["seo_title", "seo_description"]:
        name = t.connection.options.get(key + "_field", "")
        if name:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,99}", name):
                raise ConnectorError("configuration", "SEO field mapping must name a single field")
            if re.search(r"robots|index|status|price|review|rating|inventory|training", name, re.I):
                raise ConnectorError(
                    "policy", "SEO mappings cannot target protected business or crawler fields"
                )
            result[key] = name
    return result


def allowed_fields(t: Transport) -> set[str]:
    p = t.connection.platform
    if p == Platform.WEBFLOW and t.connection.options.get("collection_id"):
        return set(mapped(t))
    if p in {Platform.SHOPIFY, Platform.WEBFLOW, Platform.SQUARESPACE}:
        return {"seo_title", "seo_description"}
    if p == Platform.WORDPRESS:
        return {"title", "content", *mapped(t)}
    if p == Platform.WOOCOMMERCE:
        return {"title", "content", "short_description"}
    if p in {Platform.SANITY, Platform.CONTENTFUL, Platform.FRAMER}:
        return set(mapped(t))
    if p == Platform.BUSINESS_PROFILE:
        return {"regularHours"}
    return set()


def collect(t: Transport, q: CollectionRequest) -> Collection:
    c = t.connection
    p = c.platform
    r = c.resource
    single = q.resource_id
    records = []
    complete = bool(single)
    warnings = []
    if p in {Platform.WORDPRESS, Platform.WOOCOMMERCE}:
        base = r.rstrip("/")
        if p == Platform.WORDPRESS:
            kind = "posts" if c.options.get("content_type") == "posts" else "pages"
            url = base + "/wp-json/wp/v2/" + kind
            h = t.basic("username", "application_password")
            params = {"context": "edit", "per_page": q.limit}
        else:
            kind = "products"
            url = base + "/wp-json/wc/v3/products"
            h = t.basic("consumer_key", "consumer_secret")
            params = {"per_page": q.limit}
        data = t.request(
            "GET",
            url + ("/" + segment(single) if single else ""),
            headers=h,
            params=params,
            dynamic=True,
        )
        rows = [data] if single else data
        for row in rows:
            if p == Platform.WORDPRESS:
                fields = {
                    "title": row.get("title", {}).get("raw", ""),
                    "content": row.get("content", {}).get("raw", ""),
                    "status": row.get("status"),
                    **{key: row.get("meta", {}).get(name, "") for key, name in mapped(t).items()},
                }
            else:
                fields = {
                    "title": row.get("name", ""),
                    "content": row.get("description", ""),
                    "short_description": row.get("short_description", ""),
                    "status": row.get("status"),
                }
            records.append(
                Resource(
                    id=str(row["id"]),
                    kind=kind,
                    fields=fields,
                    revision=row.get("modified_gmt", row.get("date_modified_gmt", "")),
                    url=row.get("link", row.get("permalink", "")),
                )
            )
        warnings.append(
            "Self-hosted content changes use read-before-write checks; the API has no "
            "atomic revision precondition. Review concurrent edits."
        )
    elif p == Platform.SHOPIFY:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.myshopify\.com", r):
            raise ConnectorError("configuration", "Use the permanent myshopify.com shop domain")
        h = {"X-Shopify-Access-Token": t.secret()}
        selection = "id title descriptionHtml updatedAt onlineStoreUrl seo { title description }"
        query = (
            "query($id: ID!) { product(id:$id) { " + selection + " } }"
            if single
            else "query($first:Int!) { products(first:$first) { nodes { "
            + selection
            + " } pageInfo { hasNextPage } } }"
        )
        data = t.request(
            "POST",
            f"https://{r}/admin/api/2026-10/graphql.json",
            headers=h,
            body={"query": query, "variables": {"id": single} if single else {"first": q.limit}},
        )["data"]
        rows = [data["product"]] if single else data["products"]["nodes"]
        if not single:
            complete = not data["products"]["pageInfo"]["hasNextPage"]
        for row in rows:
            if row is None:
                raise ConnectorError("not_found", "Product was not found")
            records.append(
                Resource(
                    id=row["id"],
                    kind="product",
                    fields={
                        "title": row["title"],
                        "content": row.get("descriptionHtml", ""),
                        "seo_title": (row.get("seo") or {}).get("title") or "",
                        "seo_description": (row.get("seo") or {}).get("description") or "",
                    },
                    revision=row.get("updatedAt", ""),
                    url=row.get("onlineStoreUrl") or "",
                )
            )
        warnings.append(
            "Product SEO only. Shopify may supply fallback SEO values when fields are unset."
        )
    elif p == Platform.WEBFLOW:
        collection = c.options.get("collection_id", "")
        h = t.bearer()
        params = {"limit": q.limit}
        if c.options.get("locale_id"):
            params["localeId"] = c.options["locale_id"]
        if collection:
            url = f"https://api.webflow.com/v2/collections/{segment(collection)}/items"
            data = t.request(
                "GET", url + ("/" + segment(single) if single else ""), headers=h, params=params
            )
            rows = [data] if single else data.get("items", [])
        else:
            url = (
                "https://api.webflow.com/v2/pages/" + segment(single)
                if single
                else f"https://api.webflow.com/v2/sites/{segment(r)}/pages"
            )
            data = t.request("GET", url, headers=h, params=params)
            rows = [data] if single else data.get("pages", [])
        if not single:
            complete = int(data.get("pagination", {}).get("total", q.limit + 1)) <= q.limit
        for row in rows:
            fields = (
                {
                    "title": row.get("fieldData", {}).get("name", ""),
                    **{
                        key: row.get("fieldData", {}).get(name, "")
                        for key, name in mapped(t).items()
                    },
                }
                if collection
                else {
                    "title": row.get("title", ""),
                    "seo_title": row.get("seo", {}).get("title", ""),
                    "seo_description": row.get("seo", {}).get("description", ""),
                }
            )
            records.append(
                Resource(
                    id=row["id"],
                    kind="cms_item" if collection else "page",
                    fields=fields,
                    revision=row.get("lastUpdated", ""),
                )
            )
        warnings.append(
            "Changes are staged. Production publishing and verification require the "
            "site's normal publication workflow."
        )
    elif p == Platform.SANITY:
        base = f"https://{identifier(r)}.api.sanity.io/v2025-02-19/data/query/" + identifier(
            c.options.get("dataset", "production")
        )
        query = "*[_id == $id][0]" if single else "*[_type == $type][0..." + str(q.limit) + "]"
        params = {
            "query": query,
            "perspective": "raw",
            **(
                {"$id": json.dumps(single)}
                if single
                else {"$type": json.dumps(c.options.get("document_type", "page"))}
            ),
        }
        data = t.request("GET", base, headers=t.bearer(), params=params)["result"]
        for row in [data] if single else data:
            if not row:
                raise ConnectorError("not_found", "Document was not found")
            records.append(
                Resource(
                    id=row["_id"],
                    kind="document",
                    revision=row["_rev"],
                    fields={
                        "title": row.get("title", ""),
                        **{key: row.get(name, "") for key, name in mapped(t).items()},
                    },
                )
            )
        warnings.append(
            "Only existing drafts can be modified. Configure field mappings for this "
            "document schema."
        )
    elif p == Platform.CONTENTFUL:
        env = identifier(c.options.get("environment", "master"))
        locale = c.options.get("locale", "en-US")
        url = f"https://api.contentful.com/spaces/{identifier(r)}/environments/{env}/entries"
        data = t.request(
            "GET",
            url + ("/" + segment(single) if single else ""),
            headers=t.bearer(),
            params={"limit": q.limit},
        )
        for row in [data] if single else data.get("items", []):
            native = row.get("fields", {})
            fields = {
                "title": native.get("title", {}).get(locale, ""),
                "_native": native,
                **{key: native.get(name, {}).get(locale, "") for key, name in mapped(t).items()},
            }
            records.append(
                Resource(
                    id=row["sys"]["id"],
                    kind="entry",
                    revision=str(row["sys"]["version"]),
                    fields=fields,
                )
            )
        if not single:
            complete = data.get("total", q.limit + 1) <= q.limit
        warnings.append(
            "Writes save an unpublished entry revision; they do not publish the website."
        )
    elif p == Platform.SQUARESPACE:
        data = t.request(
            "GET",
            "https://api.squarespace.com/v2/commerce/products"
            + ("/" + segment(single) if single else ""),
            headers=t.bearer(),
        )
        rows = data.get("products", [])
        complete = not data.get("pagination", {}).get("hasNextPage", False)
        for row in rows[: q.limit]:
            records.append(
                Resource(
                    id=row["id"],
                    kind="product",
                    revision=row.get("modifiedOn", ""),
                    url=row.get("url", ""),
                    fields={
                        "title": row.get("name", ""),
                        "content": row.get("description", ""),
                        "seo_title": row.get("seoOptions", {}).get("title", ""),
                        "seo_description": row.get("seoOptions", {}).get("description", ""),
                    },
                )
            )
        complete = complete and len(rows) <= q.limit
        warnings.append(
            "Commerce products only; general pages and blogs require exported recommendations."
        )
    elif p == Platform.WIX:
        data = t.request(
            "GET",
            "https://www.wixapis.com/seo-metatags-server/v1/site-seo-tags",
            headers={"Authorization": t.secret(), "wix-site-id": r},
        )
        records = [Resource(id=r, kind="site_seo_tags", fields=data)]
        complete = True
        warnings.append(
            "Site SEO configuration is read-only in this release. Page-specific changes "
            "require Wix app/page API validation."
        )
    elif p == Platform.FRAMER:
        from seo_optimizer.connectors.framer import bridge

        records = [
            Resource.model_validate(row)
            for row in bridge(c, {"action": "collect", "limit": q.limit, "resource_id": single})
        ]
        warnings.append(
            "CMS fields only, via the official Server API. No automatic production publication."
        )
    else:
        raise ConnectorError("unsupported", "Unsupported content adapter")
    if len(records) > q.limit:
        raise ConnectorError("response_limit", "Provider ignored the requested content limit")
    return Collection(platform=p, records=records, complete=complete, warnings=warnings)


def write(t: Transport, current: Resource, changes: dict[str, str]) -> None:
    c = t.connection
    p = c.platform
    r = c.resource
    rid = segment(current.id)
    if not changes or not set(changes) <= allowed_fields(t):
        raise ConnectorError("policy", "Requested fields are not supported by this connector")
    if p == Platform.WORDPRESS:
        body: dict[str, Any] = {
            key: val for key, val in changes.items() if key in {"title", "content"}
        }
        meta = {mapped(t)[key]: val for key, val in changes.items() if key in mapped(t)}
        if meta:
            body["meta"] = meta
        t.request(
            "POST",
            r.rstrip("/") + f"/wp-json/wp/v2/{current.kind}/{rid}",
            headers=t.basic("username", "application_password"),
            body=body,
            read_only=False,
            dynamic=True,
        )
    elif p == Platform.WOOCOMMERCE:
        t.request(
            "PUT",
            r.rstrip("/") + "/wp-json/wc/v3/products/" + rid,
            headers=t.basic("consumer_key", "consumer_secret"),
            body={
                "name" if key == "title" else "description" if key == "content" else key: val
                for key, val in changes.items()
            },
            read_only=False,
            dynamic=True,
        )
    elif p == Platform.SHOPIFY:
        data = t.request(
            "POST",
            f"https://{r}/admin/api/2026-10/graphql.json",
            headers={"X-Shopify-Access-Token": t.secret()},
            body={
                "query": (
                    "mutation($product:ProductUpdateInput!) { productUpdate(product:$product) { "
                    "product { id } userErrors { field message } } }"
                ),
                "variables": {
                    "product": {
                        "id": current.id,
                        "seo": {key.removeprefix("seo_"): value for key, value in changes.items()},
                    }
                },
            },
            read_only=False,
        )
        if data.get("data", {}).get("productUpdate", {}).get("userErrors"):
            raise ConnectorError("provider_error", "Shopify rejected the product SEO update")
    elif p == Platform.WEBFLOW:
        collection = c.options.get("collection_id", "")
        url = (
            f"https://api.webflow.com/v2/collections/{segment(collection)}/items/{rid}"
            if collection
            else "https://api.webflow.com/v2/pages/" + rid
        )
        body = (
            {"fieldData": {mapped(t)[key]: value for key, value in changes.items()}}
            if collection
            else {"seo": {key.removeprefix("seo_"): value for key, value in changes.items()}}
        )
        t.request(
            "PATCH" if collection else "PUT",
            url,
            headers=t.bearer(),
            body=body,
            params={"localeId": c.options["locale_id"]} if c.options.get("locale_id") else None,
            read_only=False,
        )
    elif p == Platform.SANITY:
        if not current.id.startswith("drafts."):
            raise ConnectorError("policy", "Sanity writes require an existing draft document")
        t.request(
            "POST",
            (
                f"https://{identifier(r)}.api.sanity.io/v2025-02-19/data/mutate/"
                + identifier(c.options.get("dataset", "production"))
            ),
            headers=t.bearer(),
            body={
                "mutations": [
                    {
                        "patch": {
                            "id": current.id,
                            "ifRevisionID": current.revision,
                            "set": {mapped(t)[key]: value for key, value in changes.items()},
                        }
                    }
                ]
            },
            read_only=False,
        )
    elif p == Platform.CONTENTFUL:
        native = json.loads(json.dumps(current.fields["_native"]))
        for key, value in changes.items():
            native.setdefault(mapped(t)[key], {})[c.options.get("locale", "en-US")] = value
        t.request(
            "PUT",
            (
                f"https://api.contentful.com/spaces/{identifier(r)}/environments/"
                + identifier(c.options.get("environment", "master"))
                + f"/entries/{rid}"
            ),
            headers={
                **t.bearer(),
                "X-Contentful-Version": current.revision,
                "Content-Type": "application/vnd.contentful.management.v1+json",
            },
            body={"fields": native},
            read_only=False,
        )
    elif p == Platform.SQUARESPACE:
        seo = {
            key.removeprefix("seo_"): current.fields.get(key, "")
            for key in ["seo_title", "seo_description"]
        }
        seo.update({key.removeprefix("seo_"): value for key, value in changes.items()})
        t.request(
            "POST",
            "https://api.squarespace.com/v2/commerce/products/" + rid,
            headers=t.bearer(),
            body={"seoData": {"present": True, "value": seo}},
            read_only=False,
        )
    elif p == Platform.BUSINESS_PROFILE:
        t.request(
            "PATCH",
            "https://mybusinessbusinessinformation.googleapis.com/v1/locations/"
            + segment(r.split("/", 1)[1]),
            headers=t.bearer(),
            params={"updateMask": "regularHours"},
            body={"regularHours": json.loads(changes["regularHours"])},
            read_only=False,
        )
    elif p == Platform.FRAMER:
        from seo_optimizer.connectors.framer import bridge

        bridge(
            c,
            {
                "action": "write",
                "resource_id": current.id,
                "changes": {mapped(t)[key]: value for key, value in changes.items()},
                "expected_revision": current.revision,
            },
        )
    else:
        raise ConnectorError("unsupported", "Connector does not support publication")
