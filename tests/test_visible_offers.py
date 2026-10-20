"""Browser observations distinguish visible facts from hidden or ambiguous prices."""

import httpx
import pytest

from seo_optimizer.crawler import Crawler, capture_browser


@pytest.mark.integration
@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1"])
@pytest.mark.parametrize(
    "price,expected",
    [
        ('<div class="price">USD 89.00</div>', "89.00"),
        (
            '<div hidden><div class="price">USD 129.00</div></div>'
            '<div class="price">USD 89.00</div>',
            "89.00",
        ),
        ('<div style="opacity:0"><div class="price">USD 89.00</div></div>', None),
        ('<div class="price">USD 89.00</div><div class="price">USD 129.00</div>', None),
        ('<div class="price" data-price="89">USD 129.00</div>', "129.00"),
    ],
)
def test_visible_offer_uses_actual_browser_text(tmp_path, price, expected):
    pytest.importorskip("playwright")
    html = (
        f"<html><head><title>Product</title></head><body><main>{price}"
        '<div class="stock">In stock</div></main></body></html>'
    )
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, text=html, headers={"Content-Type": "text/html"})
        )
    ) as client:
        crawler = Crawler("http://127.0.0.1/", allow_private=True, client=client)
        evidence = capture_browser(
            "http://127.0.0.1/", crawler, "tenant", "project", "production", tmp_path
        )
    dom = next(e for e in evidence if e.kind == "dom")
    offer = dom.data["visible_offer"]
    if expected is None:
        assert offer is None
    else:
        assert offer["price"] == expected and offer["priceCurrency"] == "USD"


@pytest.mark.integration
@pytest.mark.enable_socket
@pytest.mark.allow_hosts(["127.0.0.1"])
def test_browser_collects_visible_media_and_navigation_without_claiming_mobile(tmp_path):
    pytest.importorskip("playwright")
    html = (
        "<html><head><title>Guide</title></head><body><nav>"
        '<a href="/shop" aria-label="Shop lights">Shop</a>'
        '<a hidden href="/hidden">Hidden</a></nav><main>'
        '<img src="/missing.png" alt="Workshop lamp" width="100" height="80">'
        '<img hidden src="/secret.png" alt="Hidden"><h1>Guide</h1></main></body></html>'
    )
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200 if request.url.path == "/" else 404,
                text=html if request.url.path == "/" else "Missing",
                headers={"Content-Type": "text/html"},
            )
        )
    ) as client:
        evidence = capture_browser(
            "http://127.0.0.1/",
            Crawler("http://127.0.0.1/", True, client=client),
            "tenant",
            "project",
            "production",
            tmp_path,
        )
    data = next(e.data for e in evidence if e.kind == "dom")
    assert len(data["media_observations"]) == 1
    assert data["media_observations"][0]["naturalWidth"] == 0
    assert data["media_observations"][0]["alt"] == "Workshop lamp"
    nav = data["navigation_observations"]
    assert len(nav["links"]) == 1 and nav["links"][0]["aria_label"] == "Shop lights"
    assert "mobile behavior need testing" in nav["limits"]
