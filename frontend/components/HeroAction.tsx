"use client";

import type { PointerEvent } from "react";

export function HeroAction() {
  function move(event: PointerEvent<HTMLAnchorElement>) {
    if (
      event.pointerType !== "mouse" ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    )
      return;
    const box = event.currentTarget.getBoundingClientRect();
    event.currentTarget.style.setProperty(
      "--tilt-x",
      `${(0.5 - (event.clientY - box.top) / box.height) * 7}deg`,
    );
    event.currentTarget.style.setProperty(
      "--tilt-y",
      `${((event.clientX - box.left) / box.width - 0.5) * 7}deg`,
    );
  }
  function reset(event: PointerEvent<HTMLAnchorElement>) {
    event.currentTarget.style.removeProperty("--tilt-x");
    event.currentTarget.style.removeProperty("--tilt-y");
  }
  return (
    <a
      className="button hero-action"
      href="#how"
      onPointerMove={move}
      onPointerLeave={reset}
      onPointerCancel={reset}
    >
      Try the interactive demo ↓
    </a>
  );
}
