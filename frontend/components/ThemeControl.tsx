"use client";

import { useTheme } from "./ThemeProvider";

export function ThemeControl({ compact = false }: { compact?: boolean }) {
  const { theme, choose } = useTheme();
  return (
    <fieldset className={`theme-control${compact ? " theme-compact" : ""}`}>
      <legend>Appearance</legend>
      <div>
        {(["light", "dark", "system"] as const).map((value) => {
          const label = value[0].toUpperCase() + value.slice(1);
          return (
            <button
              type="button"
              key={value}
              aria-label={label}
              title={`${label} appearance`}
              aria-pressed={theme === value}
              onClick={() => choose(value)}
            >
              <span aria-hidden="true">
                {value === "light" ? "☼" : value === "dark" ? "☾" : "◐"}
              </span>
              <span className="theme-label">{label}</span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
