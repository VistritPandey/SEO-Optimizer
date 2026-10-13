# Your Optimiser customer walkthrough

[Watch the silent customer demo](assets/your-optimiser.mp4).

The landing page has an interactive version of the same journey. Visitors can choose an update
that breaks something or a healthy design update, try the collection button, inspect the proposed
before/after, approve the example fix and check the result. Playback stops at review; it never
approves a change automatically. The demo does not change a visitor’s website.

The film is for potential customers. It explains ongoing SEO care through one concrete story:

1. A team merges a homepage update.
2. The agent checks the affected page and confirms a broken collection link and missing description.
3. It restores the existing working destination and derives a description from existing content.
4. The proposed change passes checks and is presented for the team’s review.
5. After deployment, the agent checks the served page again.
6. A subsequent healthy design update needs no fix, and monitoring continues.

Installation, model brands, infrastructure and development-test counts are intentionally kept in
the developer documentation. The customer story shows the outcome and the decisions behind it.

## What is recorded and what is illustrated

The source repairs and post-merge collection screenshot come from the recorded fictional Cedar
Workshop run. Actual model inference read source files, staged patches, ran isolated checks,
made local Git commits and fetched the served pages. Four confirmed fixture defects became zero;
the film focuses on the two homepage fixes. Product-data repairs happened in that run but are
outside this customer story. See [recorded tool events](../videos/public/your-proof.json) and
[the repair evidence](../reports/onboarding-repair.json).

The homepage merge, approval card, spacing-only update and recurring activity are illustrations
of the workflow, not footage of a live customer GitHub PR or a production deployment. The film
labels the journey as an illustrated example. The collection image is from the actual local
post-repair page. The interactive demo has explicit example controls and matching disclosure.
No new model inference was needed to build this presentation.

The film has no audio track. Always-visible on-screen captions explain each step.
The video makes no claim of ranking,
traffic, conversion or consumer-engine citation uplift. A missing description is a finding about
page information; search engines may choose another snippet. The successful link repair shows
that visitors can reach the collection, not that rankings increased.

## Verification and reproduction

[Browser checks](../reports/customer-demo.json) cover the broken and healthy paths, comparison,
approval, post-fix navigation, playback stopping at review, keyboard controls, mobile layout and
agreement with the recorded source patch. They exercise the real Next frontend while the example
workflow remains illustrative. Live GitHub and production search outcomes remain unverified.

Start the frontend, then run `uv run --no-sync python scripts/test_customer_demo.py --url
http://localhost:3000` (or the port you started). Browser dependencies are documented in the hosted
setup guide. Run `npm run typecheck --prefix videos` and `node videos/scripts/render-your.mjs` to
render the silent film. No speech tools or voice assets are required.

The composition is 1920×1080 at 30 fps. Scene timing and caption text are defined
in `videos/public/customer/story.json`. The renderer also produces stills and an optional English
caption track. Both published MP4 copies are checked with FFprobe to confirm no audio stream.
The landing page loads the video only when requested, with controls and captions. All public
assets use the fictional fixture; personal portfolio content and credentials are excluded.
