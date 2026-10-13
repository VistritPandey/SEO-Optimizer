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
