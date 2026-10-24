"use client";

import { useState } from "react";
import type { Project } from "@/lib/api";
import { testedPlatforms } from "@/lib/platforms";
import { PlatformLogo } from "./PlatformLogo";

export function WorkspaceConnections({
  projects,
  onOpen,
  onCreate,
  onGitHub,
}: {
  projects: Project[];
  onOpen: (project: Project, platform: string) => void;
  onCreate: (platform: string) => void;
  onGitHub: () => void;
}) {
  const [projectId, setProjectId] = useState("");
  const project = projects.find((item) => item.id === projectId) || projects[0];
  return (
    <section
      className="panel workspace-connections"
      id="platform-connections"
      aria-labelledby="workspace-connections-title"
    >
      <div className="section-heading">
        <div>
          <span className="eyebrow">YOUR CONNECTED WORKSPACE</span>
          <h2 id="workspace-connections-title">
            Connect your website’s tools.
          </h2>
          <p>
            Choose a platform to set up access. Content and deployment
            connections belong to a website; GitHub account access is managed
            for your workspace.
          </p>
        </div>
        {project && (
          <label>
            Website for this connection
            <select
              value={project.id}
              onChange={(event) => setProjectId(event.target.value)}
            >
              {projects.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.spec.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      {!project && (
        <p>
          Add your first website as part of setup, then grant the platform
          access you choose.
        </p>
      )}
      <div className="workspace-connection-grid">
        {testedPlatforms.map((platform) => (
          <button
            key={platform.id}
            type="button"
            className="workspace-connection-card"
            aria-label={`Set up ${platform.name}`}
            onClick={() =>
              platform.id === "github"
                ? onGitHub()
                : project
                  ? onOpen(project, platform.id)
                  : onCreate(platform.id)
            }
          >
            <span className="platform-lockup">
              <PlatformLogo platform={platform.id} size={26} />
              <strong>{platform.name}</strong>
            </span>
            <span>{platform.summary}</span>
            <span className="text-link">Set up connection ↗</span>
          </button>
        ))}
      </div>
      <div className="actions">
        {project && (
          <button
            type="button"
            className="text-link"
            onClick={() => onOpen(project, "search_console")}
          >
            Browse all platforms & search tools ↗
          </button>
        )}
        <button
          type="button"
          className="text-link"
          onClick={() => onCreate("website")}
        >
          Add another website ↗
        </button>
      </div>
    </section>
  );
}
