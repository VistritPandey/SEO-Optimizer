"""Collect search-grounded API observations without claiming consumer-engine rankings."""

import hashlib
from typing import Any, Literal

from google import genai
from google.genai import errors, interactions, types
from pydantic import HttpUrl

from seo_optimizer.contracts import utc_now
from seo_optimizer.growth import CitationObservation


def normalize_interaction(
    payload: dict[str, Any],
    query: str,
    model: str,
    experiment: str,
    market: str,
    arm: Literal["baseline", "treatment", "holdout"],
) -> CitationObservation:
    passages: list[str] = []
    urls: list[HttpUrl] = []
    search_used = False
    for step in payload.get("steps", []):
        if step.get("type") in {"google_search_call", "google_search_result"}:
            search_used = True
        if step.get("type") != "model_output":
            continue
        for block in step.get("content", []):
            if block.get("type") != "text":
                continue
            passages.append(block.get("text", ""))
            for annotation in block.get("annotations", []):
                if annotation.get("type") == "url_citation":
                    url = HttpUrl(annotation["url"])
                    if url not in urls:
                        urls.append(url)
    if not passages:
        raise ValueError("Grounded API did not return an observable answer")
    # Citations without observed retrieval cannot establish engine discovery.
    if urls and not search_used:
        raise ValueError("Citations returned without an observable search step")
    now = utc_now()
    identity = hashlib.sha256((query + now.isoformat()).encode()).hexdigest()[:24]
    return CitationObservation(
        id="api-" + identity,
        experiment=experiment,
        query=query,
        engine="Google Search-grounded API",
        engine_version=model,
        arm=arm,
        observed_at=now,
        market=market,
        answer="\n".join(passages)[:20000],
        cited_urls=urls[:100],
        source="Gemini Interactions API actual search transcript "
        + str(payload.get("id", identity)),
        retrieval_enabled=search_used,
        citation_accuracy="unreviewed",
    )


def collect_citation(
    query: str,
    model: str,
    key: str,
    experiment: str,
    market: str,
    arm: Literal["baseline", "treatment", "holdout"] = "baseline",
) -> tuple[CitationObservation, dict[str, Any]]:
    if not key or not query or len(query) > 500:
        raise ValueError("Citation collection requires a provider key and bounded query")
    client = genai.Client(
        api_key=key,
        http_options=types.HttpOptions(
            timeout=90000,
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    try:
        response = client.interactions.create(
            model=model,
            input=f"Market context: {market}. Answer this question using Google Search "
            f"and cite the sources actually used: {query}",
            tools=[{"type": "google_search"}],
            store=False,
            generation_config={"max_output_tokens": 2048},
            timeout=90,
        )
        if not isinstance(response, interactions.Interaction):
            raise ValueError("Grounded API returned an unexpected streaming response")
        payload: dict[str, Any] = response.model_dump(mode="json", exclude_none=True)
        return normalize_interaction(payload, query, model, experiment, market, arm), payload
    except errors.APIError as error:
        raise ValueError(f"Grounded API returned HTTP {error.code}") from None
    finally:
        client.close()
