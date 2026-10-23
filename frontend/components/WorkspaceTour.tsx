"use client";

import { useEffect, useRef, useState } from "react";

const steps = [
  {
    title: "Connect the website you want to protect.",
    text: "Connect a deployed website and choose its publishing platform. Use Connectors to grant scoped access to content, search evidence and deployment events.",
    target: "connect",
    action: "Connect a website",
    label: "YOUR PERMISSION, YOUR SCOPE",
  },
  {
    title: "Start with evidence, not a perfect-looking number.",
    text: "An audit collects public pages and relevant source context. Health reflects assessed checks. Missing facts stay open questions; they never become invented answers.",
    target: "overview",
    action: "See website health",
    label: "ESTABLISH A BASELINE",
  },
  {
    title: "See what the agent actually did.",
    text: "Follow collection, AI tool use and verification in the activity log. An unchanged website may reuse a validated assessment, saving another model call.",
    target: "activity",
    action: "Open audit logs",
    label: "A RECORD OF THE WORK",
  },
  {
    title: "Every repair needs a clear reason.",
    text: "Review supported changes and their evidence. Repository repairs become pull requests; CMS repairs become field proposals. Provider readback and live-page verification are separate steps.",
    target: "findings",
    action: "Review findings",
    label: "REPAIR WITH A REASON",
  },
  {
    title: "Keep watch as your website changes.",
    text: "Relevant changes to the monitored branch trigger focused audits, with periodic reconciliation. After a repair merges and deploys, the agent can verify the served result. Check settings for your monitoring and repair policy.",
    target: "policy",
    action: "Open project settings",
    label: "KEEP THE LOOP RUNNING",
  },
];
export function WorkspaceTour({
  open,
  onClose,
  onNavigate,
}: {
  open: boolean;
  onClose: () => void;
  onNavigate: (target: string) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (open) {
      setStep(0);
      dialog.current?.showModal();
    } else dialog.current?.close();
  }, [open]);
  useEffect(() => {
    if (open)
      dialog.current?.querySelector<HTMLElement>("#tour-title")?.focus();
  }, [open, step]);
  const current = steps[step];
  return (
    <dialog
      ref={dialog}
      className="workspace-tour"
      aria-labelledby="tour-title"
      aria-describedby="tour-description"
      onClose={onClose}
    >
      <div className="tour-heading">
        <span className="eyebrow">YOUR OPTIMISER / QUICK TOUR</span>
        <button
          className="tour-close"
          aria-label="Close tutorial"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <div
        className="tour-progress"
        role="img"
        aria-label={`Step ${step + 1} of ${steps.length}`}
      >
        {steps.map((_, index) => (
          <span key={index} className={index <= step ? "complete" : ""} />
        ))}
      </div>
      <div
        className="tour-preview"
        role="group"
        aria-label="Illustrative example; no changes are made"
      >
        <span className="tour-example">ILLUSTRATIVE EXAMPLE</span>
        {step === 0 && (
          <div className="tour-connection">
            <span>GitHub repository</span>
            <b>↔</b>
            <span>Your website</span>
            <small>Selected access · Monitored paths · Business goals</small>
          </div>
        )}
        {step === 1 && (
          <div className="tour-baseline">
            <strong>Evidence first</strong>
            <p>
              Passed checks <span>✓</span>
            </p>
            <p>
              Needs more context <span>?</span>
            </p>
            <p>
              Not yet assessed <span>-</span>
            </p>
          </div>
        )}
        {step === 2 && (
          <ol className="tour-events">
            <li>✓ Collect page observations</li>
            <li>✓ Inspect relevant source</li>
            <li>✓ Check proposed changes</li>
            <li>✓ Record evidence and outcome</li>
          </ol>
        )}
        {step === 3 && (
          <div className="tour-diff">
            <code className="tour-before">
              − &lt;title&gt;Untitled&lt;/title&gt;
            </code>
            <code className="tour-after">
              + &lt;title&gt;Workshop lighting guide&lt;/title&gt;
            </code>
            <small>Example only. Title supported by the page’s heading.</small>
            <b>Supported repair → checks → review</b>
          </div>
        )}
        {step === 4 && (
          <div className="tour-cycle">
            <span>Website change</span>
            <b>↓</b>
            <span>Focused audit</span>
            <b>↓</b>
            <span>Supported repair or no change</span>
            <small>After merge and deployment → verify the result</small>
          </div>
        )}
      </div>
      <span className="eyebrow">{current.label}</span>
      <h2 id="tour-title" tabIndex={-1}>
        {current.title}
      </h2>
      <p id="tour-description">{current.text}</p>
      <button
        className="text-link tour-destination"
        onClick={() => {
          onClose();
          onNavigate(current.target);
        }}
      >
        {current.action} ↗
      </button>
      <div className="tour-controls">
        <button
          className="text-link"
          disabled={step === 0}
          onClick={() => setStep(step - 1)}
        >
          ← Back
        </button>
        <span aria-live="polite">
          {step + 1} of {steps.length}
        </span>
        <button
          className="button"
          onClick={() =>
            step === steps.length - 1 ? onClose() : setStep(step + 1)
          }
        >
          {step === steps.length - 1 ? "Finish tour" : "Next →"}
        </button>
      </div>
    </dialog>
  );
}
