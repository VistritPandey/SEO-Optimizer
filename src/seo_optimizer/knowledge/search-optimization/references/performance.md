# Performance and page experience

Checks: perf.cwv, perf.media, perf.navigation. Sources: google-cwv, web-vitals, google-images, google-ai, google-js in the [registry](../sources.json).

## Measurement evidence

Core Web Vitals assess loading (LCP), interaction responsiveness (INP) and visual stability (CLS). For good field experience, use the documented 75th-percentile thresholds: LCP at or below 2.5 seconds, INP at or below 200 ms and CLS at or below 0.1. Preserve the metric definition, collection window, device and URL/origin scope; missing or sparse field data remains unknown.

A lab performance score is a diagnostic snapshot, not field INP, a guaranteed ranking score or a substitute for real users. A screenshot measures none of these metrics. Use comparable runs to inspect root causes, not repeated runs until one yields a favorable score. Attribute a regression only after checking test variance and unrelated changes.

## Select interventions from the bottleneck

Use loading traces to locate slow primary content, blocking work or excessive media. For layout shifts, identify late dimension changes or inserted content. For interaction delays, inspect main-thread work and the affected task. Avoid adding lazy loading indiscriminately to the main visible image, hiding useful content, or removing functionality for the score.

Images should support the page's content, have appropriate sizes/formats, preserve intended aspect ratio and use meaningful contextual alternatives. Decorative images can correctly use empty alt text. Never invent descriptions of unseen imagery or stuff keywords into alternatives.

## Visual reasoning

Vision may help identify overlays, clipped text, mobile layout problems or mismatched media. Pair the screenshot with the relevant DOM/accessibility structure and interaction trace. State the viewport and reproduction steps. A stylistic dislike is not a search defect.

Check keyboard/accessible navigation and the visibility of primary content against actual user tasks. Preserve branding and interaction behavior. Verification uses comparable browser runs and task checks; field metrics need time to reflect deployed changes. Passing all Web Vitals does not guarantee search rankings.
