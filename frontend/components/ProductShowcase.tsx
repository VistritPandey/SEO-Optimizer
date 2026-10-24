import { HeroWorkflow } from "./HeroWorkflow";

export function ProductShowcase() {
  return (
    <div
      className="product-showcase"
      aria-label="Illustrative Your Optimiser workspace"
    >
      <div className="showcase-titlebar">
        <span className="showcase-lights" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span>
          Your Optimiser <span className="showcase-divider">/</span> Cedar
          Workshop
        </span>
        <span className="showcase-session">Interactive workspace</span>
      </div>
      <div className="showcase-workspace">
        <div className="showcase-sidebar" aria-hidden="true">
          <span className="showcase-wordmark">
            Your Optimiser<span>Search care, on repeat.</span>
          </span>
          <small>YOUR WEBSITE</small>
          <strong className="showcase-site">
            ◈ Cedar Workshop<span>cedar.example</span>
          </strong>
          <div className="showcase-nav">
            <span>▦ Website overview</span>
            <span>
              ◷ Findings <b>2</b>
            </span>
            <span className="is-active">↗ AI audits & logs</span>
            <span>▤ Pages inspected</span>
            <span>⌁ Connected tools</span>
          </div>
          <div className="showcase-monitor">
            <span /> Monitoring relevant changes
          </div>
        </div>
        <div className="showcase-agent">
          <HeroWorkflow />
        </div>
        <div className="showcase-evidence" aria-hidden="true">
          <small>A CLEAR FOLLOW-THROUGH</small>
          <h3>
            Every change
            <br />
            <em>has a reason.</em>
          </h3>
          <ol>
            <li>
              <span>01</span>
              <div>
                <strong>Observe the update</strong>
                <p>The changed page and its links.</p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>Confirm the problem</strong>
                <p>Evidence before an edit.</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Review the repair</strong>
                <p>A focused, tested proposal.</p>
              </div>
            </li>
            <li>
              <span>04</span>
              <div>
                <strong>Check what went live</strong>
                <p>Then keep watching.</p>
              </div>
            </li>
          </ol>
          <p className="showcase-note">
            Illustrative workspace.
            <br />
            Your real results stay in your dashboard.
          </p>
        </div>
      </div>
      <div className="showcase-bottom">
        <span>
          <i /> Your website keeps moving. So does its care.
        </span>
        <a href="#how">Explore the full example ↗</a>
      </div>
    </div>
  );
}
