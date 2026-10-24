FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md LICENSE ./
COPY LICENSES/ ./LICENSES/
COPY src ./src
RUN pip install --no-cache-dir ".[hosted]"
RUN useradd --create-home --uid 10001 optimizer && mkdir /data && chown optimizer /data
USER optimizer
ENV OPT_DATA_DIR=/data PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["your-optimiser", "serve", "--host", "0.0.0.0", "--port", "8000"]
