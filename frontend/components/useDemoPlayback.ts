"use client";

import { useEffect, useRef, useState, type SyntheticEvent } from "react";

export function useDemoPlayback<T extends HTMLElement>(
  step: number,
  duration: number,
  advance: () => void,
) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(true);
  const [ready, setReady] = useState(false);
  const [visible, setVisible] = useState(false);
  const [choice, setChoice] = useState<boolean | null>(null);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateMotion = () => setReducedMotion(media.matches);
    updateMotion();
    media.addEventListener("change", updateMotion);
    const observer = new IntersectionObserver(
      ([entry]) =>
        setInView(entry.isIntersecting && entry.intersectionRatio >= 0.3),
      { threshold: 0.3 },
    );
    if (ref.current) observer.observe(ref.current);
    setReady(true);
    const update = () => setVisible(document.visibilityState === "visible");
    update();
    document.addEventListener("visibilitychange", update);
    return () => {
      document.removeEventListener("visibilitychange", update);
      media.removeEventListener("change", updateMotion);
      observer.disconnect();
    };
  }, []);
  const playing = choice ?? (ready && reducedMotion === false);
  const running = playing && inView && visible;
  useEffect(() => {
    if (!running) return;
    const timer = window.setTimeout(advance, duration);
    return () => window.clearTimeout(timer);
  }, [running, step, duration, advance]);

  function interact(event: SyntheticEvent<T>) {
    if (!(event.target as Element).closest("[data-demo-playback]"))
      setChoice(false);
  }
  return {
    ref,
    playing,
    running,
    pause: () => setChoice(false),
    toggle: () => setChoice(!playing),
    interaction: { onPointerDownCapture: interact, onFocusCapture: interact },
  };
}
