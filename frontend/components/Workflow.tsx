"use client";

import { useEffect, useState } from "react";

const stages = [
  "Website updated",
  "Checking the change",
  "What needs attention",
  "Review the fix",
  "Check the result",
  "Keep watching",
];
const broken = [
  [
    "Your team ships a new homepage.",
    "The new design looks good. But the collection button now leads to a missing page, and the search description has disappeared.",
  ],
  [
    "Your Optimiser checks what changed.",
    "The agent reads the changed page, follows its links and compares it with the website. It checks for a real problem before preparing an edit.",
  ],
  [
    "Two small changes. Two real problems.",
    "Visitors cannot reach the collection from the main button. Search engines have also lost the page’s description. The design and product copy are still fine.",
  ],
  [
    "A fix, ready for your review.",
    "The agent restores the working collection link and writes a description from the existing page content. It tests the changes and prepares a pull request—your team’s reviewable update.",
  ],
  [
    "Check the website after the fix goes live.",
    "Approval is not the finish line. The agent checks the served page again: the button opens the collection and the search description is present.",
  ],
  [
    "The next update? Still covered.",
    "Your team changes the spacing. The agent checks again, finds no SEO problem and leaves the page alone. Regular checks continue between website updates.",
  ],
];
const healthy = [
  [
    "Your team refreshes the design.",
    "A little more breathing room around the homepage heading. The links, page description and product information are unchanged.",
  ],
  [
    "The same careful check.",
    "Your Optimiser checks the affected page and confirms that visitors can still reach the collection and search information remains intact.",
  ],
  [
    "Everything checked still works.",
    "The collection opens, the description is present and the page remains available. There is no confirmed problem to fix.",
  ],
  [
    "No unnecessary changes.",
    "The agent leaves the design alone. No speculative rewrite. No extra pull request for your team to review.",
  ],
  [
    "A clear record of the check.",
    "You can see what was checked and why no change was needed. A healthy update stays a healthy update.",
  ],
  [
    "Ready for the next website update.",
    "Your team carries on building. Your Optimiser keeps checking the website as it changes, with regular checks in between.",
  ],
];

export function Workflow() {
  const [scenario, setScenario] = useState<"broken" | "healthy">("broken");
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [comparison, setComparison] = useState<"before" | "after">("after");
  const [pageView, setPageView] = useState<"home" | "collection" | "missing">(
    "home",
  );
  const fixed = scenario === "healthy" || step >= 4;
  const story = scenario === "broken" ? broken : healthy;
  useEffect(() => {
    if (!playing) return;
    // A review is an explicit choice, even in the demonstration.
    if (step === 5 || (step === 3 && scenario === "broken")) {
      setPlaying(false);
      return;
    }
    const timer = setTimeout(() => {
      setStep((value) => value + 1);
      setPageView("home");
    }, 4200);
    return () => clearTimeout(timer);
  }, [playing, step, scenario]);
  function choose(value: "broken" | "healthy") {
    setScenario(value);
    setStep(0);
    setPlaying(false);
    setPageView("home");
    setComparison("after");
  }
  function advance() {
    setStep((value) => Math.min(value + 1, 5));
    setPageView("home");
  }
  return (
    <div className="customer-demo" data-step={step} data-scenario={scenario}>
      <div className="demo-toolbar">
        <div>
          <span className="demo-live-dot" /> Interactive example{" "}
          <small>· fictional store</small>
        </div>
        <div
          className="demo-scenarios"
          role="group"
          aria-label="Choose a website update"
        >
          <button
            aria-pressed={scenario === "broken"}
            onClick={() => choose("broken")}
          >
            Something breaks
          </button>
          <button
            aria-pressed={scenario === "healthy"}
            onClick={() => choose("healthy")}
          >
            Nothing breaks
          </button>
        </div>
      </div>
      <div className="demo-layout">
        <div className="demo-website">
          <div className="demo-browser">
            <span>● ● ●</span>
            <span>
              cedar.example /{" "}
              {pageView === "home"
                ? "home"
                : pageView === "collection"
                  ? "collection"
                  : "missing-page"}
            </span>
            <span>↗</span>
          </div>
          <div className="demo-store-nav">
            <strong>cedar.</strong>
            <span>Thoughtful lighting</span>
          </div>
          {pageView === "home" ? (
            <div className="demo-store-home">
              <div className="demo-store-copy">
                <span className="eyebrow">QUIET OBJECTS. WARM SPACES.</span>
                <h3>
                  Light that feels
                  <br />
                  <em>like home.</em>
                </h3>
                <p>
                  Thoughtful lighting for everyday spaces. Solid cedar, soft
                  linen, a little warmth.
                </p>
                <button
                  className="demo-shop-button"
                  onClick={() => setPageView(fixed ? "collection" : "missing")}
                >
                  Explore the collection ↗
                </button>
                <small>Try the button to see where it leads.</small>
              </div>
              <div
                className="demo-lamp"
                aria-label="Illustration of a cedar desk lamp"
                role="img"
              >
                <div className="lamp-glow" />
                <div className="lamp-shade" />
                <div className="lamp-stem" />
                <div className="lamp-base" />
              </div>
            </div>
          ) : (
            <div className={"demo-destination " + pageView}>
              {pageView === "missing" ? (
                <>
                  <span className="demo-error-code">404</span>
                  <h3>This collection cannot be found.</h3>
                  <p>
                    The homepage looks fine. The visitor’s next step is broken.
                  </p>
                </>
              ) : (
                <>
                  <span className="eyebrow">THE COLLECTION</span>
                  <h3>A little light for everyday life.</h3>
                  <div className="demo-product">
                    <span>◒</span>
                    <div>
                      <strong>Cedar Desk Lamp</strong>
                      <p>Solid cedar · linen shade · USD 89.00</p>
                    </div>
                    <span className="pill">In stock</span>
                  </div>
                </>
              )}
              <button className="text-link" onClick={() => setPageView("home")}>
                ← Back to the homepage
              </button>
            </div>
          )}
          <div className="demo-search-card">
            <span className="eyebrow">PAGE INFORMATION FOR SEARCH</span>
            <strong>Cedar Workshop — Thoughtful lighting</strong>
            <p className={!fixed ? "demo-missing" : ""}>
              {fixed
                ? "Thoughtful lighting for everyday spaces. Meet the Cedar Desk Lamp: a solid cedar base, linen shade, and warm 2700K light."
                : "Page description missing after the update"}
            </p>
            <small>
              A page description helps explain the page; search engines choose
              the displayed snippet.
            </small>
          </div>
        </div>
        <div className="demo-agent">
          <div className="demo-agent-heading">
            <span className="demo-agent-mark">y</span>
            <div>
              <strong>Your Optimiser</strong>
              <small>
                {step === 5
                  ? "Watching for the next update"
                  : "Looking after this website"}
              </small>
            </div>
            <span className="demo-status">
              {step >= 4 ? "Checked" : "Active"}
            </span>
          </div>
          <ol className="demo-timeline" aria-label="Demo progress">
            {stages.map((label, index) => (
              <li key={label}>
                <button
                  aria-current={step === index ? "step" : undefined}
                  onClick={() => {
                    setStep(index);
                    setPlaying(false);
                    setPageView("home");
                  }}
                >
                  <span>{index < step ? "✓" : index + 1}</span>
                  {scenario === "healthy" && index === 3
                    ? "Leave the page alone"
                    : label}
                </button>
              </li>
            ))}
          </ol>
          <div className="demo-story" aria-live="polite">
            <span className="eyebrow">
              {String(step + 1).padStart(2, "0")} / 06
            </span>
            <h3>{story[step][0]}</h3>
            <p>{story[step][1]}</p>
          </div>
          {step === 2 && scenario === "broken" && (
            <div className="demo-findings">
              <span>
                ↗ Collection link <strong>Missing page</strong>
              </span>
              <span>
                ≡ Search description <strong>Missing</strong>
              </span>
            </div>
          )}
          {step === 3 && scenario === "broken" && (
            <div className="demo-change-card">
              <div role="group" aria-label="Compare the proposed fix">
                <button
                  aria-pressed={comparison === "before"}
                  onClick={() => setComparison("before")}
                >
                  Before
                </button>
                <button
                  aria-pressed={comparison === "after"}
                  onClick={() => setComparison("after")}
                >
                  Proposed fix
                </button>
              </div>
              <dl>
                <dt>Collection button</dt>
                <dd>
                  {comparison === "before"
                    ? "/collections/lighting/ → missing page"
                    : "/shop/ → existing collection"}
                </dd>
                <dt>Page description</dt>
                <dd>
                  {comparison === "before"
                    ? "Missing"
                    : "Restored from existing page content"}
                </dd>
              </dl>
              <span className="demo-check">
                ✓ Page checks passed · ready to review
              </span>
            </div>
          )}
          {step >= 4 && (
            <div className="demo-result">
              <span>✓</span>
              <div>
                <strong>
                  {scenario === "healthy"
                    ? "No fix needed"
                    : "Collection opens. Description restored."}
                </strong>
                <small>
                  {step === 5
                    ? "Next design update checked · no unnecessary edit"
                    : scenario === "healthy"
                      ? "Design kept exactly as your team intended"
                      : "Page checked again after the update"}
                </small>
              </div>
            </div>
          )}
          <div className="demo-controls">
            <button
              className="button"
              onClick={() => {
                if (step === 5) choose(scenario);
                else advance();
              }}
            >
              {step === 0
                ? "Publish example update →"
                : step === 3 && scenario === "broken"
                  ? "Approve example fix →"
                  : step === 5
                    ? "Try again ↺"
                    : "Next step →"}
            </button>
            {step !== 5 && (
              <button
                className="demo-play"
                aria-pressed={playing}
                onClick={() => setPlaying(!playing)}
              >
                {playing ? "Pause" : "Play walkthrough"}
              </button>
            )}
          </div>
        </div>
      </div>
      <div className="demo-caption">
        <span>Update → check → fix when needed → verify → keep watching.</span>
        <small>
          Illustrated walkthrough based on a recorded repair. No live website is
          changed here.
        </small>
      </div>
    </div>
  );
}
