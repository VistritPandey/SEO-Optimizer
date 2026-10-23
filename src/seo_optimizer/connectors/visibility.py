"Repeatable API experiments; citation URLs come from annotations, never answer-text guesses."

from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import HttpUrl

from seo_optimizer.connectors.models import Collection, CollectionRequest, Resource
from seo_optimizer.connectors.transport import ConnectorError, Transport


def safe_citations(values: list[str]) -> list[str]:
    result = []
    for value in values:
        try:
            url = HttpUrl(value)
        except ValueError:
            continue
        if not url.username and not url.password and str(url) not in result:
            result.append(str(url))
    return result[:100]


def collect(t: Transport, q: CollectionRequest) -> Collection:
    if not q.query or not q.model:
        raise ConnectorError("configuration", "Choose an explicit model and a bounded query")
    key = t.secret(q.engine + "_key")
    prompt = (
        f"Market context: {q.market}. Use web search to answer this question "
        f"and cite sources actually used: {q.query}"
    )
    answer = []
    citations = []
    retrieval = False
    usage: dict[str, Any] = {}
    if q.engine == "google":
        from seo_optimizer.citations import collect_citation

        observation, transcript = collect_citation(q.query, q.model, key, q.experiment, q.market)
        return Collection(
            platform=t.connection.platform,
            measurement="api_experiment",
            records=[
                Resource(
                    id=observation.id,
                    kind="api_answer",
                    fields={
                        **observation.model_dump(mode="json"),
                        "usage": transcript.get("usage", {}),
                    },
                )
            ],
            warnings=[
                (
                    "Search-grounded API experiment, not a measurement of the Gemini consumer "
                    "product or universal ranking."
                )
            ],
        )
    if q.engine in {"openai", "perplexity"}:
        url = (
            "https://api.openai.com/v1/responses"
            if q.engine == "openai"
            else "https://api.perplexity.ai/v1/agent"
        )
        body: dict[str, Any] = {
            "model": q.model,
            "input": prompt,
            "tools": [{"type": "web_search"}],
            "max_output_tokens": 2048,
            "store": False,
        }
        if q.engine == "openai":
            body["max_tool_calls"] = 3
        else:
            body["max_steps"] = 3
        data = t.request(
            "POST", url, headers={"Authorization": "Bearer " + key}, body=body, read_only=False
        )
        if data.get("status") not in {None, "completed"}:
            raise ConnectorError("incomplete", "Visibility answer was not completed")
        for block in data.get("output", []):
            if block.get("type") in {"web_search_call", "search_results"}:
                retrieval = True
            if block.get("type") == "message":
                for content in block.get("content", []):
                    if content.get("type") == "output_text":
                        answer.append(content.get("text", ""))
                        for citation in content.get("annotations", []):
                            if citation.get("type") == "url_citation":
                                citations.append(citation.get("url", ""))
        usage = data.get("usage", {})
    else:
        data = t.request(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            body={
                "model": q.model,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
                "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
            },
            read_only=False,
        )
        for block in data.get("content", []):
            if block.get("type") == "web_search_tool_result":
                if isinstance(block.get("content"), dict):
                    raise ConnectorError("search_failed", "Search tool did not complete")
                retrieval = True
            if block.get("type") == "text":
                answer.append(block.get("text", ""))
                citations.extend(
                    c.get("url", "")
                    for c in block.get("citations", [])
                    if c.get("type") == "web_search_result_location"
                )
        usage = data.get("usage", {})
    if not answer or not retrieval:
        raise ConnectorError(
            "unresolved",
            "No completed answer with observed search execution; visibility remains unresolved",
        )
    urls = safe_citations(citations)
    host = t.connection.resource.removeprefix("www.").lower()
    fields = {
        "query": q.query,
        "market": q.market,
        "engine": q.engine + " search-enabled API",
        "engine_version": q.model,
        "experiment": q.experiment,
        "answer": "\n".join(answer)[:20000],
        "cited_urls": urls,
        "retrieval_enabled": retrieval,
        "target_cited": any(urlparse(u).hostname in {host, "www." + host} for u in urls),
        "citation_accuracy": "unreviewed",
        "usage": usage,
    }
    return Collection(
        platform=t.connection.platform,
        measurement="api_experiment",
        records=[Resource(id=str(uuid4()), kind="api_answer", fields=fields)],
        warnings=[
            (
                "API experiment only. Consumer answers differ by session, product, geography"
                " and time. No universal GEO ranking is assigned."
            )
        ],
    )
