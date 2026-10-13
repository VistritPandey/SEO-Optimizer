# Recorded worker demo

[Watch the 1080p demo](assets/optimizer-demo.mp4). The silent video runs for about 53 seconds.
The terminal segment plays at 1.5× speed; the browser segment plays at normal speed.

The demo uses Remotion to frame recordings of actual commands and browser interactions.
It does not animate invented command results. `scripts/record_demo.py` runs commands through
an OS pseudo-terminal, streams their stdout/stderr to a local terminal view, and records that
view with Playwright. It also records clicks in the running application's `/guide`.

## What is demonstrated

| Approximate time | Scene | Evidence |
|---|---|---|
| 0–6 seconds | Introduce the controlled experiment | Downloaded portfolio, deliberately removed title, local branch |
| 6–27 seconds | Actual command recording | Portfolio runner, `git show`, full `pytest` run |
| 27–37 seconds | Explain the before/after | Exact title insertion; metadata and isolated React build checks |
| 37–46 seconds | Actual guide interaction | Observe, assess, verify, publish, confirm and remember steps |
| 46–53 seconds | Recorded outcomes | 154 passing tests, one verified fix, no repeat-audit commit |

This recording uses rules, with `--skip-model`. It makes no claim about model reasoning quality.
The portfolio's compiled React assets are served locally, with metadata edits reflected from
`public/index.html`. That fixture simulates deployment for metadata changes. It does not
establish a live GitHub PR, a Vercel deployment, or improved search rankings.

The controlled repair passed an isolated production build. The runner then merged the fix
locally and fetched the served page to verify it. The repeat audit created no additional commit;
a JSON data event was audited and an unrelated README event skipped model work.
No React application source was changed and nothing was pushed to GitHub.

## Inspect the evidence

- [Recorded command arguments, exit codes and timestamped output](../videos/public/capture.json)
- [Selected run evidence and exact test/merge revisions](../videos/public/demo.json)
- [Unaccelerated terminal recording](../videos/public/terminal.mp4)
- [Unaccelerated guide recording](../videos/public/guide.mp4)
- [Composition](../videos/src/Demo.tsx) and [renderer](../videos/scripts/render.mjs)

The explanatory result cards read `demo.json`. Its preparation script validates the recorded
command exits and the portfolio result before generating the cards.

## Render or edit the existing recording

Requires Node.js 22 or newer. From the repository root:

```sh
cd videos
npm ci
npm run typecheck
npm run render
# Open the editable Remotion composition:
npm run studio
```

`npm run render` writes the MP4, five full-resolution stills, and render metadata to
`videos/out/`. Those intermediate outputs and Remotion's browser cache are ignored by Git.
The committed recordings allow editing/rendering without rerunning the portfolio test.

## Capture a fresh run

Install the Python browser extra and Chromium, and keep Docker running. The portfolio test
must have already produced its build image and compiled assets:

```sh
uv sync --locked --extra browser
uv run playwright install chromium
uv run python scripts/test_portfolio.py --skip-model
```

Start the app in another terminal (the guide is public):

```sh
uv run seo-optimizer serve --host 127.0.0.1 --port 8787
```

Then record the fresh terminal execution and guide interactions. FFmpeg and ffprobe must be
available on `PATH`:

```sh
uv run python scripts/record_demo.py --guide-url http://127.0.0.1:8787/guide
ffmpeg -y -i .data/demo-recording/terminal.webm -an \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p videos/public/terminal.mp4
ffmpeg -y -i .data/demo-recording/guide.webm -an \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p videos/public/guide.mp4
node videos/scripts/prepare.mjs
cd videos
npm run typecheck
npm run render
```

The recorder starts a new local test branch through the existing portfolio runner. It refuses
uncommitted work in the test checkout. The guide URL can use another port. Raw WebM recordings,
intermediate screenshots and the full fresh-run JSON remain under ignored `.data/demo-recording/`.

Copy `videos/out/optimizer-demo.mp4` and `videos/out/poster.png` into `docs/assets/` when
publishing a refreshed README demo. Source recordings and their evidence should be updated
together. Remotion's [render documentation](https://www.remotion.dev/docs/render) describes
alternative export options.
