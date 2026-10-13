# A real model repair, recorded

[Watch the 70-second 1080p demo](assets/optimizer-demo.mp4).
The fictional Cedar Workshop storefront is the only website used in the public video.
Personal repositories and their reports remain in ignored local storage.

The video follows a customer into a broken collection link, shows real Gemini inspection and
patch proposals, explains the exact changed source, and returns to the working storefront.
It uses actual Playwright browser recordings and terminal excerpts. The tool timeline replays
recorded executed calls with condensed timing; it is not a live inference screen.
Patch cards and metrics are extracted from the saved run rather than authored answers.

## What the model actually did

The recorded repair uses `gemini-3.8-flash` through Google GenAI Python SDK 2.30.0.
The provider made six inference requests and executed thirteen tools. It read repository files,
loaded relevant private check guidance, staged replacements for two files, and checked them.

| Source | Before | Model-generated repair |
|---|---|---|
| `web/index.html` | Collection CTA points at a confirmed 404 | Replace it with the observed working `/shop/` route |
| `web/index.html` | No description | Describe the existing product using visible content and supplied facts |
| `web/products/cedar-lamp/index.html` | Two conflicting canonicals | Retain the product's self-referential canonical |
| `web/products/cedar-lamp/index.html` | Invalid JSON-LD; declared price USD 129.00 | Repair JSON and align the offer with the visible and supplied USD 89.00 price |

The application checked policy and exact source, ran semantic checks in a network-isolated
Docker container, independently checked the final files, committed one file at a time, merged
locally, and fetched the served pages again. The before/after audit changed from four confirmed
defects to zero. One automated commerce comparison remains unresolved because the normal
crawler lacks the required visible-offer observations. Owner-controlled semantic checks
independently confirmed the synthetic price; this does not erase that coverage limitation.

The original private preview and training opt-out remained byte-for-byte unchanged.
The repeat **model** audit completed without another edit or commit. It made six additional
inference requests, including unsuccessful probes for an uncollected preview and missing
sitemap; those failures remain visible in the run record. A real local documentation branch
was then merged into `main`, its push job was processed, and it triggered zero inference requests.
That last event is a local queue simulation, not an authenticated live GitHub webhook.

## Video chapters

| Time | What is shown |
|---|---|
| 0–5s | The fictional storefront and model |
| 5–13s | Actual browser click into the 404 |
| 13–19s | Source and page evidence |
| 19–28s | Replay of the executed model tool trace |
| 28–42s | Exact link, description, canonical and offer changes |
| 42–49s | Actual terminal excerpts and independent verification steps |
| 49–59s | Actual browser navigation after the repair |
| 59–70s | Outcomes, repeat audit and merged-documentation control |

This is a controlled integration case, not a representative model benchmark. Two complete
repair runs succeeded. Four earlier development runs were blocked by token or tool-batch
limits; their records are retained. They did not publish model changes. Rankings, traffic,
conversions, broad content quality and live GitHub/cloud deployment remain unmeasured.
The recorded primary inference used 61,398 input tokens and 9,033 output tokens, including
reported thinking tokens. API cost is unknown because verified pricing was not configured;
unknown cost is not zero cost.

## Inspect the actual evidence

- [Recorded repair and controls](../videos/public/agent-run.json)
- [First successful repair](../reports/agent-demo-repair.json)
- [Full captured command output and timestamps](../videos/public/capture.json)
- [Selected video data](../videos/public/demo.json)
- [Terminal excerpt source offsets](../videos/public/highlights.json)
- [Model-generated diff](../videos/public/agent-run.json) and [composition](../videos/src/Demo.tsx)

The service's private check instructions are used internally. Persisted guidance tool results
contain identifiers rather than the private instruction text. The synthetic runner instruments
real provider calls; it does not substitute a fake model or supply expected replacement strings.
The separate owner checker asserts observable outcomes and preservation rules.

## Run the synthetic agent test

Requires Python 3.12, uv, Docker, the browser extra and installed Chromium. Put your own
`GOOGLE_API_KEY` or `GEMINI_API_KEY` in the ignored `.env`; the key is never printed or recorded.

```sh
uv sync --locked --extra browser
uv run playwright install chromium
docker pull python:3.12-slim
uv run python scripts/demo_agent.py --provider google --model gemini-3.8-flash
```

The runner creates a new repository and account under ignored `.data/agent-demo/`, starts its
own loopback server, and runs the actual worker. It records before/after browser videos and
anonymous evidence under `videos/public/`. The demo explicitly permits the evidenced static
HTML content edit and supplies fictional owner facts. Its limits are 12 tool turns, up to 16
calls per turn, 150,000 cumulative inference tokens, and 600 seconds per job. Default application
limits stay at eight calls per turn and 100,000 cumulative tokens. Intermediate inspection and
verification failures cannot grant publication authority; successful source reads and independent
policy/build/deployment checks are still required.

For Ollama, use `--provider ollama --model YOUR_LOCAL_MODEL`; outcomes remain unverified until
that provider completes this case. Personal-site tests use `scripts/test_portfolio.py` with a
privately supplied repository URL and default to an ignored report path. Do not commit those
reports or recordings.

## Record and render

The full recorder runs the real model case again, including its repeat and merged-documentation
controls. FFmpeg, ffprobe and Node.js 22 or newer must be installed:

```sh
uv run python scripts/record_demo.py
ffmpeg -y -i videos/public/before.webm -an -c:v libx264 -crf 18 \
  -pix_fmt yuv420p videos/public/before.mp4
ffmpeg -y -i videos/public/after.webm -an -c:v libx264 -crf 18 \
  -pix_fmt yuv420p videos/public/after.mp4
node videos/scripts/highlights.mjs
node videos/scripts/prepare.mjs
cd videos
npm ci
npm run typecheck
npm run render
# Edit and preview the composition:
npm run studio
```

Committed MP4 captures allow rendering without another API call. The recorder's full terminal
WebM and local control databases remain ignored. Rendering writes the MP4, nine scene stills
and render metadata to ignored `videos/out/`. Copy the final MP4 and `poster.png` to
`docs/assets/optimizer-demo.mp4` and `docs/assets/demo-poster.png` when refreshing the README.

See the official [Google GenAI SDK](https://github.com/googleapis/python-genai),
[Gemini function-calling guide](https://ai.google.dev/gemini-api/docs/function-calling), and
[Remotion rendering documentation](https://www.remotion.dev/docs/render) for API/export details.
