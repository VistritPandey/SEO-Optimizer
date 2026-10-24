FROM node:24.12-bookworm-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
COPY integrations/framer/package*.json /bridge/
RUN cd /bridge && npm ci --ignore-scripts --no-audit --no-fund
ARG NEXT_PUBLIC_FIREBASE_API_KEY
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
ARG NEXT_PUBLIC_FIREBASE_APP_ID
ARG NEXT_PUBLIC_SITE_URL
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends nginx git ca-certificates libstdc++6 libatomic1 tini && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node
COPY pyproject.toml README.md uv.lock LICENSE ./
COPY LICENSES/ ./LICENSES/
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
COPY src/ ./src/
COPY integrations/framer/bridge.mjs /app/integrations/framer/bridge.mjs
COPY --from=web /bridge/node_modules /app/integrations/framer/node_modules/
RUN uv sync --locked --no-dev --extra hosted --extra browser && uv run --no-sync playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/* && chmod -R a+rX /root/.cache/ms-playwright && mv /root/.cache/ms-playwright /opt/playwright
COPY --from=web /web/.next/standalone /app/web/
COPY --from=web /web/.next/static /app/web/.next/static/
COPY --from=web /web/public /app/web/public/
COPY deploy/combined-entrypoint.py deploy/combined-nginx.conf /app/deploy/
RUN useradd --create-home --uid 10001 optimizer && chown -R optimizer:optimizer /app/web
USER optimizer
ENV PATH="/app/.venv/bin:$PATH" PLAYWRIGHT_BROWSERS_PATH=/opt/playwright PYTHONUNBUFFERED=1 NODE_ENV=production OPT_FRAMER_BRIDGE=/app/integrations/framer/bridge.mjs OPT_COMBINED_DEPLOYMENT=1 OPT_BACKEND_URL=http://127.0.0.1:8000 OPT_DATA_DIR=/tmp/your-optimiser PORT=8080
EXPOSE 8080
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "/app/deploy/combined-entrypoint.py"]
