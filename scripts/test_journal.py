"""Verify the served journal, article facts, structured data and recorded demo.

No model, account, GitHub write or contact-form submission is used by this check.
"""

import argparse
import hashlib
import json
from pathlib import Path

import httpx
from test_public_site import CANONICAL, Document

ARTICLES = (
    "/blog/what-is-an-autonomous-seo-agent",
    "/blog/seo-checklist-after-a-website-update",
    "/blog/seo-and-geo-what-to-fix-first",
)
ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:3002")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/journal-qa.json")
    args = parser.parse_args()
    passed = []
    with httpx.Client(base_url=args.base_url, timeout=30) as client:
        homepage = client.get("/")
        assert homepage.status_code == 200
        document = Document(homepage.text)
        assert "autonomous SEO agent" in document.title
        assert "/blog" in document.links
        assert all(path not in document.links for path in ARTICLES)
        assert {"journal-title", "guide-title"}.isdisjoint(document.ids)
        passed.append(
            "Homepage names the autonomous SEO agent and links the separate Blog page "
            "without duplicating article or guide sections"
        )
        index = client.get("/blog")
        assert index.status_code == 200
        index_document = Document(index.text)
        assert "Blog" in index_document.title and "Your Optimiser" in index_document.title
        assert "Journal" not in index.text and "JOURNAL" not in index.text
        assert all(path in index_document.links for path in ARTICLES)
        collection = next(s for s in index_document.schemas if s.get("@type") == "CollectionPage")
        assert {item["url"] for item in collection["mainEntity"]["itemListElement"]} == {
            CANONICAL + path for path in ARTICLES
        }
        passed.append(
            "Journal index links exactly the published articles in its collection metadata"
        )

        cover_paths, cover_hashes = set(), set()
        for path in (*ARTICLES, "/guides/continuous-seo"):
            response = client.get(path)
            assert response.status_code == 200
            page = Document(response.text)
            graph = next(s["@graph"] for s in page.schemas if "@graph" in s)
            article = next(s for s in graph if s["@type"] == "BlogPosting")
            breadcrumb = next(s for s in graph if s["@type"] == "BreadcrumbList")
            assert article["headline"] in page.title
            assert article["mainEntityOfPage"] == CANONICAL + path
            assert article["author"]["@type"] == "Organization"
            assert article["author"]["name"] == "Your Optimiser"
            assert article["author"]["@id"] == CANONICAL + "/#organization"
            assert article["publisher"]["@id"] == CANONICAL + "/#organization"
            assert article["isPartOf"]["name"] == "Your Optimiser Blog"
            assert article["mentions"]["@id"] == CANONICAL + "/#application"
            assert "Your Optimiser" in page.meta["description"]
            assert "Your Optimiser" in page.meta["twitter:title"]
            assert page.meta["author"] == "Your Optimiser"
            assert article["datePublished"] in response.text
            assert article["dateModified"] in response.text
            assert breadcrumb["itemListElement"][-1]["item"] == CANONICAL + path
            assert page.meta["og:type"] == "article"
            image_path = article["image"].removeprefix(CANONICAL)
            assert image_path not in cover_paths, "Published pieces reuse a cover URL"
            cover_paths.add(image_path)
            image = client.get(image_path)
            assert image.status_code == 200
            assert image.content[:4] == b"RIFF" and image.content[8:12] == b"WEBP"
            assert len(image.content) < 250_000, "Editorial image exceeds the delivery budget"
            cover_hashes.add(hashlib.sha256(image.content).hexdigest())
            assert image_path in index.text
            assert page.meta["og:image"] == article["image"]
            assert page.meta["twitter:image"] == article["image"]
            assert len(page.headings) == 1
            assert 'aria-label="In this article"' in response.text
            assert "THE TAKEAWAY" in response.text
        assert len(cover_hashes) == 4, "Different cover URLs serve identical image bytes"
        passed.append(
            "All three posts and the guide use distinct cover files, consistently linked "
            "from the separate blog index, article schema and social previews"
        )
        passed.append(
            "Three articles and the existing guide have matching visible facts, "
            "brand identity, authorship, dates, canonicals, article sharing metadata, "
            "breadcrumbs, contents and optimised cover images"
        )
        assert client.get("/blog/an-unpublished-article").status_code == 404
        passed.append("Unpublished article paths return 404")
        method = client.get(ARTICLES[0]).text
        assert "fictional" in method and "local Git" in method
        assert "reports/agent-session.json" in method
        geo = client.get(ARTICLES[2]).text
        assert "Google-specific" in geo and "llms.txt" in geo
        assert "not a ranking feature" in geo
        passed.append("Original repair evidence and engine-specific AI-search limits stay explicit")

        workflow = client.get("/how-it-works").text
        assert 'id="agent-demo"' in workflow
        assert "/agent-at-work.mp4" in workflow and 'preload="none"' in workflow
        video = client.get("/agent-at-work.mp4")
        assert video.status_code == 200 and b"ftyp" in video.content[:16]
        assert len(video.content) == (ROOT / "videos/releases/agent-at-work.mp4").stat().st_size
        captions = client.get("/agent-at-work.vtt")
        assert captions.status_code == 200 and captions.text.startswith("WEBVTT")
        assert "00:00:52.000" in captions.text
        passed.append("Recorded silent demo and captions resolve from the how-it-works page")
    report = {
        "environment": args.base_url,
        "passed": passed,
        "failed": [],
        "unverified": ["Search indexing, rankings, traffic and AI citations"],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
