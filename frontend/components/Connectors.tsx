"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Project } from "@/lib/api";
import { PlatformLogo } from "./PlatformLogo";
import { testedPlatform, coverageLabels } from "@/lib/platforms";

type Definition = {
  name: string;
  group: string;
  resource: string;
  options: string[];
  secrets: string[];
  write: boolean;
  note: string;
  source: string;
};
type Proposal = {
  id: string;
  status: string;
  reason: string;
  resource_id: string;
  diff: Record<string, { before: string; after: string }>;
  verification?: Record<string, unknown>;
  pr?: { url: string };
};
type Evidence = {
  id: string;
  collection: {
    collected_at: string;
    complete: boolean;
    warnings: string[];
    cost_usd: number | null;
    measurement: string;
    records: { id: string; kind: string; fields: Record<string, unknown> }[];
  };
};
type Connection = {
  platform: string;
  definition: Definition;
  connected: boolean;
  status: string;
  config: {
    label?: string;
    resource?: string;
    options?: Record<string, string>;
    allow_writes?: boolean;
    auto_apply?: boolean;
    enabled?: boolean;
    interval_seconds?: number;
  };
  credential_fields: string[];
  webhook_url?: string | null;
  last_sync: number | null;
  last_error: string | null;
  evidence: Evidence[];
  proposals: Proposal[];
  history: { time: number; status: string; proposal: string }[];
};
type Connections = { connections: Connection[] };
const label = (value: string) => value.replaceAll("_", " ");
const pastDate = (days: number) =>
  new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
function external(value?: string) {
  try {
    const url = new URL(value || "");
    return url.protocol === "https:" ? url.href : undefined;
  } catch {
    return undefined;
  }
}

export function Connectors({ project }: { project: Project }) {
  const [data, setData] = useState<Connections | null>(null);
  const [platform, setPlatform] = useState("search_console");
  const [resource, setResource] = useState("");
  const [options, setOptions] = useState<Record<string, string>>({});
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [writes, setWrites] = useState(false);
  const [automatic, setAutomatic] = useState(false);
  const [enabled, setEnabled] = useState(true);
  const [interval, setIntervalHours] = useState(24);
  const [request, setRequest] = useState({
    start: pastDate(7),
    end: pastDate(1),
    limit: 25,
    resource_id: "",
    query: "",
    engine: "google",
    model: "",
    market: "United States",
    experiment: "visibility",
  });
  const [proposal, setProposal] = useState("");
  const [importBody, setImportBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const path = "projects/" + project.id + "/connectors";
  const selected = data?.connections.find((item) => item.platform === platform);
  const refresh = useCallback(async () => {
    setData(await api<Connections>("projects/" + project.id + "/connectors"));
  }, [project.id]);
  useEffect(() => {
    let alive = true;
    const collect = () =>
      api<Connections>("projects/" + project.id + "/connectors")
        .then((value) => {
          if (alive) setData(value);
        })
        .catch((failure) => {
          if (alive) setError(failure.message);
        });
    collect();
    const timer = window.setInterval(collect, 10000);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [project.id]);
  function choose(item: Connection) {
    setPlatform(item.platform);
    setResource(item.config.resource || "");
    setOptions(item.config.options || {});
    setCredentials({});
    setWrites(item.config.allow_writes || false);
    setAutomatic(item.config.auto_apply || false);
    setEnabled(item.config.enabled !== false);
    setIntervalHours((item.config.interval_seconds || 86400) / 3600);
    setProposal("");
    setNotice("");
    setError("");
  }
  async function action(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await work();
      await refresh();
    } catch (failure) {
      setError(
        failure instanceof Error
          ? failure.message
          : "Connection action failed.",
      );
    } finally {
      setBusy(false);
    }
  }
  const groups = [
    ...new Set(data?.connections.map((item) => item.definition.group)),
  ];
  const connected =
    data?.connections.filter((item) => item.connected).length || 0;
  return (
    <section className="connector-workspace" aria-label="Website connectors">
      <div className="panel connector-intro">
        <span className="eyebrow">CONNECTED EVIDENCE & ACTIONS</span>
        <h2>Give your agent the right access.</h2>
        <p>
          Connect where your content lives, see how people find it, and verify
          changes after publication. Each connection has its own permissions.
        </p>
        <div className="connector-summary">
          <span>
            <strong>{connected}</strong> connected platforms
          </span>
          <span>Credentials encrypted at rest</span>
          <span>Publication follows project policy</span>
        </div>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="audit-policy-strip" role="status">
          {notice}
        </p>
      )}
      {!data && <p role="status">Loading available platforms…</p>}
      {data && (
        <label className="panel connector-mobile-picker">
          Choose a platform
          <select
            value={platform}
            onChange={(event) => {
              const item = data.connections.find(
                (value) => value.platform === event.target.value,
              );
              if (item) choose(item);
            }}
          >
            {groups.map((group) => (
              <optgroup key={group} label={group}>
                {data.connections
                  .filter((item) => item.definition.group === group)
                  .map((item) => (
                    <option key={item.platform} value={item.platform}>
                      {item.definition.name}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
        </label>
      )}
      <div className="connector-layout">
        <nav
          className="panel connector-directory"
          aria-label="Connector platforms"
        >
          {groups.map((group) => (
            <div key={group}>
              <h3>{group}</h3>
              {data?.connections
                .filter((item) => item.definition.group === group)
                .map((item) => (
                  <button
                    key={item.platform}
                    type="button"
                    aria-pressed={item.platform === platform}
                    onClick={() => choose(item)}
                  >
                    <span className="platform-lockup">
                      <PlatformLogo platform={item.platform} size={20} />
                      {item.definition.name}
                    </span>
                    <small>
                      {item.connected ? label(item.status) : "Not connected"}
                    </small>
                  </button>
                ))}
            </div>
          ))}
        </nav>
        {selected && (
          <div className="connector-detail">
            <form
              className="panel"
              onSubmit={(event) => {
                event.preventDefault();
                action(async () => {
                  await api(path + "/" + platform, "PUT", {
                    platform,
                    resource,
                    options,
                    credentials,
                    allow_writes: writes,
                    auto_apply: writes && automatic,
                    enabled,
                    interval_seconds: interval * 3600,
                  });
                  setCredentials({});
                  setNotice(
                    "Connection saved. Collect evidence to check access and see supported proposals.",
                  );
                });
              }}
            >
              <div className="connector-title">
                <h2 className="platform-lockup">
                  <PlatformLogo platform={platform} size={28} />
                  {selected.definition.name}
                </h2>
                <span className="audit-badge">{label(selected.status)}</span>
              </div>
              {testedPlatform(platform) && (
                <p className="platform-coverage">
                  {coverageLabels[testedPlatform(platform)!.coverage]} ·
                  Connected does not mean a check has passed.
                </p>
              )}
              <p>{selected.definition.note}</p>
              <p>
                <a
                  href={external(selected.definition.source)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Platform documentation ↗
                </a>
              </p>
              {selected.last_error && (
                <p role="status">{selected.last_error}</p>
              )}
              <label>
                Account or resource
                <input
                  required
                  value={resource}
                  maxLength={500}
                  placeholder={selected.definition.resource}
                  onChange={(event) => setResource(event.target.value)}
                />
              </label>
              <div className="form-grid">
                {selected.definition.options.map((name) => (
                  <label key={name}>
                    {label(name)}
                    <input
                      value={options[name] || ""}
                      maxLength={500}
                      onChange={(event) =>
                        setOptions({ ...options, [name]: event.target.value })
                      }
                    />
                  </label>
                ))}
              </div>
              {selected.definition.secrets.length > 0 && (
                <details className="connector-credentials">
                  <summary>Credentials and access</summary>
                  <p>
                    Use credentials scoped to this account. Saved values are
                    never returned here. Leave a field untouched to keep it;
                    disconnect to remove all stored credentials.
                  </p>
                  <div className="form-grid">
                    {selected.definition.secrets.map((name) => (
                      <label key={name}>
                        {label(name)}{" "}
                        {selected.credential_fields.includes(name) && (
                          <small>Saved</small>
                        )}
                        <input
                          type="password"
                          autoComplete="new-password"
                          spellCheck={false}
                          value={credentials[name] || ""}
                          onChange={(event) =>
                            setCredentials({
                              ...credentials,
                              [name]: event.target.value,
                            })
                          }
                        />
                      </label>
                    ))}
                  </div>
                </details>
              )}
              <div className="form-grid">
                <label>
                  Recheck interval (hours)
                  <input
                    type="number"
                    min={1}
                    max={168}
                    value={interval}
                    onChange={(event) =>
                      setIntervalHours(Number(event.target.value))
                    }
                  />
                </label>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(event) => setEnabled(event.target.checked)}
                  />
                  Enable connection
                </label>
              </div>
              {selected.definition.write && (
                <>
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={writes}
                      onChange={(event) => {
                        setWrites(event.target.checked);
                        if (!event.target.checked) setAutomatic(false);
                      }}
                    />
                    Allow supported writes
                  </label>
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={automatic}
                      disabled={!writes}
                      onChange={(event) => setAutomatic(event.target.checked)}
                    />
                    Automatically apply grounded repairs within project policy
                  </label>
                  {!project.spec.auto_fix && (
                    <p>
                      Project repairs are paused. Enable them in Project
                      settings before applying changes.
                    </p>
                  )}
                </>
              )}
              <div className="actions">
                <button className="button" disabled={busy}>
                  Save connection
                </button>
                {selected.connected &&
                  [
                    "search_console",
                    "shopify",
                    "ga4",
                    "business_profile",
                    "webflow",
                    "gitlab",
                    "bitbucket",
                  ].includes(platform) && (
                    <button
                      type="button"
                      className="button secondary"
                      disabled={busy}
                      onClick={() =>
                        action(async () => {
                          const result = await api<{ url: string }>(
                            path + "/" + platform + "/oauth",
                            "POST",
                          );
                          window.location.assign(result.url);
                        })
                      }
                    >
                      Authorize account ↗
                    </button>
                  )}
                {selected.connected && (
                  <button
                    type="button"
                    className="text-link"
                    disabled={busy}
                    onClick={() =>
                      action(async () => {
                        await api(path + "/" + platform, "DELETE");
                        setCredentials({});
                        setNotice(
                          "Stored connection credentials removed. You can also revoke access in the platform's settings.",
                        );
                      })
                    }
                  >
                    Disconnect
                  </button>
                )}
              </div>
            </form>
            {selected.connected &&
              !["server_logs", "deployment"].includes(platform) && (
                <form
                  className="panel"
                  onSubmit={(event) => {
                    event.preventDefault();
                    action(async () => {
                      await api(
                        path + "/" + platform + "/collect",
                        "POST",
                        request,
                      );
                      setNotice(
                        "Collection queued. Results and proposals will appear here; progress is in AI audits & logs.",
                      );
                    });
                  }}
                >
                  <h3>Collect evidence</h3>
                  <div className="form-grid">
                    <label>
                      From
                      <input
                        type="date"
                        value={request.start}
                        onChange={(e) =>
                          setRequest({ ...request, start: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Through
                      <input
                        type="date"
                        value={request.end}
                        onChange={(e) =>
                          setRequest({ ...request, end: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Specific resource or source path
                      <input
                        value={request.resource_id}
                        onChange={(e) =>
                          setRequest({
                            ...request,
                            resource_id: e.target.value,
                          })
                        }
                        placeholder="Optional page, product, entry or source-file ID"
                      />
                    </label>
                    <label>
                      Row budget
                      <input
                        type="number"
                        min={1}
                        max={100}
                        value={request.limit}
                        onChange={(e) =>
                          setRequest({
                            ...request,
                            limit: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                  </div>
                  {["dataforseo", "ai_visibility"].includes(platform) && (
                    <>
                      <p>
                        Each request can incur a provider charge. These
                        experiments are collected only when requested.
                      </p>
                      <label>
                        Question or keyword
                        <input
                          required
                          value={request.query}
                          onChange={(e) =>
                            setRequest({ ...request, query: e.target.value })
                          }
                          maxLength={500}
                        />
                      </label>
                      <label>
                        Market
                        <input
                          value={request.market}
                          onChange={(e) =>
                            setRequest({ ...request, market: e.target.value })
                          }
                        />
                      </label>
                    </>
                  )}
                  {platform === "ai_visibility" && (
                    <div className="form-grid">
                      <label>
                        API engine
                        <select
                          value={request.engine}
                          onChange={(e) =>
                            setRequest({ ...request, engine: e.target.value })
                          }
                        >
                          {["google", "openai", "anthropic", "perplexity"].map(
                            (name) => (
                              <option key={name}>{name}</option>
                            ),
                          )}
                        </select>
                      </label>
                      <label>
                        Explicit model identifier
                        <input
                          required
                          value={request.model}
                          onChange={(e) =>
                            setRequest({ ...request, model: e.target.value })
                          }
                        />
                      </label>
                      <label>
                        Experiment name
                        <input
                          value={request.experiment}
                          onChange={(e) =>
                            setRequest({
                              ...request,
                              experiment: e.target.value,
                            })
                          }
                        />
                      </label>
                    </div>
                  )}
                  <button className="button secondary" disabled={busy}>
                    Collect evidence
                  </button>
                  {selected.last_sync && (
                    <p>
                      Last collection:{" "}
                      {new Date(selected.last_sync * 1000).toLocaleString()}
                    </p>
                  )}
                </form>
              )}
            <section className="panel">
              <h3>Observed evidence</h3>
              {selected.evidence.length > 0 && (
                <button
                  type="button"
                  className="text-link"
                  onClick={() => {
                    const file = new Blob(
                      [
                        JSON.stringify(
                          {
                            platform,
                            evidence: selected.evidence,
                            proposals: selected.proposals,
                          },
                          null,
                          2,
                        ),
                      ],
                      { type: "application/json" },
                    );
                    const url = URL.createObjectURL(file);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download =
                      "your-optimiser-" + platform + "-evidence.json";
                    link.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Export observations & proposals ↓
                </button>
              )}
              {!selected.evidence.length && (
                <p>
                  No observations yet. Connecting an account does not establish
                  that a check passed.
                </p>
              )}
              {selected.evidence
                .slice()
                .reverse()
                .map((item) => (
                  <details key={item.id}>
                    <summary>
                      {new Date(item.collection.collected_at).toLocaleString()}{" "}
                      · {item.collection.records.length} records ·{" "}
                      {label(item.collection.measurement)}
                    </summary>
                    <p>
                      {item.collection.complete
                        ? "Provider response reported complete coverage for this request."
                        : "Bounded or partial coverage; additional data may exist."}
                    </p>
                    {item.collection.cost_usd != null && (
                      <p>
                        Reported provider charge: $
                        {item.collection.cost_usd.toFixed(4)}
                      </p>
                    )}
                    {item.collection.warnings.map((warning) => (
                      <p key={warning}>{warning}</p>
                    ))}
                    <p>
                      Evidence reference: <code>{item.id}</code>
                    </p>
                    <pre>
                      {JSON.stringify(item.collection.records, null, 2)}
                    </pre>
                  </details>
                ))}
            </section>
            <section className="panel">
              <h3>Reviewable repairs</h3>
              {!selected.proposals.length && (
                <p>
                  No supported repairs proposed. Missing evidence stays
                  unresolved; the agent does not invent business facts to raise
                  a score.
                </p>
              )}
              {selected.proposals
                .slice()
                .reverse()
                .map((item) => (
                  <article key={item.id} className="connector-proposal">
                    <div className="connector-title">
                      <h4>{item.resource_id}</h4>
                      <span className="audit-badge">{label(item.status)}</span>
                    </div>
                    <p>{item.reason}</p>
                    {Object.entries(item.diff).map(([key, value]) => (
                      <div key={key}>
                        <strong>{label(key)}</strong>
                        <pre className="connector-before">
                          {value.before || "(missing)"}
                        </pre>
                        <pre className="connector-after">{value.after}</pre>
                      </div>
                    ))}
                    {item.verification && (
                      <pre>{JSON.stringify(item.verification, null, 2)}</pre>
                    )}
                    {external(item.pr?.url) && (
                      <a
                        href={external(item.pr?.url)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Review pull request ↗
                      </a>
                    )}
                    <div className="actions">
                      {["apply", "rollback", "verify"]
                        .filter((operation) =>
                          operation === "apply"
                            ? item.status === "proposed"
                            : operation === "rollback"
                              ? [
                                  "verified",
                                  "deployed_verified",
                                  "waiting_publication",
                                ].includes(item.status)
                              : [
                                  "verified",
                                  "waiting_publication",
                                  "pr_opened",
                                ].includes(item.status),
                        )
                        .map((operation) => (
                          <button
                            type="button"
                            className="button secondary"
                            disabled={
                              busy ||
                              (!selected.config.allow_writes &&
                                operation !== "verify")
                            }
                            key={operation}
                            onClick={() =>
                              action(async () => {
                                await api(
                                  path +
                                    "/" +
                                    platform +
                                    "/proposals/" +
                                    item.id +
                                    "/" +
                                    operation,
                                  "POST",
                                );
                                setNotice(
                                  label(operation) +
                                    " queued. Follow the outcome in activity.",
                                );
                              })
                            }
                          >
                            {operation === "apply"
                              ? "Apply supported change"
                              : operation === "rollback"
                                ? "Restore previous values"
                                : "Verify live page"}
                          </button>
                        ))}
                    </div>
                  </article>
                ))}
              {selected.definition.write && (
                <details>
                  <summary>Propose a supported change</summary>
                  <p>
                    Use resource_id, changes, reason, evidence_ids and optional
                    fact_ids and verification_url. Fields and evidence are
                    validated on the server.
                  </p>
                  <label>
                    Proposal JSON
                    <textarea
                      rows={7}
                      value={proposal}
                      onChange={(e) => setProposal(e.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className="button secondary"
                    disabled={busy || !proposal}
                    onClick={() =>
                      action(async () => {
                        await api(
                          path + "/" + platform + "/proposals",
                          "POST",
                          JSON.parse(proposal),
                        );
                        setProposal("");
                        setNotice("Proposal recorded for review.");
                      })
                    }
                  >
                    Preview supported proposal
                  </button>
                </details>
              )}
            </section>
            {["server_logs", "ai_visibility"].includes(platform) &&
              selected.connected && (
                <section className="panel">
                  <h3>Import observed records</h3>
                  <p>
                    Use structured JSON with kind, records and source. Logs omit
                    visitor IPs, cookies and query strings. Consumer
                    observations remain separate from API experiments.
                  </p>
                  <label>
                    Evidence import JSON
                    <textarea
                      rows={8}
                      value={importBody}
                      onChange={(e) => setImportBody(e.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className="button secondary"
                    disabled={busy || !importBody}
                    onClick={() =>
                      action(async () => {
                        await api(
                          path + "/" + platform + "/import",
                          "POST",
                          JSON.parse(importBody),
                        );
                        setImportBody("");
                        setNotice("Observed records imported.");
                      })
                    }
                  >
                    Import evidence
                  </button>
                </section>
              )}
            {selected.history.length > 0 && (
              <section className="panel">
                <h3>Connection activity</h3>
                <ol>
                  {selected.history
                    .slice()
                    .reverse()
                    .map((item, index) => (
                      <li key={index}>
                        {new Date(item.time * 1000).toLocaleString()} ·{" "}
                        {label(item.status)}
                      </li>
                    ))}
                </ol>
              </section>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
