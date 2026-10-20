"use client";

import { useEffect, useState } from "react";

type Theme = "system" | "light" | "dark";
export function ThemeControl() {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    try {
      const saved = localStorage.getItem("optimiser-theme");
      if (saved === "dark" || saved === "light") setTheme(saved);
    } catch {
      /* Use the system preference if storage is unavailable. */
    }
  }, []);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    function apply() {
      document.documentElement.dataset.theme =
        theme === "system" ? (media.matches ? "dark" : "light") : theme;
    }
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);
  function choose(value: Theme) {
    setTheme(value);
    try {
      localStorage.setItem("optimiser-theme", value);
    } catch {
      /* Keep the session choice. */
    }
  }
  return (
    <fieldset className="theme-control">
      <legend>Appearance</legend>
      <div>
        {(["light", "dark", "system"] as const).map((value) => (
          <button
            type="button"
            key={value}
            aria-pressed={theme === value}
            onClick={() => choose(value)}
          >
            <span aria-hidden="true">
              {value === "light" ? "☼" : value === "dark" ? "☾" : "◐"}
            </span>
            {value[0].toUpperCase() + value.slice(1)}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
