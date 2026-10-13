# Optimization workflow demonstration

The new 90-second, 1920 × 1080 Remotion video presents the optimization service through actual
website problems, tool actions and independently verified results. It extends the earlier
technical recording with the working research dashboard, a supported original-content task,
a real Docker check, Git publication, served-page verification and model-comparison evidence.

Watch [the workflow video](assets/optimizer-workflow.mp4).

| Time | Evidence shown |
|---|---|
| 0–6 s | The application's research workspace and complete observation/publication loop |
| 6–14 s | Recorded broken shopping path and contradictory product declarations |
| 14–23 s | Actual terminal inspection and native model tools from the technical recording |
| 23–31 s | Verified navigation, canonical, product data and private-policy preservation |
| 31–41 s | Real dashboard brief with reviewed owner material and explicitly synthetic search inputs |
| 41–52 s | Autonomous audit → strategy → content jobs, actual Docker output and local commit |
| 52–61 s | Recorded before/after page: the supported owner passage is now served |
| 61–80 s | Repository repair comparison and controls, including unsuccessful attempts |
| 80–90 s | What was verified and which live search outcomes remain unmeasured |

The fictional store and original-content fixtures contain no personal portfolio material.
The content demonstration's notebook and query counts are synthetic and visibly labeled.
The worker publishes that supported passage deterministically: it makes zero model calls.
The technical recording separately contains actual native model inference and source changes.
Explanatory scenes and tables are generated from saved evidence; terminal/browser clips are
actual captures. Waiting is trimmed in the older terminal highlight. There is no fabricated
terminal activity, GitHub upload, real search traffic gain or invented citation uplift.

The comparison uses a frozen anonymous repository, four repair targets and separate healthy /
irrelevant-merge controls. A timeout is a failed completion, not proof of an incorrect edit.
The full harness adds private knowledge and rule evidence. The minimal runner retains common
source, fact, privacy, behavior and verification gates. Treat this development experiment as a
way to find runtime/model weaknesses, not a statistically powered claim about every model.

## Reproduce

```sh
uv sync --locked --extra browser
uv run playwright install chromium
uv run python scripts/demo_growth.py
uv run seo-optimizer benchmark-repairs --output .data/repair-benchmark/run.json
node videos/scripts/prepare-growth.mjs .data/repair-benchmark/run.json
npm --prefix videos ci
npm --prefix videos run typecheck
node videos/scripts/render-growth.mjs
```

Docker needs the configured verification image; the local model must already be installed.
The paid provider uses the ignored `.env` credential. The old technical assets can be recreated
with `scripts/record_demo.py`, `videos/scripts/prepare.mjs`, and `videos/scripts/highlights.mjs`;
see [the technical recording guide](demo-video.md).

The new content capture is [growth-run.json](../videos/public/growth-run.json); the video table
and verification excerpts come from [growth-proof.json](../videos/public/growth-proof.json).
Full model qualification and failed development observations are retained in the reports.
The [research guide](research-workspace.md) documents how actual account measurements enter
this workflow and why a verified source change is not automatically a search outcome.
