"use client";

import { useState } from "react";
import type { Project } from "@/lib/api";
import { ThemeControl } from "./ThemeControl";
import { Brand } from "./Brand";
import { PlatformLogo } from "./PlatformLogo";

const sections = [
  ["overview", "Website overview", "overview"],
  ["findings", "Findings", "findings"],
  ["activity", "AI audits & logs", "activity"],
  ["pages", "Pages inspected", "pages"],
  ["research", "Content & research", "research"],
  ["connectors", "Connectors", "connection"],
  ["policy", "Project settings", "settings"],
];
function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    overview: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    findings: "M12 3 2 21h20L12 3Z M12 9v5 M12 17h.01",
    activity: "M3 12h4l3-8 4 16 3-8h4",
    pages: "M6 3h9l4 4v14H6V3Z M14 3v5h5 M9 12h7 M9 16h7",
    research:
      "M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1Z M12 5v15",
    settings: "M4 7h16 M4 17h16 M8 4v6 M16 14v6",
    connection:
      "M10 14l4-4 M8 16l-2 2a3 3 0 0 1-4-4l5-5a3 3 0 0 1 4 0 M16 8l2-2a3 3 0 0 1 4 4l-5 5a3 3 0 0 1-4 0",
    tour: "M9 8a3 3 0 1 1 5 2c-2 1-2 2-2 3 M12 17h.01 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    plus: "M12 5v14 M5 12h14",
    exit: "M9 4H4v16h5 M10 12h11 M17 8l4 4-4 4",
  };
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name] || paths.overview} />
    </svg>
  );
}

export function WorkspaceSidebar({
  projects,
  selected,
  tab,
  email,
  connectionsOpen = false,
  findings,
  onHome,
  onConnect,
  onSelect,
  onTab,
  onTour,
  onSignOut,
}: {
  projects: Project[];
  selected: Project | null;
  tab: string;
  email: string;
  connectionsOpen?: boolean;
  findings: number;
  onHome: (connections?: boolean) => void;
  onConnect: () => void;
  onSelect: (project: Project) => void;
  onTab: (tab: string) => void;
  onTour: () => void;
  onSignOut: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  function navigate(action: () => void) {
    action();
    setMenuOpen(false);
  }
  return (
    <aside className="sidebar workspace-sidebar">
      <div className="sidebar-brand-row">
        <Brand
          href="/dashboard"
          label="Your Optimiser workspace home"
          onClick={(event) => {
            if (
              event.metaKey ||
              event.ctrlKey ||
              event.shiftKey ||
              event.altKey
            )
              return;
            event.preventDefault();
            navigate(() => onHome());
          }}
        />
        <button
          className="sidebar-toggle"
          aria-label="Workspace menu"
          aria-expanded={menuOpen}
          aria-controls="workspace-navigation"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          {menuOpen ? "Close ×" : "Menu ☰"}
        </button>
      </div>
      <div
        id="workspace-navigation"
        className={`sidebar-scroll ${menuOpen ? "is-open" : ""}`}
      >
        <nav aria-label="Workspace navigation" className="sidebar-section">
          <span className="eyebrow">WORKSPACE</span>
          <button
            className={`nav-item ${!selected && !connectionsOpen ? "active" : ""}`}
            onClick={() => navigate(() => onHome())}
          >
            <Icon name="overview" />
            All websites
          </button>
          <button
            className={`nav-item ${connectionsOpen ? "active" : ""}`}
            onClick={() => navigate(() => onHome(true))}
          >
            <Icon name="connection" />
            Connections
          </button>
        </nav>
        <nav
          aria-label="Your websites"
          className="sidebar-section sidebar-websites"
        >
          <div className="sidebar-section-heading">
            <span className="eyebrow">
              WEBSITES <small>{projects.length}</small>
            </span>
            <button
              className="sidebar-add"
              onClick={() => navigate(onConnect)}
              aria-label="Connect website"
            >
              <Icon name="plus" />
            </button>
          </div>
          {projects.map((project) => (
            <button
              key={project.id}
              className={`nav-item ${selected?.id === project.id ? "active" : ""}`}
              onClick={() => navigate(() => onSelect(project))}
            >
              <span className="sidebar-platform">
                <PlatformLogo
                  platform={String(
                    project.spec.publishing_platform || "github",
                  )}
                  size={19}
                />
                <span
                  className={`project-status-dot ${project.spec.enabled ? "enabled" : ""}`}
                  role="img"
                  aria-label={
                    project.spec.enabled
                      ? "Monitoring enabled"
                      : "Monitoring paused"
                  }
                />
              </span>
              <span className="sidebar-website-name">
                {project.spec.name}
                <small>{new URL(project.spec.website_url).hostname}</small>
              </span>
              {selected?.id === project.id && <span aria-hidden="true">↗</span>}
            </button>
          ))}
          {!projects.length && (
            <button className="nav-item" onClick={() => navigate(onConnect)}>
              <Icon name="plus" />
              Connect your first website
            </button>
          )}
        </nav>
        {selected && (
          <nav
            className="sidebar-section sidebar-project-sections"
            aria-label="Selected website navigation"
          >
            <span className="eyebrow">THIS WEBSITE</span>
            {sections.map(([id, label, icon]) => (
              <button
                key={id}
                className={`nav-item ${tab === id ? "active" : ""}`}
                aria-current={tab === id ? "page" : undefined}
                onClick={() => navigate(() => onTab(id))}
              >
                <Icon name={icon} />
                <span>{label}</span>
                {id === "findings" && findings > 0 && (
                  <span className="sidebar-count">{findings}</span>
                )}
              </button>
            ))}
          </nav>
        )}
      </div>
      <div className={`sidebar-bottom ${menuOpen ? "is-open" : ""}`}>
        <ThemeControl />
        <button className="sidebar-tour" onClick={() => navigate(onTour)}>
          <Icon name="tour" />
          <span>
            How it works<small>A quick guided tour</small>
          </span>
          <span aria-hidden="true">↗</span>
        </button>
        <div className="sidebar-identity">
          <span className="sidebar-avatar" aria-hidden="true">
            {email ? email[0].toUpperCase() : "Y"}
          </span>
          <span>
            <strong>Your workspace</strong>
            <small>{email || "Loading account…"}</small>
          </span>
          <button onClick={onSignOut} aria-label="Sign out">
            <Icon name="exit" />
          </button>
        </div>
      </div>
    </aside>
  );
}
