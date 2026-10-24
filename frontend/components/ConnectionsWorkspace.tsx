"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { useCallback, useEffect, useState } from "react";
import { firebaseAuth } from "@/lib/firebase";
import { api, type Project } from "@/lib/api";
import catalog from "@/lib/connection-catalog.json";
import { testedPlatform } from "@/lib/platforms";
import {
  rememberWebsite,
  rememberedWebsite,
  selectWebsite,
  websitePath,
} from "@/lib/website-navigation.mjs";
import { Connectors, type Connection } from "./Connectors";
import { PlatformLogo } from "./PlatformLogo";
import { WorkspaceSidebar } from "./WorkspaceSidebar";
import { WorkspaceTour } from "./WorkspaceTour";

type Account = {
  email: string;
  github_connection?: { status: string; login?: string };
};
type Snapshot = { project: Project; connections: Connection[]; error?: string };

export function ConnectionsWorkspace({
  platform = "",
  projectId = "",
}: {
  platform?: string;
  projectId?: string;
}) {
  const router = useRouter();
  const [account, setAccount] = useState<Account | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [tour, setTour] = useState(false);
  const [preferredId, setPreferredId] = useState("");
  const project = selectWebsite(projects, projectId, preferredId);
  const definition = catalog.find((item) => item.platform === platform);
  const current = snapshots
    .find((item) => item.project.id === project?.id)
    ?.connections.find((item) => item.platform === platform);
  const refresh = useCallback(async () => {
    const [profile, list] = await Promise.all([
      api<Account>("account"),
      api<Project[]>("projects"),
    ]);
    const records = await Promise.all(
      list.map(async (item) => {
        try {
          const value = await api<{ connections: Connection[] }>(
            `projects/${item.id}/connectors`,
          );
          return { project: item, connections: value.connections };
        } catch (failure) {
          return {
            project: item,
            connections: [],
            error:
              failure instanceof Error
                ? failure.message
                : "Connection status unavailable.",
          };
        }
      }),
    );
    const uid = firebaseAuth().currentUser?.uid || "";
    const chosen = selectWebsite(list, projectId, rememberedWebsite(uid));
    if (chosen) {
      setPreferredId(chosen.id);
      rememberWebsite(uid, chosen.id);
    }
    setAccount(profile);
    setProjects(list);
    setSnapshots(records);
    setReady(true);
    setError("");
  }, [projectId]);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setInterval> | undefined;
    const load = () =>
      refresh().catch((failure) => {
        if (alive) {
          setError(failure.message);
          setReady(true);
        }
      });
    const unsubscribe = onAuthStateChanged(firebaseAuth(), (user) => {
      if (timer) clearInterval(timer);
      if (!user) {
        router.replace("/login");
        return;
      }
      if (!user.emailVerified) {
        router.replace("/dashboard");
        return;
      }
      void load();
      timer = setInterval(load, 30000);
    });
    return () => {
      alive = false;
      unsubscribe();
      if (timer) clearInterval(timer);
    };
  }, [refresh, router]);
  const path = (name: string, id = project?.id) =>
    `/dashboard/connections/${name}${id ? `?project=${encodeURIComponent(id)}` : ""}`;
  async function github(operation: "connect" | "install" | "disconnect") {
    setBusy(true);
    setError("");
    try {
      if (operation === "disconnect") {
        await api("github/connect", "DELETE");
        await refresh();
      } else {
        const result = await api<{ url: string }>(
          `github/${operation}`,
          "POST",
        );
        const destination = new URL(result.url);
        if (
          destination.protocol !== "https:" ||
          destination.hostname !== "github.com"
        )
          throw new Error("GitHub returned an invalid sign-in address.");
        window.location.assign(destination.href);
      }
    } catch (failure) {
      setError(
        failure instanceof Error ? failure.message : "Connection failed.",
      );
    } finally {
      setBusy(false);
    }
  }
  const configured = snapshots.flatMap((snapshot) =>
    snapshot.connections
      .filter((item) => item.connected)
      .map((connection) => ({ project: snapshot.project, connection })),
  );
  return (
    <div className="workspace-shell workspace-v2">
      <WorkspaceSidebar
        services={configured.map(({ project: item, connection }) => ({
          platform: connection.platform,
          name: connection.definition.name,
          projectId: item.id,
          website: item.spec.name,
        }))}
        activeService={`${project?.id || ""}:${platform}`}
        onService={(name, id) => router.push(path(name, id))}
        projects={projects}
        selected={null}
        tab="connectors"
        email={account?.email || ""}
        connectionsOpen
        findings={0}
        onHome={(connections) =>
          router.push(connections ? "/dashboard/connections" : "/dashboard")
        }
        onConnect={() => router.push("/dashboard?connect=website")}
        onSelect={(item) => {
          rememberWebsite(firebaseAuth().currentUser?.uid || "", item.id);
          router.push(websitePath("overview", item.id));
        }}
        onTab={(tab) => router.push(websitePath(tab, project?.id || ""))}
        onTour={() => setTour(true)}
        onSignOut={() => {
          void signOut(firebaseAuth())
            .then(() => router.push("/login"))
            .catch(() => setError("Sign out failed. Please try again."));
        }}
      />
      <WorkspaceTour
        open={tour}
        onClose={() => setTour(false)}
        onNavigate={(target) => {
          setTour(false);
          router.push(
            target === "connect"
              ? "/dashboard?connect=website"
              : websitePath(target, project?.id || ""),
          );
        }}
      />
      <main id="main-content" className="dashboard-main">
        <header className="topbar">
          <span>
            WORKSPACE / <Link href="/dashboard/connections">CONNECTIONS</Link>
            {platform
              ? ` / ${platform === "github" ? "GitHub" : definition?.name || "Platform"}`
              : ""}
          </span>
          <Link href="/dashboard">Website overview ↗</Link>
        </header>
        <section className="connections-heading">
          <span className="eyebrow">YOUR CONNECTED WORKSPACE</span>
          <h1 className="platform-lockup">
            {platform && <PlatformLogo platform={platform} size={32} />}
            {platform
              ? platform === "github"
                ? "GitHub"
                : definition?.name || "Connection unavailable"
              : "Connections"}
          </h1>
          <p>
            {platform
              ? testedPlatform(platform)?.summary ||
                definition?.note ||
                "Repository access, reviewed fixes and deployment follow-through."
              : "See what is connected, what it can do, and where your agent needs access."}
          </p>
        </section>
        {error && (
          <p className="alert" role="alert">
            {error}{" "}
            <button
              className="text-link"
              onClick={() => {
                void refresh().catch((failure) => setError(failure.message));
              }}
            >
              Try again
            </button>
          </p>
        )}
        {!ready && <p role="status">Loading your connections…</p>}
        {ready &&
          snapshots
            .filter((item) => item.error)
            .map((item) => (
              <p className="notice" role="status" key={item.project.id}>
                {item.project.spec.name}: {item.error} Its connection status is
                unknown until it can be refreshed.
              </p>
            ))}
        {ready && platform === "github" && (
          <section className="panel">
            <h2>Repository access</h2>
            <p>
              {account?.github_connection?.status === "connected"
                ? `Connected${account.github_connection.login ? ` as ${account.github_connection.login}` : ""}. Only repositories selected in the GitHub App installation are accessible.`
                : "Connect GitHub and choose which repositories the agent can access."}
            </p>
            <p>
              Inspect relevant changes, prepare tested fixes in a branch, open a
              pull request, and verify the deployed result. Merging follows each
              website’s policy.
            </p>
            <div className="actions">
              <button
                className="button"
                disabled={busy}
                onClick={() => {
                  void github(
                    account?.github_connection?.status === "connected"
                      ? "install"
                      : "connect",
                  );
                }}
              >
                {account?.github_connection?.status === "connected"
                  ? "Manage repository access ↗"
                  : "Connect GitHub ↗"}
              </button>
            </div>
            {account?.github_connection?.status !== "not_connected" &&
              account?.github_connection && (
                <details>
                  <summary>Disconnect GitHub</summary>
                  <p>
                    This pauses connected repository projects and removes their
                    active installation credentials. Findings and existing pull
                    requests remain.
                  </p>
                  <button
                    className="text-link"
                    disabled={busy}
                    onClick={() => {
                      void github("disconnect");
                    }}
                  >
                    Disconnect and pause projects
                  </button>
                </details>
              )}
          </section>
        )}
        {ready && platform && platform !== "github" && definition && (
          <>
            <label className="panel connection-website-picker">
              Website for this connection
              <select
                value={project?.id || ""}
                onChange={(event) =>
                  router.push(path(platform, event.target.value))
                }
              >
                {!project && <option value="">Select a website</option>}
                {projects.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.spec.name}
                  </option>
                ))}
              </select>
            </label>
            {project ? (
              <>
                <div className="connection-metrics">
                  <article>
                    <span>CONNECTION</span>
                    <strong className="connection-status-value">
                      {current
                        ? current.status.replaceAll("_", " ")
                        : "Loading…"}
                    </strong>
                    <p>
                      {current?.config.resource ||
                        "Choose the account or resource below."}
                    </p>
                  </article>
                  <article>
                    <span>LAST COLLECTION</span>
                    <strong className="connection-status-value">
                      {current?.last_sync
                        ? new Date(current.last_sync * 1000).toLocaleString()
                        : "Not collected"}
                    </strong>
                    <p>
                      {current?.evidence.length || 0} saved evidence snapshots
                    </p>
                  </article>
                  <article>
                    <span>SUPPORTED ACTIONS</span>
                    <strong className="connection-status-value">
                      {definition.write
                        ? "Collect & repair"
                        : "Collect & measure"}
                    </strong>
                    <p>
                      {current?.config.auto_apply
                        ? "Automatic supported repairs enabled"
                        : "Changes follow your website’s permissions"}
                    </p>
                  </article>
                </div>
                <Connectors
                  key={`${project.id}:${platform}`}
                  project={project}
                  initialPlatform={platform}
                  lockedPlatform
                />
              </>
            ) : (
              <section className="panel">
                <h2>Add a website first</h2>
                <p>
                  Each content account and its evidence belong to a website.
                  This keeps credentials and permissions separate.
                </p>
                <Link
                  className="button"
                  href={`/dashboard?connect=${encodeURIComponent(platform)}`}
                >
                  Add website ↗
                </Link>
              </section>
            )}
          </>
        )}
        {ready && !platform && (
          <>
            <section className="section">
              <div className="section-heading">
                <h2>Your connections</h2>
                <span>
                  {configured.length +
                    (account?.github_connection?.status === "connected"
                      ? 1
                      : 0)}{" "}
                  configured
                </span>
              </div>
              <div className="workspace-connection-grid">
                {account?.github_connection?.status === "connected" && (
                  <Link
                    className="workspace-connection-card"
                    href={path("github")}
                  >
                    <span className="platform-lockup">
                      <PlatformLogo platform="github" size={26} />
                      <strong>GitHub</strong>
                    </span>
                    <span className="pill">Connected</span>
                    <span>Workspace repository access</span>
                    <span className="text-link">
                      View repository connection ↗
                    </span>
                  </Link>
                )}
                {configured.map(({ project: item, connection }) => (
                  <Link
                    className="workspace-connection-card"
                    key={`${item.id}:${connection.platform}`}
                    href={path(connection.platform, item.id)}
                  >
                    <span className="platform-lockup">
                      <PlatformLogo platform={connection.platform} size={26} />
                      <strong>{connection.definition.name}</strong>
                    </span>
                    <span className="pill">
                      {connection.status.replaceAll("_", " ")}
                    </span>
                    <span>{item.spec.name}</span>
                    <span>{connection.config.resource}</span>
                    <span className="text-link">
                      View connection & activity ↗
                    </span>
                  </Link>
                ))}
              </div>
              {!configured.length &&
                account?.github_connection?.status !== "connected" && (
                  <p>
                    No connections configured yet. Choose a platform below to
                    get started.
                  </p>
                )}
              <p className="muted">
                Configured access is shown separately from successful
                collection. Each service page shows its latest result and
                available actions.
              </p>
            </section>
            <section className="section">
              <h2>Available platforms</h2>
              <p>
                Choose a service to see its supported scope and set up access.
              </p>
              <div className="workspace-connection-grid">
                <Link
                  className="workspace-connection-card"
                  href={path("github")}
                >
                  <span className="platform-lockup">
                    <PlatformLogo platform="github" size={26} />
                    <strong>GitHub</strong>
                  </span>
                  <span>
                    Repository changes, pull requests and verification.
                  </span>
                  <span className="text-link">Manage access ↗</span>
                </Link>
              </div>
              {Array.from(new Set(catalog.map((item) => item.group))).map(
                (group) => (
                  <div key={group}>
                    <h3>{group}</h3>
                    <div className="workspace-connection-grid">
                      {catalog
                        .filter((item) => item.group === group)
                        .map((item) => (
                          <Link
                            key={item.platform}
                            href={path(item.platform)}
                            className="workspace-connection-card"
                          >
                            <span className="platform-lockup">
                              <PlatformLogo
                                platform={item.platform}
                                size={26}
                              />
                              <strong>{item.name}</strong>
                            </span>
                            <span>{item.note}</span>
                            <span className="pill">
                              {item.write
                                ? "Supported repairs"
                                : "Evidence & measurement"}
                            </span>
                            <span className="text-link">View platform ↗</span>
                          </Link>
                        ))}
                    </div>
                  </div>
                ),
              )}
            </section>
          </>
        )}
        <footer>
          Your Optimiser · Your connections, permissions and evidence in one
          place.
          <nav aria-label="Workspace help and policies">
            <Link href="/contact">Help</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/terms">Terms</Link>
          </nav>
        </footer>
      </main>
    </div>
  );
}
