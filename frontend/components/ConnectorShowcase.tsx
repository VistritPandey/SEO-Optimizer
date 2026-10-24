"use client";

import Link from "next/link";
import { useState, useSyncExternalStore } from "react";
import { testedPlatforms } from "@/lib/platforms";
import { PlatformLogo } from "./PlatformLogo";

function subscribeMotionPreference(changed: () => void) {
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  media.addEventListener("change", changed);
  return () => media.removeEventListener("change", changed);
}

export function ConnectorBrands() {
  return (
    <ul
      className="connector-brands"
      aria-label="Connect your publishing platform"
    >
      {testedPlatforms
        .filter((platform) => platform.coverage === "hosted")
        .map((platform) => (
          <li key={platform.id}>
            <PlatformLogo platform={platform.id} size={20} />
            <span>{platform.name}</span>
          </li>
        ))}
    </ul>
  );
}

export function ConnectorShowcase() {
  const reducedMotion = useSyncExternalStore(
    subscribeMotionPreference,
    () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    () => true,
  );
  const [playback, setPlayback] = useState<boolean | null>(null);
  const playing = playback ?? !reducedMotion;
  return (
    <section
      className="connector-showcase marketing-section"
      id="connections"
      aria-labelledby="connections-title"
    >
      <div className="customer-intro">
        <div>
          <span className="eyebrow">
            YOUR WEBSITE. YOUR TOOLS. ONE WORKSPACE.
          </span>
          <h2 id="connections-title">
            Works where
            <br />
            <em>your website lives.</em>
          </h2>
        </div>
        <p>
          Connect your code, content and deployment tools. Give the agent access
          to the parts you want it to look after, with a record of what it
          checks and changes.
        </p>
      </div>
      <div className="connector-slider-toolbar">
        <span>Connected to the way you build.</span>
        <button
          className="connector-slider-control"
          type="button"
          aria-label={
            playing ? "Pause platform slider" : "Play platform slider"
          }
          aria-controls="platform-slider"
          onClick={() => setPlayback(!playing)}
        >
          <span aria-hidden="true">{playing ? "Ⅱ" : "▷"}</span>{" "}
          {playing ? "Pause" : "Play"}
        </button>
      </div>
      <div
        className="connector-slider"
        id="platform-slider"
        data-playing={playing}
        role="region"
        aria-label="Website platforms"
        aria-roledescription="carousel"
        tabIndex={0}
      >
        <div className="connector-slider-track">
          {[0, 1].map((copy) => (
            <ul
              className="connector-slider-group"
              key={copy}
              aria-hidden={copy === 1 ? true : undefined}
            >
              {testedPlatforms.map((platform) => (
                <li key={platform.id}>
                  <PlatformLogo platform={platform.id} size={34} />
                  <h3>{platform.name}</h3>
                  <p>{platform.summary}</p>
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>
      <div className="connector-showcase-footnote">
        <p>
          Connect only what you need. You choose the access; your team keeps
          control of reviews and publishing.
        </p>
        <Link href="/login?mode=register" className="text-link">
          Connect your first website ↗
        </Link>
      </div>
    </section>
  );
}
