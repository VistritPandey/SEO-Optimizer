"use client";

import { useEffect, useLayoutEffect, useRef } from "react";
import { usePathname } from "next/navigation";

export function NavigationScroll() {
  const pathname = usePathname();
  const destination = useRef<string | null>(null);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (
        event.defaultPrevented ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      )
        return;
      const anchor =
        event.target instanceof Element
          ? event.target.closest<HTMLAnchorElement>("a[href]")
          : null;
      if (
        !anchor ||
        anchor.hasAttribute("download") ||
        (anchor.target && anchor.target !== "_self")
      )
        return;
      const url = new URL(anchor.href);
      destination.current =
        url.origin === location.origin &&
        !url.hash &&
        url.pathname !== location.pathname
          ? url.pathname
          : null;
    }
    function onHistoryNavigation() {
      destination.current = null;
    }
    document.addEventListener("click", onClick, true);
    window.addEventListener("popstate", onHistoryNavigation);
    return () => {
      document.removeEventListener("click", onClick, true);
      window.removeEventListener("popstate", onHistoryNavigation);
    };
  }, []);

  useLayoutEffect(() => {
    if (destination.current === pathname) {
      destination.current = null;
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    }
  }, [pathname]);

  return null;
}
