"use client";

import { useCallback, useState } from "react";
import { m, useReducedMotion } from "motion/react";
import { DemoPlayback } from "./DemoPlayback";
import { useDemoPlayback } from "./useDemoPlayback";

const stages = ["Update", "Inspect", "Propose", "Verify"];
const titles = [
  "Your team ships a new homepage.",
  "The agent follows the evidence.",
  "A small fix. A clear review.",
  "Checked live. Back to watching.",
];
const descriptions = [
  "A fresh design goes live. Two small search details slip through.",
  "It checks the affected page and destination before proposing an edit.",
  "Restore the existing destination and description. Your team stays in control.",
  "After approval and deployment, the agent checks what visitors actually receive.",
];

export function HeroWorkflow() {
  const [stage, setStage] = useState(0);
  const reducedMotion = useReducedMotion();
  const advance = useCallback(
    () => setStage((value) => (value + 1) % stages.length),
    [],
  );
  const playback = useDemoPlayback<HTMLElement>(stage, 5200, advance);
  return (
    <aside
      ref={playback.ref}
      {...playback.interaction}
      data-stage={stage}
      className="hero-workflow"
      aria-label="Interactive SEO workflow example"
    >
      <div className="hero-workflow-label">
        <span>ONE UPDATE, FOLLOWED THROUGH</span>
        <span className="workflow-example">Illustrated example</span>
      </div>
      <DemoPlayback
        name="hero example"
        step={stage}
        total={4}
        duration={5200}
        playing={playback.playing}
        running={playback.running}
        toggle={playback.toggle}
      />
      <div
        className="workflow-steps"
        role="group"
        aria-label="Explore the workflow"
      >
        {stages.map((label, index) => (
          <button
            key={label}
            type="button"
            aria-pressed={stage === index}
            onClick={() => setStage(index)}
            className={
              stage === index ? "current" : stage > index ? "complete" : ""
            }
          >
            <span aria-hidden="true">
              {stage > index ? "✓" : `0${index + 1}`}
            </span>
            {label}
          </button>
        ))}
      </div>
      <div
        className="workflow-scene"
        aria-live={playback.playing ? "off" : "polite"}
        aria-atomic="true"
      >
        <h2>{titles[stage]}</h2>
        <p>{descriptions[stage]}</p>
        <m.div
          key={stage}
          className="workflow-artifact"
          initial={{
            opacity: reducedMotion ? 1 : 0,
            y: reducedMotion ? 0 : 6,
          }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: reducedMotion ? 0 : 0.16 }}
        >
          {stage === 0 && (
            <>
              <div className="artifact-bar">
                <span className="artifact-dots" aria-hidden="true">
                  ● ● ●
                </span>
                <span>store.example /</span>
                <span>Homepage</span>
              </div>
              <div className="artifact-page">
                <span className="eyebrow">THE NEW COLLECTION</span>
                <strong>
                  A little light.
                  <br />
                  <em>A fresh start.</em>
                </strong>
                <span className="artifact-shop">Shop the collection ↗</span>
              </div>
              <div className="artifact-foot">
                <span className="dot" /> New homepage deployed{" "}
                <span>Ready to check</span>
              </div>
            </>
          )}
          {stage === 1 && (
            <div className="artifact-checks">
              <div>
                <span className="check-warn" aria-hidden="true">
                  !
                </span>
                <section>
                  <strong>Shopping link leads nowhere</strong>
                  <small>/collections/lighting/ returns 404</small>
                </section>
                <span className="check-label">Finding</span>
              </div>
              <div>
                <span className="check-warn" aria-hidden="true">
                  !
                </span>
                <section>
                  <strong>Page description is missing</strong>
                  <small>Confirmed in the served homepage</small>
                </section>
                <span className="check-label">Finding</span>
              </div>
              <div>
                <span className="check-good" aria-hidden="true">
                  ✓
                </span>
                <section>
                  <strong>The rest stays as it is</strong>
                  <small>Healthy content needs no rewrite</small>
                </section>
                <span className="check-label">Keep</span>
              </div>
            </div>
          )}
          {stage === 2 && (
            <div className="artifact-proposal">
              <div className="artifact-bar">
                <strong>Homepage repair</strong>
                <span>Awaiting your review</span>
              </div>
              <div className="proposal-line">
                <span>Destination</span>
                <del>/collections/lighting/</del>
                <ins>/shop/ · existing page</ins>
              </div>
              <div className="proposal-line">
                <span>Description</span>
                <del>Missing</del>
                <ins>Restored from existing page copy</ins>
              </div>
              <p>No new product claims. No unrelated redesign.</p>
            </div>
          )}
          {stage === 3 && (
            <div className="artifact-checks">
              <div>
                <span className="check-good" aria-hidden="true">
                  ✓
                </span>
                <section>
                  <strong>The collection opens</strong>
                  <small>/shop/ returns 200 after deployment</small>
                </section>
                <span className="check-label">Verified</span>
              </div>
              <div>
                <span className="check-good" aria-hidden="true">
                  ✓
                </span>
                <section>
                  <strong>The description is present</strong>
                  <small>Confirmed on the live homepage</small>
                </section>
                <span className="check-label">Verified</span>
              </div>
              <div className="watching-next">
                <span className="dot" />
                <strong>Watching for the next website update</strong>
              </div>
            </div>
          )}
        </m.div>
      </div>
      <div className="workflow-controls">
        <span>
          {stage === 3
            ? "A verified fix is more than an edit."
            : "Evidence → review → live verification."}
        </span>
        <button
          type="button"
          className="workflow-next"
          onClick={() => setStage(stage === 3 ? 0 : stage + 1)}
        >
          {stage === 0
            ? "Check this update →"
            : stage === 1
              ? "See the proposal →"
              : stage === 2
                ? "Approve this example →"
                : "Replay example ↺"}
        </button>
      </div>
      <p className="workflow-disclosure">
        Explore an example. This does not run an audit or change your website.
      </p>
    </aside>
  );
}
