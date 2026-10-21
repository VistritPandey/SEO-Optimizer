"use client";

import { useCallback, useState } from "react";
import { DemoPlayback } from "./DemoPlayback";
import { useDemoPlayback } from "./useDemoPlayback";

const stepDuration = 1500;
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
  const advance = useCallback(
    () => setStage((value) => (value + 1) % stages.length),
    [],
  );
  const playback = useDemoPlayback<HTMLElement>(stage, stepDuration, advance);
  return (
    <aside
      ref={playback.ref}
      {...playback.interaction}
      data-stage={stage}
      className="hero-workflow hero-terminal"
      data-running={playback.running}
      aria-label="Interactive SEO workflow example"
    >
      <div className="hero-workflow-label">
        <span>YOUR AGENT, AT WORK</span>
        <span className="workflow-example">Interactive example</span>
      </div>
      <DemoPlayback
        name="hero example"
        step={stage}
        total={4}
        duration={stepDuration}
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
        <div key={stage} className="workflow-artifact terminal-window">
          <div className="terminal-chrome">
            <span className="terminal-lights" aria-hidden="true">
              <i /><i /><i />
            </span>
            <span>your-optimiser / agent</span>
            <span className="terminal-session">SESSION 001</span>
          </div>
          <div className="terminal-output" aria-label={`${stages[stage]} example output`}>
            {stage === 0 && (
              <>
                <div className="terminal-line terminal-muted">A website update arrives</div>
                <div className="terminal-line"><span className="terminal-prompt">→</span> main · homepage changed</div>
                <div className="terminal-line terminal-file">web/index.html</div>
                <div className="terminal-line">Check the affected page and its links.</div>
                <div className="terminal-line terminal-success">Watching the pages that matter.</div>
              </>
            )}
            {stage === 1 && (
              <>
                <div className="terminal-line"><span className="terminal-prompt">→</span> read_file <span className="terminal-file">web/index.html</span></div>
                <div className="terminal-line terminal-warning">/collections/lighting/ returns 404</div>
                <div className="terminal-line terminal-warning">Page description is missing</div>
                <div className="terminal-line terminal-success">/shop/ · existing page</div>
                <div className="terminal-line terminal-muted">Evidence collected. Prepare a focused fix.</div>
              </>
            )}
            {stage === 2 && (
              <>
                <div className="terminal-line"><span className="terminal-prompt">→</span> apply_patch <span className="terminal-file">web/index.html</span></div>
                <div className="terminal-line terminal-warning">- href=&quot;/collections/lighting/&quot;</div>
                <div className="terminal-line terminal-success">+ href=&quot;/shop/&quot;</div>
                <div className="terminal-line terminal-success">+ Description from existing page copy</div>
                <div className="terminal-line terminal-muted">run_checks ✓ · Pull request ready for review</div>
              </>
            )}
            {stage === 3 && (
              <>
                <div className="terminal-line terminal-muted">After your review, merge and deployment</div>
                <div className="terminal-line terminal-success">/shop/ returns 200 after deployment</div>
                <div className="terminal-line terminal-success">Page description present · verified</div>
                <div className="terminal-line">Healthy content left unchanged.</div>
                <div className="terminal-line terminal-prompt">Watching for the next website update<span className="terminal-cursor" aria-hidden="true">▌</span></div>
              </>
            )}
          </div>
          <div className="terminal-footnote">
            <span>{stage === 2 ? "PATCH EXCERPTS" : "EVIDENCE BEFORE ACTION"}</span>
            <span>SEO CARE, IN THE CODE</span>
          </div>
        </div>
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
