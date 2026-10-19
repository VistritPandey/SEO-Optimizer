"use client";

import { useState } from "react";

export function WalkthroughVideo() {
  const [open, setOpen] = useState(false);
  return (
    <details
      className="customer-video"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>▷ Prefer to watch? See the customer walkthrough</summary>
      {open ? (
        <video
          controls
          muted
          playsInline
          preload="none"
          poster="/demo-poster.webp"
          aria-label="Your Optimiser customer walkthrough"
        >
          <source src="/demo.mp4" type="video/mp4" />
          <track
            kind="captions"
            src="/demo-captions.vtt"
            srcLang="en"
            label="English"
          />
          Your browser does not support video playback.
        </video>
      ) : (
        <p>
          <a href="/demo.mp4">Open the silent video walkthrough ↗</a>
        </p>
      )}
      <p>
        <small>
          An illustrated customer journey based on a recorded website repair. It
          shows the workflow, not a promise of higher rankings.
        </small>
      </p>
    </details>
  );
}
