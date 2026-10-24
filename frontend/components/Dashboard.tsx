"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  onAuthStateChanged,
  sendEmailVerification,
  signOut,
  type User,
} from "firebase/auth";
import { firebaseAuth } from "@/lib/firebase";
import { api, type Activity, type Project } from "@/lib/api";
import { AuditWorkspace } from "./AuditWorkspace";
import { AgentPreferences } from "./AgentPreferences";
import { Connectors } from "./Connectors";
import { WorkspaceSidebar } from "./WorkspaceSidebar";
import { WorkspaceTour } from "./WorkspaceTour";
import { ConnectorBrands } from "./ConnectorShowcase";
import { PlatformLogo } from "./PlatformLogo";
import { m } from "motion/react";
import connectionCatalog from "@/lib/connection-catalog.json";
type Account = {
  email: string;
  tier: string;
  jobs_used: number;
  job_limit: number | null;
  project_limit: number;
  github_install_url?: string;
  github_connection?: {
    status: "not_connected" | "connected" | "reconnect_required";
    login: string | null;
  };
};
type Repository = { repository: string; branch: string; private: boolean };
export function Dashboard({
  initialProjectId = "",
  initialConnect = "",
}: {
  initialProjectId?: string;
  initialConnect?: string;
}) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [activity, setActivity] = useState<Activity>({
    jobs: [],
    findings: [],
  });
  const [newProject, setNewProject] = useState(false);
  const [publishingPlatform, setPublishingPlatform] = useState("github");
  const [connectorPlatform, setConnectorPlatform] = useState("");
  const [tab, setTab] = useState("overview");
  const [tourOpen, setTourOpen] = useState(false);
  const [tourSeen, setTourSeen] = useState(true);
  const [homeAnchor, setHomeAnchor] = useState("");
  useEffect(() => {
    if (!user) return;
    try {
      setTourSeen(
        localStorage.getItem("optimiser-tour-v1:" + user.uid) === "seen",
      );
    } catch {
      setTourSeen(false);
    }
  }, [user]);
  useEffect(() => {
    if (homeAnchor && !selected && !newProject && account)
      document.getElementById(homeAnchor)?.scrollIntoView({ block: "start" });
  }, [homeAnchor, selected, newProject, account]);
  function closeTour() {
    setTourOpen(false);
    setTourSeen(true);
    try {
      if (user) localStorage.setItem("optimiser-tour-v1:" + user.uid, "seen");
    } catch {
      /* Storage may be disabled. The tour remains available. */
    }
  }
  function home(connections = false) {
    if (connections) {
      router.push("/dashboard/connections");
      return;
    }
    selectedId.current = null;
    setSelected(null);
    setNewProject(false);
    setConnectorPlatform("");
    setHomeAnchor(connections ? "platform-connections" : "main-content");
    setError("");
    setNotice("");
  }
  async function tourNavigate(target: string) {
    if (target === "connect" || (!selected && !projects.length)) {
      beginProject();
      return;
    }
    if (!selected && projects[0]) await choose(projects[0]);
    setTab(target);
  }
  const [workspace, setWorkspace] = useState("{}");
  const [spec, setSpec] = useState("{}");
  const [strategy, setStrategy] = useState<{
    opportunities: {
      id: string;
      query: string;
      action: string;
      brief: { ready: boolean; dependencies: string[] };
    }[];
    dependencies: string[];
  } | null>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncError, setSyncError] = useState("");
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [activityReady, setActivityReady] = useState(false);
  const selectedId = useRef<string | null>(null);
  const refresh = useCallback(async () => {
    const [profile, list] = await Promise.all([
      api<Account>("account"),
      api<Project[]>("projects"),
    ]);
    setAccount(profile);
    setProjects(list);
    setLastSync(new Date());
    setSyncError("");
    setLoading(false);
  }, []);
  useEffect(() => {
    try {
      return onAuthStateChanged(firebaseAuth(), (current) => {
        if (!current) {
          router.replace("/login");
          return;
        }
        setUser(current);
        if (current.emailVerified)
          refresh().catch((error) => {
            setError(error.message);
            setLoading(false);
          });
      });
    } catch (error) {
      setLoading(false);
      setError(
        error instanceof Error ? error.message : "Authentication unavailable.",
      );
    }
  }, [refresh, router]);
  useEffect(() => {
    selectedId.current = selected?.id || null;
    if (!selected) return;
    let alive = true;
    let collecting = false;
    const collect = async () => {
      if (collecting) return;
      collecting = true;
      await Promise.all([
        api<Activity>("projects/" + selected.id + "/activity"),
        api<Project>("projects/" + selected.id),
      ])
        .then(([value, project]) => {
          if (alive && selectedId.current === selected.id) {
            setActivity(value);
            setSelected(project);
            setActivityReady(true);
            setLastSync(new Date());
            setSyncError("");
          }
        })
        .catch((error) => {
          if (alive) setSyncError(error.message);
        })
        .finally(() => {
          collecting = false;
        });
    };
    collect();
    const timer = setInterval(collect, 7000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [selected?.id]);
  async function action(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
    } catch (error) {
      setError(error instanceof Error ? error.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }
  function beginProject(platform = "github") {
    selectedId.current = null;
    setSelected(null);
    setNewProject(true);
    setPublishingPlatform(
      platform === "github" ||
        connectionCatalog.some(
          (item) =>
            item.platform === platform &&
            ["Publishing", "Repositories"].includes(item.group),
        )
        ? platform
        : "website",
    );
    setConnectorPlatform(
      platform === "github" || platform === "website" ? "" : platform,
    );
    setError("");
    setNotice("");
  }
  async function choose(project: Project, connection = "") {
    setSelected(project);
    setNewProject(false);
    setConnectorPlatform(connection);
    setTab(connection ? "connectors" : "overview");
    if (selected?.id !== project.id) {
      setActivity({ jobs: [], findings: [] });
      setActivityReady(false);
    }
    setWorkspace("{}");
    setStrategy(null);
    selectedId.current = project.id;
    const { provider: _provider, ...editable } = project.spec;
    setSpec(JSON.stringify(editable, null, 2));
    await action(async () => {
      const [research, brief] = await Promise.all([
        api<unknown>("projects/" + project.id + "/workspace"),
        api<NonNullable<typeof strategy>>(
          "projects/" + project.id + "/strategy",
        ),
      ]);
      if (selectedId.current === project.id) {
        setWorkspace(JSON.stringify(research, null, 2));
        setStrategy(brief);
      }
    });
  }
  const initialRouteOpened = useRef(false);
  useEffect(() => {
    if (!account || initialRouteOpened.current) return;
    initialRouteOpened.current = true;
    if (initialConnect) beginProject(initialConnect);
    else if (initialProjectId) {
      const project = projects.find((item) => item.id === initialProjectId);
      if (project) void choose(project);
      else setError("This website is unavailable in your workspace.");
    }
  }, [account, projects, initialProjectId, initialConnect]);
  async function connect() {
    await action(async () => {
      const value = await api<{ url: string }>("github/connect", "POST");
      window.location.assign(value.url);
    });
  }
  async function install() {
    await action(async () => {
      const value = await api<{ url: string }>("github/install", "POST");
      window.location.assign(value.url);
    });
  }
  async function loadRepos() {
    await action(async () => {
      const value = await api<{ repositories: Repository[] }>(
        "github/repositories",
      );
      setRepos(value.repositories);
      if (!value.repositories.length)
        setNotice(
          "Install the GitHub App on selected repositories, then refresh.",
        );
    });
  }
  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await action(async () => {
      let repo: Repository | undefined;
      if (publishingPlatform === "github") {
        const verified = await api<{ repositories: Repository[] }>(
          "github/repositories",
        );
        setRepos(verified.repositories);
        repo = verified.repositories.find(
          (item) => item.repository === data.get("repository"),
        );
        if (!repo) throw new Error("Choose a verified repository.");
      }
      const value = await api<Project>("projects", "POST", {
        spec: {
          name: data.get("name"),
          website_url: data.get("url"),
          repository: repo?.repository || "",
          publishing_platform: publishingPlatform,
          branch: repo?.branch || "main",
          website_types: [data.get("type")],
          goals: [String(data.get("goal"))].filter(Boolean),
          allowed_paths: String(data.get("paths"))
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          auto_fix: data.get("auto_fix") === "on",
          auto_merge: false,
        },
      });
      await refresh();
      const connection =
        connectorPlatform ||
        (publishingPlatform !== "github" && publishingPlatform !== "website"
          ? publishingPlatform
          : "");
      if (connection) {
        router.push(
          `/dashboard/connections/${connection}?project=${encodeURIComponent(value.id)}`,
        );
        return;
      }
      await choose(value, connection);
      setNewProject(false);
      setNotice(
        connection
          ? "Website added. Complete the platform connection below; your initial website audit runs separately."
          : "Website connected. Follow its audit progress below.",
      );
    });
  }
  return (
    <div className="workspace-shell workspace-v2">
      <WorkspaceSidebar
        projects={projects}
        selected={selected}
        tab={tab}
        email={account?.email || user?.email || ""}
        findings={activity.findings.filter((item) => item.active).length}
        onHome={home}
        onConnect={() => beginProject()}
        connectionsOpen={
          !selected && !newProject && homeAnchor === "platform-connections"
        }
        onSelect={(project) => {
          void choose(project);
        }}
        onTab={(value) => {
          if (value === "connectors")
            router.push(`/dashboard/connections?project=${selected?.id || ""}`);
          else setTab(value);
        }}
        onTour={() => setTourOpen(true)}
        onSignOut={() => {
          void action(async () => {
            await signOut(firebaseAuth());
            router.push("/login");
          });
        }}
      />
      <WorkspaceTour
        open={tourOpen}
        onClose={closeTour}
        onNavigate={(target) => {
          void tourNavigate(target);
        }}
      />
      <m.main
        id="main-content"
        className="dashboard-main"
        initial={false}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        <header className="topbar">
          <span>
            WORKSPACE /{" "}
            {selected?.spec.name ||
              (newProject ? "CONNECT WEBSITE" : "OVERVIEW")}
          </span>
          <div className="workspace-sync">
            <span className={syncError ? "sync-dot stale" : "sync-dot"} />
            <span>
              {syncError
                ? "Updates interrupted"
                : lastSync
                  ? `Updated ${lastSync.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                  : "Connecting…"}
            </span>
            <span className="pill">{account?.tier || "Workspace"}</span>
          </div>
        </header>
        {error && (
          <p role="alert" className="alert">
            {error}
          </p>
        )}
        {syncError && selected && (
          <div className="notice" role="status">
            Live updates paused. Your last saved results are still shown.{" "}
            {syncError}{" "}
            <button className="text-link" onClick={() => choose(selected)}>
              Reload project
            </button>
          </div>
        )}
        {notice && (
          <p role="status" className="notice">
            {notice}
          </p>
        )}
        {account && !tourSeen && !newProject && (
          <section className="workspace-welcome" aria-label="Getting started">
            <span className="welcome-symbol" aria-hidden="true">
              ↗
            </span>
            <div>
              <h2>New here? See how the agent works.</h2>
              <p>
                From your first audit to a reviewed repair, take a quick tour of
                your workspace.
              </p>
            </div>
            <button
              className="button secondary"
              onClick={() => setTourOpen(true)}
            >
              Take the tour
            </button>
            <button
              className="tour-close"
              aria-label="Dismiss welcome"
              onClick={closeTour}
            >
              ×
            </button>
          </section>
        )}
        {user && !user.emailVerified ? (
          <section className="panel">
            <h1>One small step.</h1>
            <p>Verify your email to connect a repository and begin.</p>
            <button
              className="button"
              onClick={() =>
                action(async () => {
                  await sendEmailVerification(user);
                  setNotice("Verification email sent.");
                })
              }
            >
              Resend verification
            </button>
            <button
              className="text-link"
              onClick={() =>
                action(async () => {
                  await user.reload();
                  await user.getIdToken(true);
                  setUser(user);
                  if (user.emailVerified) await refresh();
                })
              }
            >
              I’ve verified my email ↗
            </button>
          </section>
        ) : !account ? (
          <section className="panel">
            <span className="eyebrow">YOUR WORKSPACE</span>
            <h1>
              {loading
                ? "Loading your workspace"
                : "Your workspace couldn’t be loaded"}
            </h1>
            <p>
              {loading
                ? "Checking your session and loading your saved websites. This can take a moment when the service starts."
                : "Your session or the workspace service may be unavailable. Your saved websites have not been changed."}
            </p>
            {loading ? (
              <div
                className="workspace-skeleton"
                role="status"
                aria-label="Loading saved websites"
              >
                <span />
                <span />
                <span />
              </div>
            ) : (
              <div className="actions">
                <button
                  className="button"
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      setLoading(true);
                      try {
                        await refresh();
                      } finally {
                        setLoading(false);
                      }
                    })
                  }
                >
                  Reload workspace
                </button>
                <Link className="text-link" href="/login">
                  Sign in again ↗
                </Link>
              </div>
            )}
          </section>
        ) : newProject ? (
          <>
            <section className="page-heading">
              <span className="eyebrow">A NEW CONNECTION</span>
              <h1>
                Give your website
                <br />
                <em>a working partner.</em>
              </h1>
              <p>
                Connect your website first, then grant access to its publishing
                platform and search evidence.
              </p>
              <ConnectorBrands />
            </section>
            <section className="panel">
              <label>
                Website platform
                <select
                  value={publishingPlatform}
                  onChange={(event) => {
                    setPublishingPlatform(event.target.value);
                    setConnectorPlatform("");
                  }}
                >
                  {[
                    ["github", "GitHub"],
                    ["wordpress", "WordPress"],
                    ["woocommerce", "WooCommerce"],
                    ["shopify", "Shopify"],
                    ["webflow", "Webflow"],
                    ["gitlab", "GitLab"],
                    ["bitbucket", "Bitbucket"],
                    ["wix", "Wix"],
                    ["squarespace", "Squarespace"],
                    ["framer", "Framer"],
                    ["sanity", "Sanity"],
                    ["contentful", "Contentful"],
                    ["website", "Other website"],
                  ].map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              {publishingPlatform === "github" && (
                <>
                  <h2>01 · Repository access</h2>
                  <div className="actions">
                    {account.github_install_url && (
                      <button
                        className="button secondary"
                        disabled={busy}
                        onClick={install}
                      >
                        Install GitHub App ↗
                      </button>
                    )}
                    <button
                      className="button secondary"
                      disabled={busy}
                      onClick={connect}
                    >
                      {account.github_connection?.status === "connected"
                        ? "Refresh GitHub authorisation ↗"
                        : "Connect GitHub account ↗"}
                    </button>
                    <button
                      className="text-link"
                      disabled={busy}
                      onClick={loadRepos}
                    >
                      Refresh repositories ↻
                    </button>
                  </div>
                  <p>
                    Installation limits access to selected repositories. Account
                    authorization verifies which repositories you can manage.
                  </p>
                  {account.github_connection?.status === "connected" && (
                    <p className="audit-policy-strip">
                      GitHub connected. Choose a granted repository below, or
                      install the app on another repository.
                    </p>
                  )}
                </>
              )}
              {publishingPlatform !== "github" && (
                <p>
                  Your first audit checks the live website. Configure publishing
                  access in Connectors after creating the project.
                </p>
              )}
            </section>
            <form className="panel" onSubmit={create}>
              <h2>02 · Your website</h2>
              <div className="form-grid">
                <label>
                  Project name
                  <input name="name" required maxLength={100} />
                </label>
                <label>
                  Deployed website URL
                  <input
                    name="url"
                    type="url"
                    required
                    placeholder="https://example.com"
                  />
                </label>
                {publishingPlatform === "github" && (
                  <label>
                    Verified repository
                    <select name="repository" required>
                      <option value="">Select repository</option>
                      {repos.map((repo) => (
                        <option key={repo.repository}>{repo.repository}</option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  Website type
                  <select name="type">
                    <option value="generic">General website</option>
                    <option value="ecommerce">Ecommerce</option>
                    <option value="local">Local business</option>
                    <option value="saas">SaaS</option>
                    <option value="publishing">Publishing</option>
                    <option value="docs">Documentation</option>
                  </select>
                </label>
                <label>
                  Directories to monitor
                  <input
                    name="paths"
                    defaultValue="public,web,src,app,pages,content"
                    required
                  />
                </label>
                <label>
                  What matters to your business?
                  <input
                    name="goal"
                    placeholder="Help qualified customers find our products"
                    maxLength={500}
                  />
                </label>
              </div>
              <label className="checkbox">
                <input name="auto_fix" type="checkbox" />
                Allow supported repairs within connection permissions
              </label>
              <p>
                Content publication starts off. Reviewed facts and original
                source material are required before enabling content refreshes.
                You review and merge hosted PRs.
              </p>
              <button
                className="button"
                disabled={
                  busy || (publishingPlatform === "github" && !repos.length)
                }
              >
                Connect & start audit ↗
              </button>
            </form>
          </>
        ) : selected ? (
          <>
            <section className="page-heading">
              <div className="project-context">
                <span className="eyebrow">YOUR WEBSITE</span>
                <span className="audit-badge">
                  {selected.spec.enabled
                    ? "Monitoring enabled"
                    : "Monitoring paused"}
                </span>
              </div>
              <h1 className="platform-lockup">
                <PlatformLogo
                  platform={String(
                    selected.spec.publishing_platform || "github",
                  )}
                  size={32}
                />
                {selected.spec.name}
              </h1>
              <p className="project-origin">{selected.spec.website_url}</p>
              <p className="project-repository">
                {selected.spec.repository} <span>·</span>{" "}
                {String(selected.spec.branch || "main")}
              </p>
              <div className="actions">
                <button
                  className="button"
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      await api("projects/" + selected.id + "/jobs", "POST");
                      setNotice("Audit queued.");
                    })
                  }
                >
                  Run audit ↗
                </button>
                <button
                  className="text-link"
                  onClick={() =>
                    action(async () => {
                      const updated = await api<Project>(
                        "projects/" + selected.id,
                        "PATCH",
                        {
                          ...selected.spec,
                          enabled: !selected.spec.enabled,
                        },
                      );
                      setSelected(updated);
                      setSpec(JSON.stringify(updated.spec, null, 2));
                      await refresh();
                    })
                  }
                >
                  {selected.spec.enabled
                    ? "Pause monitoring"
                    : "Resume monitoring"}
                </button>
              </div>
            </section>
            {!activityReady && (
              <p className="audit-loading" role="status">
                Loading audit history and evidence…
              </p>
            )}
            {activityReady && (
              <AuditWorkspace
                key={selected.id}
                project={selected}
                activity={activity}
                tab={tab}
                onTab={(value) => {
                  if (value === "connectors")
                    router.push(
                      `/dashboard/connections?project=${selected?.id || ""}`,
                    );
                  else setTab(value);
                }}
              />
            )}
            {tab === "connectors" && (
              <Connectors
                key={"connectors:" + selected.id + ":" + connectorPlatform}
                project={selected}
                initialPlatform={
                  connectorPlatform ||
                  String(selected.spec.publishing_platform || "search_console")
                }
              />
            )}
            {tab === "research" && (
              <section className="panel">
                <h2>Useful content starts with your evidence.</h2>
                <p>
                  Add owner-reviewed original materials, measured search
                  observations and citation transcripts. Synthetic observations
                  must be labelled. Unsupported claims remain dependencies.
                </p>
                <label>
                  Research workspace JSON
                  <textarea
                    value={workspace}
                    onChange={(event) => setWorkspace(event.target.value)}
                    rows={16}
                    spellCheck={false}
                  />
                </label>
                <button
                  className="button"
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      await api(
                        "projects/" + selected.id + "/workspace",
                        "PUT",
                        JSON.parse(workspace),
                      );
                      setStrategy(
                        await api<NonNullable<typeof strategy>>(
                          "projects/" + selected.id + "/strategy",
                        ),
                      );
                      setNotice("Research saved and strategy refreshed.");
                    })
                  }
                >
                  Save evidence ↗
                </button>
                <div className="opportunities">
                  {strategy?.opportunities.map((opportunity) => (
                    <article key={opportunity.id}>
                      <h3>{opportunity.query}</h3>
                      <span className="pill">
                        {opportunity.action.replaceAll("_", " ")}
                      </span>
                      <p>
                        {opportunity.brief.dependencies.join("; ") ||
                          "Supported brief ready"}
                      </p>
                      {opportunity.brief.ready &&
                        opportunity.action === "refresh" && (
                          <button
                            className="button secondary"
                            disabled={busy}
                            onClick={() =>
                              action(async () => {
                                await api(
                                  "projects/" +
                                    selected.id +
                                    "/content/" +
                                    opportunity.id,
                                  "POST",
                                );
                                setNotice(
                                  "Content refresh queued; project publication policy and checks still apply.",
                                );
                              })
                            }
                          >
                            Queue supported refresh ↗
                          </button>
                        )}
                    </article>
                  ))}
                </div>
                <details>
                  <summary>Content opportunities & dependencies</summary>
                  <pre>{JSON.stringify(strategy, null, 2)}</pre>
                </details>
              </section>
            )}
            {tab === "policy" && (
              <section className="panel">
                <h2>Monitoring & repair policy</h2>
                <div className="audit-policy-strip">
                  <p>
                    <strong>
                      {selected.spec.auto_fix
                        ? "Repair proposals enabled"
                        : "Audit only"}
                    </strong>{" "}
                    · Hosted pull requests require your review and merge.
                    Private pages and crawler preferences are preserved.
                  </p>
                </div>
                <p>
                  Configure monitored paths, route mappings, verified facts,
                  crawler preferences and required checks. Application policy
                  preserves private pages and unsupported claims. Build commands
                  run in an isolated executor; local workers use Docker and
                  hosted workers can use Cloud Build.
                </p>
                <AgentPreferences value={spec} onChange={setSpec} />
                <details>
                  <summary>Advanced project settings</summary>
                  <label>
                    Project settings JSON
                    <textarea
                      value={spec}
                      onChange={(event) => setSpec(event.target.value)}
                      rows={18}
                      spellCheck={false}
                    />
                  </label>
                </details>
                <button
                  className="button"
                  disabled={busy}
                  onClick={() =>
                    action(async () => {
                      const updated = await api<Project>(
                        "projects/" + selected.id,
                        "PATCH",
                        JSON.parse(spec),
                      );
                      setSelected(updated);
                      await refresh();
                      setNotice("Policy updated.");
                    })
                  }
                >
                  Save policy ↗
                </button>
              </section>
            )}
          </>
        ) : (
          <>
            <section className="page-heading">
              <span className="eyebrow">WEBSITE OPERATIONS</span>
              <h1>
                Your search visibility,
                <br />
                <em>in good hands.</em>
              </h1>
              <p>
                Your websites, the agent’s work, and what needs your attention.
              </p>
            </section>
            <div className="metrics">
              <article>
                <span>CONNECTED WEBSITES</span>
                <strong>
                  {projects.length}
                  <small>/{account.project_limit}</small>
                </strong>
                <p>Each with its own goals and policy.</p>
              </article>
              <article>
                <span>THIS MONTH’S JOBS</span>
                <strong>
                  {account.jobs_used}
                  <small>/{account.job_limit ?? "∞"}</small>
                </strong>
                <p>
                  Audits, content jobs, review follow-ups and citation probes.
                </p>
              </article>
              <article>
                <span>MONITORING ENABLED</span>
                <strong>
                  {projects.filter((project) => project.spec.enabled).length}
                  <small>/{projects.length}</small>
                </strong>
                <p>Checks follow relevant repository changes.</p>
              </article>
            </div>
            <section className="section">
              <div className="section-heading">
                <h2>Your projects</h2>
                <button className="button" onClick={() => beginProject()}>
                  Connect website ＋
                </button>
              </div>
              <div className="project-grid">
                {projects.map((project) => (
                  <button
                    className="project-card"
                    key={project.id}
                    onClick={() => choose(project)}
                  >
                    <span className="pill">
                      {project.spec.enabled ? "Monitoring" : "Paused"}
                    </span>
                    <h3 className="platform-lockup">
                      <PlatformLogo
                        platform={String(
                          project.spec.publishing_platform || "github",
                        )}
                        size={23}
                      />
                      {project.spec.name}
                    </h3>
                    <p>{project.spec.website_url}</p>
                    <div className="project-health">
                      <span>OBSERVED HEALTH</span>
                      <strong>
                        {project.last_report.score ?? "-"}
                        <small>/100</small>
                      </strong>
                    </div>
                    <span>
                      {project.last_report.pages ?? 0} pages observed ↗
                    </span>
                  </button>
                ))}
              </div>
              {!projects.length && (
                <div className="empty">
                  <h3>A good place to start.</h3>
                  <p>
                    Connect your website and publishing platform. Your first
                    audit will start automatically.
                  </p>
                  <button className="button" onClick={() => beginProject()}>
                    Connect your first website ↗
                  </button>
                </div>
              )}
            </section>
            <section className="panel">
              <h2>Your connected tools</h2>
              <p>
                Manage your publishing platforms, search data and repository
                access from a dedicated workspace.
              </p>
              <Link className="button secondary" href="/dashboard/connections">
                View connections ↗
              </Link>
            </section>
          </>
        )}
        <footer>
          Your Optimiser · Measured improvements, with a record of every change.
          <nav aria-label="Workspace help and policies">
            <Link href="/how-it-works">How it works</Link>
            <Link href="/contact">Help</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/terms">Terms</Link>
          </nav>
        </footer>
      </m.main>
    </div>
  );
}
