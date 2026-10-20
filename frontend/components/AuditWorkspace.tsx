"use client";

import { useState } from "react";
import type { Activity, AuditReport, Job, Project } from "@/lib/api";

const labels: Record<string, string> = {
  queued: "Queued",
  running: "Auditing",
  complete: "Complete",
  blocked: "Needs attention",
  failed: "Failed",
  waiting_checks: "Checking proposal",
  waiting_deployment: "Awaiting deployment",
  needs_data: "Needs evidence",
  healthy: "Passed",
  defect: "Issue found",
  not_checked: "Not assessed",
  not_applicable: "Not applicable",
  needs_model: "Awaiting review",
  read_file: "Read source file",
  get_diff: "Inspect changed routes",
  get_check: "Consult check guidance",
  inspect_route: "Inspect page evidence",
  crawl_page: "Inspect page",
  run_checks: "Run verification",
  apply_patch: "Stage proposed repair",
  audit: "Website audit",
  push: "Website change",
  followup: "PR follow-up",
};
export function human(value: string) {
  return labels[value] || value.replaceAll("_", " ");
}
function date(value?: number) {
  return value
    ? new Date(value * 1000).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Time not recorded";
}
function duration(job: Job) {
  return job.created_at && job.updated_at
    ? `${Math.max(0, Math.round(job.updated_at - job.created_at))}s`
    : "—";
}
function reportFor(job: Job): AuditReport | undefined {
  return job.result.after_report
    ? { ...job.result.report, ...job.result.after_report }
    : job.result.report;
}
function safeLink(value?: string, github = false) {
  try {
    const url = new URL(value || "");
    return url.protocol === "https:" &&
      (!github || url.hostname === "github.com")
      ? url.href
      : undefined;
  } catch {
    return undefined;
  }
}
function Badge({ value }: { value: string }) {
  return <span className={`audit-badge state-${value}`}>{human(value)}</span>;
}
function Metric({
  label,
  value,
  note,
}: {
  label: string;
  value: string | number;
  note: string;
}) {
  return (
    <article>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  );
}

export function AuditWorkspace({
  project,
  activity,
  tab,
  onTab,
}: {
  project: Project;
  activity: Activity;
  tab: string;
  onTab: (tab: string) => void;
}) {
  const [filter, setFilter] = useState("active");
  const [query, setQuery] = useState("");
  const [jobFilter, setJobFilter] = useState("all");
  const active = activity.findings.filter((item) => item.active);
  const defects = active.filter((item) => item.details.status === "defect");
  const unresolved = active.filter(
    (item) => item.details.status === "unresolved",
  );
  const audits = activity.jobs.filter(
    (job) => job.status === "complete" && reportFor(job),
  );
  const report = project.last_report;
  const coverage = report.coverage || [];
  const assessed = coverage.filter((item) =>
    ["healthy", "defect"].includes(item.state),
  );
  const working = activity.jobs.filter((job) =>
    ["queued", "running", "waiting_checks", "waiting_deployment"].includes(
      job.status,
    ),
  );
  const latestRepair = activity.jobs.find((job) =>
    safeLink(job.result.pr?.url, true),
  );
  const liveEvents = (working[0]?.events || []).slice(-4);
  const liveMessage = liveEvents.at(-1)?.message || working[0]?.result.summary;
  const fixes = activity.jobs.reduce(
    (total, job) => total + (job.result.verified_fixes || 0),
    0,
  );
  const trend = audits
    .slice(0, 8)
    .reverse()
    .filter((job) => typeof reportFor(job)?.score === "number");
  const findings = activity.findings.filter(
    (item) =>
      (filter === "all" ||
        (filter === "resolved"
          ? !item.active
          : item.active &&
            (filter === "active" || item.details.status === filter))) &&
      `${item.details.summary} ${item.details.url} ${item.details.check_id}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    <div className="audit-workspace">
      <div className="audit-metrics">
        <Metric
          label={
            coverage.some((item) =>
              ["needs_model", "needs_data", "not_checked"].includes(item.state),
            )
              ? "Partial check health"
              : "Observed health"
          }
          value={report.score == null ? "—" : `${report.score}/100`}
          note={`${assessed.length} checks assessed · ${coverage.length || report.total_checks || 0} in catalog`}
        />
        <Metric
          label="Issues found"
          value={defects.length}
          note={`${unresolved.length} open ${unresolved.length === 1 ? "question needs" : "questions need"} evidence`}
        />
        <Metric
          label="Pages observed"
          value={report.pages ?? "—"}
          note="From the latest audit, not a site-wide index count"
        />
        <Metric
          label="Verified fixes"
          value={fixes}
          note={
            working.length
              ? `${working.length} job in progress`
              : "Verified after deployment, with recorded evidence"
          }
        />
      </div>
      <div className="audit-tabs" role="tablist" aria-label="Audit workspace">
        {[
          ["overview", "Overview"],
          ["findings", "Findings"],
          ["activity", "AI audits & logs"],
          ["pages", "Pages"],
          ["research", "Research"],
          ["policy", "Settings"],
        ].map(([id, label]) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => onTab(id)}
          >
            {label}
            {id === "findings" && active.length > 0 && (
              <span>{active.length}</span>
            )}
          </button>
        ))}
      </div>
      {tab === "overview" && (
        <>
          <div className="audit-columns">
            <section className="audit-panel">
              <div className="audit-panel-heading">
                <div>
                  <span className="eyebrow">MEASURED, NOT ASSUMED</span>
                  <h2>Health over time</h2>
                </div>
                <span className="audit-subtle">
                  Last {trend.length} {trend.length === 1 ? "audit" : "audits"}
                </span>
              </div>
              {trend.length ? (
                <>
                  <div
                    className="audit-trend"
                    role="img"
                    aria-label={trend
                      .map(
                        (job) =>
                          `${date(job.updated_at)}: ${reportFor(job)?.score} out of 100`,
                      )
                      .join("; ")}
                  >
                    {trend.map((job, index) => (
                      <div key={job.id}>
                        <strong>{reportFor(job)?.score}</strong>
                        <div className="audit-trend-track">
                          <span
                            style={{
                              height: `${Math.max(2, Number(reportFor(job)?.score))}%`,
                            }}
                          />
                        </div>
                        <small>{index + 1}</small>
                      </div>
                    ))}
                  </div>
                  <p className="audit-subtle">
                    Changes in check coverage or policy can change this score.
                    It does not measure rankings, traffic or AI citations.
                  </p>
                </>
              ) : (
                <div className="audit-empty">
                  <span>◎</span>
                  <h3>Your baseline starts here</h3>
                  <p>
                    The first completed audit will establish observed health. No
                    score is estimated in advance.
                  </p>
                </div>
              )}
            </section>
            <section className="audit-panel">
              <span className="eyebrow">WHAT NEEDS YOUR ATTENTION</span>
              <h2>Next steps</h2>
              {working.length > 0 && (
                <div className="audit-next">
                  <Badge value={working[0].status} />
                  <p>
                    {liveMessage?.startsWith("Agent tool requested: ")
                      ? human(liveMessage.replace("Agent tool requested: ", ""))
                      : liveMessage ||
                        "The agent is collecting evidence and checking your website."}
                  </p>
                </div>
              )}
              {!!liveEvents.length && (
                <ol
                  className="audit-live-events"
                  aria-label="Recent agent actions"
                >
                  {liveEvents.map((event, index) => (
                    <li key={`${event.time}-${index}`}>
                      <time
                        dateTime={new Date(event.time * 1000).toISOString()}
                      >
                        {new Date(event.time * 1000).toLocaleTimeString(
                          undefined,
                          {
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )}
                      </time>
                      <span>
                        {event.message.startsWith("Agent tool requested: ")
                          ? human(
                              event.message.replace(
                                "Agent tool requested: ",
                                "",
                              ),
                            )
                          : event.message}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
              {latestRepair?.result.pr && (
                <a
                  className="audit-repair-link"
                  href={safeLink(latestRepair.result.pr.url, true)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span className="eyebrow">
                    {latestRepair.result.verified_fixes
                      ? "VERIFIED ON YOUR WEBSITE"
                      : "THE AGENT PREPARED A REPAIR"}
                  </span>
                  <strong>
                    {latestRepair.result.verified_fixes
                      ? `View verified repair #${latestRepair.result.pr.number}`
                      : `Review pull request #${latestRepair.result.pr.number}`}{" "}
                    <span>↗</span>
                  </strong>
                  <small>
                    {latestRepair.result.verified_fixes
                      ? `${latestRepair.result.verified_fixes} fix verified after deployment.`
                      : "Open the source changes and repository checks on GitHub. Your review is required before merging."}
                  </small>
                </a>
              )}
              <button
                className="audit-next audit-next-button"
                onClick={() => {
                  setFilter("defect");
                  onTab("findings");
                }}
              >
                <strong>
                  {defects.length} {defects.length === 1 ? "issue" : "issues"}{" "}
                  to review <span>↗</span>
                </strong>
                <p>
                  {defects.length
                    ? "Review the observation and proposed next step for each issue."
                    : "No issues to review in the current findings. Coverage limits still apply."}
                </p>
              </button>
              <button
                className="audit-next audit-next-button"
                onClick={() => {
                  setFilter("unresolved");
                  onTab("findings");
                }}
              >
                <strong>
                  {unresolved.length} evidence{" "}
                  {unresolved.length === 1 ? "dependency" : "dependencies"}{" "}
                  <span>↗</span>
                </strong>
                <p>
                  Confirm page visibility, business facts or other missing
                  inputs before changes can proceed.
                </p>
              </button>
              <div className="audit-policy-strip">
                <span className="dot" />
                <p>
                  {project.spec.auto_fix
                    ? "Supported repairs can open a PR. You review and merge."
                    : "Audit only. Automatic repair proposals are off."}
                </p>
              </div>
            </section>
          </div>
          <section className="audit-panel">
            <div className="audit-panel-heading">
              <div>
                <span className="eyebrow">TRANSPARENT COVERAGE</span>
                <h2>What was checked</h2>
              </div>
              <span className="audit-subtle">
                {assessed.length} concluded ·{" "}
                {
                  coverage.filter((item) => item.state === "not_applicable")
                    .length
                }{" "}
                not applicable ·{" "}
                {
                  coverage.filter((item) =>
                    ["needs_model", "needs_data", "not_checked"].includes(
                      item.state,
                    ),
                  ).length
                }{" "}
                need evidence or review
              </span>
            </div>
            <p className="audit-subtle">
              Every catalog check has an outcome below. A completed audit can
              still have missing evidence. Health scores exclude unresolved and
              inapplicable checks; they do not measure rankings.
            </p>
            {!coverage.length ? (
              <p>Coverage appears after the first audit.</p>
            ) : (
              <div className="audit-coverage">
                {[...new Set(coverage.map((item) => item.module))].map(
                  (module) => {
                    const rows = coverage.filter(
                      (item) => item.module === module,
                    );
                    return (
                      <details key={module}>
                        <summary>
                          <span>{human(module)}</span>
                          <small>
                            {
                              rows.filter((item) =>
                                ["healthy", "defect"].includes(item.state),
                              ).length
                            }
                            /{rows.length} assessed
                          </small>
                        </summary>
                        {rows.map((item) => (
                          <details
                            className="audit-check-detail"
                            key={item.check_id}
                          >
                            <summary>
                              <span>{item.title}</span>
                              <Badge value={item.state} />
                            </summary>
                            <p>
                              {item.reason ||
                                "This older audit did not record a per-check explanation. Run a fresh audit to collect the current assessment details."}
                            </p>
                            {item.method && (
                              <small>
                                Method: {human(item.method)} · {item.check_id}
                              </small>
                            )}
                            {!!item.dependencies?.length && (
                              <div>
                                <strong>Needed to finish</strong>
                                <ul>
                                  {item.dependencies.map((dependency) => (
                                    <li key={dependency}>{dependency}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {!!item.evidence_urls?.length && (
                              <div>
                                <strong>Observed pages</strong>
                                <ul>
                                  {item.evidence_urls.map((url) => (
                                    <li key={url}>
                                      {safeLink(url) ? (
                                        <a
                                          href={safeLink(url)}
                                          target="_blank"
                                          rel="noreferrer"
                                        >
                                          {url} ↗
                                        </a>
                                      ) : (
                                        url
                                      )}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </details>
                        ))}
                      </details>
                    );
                  },
                )}
              </div>
            )}
          </section>
          <AuditRuns
            jobs={activity.jobs.slice(0, 3)}
            title="Recent audits"
            onAll={() => onTab("activity")}
          />
        </>
      )}
      {tab === "findings" && (
        <section className="audit-panel">
          <div className="audit-panel-heading">
            <div>
              <span className="eyebrow">EVIDENCE BEFORE ACTION</span>
              <h2>Findings</h2>
            </div>
            <span className="audit-subtle">
              Severity and evidence strength are separate
            </span>
          </div>
          <div className="audit-filters">
            <label>
              <span className="sr-only">Filter findings</span>
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="active">All active</option>
                <option value="defect">Issues found</option>
                <option value="unresolved">Needs evidence</option>
                <option value="resolved">Closed findings</option>
                <option value="all">Full history</option>
              </select>
            </label>
            <label>
              <span className="sr-only">Search findings</span>
              <input
                placeholder="Search page, issue or check…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
          </div>
          {!findings.length && (
            <div className="audit-empty">
              <span>✓</span>
              <h3>No findings in this view</h3>
              <p>
                {activity.jobs.length
                  ? "Try another filter. An empty list does not establish that every check passed."
                  : "Your first findings will appear after the audit completes."}
              </p>
            </div>
          )}
          <div className="audit-finding-list">
            {findings.map((item) => {
              const f = item.details;
              const evidence = activity.jobs
                .flatMap((job) => [
                  ...(job.result.evidence || []),
                  ...(job.result.after_evidence || []),
                ])
                .filter((record) => f.evidence_ids?.includes(record.id));
              return (
                <details key={item.id} className="audit-finding">
                  <summary>
                    <span className={`audit-severity severity-${f.severity}`}>
                      {f.severity}
                    </span>
                    <div>
                      <strong>{f.summary || human(f.check_id)}</strong>
                      <small>{f.url || "Project-wide assessment"}</small>
                    </div>
                    <Badge value={item.active ? f.status : "closed"} />
                  </summary>
                  <div className="audit-finding-body">
                    <div className="audit-finding-facts">
                      <span>
                        Evidence:{" "}
                        <strong>{f.evidence_strength || "Not recorded"}</strong>
                      </span>
                      <span>
                        Check: <code>{f.check_id}</code>
                      </span>
                    </div>
                    <h3>Recommended next step</h3>
                    <p>
                      {f.action?.rationale ||
                        "Inspect the recorded evidence before taking action."}
                    </p>
                    {!!f.dependencies?.length && (
                      <>
                        <h3>Required evidence</h3>
                        <ul>
                          {f.dependencies.map((value) => (
                            <li key={value}>{value}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    {!!f.verification_criteria?.length && (
                      <>
                        <h3>How to verify</h3>
                        <ul>
                          {f.verification_criteria.map((value) => (
                            <li key={value}>{value}</li>
                          ))}
                        </ul>
                      </>
                    )}
                    <h3>Observed evidence</h3>
                    {evidence.length ? (
                      evidence
                        .filter(
                          (record, index, all) =>
                            all.findIndex((v) => v.id === record.id) === index,
                        )
                        .map((record) => (
                          <div className="audit-evidence" key={record.id}>
                            <strong>{record.observation}</strong>
                            <small>
                              {record.url || record.kind} ·{" "}
                              {record.collected_at
                                ? new Date(record.collected_at).toLocaleString()
                                : "Time not recorded"}
                            </small>
                          </div>
                        ))
                    ) : (
                      <p>
                        Evidence is not available in the loaded job history.
                      </p>
                    )}
                    <details className="audit-raw">
                      <summary>View recorded details</summary>
                      <pre>
                        {JSON.stringify({ finding: f, evidence }, null, 2)}
                      </pre>
                    </details>
                  </div>
                </details>
              );
            })}
          </div>
        </section>
      )}
      {tab === "activity" && (
        <>
          <div className="audit-filters">
            <label>
              Job status
              <select
                value={jobFilter}
                onChange={(e) => setJobFilter(e.target.value)}
              >
                <option value="all">All jobs</option>
                <option value="complete">Completed</option>
                <option value="running">Running</option>
                <option value="blocked">Needs attention</option>
                <option value="failed">Failed</option>
              </select>
            </label>
            <p className="audit-subtle">
              Recorded agent actions, checks and integration events. Updates
              automatically.
            </p>
          </div>
          <AuditRuns
            jobs={activity.jobs.filter(
              (job) => jobFilter === "all" || job.status === jobFilter,
            )}
            title="AI audits & activity log"
          />
        </>
      )}
      {tab === "pages" && (
        <section className="audit-panel">
          <div className="audit-panel-heading">
            <div>
              <span className="eyebrow">LATEST OBSERVATIONS</span>
              <h2>Pages inspected</h2>
            </div>
            <span className="audit-subtle">
              {report.page_summaries?.length || 0} HTML pages
            </span>
          </div>
          <p className="audit-subtle">
            These are fetched pages, not proof of search-engine indexing.
          </p>
          <div className="audit-pages">
            {report.page_summaries?.map((page) => (
              <article key={page.evidence_id}>
                <span className="audit-page-icon">↗</span>
                <div>
                  <h3>{page.title || "No observed title"}</h3>
                  {safeLink(page.url) ? (
                    <a
                      href={safeLink(page.url)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {page.url} ↗
                    </a>
                  ) : (
                    <p>{page.url}</p>
                  )}
                  <p>{page.excerpt.slice(0, 220)}</p>
                </div>
              </article>
            ))}
          </div>
          {!report.page_summaries?.length && <p>No page observations yet.</p>}
        </section>
      )}
    </div>
  );
}

function projectRepairExplanation(job: Job, report: AuditReport) {
  const declined = job.events.some(
    (event) =>
      event.message ===
      "Assessment complete; no source changes will be published",
  );
  return declined
    ? "No source changes were selected for publication under this project’s repair policy. Open findings may still need evidence or a supported repair. A completed audit is not a guarantee of complete SEO coverage."
    : report.findings
      ? "Findings do not automatically become code changes. A repair needs supporting evidence, permission and successful verification before a PR can be published. Review the findings and recorded job details."
      : "This audit did not publish a repair. Review its assessed coverage and recorded outcome; no PR does not mean every SEO check was completed.";
}

function AuditRuns({
  jobs,
  title,
  onAll,
}: {
  jobs: Job[];
  title: string;
  onAll?: () => void;
}) {
  return (
    <section className="audit-panel">
      <div className="audit-panel-heading">
        <div>
          <span className="eyebrow">THE AGENT’S WORK</span>
          <h2>{title}</h2>
        </div>
        {onAll && (
          <button className="text-link" onClick={onAll}>
            View all activity ↗
          </button>
        )}
      </div>
      {!jobs.length && (
        <div className="audit-empty">
          <h3>No jobs yet</h3>
          <p>Start an audit to collect the first observations.</p>
        </div>
      )}
      {jobs.map((job) => {
        const report = reportFor(job);
        return (
          <details className="audit-run" key={job.id}>
            <summary>
              <span className={`audit-run-mark state-${job.status}`}>
                {job.status === "complete"
                  ? "✓"
                  : job.status === "running"
                    ? "◌"
                    : "·"}
              </span>
              <div>
                <strong>{job.result.summary || human(job.kind)}</strong>
                <small>
                  {human(job.kind)} · {date(job.created_at)} · {duration(job)}
                </small>
              </div>
              <Badge value={job.status} />
            </summary>
            <div className="audit-run-body">
              <div className="audit-run-stats">
                <span>
                  Pages <strong>{report?.pages ?? "—"}</strong>
                </span>
                <span>
                  Verified fixes{" "}
                  <strong>
                    {job.result.verified_fixes ?? "Not established"}
                  </strong>
                </span>
                <span>
                  AI runtime{" "}
                  <strong>
                    {report?.assessment_reused
                      ? "Reused assessment"
                      : report?.model_runtime_ms
                        ? `${(report.model_runtime_ms / 1000).toFixed(1)}s`
                        : "Not recorded"}
                  </strong>
                </span>
                <span>
                  Tokens{" "}
                  <strong>
                    {report?.usage
                      ? (
                          (report.usage.input_tokens || 0) +
                          (report.usage.output_tokens || 0)
                        ).toLocaleString()
                      : "Not recorded"}
                  </strong>
                </span>
              </div>
              {report?.assessment_reused && (
                <p className="audit-policy-strip">
                  Inputs were unchanged. A validated assessment was reused; no
                  new AI call was needed for this audit.
                </p>
              )}
              {job.status === "complete" && report && !job.result.pr && (
                <div className="audit-no-pr">
                  <strong>No pull request was opened for this audit.</strong>
                  <p>{projectRepairExplanation(job, report)}</p>
                </div>
              )}
              {safeLink(job.result.pr?.url, true) && (
                <a
                  className="button secondary"
                  href={safeLink(job.result.pr?.url, true)}
                  target="_blank"
                  rel="noreferrer"
                >
                  Review pull request #{job.result.pr?.number} ↗
                </a>
              )}
              {job.result.error_type && (
                <p role="note" className="alert">
                  {job.result.summary}
                </p>
              )}
              <h3>Execution log</h3>
              <ol className="audit-log">
                {job.events.map((event, index) => (
                  <li key={`${event.time}-${index}`}>
                    <time>{date(event.time)}</time>
                    <span>{event.message}</span>
                  </li>
                ))}
                {report?.tool_trace?.map((tool, index) => (
                  <li key={`tool-${index}`}>
                    <span
                      className={`audit-log-status ${tool.success ? "ok" : "failed"}`}
                    >
                      {tool.success ? "✓" : "!"}
                    </span>
                    <span>
                      {human(tool.name)}{" "}
                      <small>
                        {tool.success ? "Completed" : "Unsuccessful"}
                        {tool.runtime_ms != null
                          ? ` · ${(tool.runtime_ms / 1000).toFixed(2)}s`
                          : ""}
                      </small>
                    </span>
                  </li>
                ))}
              </ol>
              {!job.events.length && !report?.tool_trace?.length && (
                <p>No execution events recorded yet.</p>
              )}
              <p className="audit-subtle">
                {report?.usage?.api_cost_usd != null
                  ? `Recorded API cost: $${report.usage.api_cost_usd.toFixed(4)}.`
                  : "API cost was not supplied. No cost estimate is shown."}
                {job.attempts ? ` Delivery attempts: ${job.attempts}.` : ""}
              </p>
              <details className="audit-raw">
                <summary>View recorded job details</summary>
                <pre>{JSON.stringify(job.result, null, 2)}</pre>
              </details>
            </div>
          </details>
        );
      })}
    </section>
  );
}
