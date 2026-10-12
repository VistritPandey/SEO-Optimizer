"""Vercel ASGI entrypoint. The worker runs separately."""

from seo_optimizer.web import create_app

app = create_app()
