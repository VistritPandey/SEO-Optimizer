"""Hosted ASGI entrypoint. Durable jobs run in a separate worker."""

import os

from seo_optimizer.web import create_app

if os.getenv("VERCEL"):
    os.environ.setdefault("OPT_ENV", "production")
    os.environ.setdefault("OPT_DATA_DIR", "/tmp/optimizer")

app = create_app()
