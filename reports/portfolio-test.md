# Portfolio integration test

Tested October 12, 2026 against the supplied
[Vistrit-Portfolio repository](https://github.com/VistritPandey/Vistrit-Portfolio), downloaded at
revision `f635b055bd303ad5a328d68c14bcb705574e591f`.
Changes were made on separate local test branches. No push, GitHub PR or cloud deployment occurred.

## Results

| Test | Observed result |
|---|---|
| Original React application | Production build passed; real Chromium rendered the name and sections |
| Existing public metadata | Title present; missing description recorded as a finding |
| Controlled missing title | Worker used a settled same-page rendered heading with HTTP/DOM evidence |
| Actual patch verification | Static metadata checks and a real Docker production build passed |
| Commit/merge/served verification | One file committed and merged in the local checkout; served title verified |
| Repeat audit | Completed with zero new findings and no additional commit |
| Real Ollama audit | gemma4:12b returned valid output, chose no additional changes and made zero tool calls |
| React behavior preservation | All files under `src/` retained their original fingerprint |
| Reproducibility rerun | Fresh upstream-based branch and an owned temporary fixture server passed the rules cycle again |
| JSON data push | Changes to the page's data file trigger a page audit |
| Irrelevant README push | Skips page/model work and advances the remembered revision |

Only `public/index.html` differs from the upstream revision. The restored title uses the observed
heading, “Hey I'm Vistrit Pandey!!”. The original biography, resume data, React source, scripts,
controls and styles were retained.

The Ollama run reported **9,054 input tokens**, **548 output tokens** and **156.1 seconds** of
model runtime, with zero API charge. Its valid no-op is not a verified LLM repair. The description
remains absent; no claim is made that the model fixed it or that this one run qualifies the
model for reliable autonomous editing. Electricity/hardware costs and search outcomes remain unknown.

## What the test actually ran

The downloaded React 16/react-scripts 3.4.3 application was compiled using Node 22 in an image
containing its locked dependencies. Dependency installation disabled lifecycle scripts.
Runtime verification used the application's real sandbox: no network, read-only source,
non-root UID 65534, dropped capabilities, 1 CPU, 1 GiB RAM and a writable temporary build area.
The legacy build required `NODE_OPTIONS=--openssl-legacy-provider` and `PUBLIC_URL=/` for local assets.
Existing unused-variable and old Browserslist-data warnings were retained; they were not presented
as newly introduced regressions or silently rewritten.

The HTTP fixture serves the real compiled React assets while refreshing the document head from
`public/index.html`. This explicitly simulates metadata deployment without rebuilding unchanged
React assets on every request. Each proposed source patch still underwent a fresh sandboxed build.
Chromium collection blocked external resources, including external analytics/fonts.

The biography is historical test data. Dates, student status, roles, addresses and affiliations
were not independently verified as current or rewritten into new claims.

## Reproduce

```sh
uv sync --locked --extra browser
uv run playwright install chromium
# Start Docker and Ollama separately.
uv run python scripts/test_portfolio.py --model gemma4:12b
```

For rules only, use `--skip-model`. To reuse already compiled preview assets and the verification
image, add `--reuse-build`. Each run creates a fresh branch from the downloaded upstream revision
and a temporary loopback HTTP server; existing committed experiments remain on their branches.
Uncommitted work in the local checkout prevents a run.

To inspect the resulting local site afterward:

```sh
uv run python scripts/portfolio_fixture.py \
  --repository .data/portfolio-test --build .data/portfolio-built --port 8811
```

Machine-readable evidence: [full experiment](portfolio-test.json),
[rules-only reproducibility rerun](portfolio-replay.json), and
[interactive guide checks](guide-test.json). The full offline suite currently passes **154 tests**.
Real cloud events, GitHub permissions, PR publication, indexing, rankings, citations and
conversions are outside this local experiment's verified scope.

The portfolio exercise also exposed a missing `.json` invalidation path. The scanner now treats
unknown JSON changes as potentially relevant page data. Completed no-route jobs advance the
last revision while retaining the previous page report. Both have offline regression tests and
real local push-event coverage in the reproducibility run.
