"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Brand } from "./Brand";
import { ThemeControl } from "./ThemeControl";
import { site } from "@/lib/site";

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const header = useRef<HTMLElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    function onOutsidePointer(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !header.current?.contains(event.target)
      ) {
        setOpen(false);
      }
    }
    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && open) {
        setOpen(false);
        toggle.current?.focus();
      }
    }
    const desktop = window.matchMedia("(min-width: 1101px)");
    function onResize() {
      if (desktop.matches) setOpen(false);
    }
    document.addEventListener("pointerdown", onOutsidePointer);
    document.addEventListener("keydown", onEscape);
    desktop.addEventListener("change", onResize);
    return () => {
      document.removeEventListener("pointerdown", onOutsidePointer);
      document.removeEventListener("keydown", onEscape);
      desktop.removeEventListener("change", onResize);
    };
  }, [open]);

  return (
    <header
      className="marketing-nav public-header"
      ref={header}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <Brand onClick={() => setOpen(false)} />
      <button
        ref={toggle}
        type="button"
        className="public-menu-toggle"
        aria-label={open ? "Close navigation menu" : "Open navigation menu"}
        aria-expanded={open}
        aria-controls="public-navigation"
        onClick={() => setOpen((value) => !value)}
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d={open ? "M6 6l12 12M6 18L18 6" : "M4 6h16M4 12h16M4 18h16"} />
        </svg>
      </button>
      <nav
        id="public-navigation"
        className="public-navigation"
        aria-label="Main navigation"
        data-open={open}
        onClick={(event) => {
          if (
            event.target instanceof Element &&
            event.target.closest("a[href]")
          )
            setOpen(false);
        }}
      >
        <Link href="/how-it-works">How it works</Link>
        <Link href="/seo-and-ai-search">What we look after</Link>
        <Link href="/#pricing">Pricing</Link>
        <Link href="/blog">Blog</Link>
        <a
          className="nav-github"
          href={site.repository}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Your Optimiser on GitHub (opens in a new tab)"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.55.1.76-.24.76-.54v-2.07c-3.1.67-3.76-1.32-3.76-1.32-.5-1.28-1.24-1.62-1.24-1.62-1.01-.69.08-.68.08-.68 1.12.08 1.71 1.15 1.71 1.15.99 1.7 2.59 1.21 3.22.92.1-.72.38-1.21.71-1.49-2.48-.28-5.08-1.24-5.08-5.52 0-1.22.43-2.22 1.14-3-.11-.28-.49-1.42.11-2.96 0 0 .93-.3 3.05 1.14a10.6 10.6 0 0 1 5.55 0c2.12-1.44 3.05-1.14 3.05-1.14.6 1.54.22 2.68.11 2.96.71.78 1.14 1.78 1.14 3 0 4.29-2.61 5.24-5.1 5.51.4.35.76 1.02.76 2.06v3.06c0 .3.2.65.77.54A11.1 11.1 0 0 0 12 .9Z" />
          </svg>
          <span>GitHub</span>
        </a>
        <Link className="nav-signin" href="/dashboard" prefetch={false}>
          Your workspace ↗
        </Link>
        <ThemeControl compact />
      </nav>
      <noscript>
        <style>{`@media(max-width:1100px){.public-header .public-menu-toggle{display:none!important}.public-header{flex-wrap:wrap!important}.public-header .public-navigation{display:flex!important;position:static!important;flex-basis:100%;max-height:none;box-shadow:none}}`}</style>
      </noscript>
    </header>
  );
}
