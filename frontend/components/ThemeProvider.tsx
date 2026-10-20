"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "system" | "light" | "dark";
const KEY = "optimiser-theme";
const ThemeContext = createContext<{
  theme: Theme;
  choose: (theme: Theme) => void;
} | null>(null);
function valid(value: string | null): Theme {
  return value === "light" || value === "dark" ? value : "system";
}
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("system");
  const [ready, setReady] = useState(false);
  useEffect(() => {
    try {
      setTheme(valid(localStorage.getItem(KEY)));
    } catch {
      /* System mode also works when browser storage is unavailable. */
    }
    setReady(true);
    function sync(event: StorageEvent) {
      if (event.key === KEY) setTheme(valid(event.newValue));
    }
    window.addEventListener("storage", sync);
    return () => window.removeEventListener("storage", sync);
  }, []);
  useEffect(() => {
    if (!ready) return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    function apply() {
      document.documentElement.dataset.theme =
        theme === "system" ? (media.matches ? "dark" : "light") : theme;
    }
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme, ready]);
  function choose(value: Theme) {
    setTheme(value);
    try {
      localStorage.setItem(KEY, value);
    } catch {
      /* Retain the choice for this session. */
    }
  }
  return (
    <ThemeContext.Provider value={{ theme, choose }}>
      {children}
    </ThemeContext.Provider>
  );
}
export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("Theme controls require ThemeProvider");
  return context;
}
