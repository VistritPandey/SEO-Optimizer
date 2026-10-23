"""Live-page verification remains distinct from successful provider readback."""

import time
from typing import Any
from urllib.parse import urlparse

from seo_optimizer.audit import PageParser
from seo_optimizer.connectors.models import Platform
from seo_optimizer.connectors.service import ConnectorService
from seo_optimizer.connectors.transport import ConnectorError
from seo_optimizer.crawler import Crawler


def verify_live(service: ConnectorService, p: Platform, proposal_id: str) -> dict[str, Any]:
    state, version = service.lock(p)
    proposal = next((row for row in state.get("proposals", []) if row["id"] == proposal_id), None)
    try:
        if proposal is None:
            raise ConnectorError("not_found", "Proposal not found")
        if proposal["status"] not in {
            "verified",
            "waiting_publication",
            "deployed_verified",
            "pr_opened",
        }:
            raise ConnectorError("policy", "Only published or reviewed changes can be verified")
        url = proposal.get("verification_url") or proposal["before"].get("url", "")
        if not url or urlparse(url).netloc != urlparse(str(service.spec.website_url)).netloc:
            raise ConnectorError(
                "dependency", "Set an exact project page URL before live verification"
            )
        crawler = Crawler(
            str(service.spec.website_url),
            service.store.settings.allow_private_network,
            service.client,
        )
        try:
            response = crawler.fetch(url)
        finally:
            crawler.close()
        page = PageParser()
        page.feed(response.text)
        actual = {
            "seo_title": "".join(page.title).strip(),
            "seo_description": page.descriptions[0] if len(page.descriptions) == 1 else "",
        }
        expected = {k: v for k, v in proposal["changes"].items() if k in actual}
        if not expected:
            raise ConnectorError(
                "dependency", "These changes need project-specific live verification criteria"
            )
        passed = response.status_code == 200 and all(actual[k] == v for k, v in expected.items())
        proposal.setdefault("verification", {}).update(
            deployed_site="passed" if passed else "failed",
            url=url,
            checked_at=time.time(),
            status_code=response.status_code,
            expected=expected,
            observed=actual,
        )
        if passed:
            proposal["status"] = "deployed_verified"
        state["lease_until"] = 0
        service.save(p, state, version)
        return {k: v for k, v in proposal.items() if k not in {"before", "after"}}
    except Exception:
        state["lease_until"] = 0
        service.save(p, state, version)
        raise
