"use client";

export function AgentPreferences({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  let policy: Record<string, unknown>;
  try {
    policy = JSON.parse(value);
    if (!policy || typeof policy !== "object" || Array.isArray(policy))
      throw Error();
  } catch {
    return <p>Correct the advanced settings JSON to edit agent preferences.</p>;
  }
  const conventions =
    policy.git_conventions && typeof policy.git_conventions === "object"
      ? (policy.git_conventions as Record<string, string>)
      : {};
  const rules = {
    branch_prefix: "optimizer",
    branch_suffix: "",
    commit_style: "plain",
    commit_type: "fix",
    commit_scope: "",
    ...conventions,
  };
  function updateRule(key: string, next: string) {
    onChange(
      JSON.stringify(
        { ...policy, git_conventions: { ...rules, [key]: next } },
        null,
        2,
      ),
    );
  }
  const branch = `${rules.branch_prefix}/<job-id>${rules.branch_suffix ? `-${rules.branch_suffix}` : ""}`;
  const commit =
    rules.commit_style === "conventional"
      ? `${rules.commit_type}${rules.commit_scope ? `(${rules.commit_scope})` : ""}: fix page.tsx`
      : "Fix page.tsx";
  return (
    <div className="agent-preferences">
      <fieldset>
        <legend>Coding instructions</legend>
        <p>
          Give the agent your project’s coding practices and preferred approach
          to repairs.
        </p>
        <label>
          Project instructions (optional)
          <textarea
            rows={5}
            maxLength={8000}
            value={
              typeof policy.agent_instructions === "string"
                ? policy.agent_instructions
                : ""
            }
            placeholder="Follow existing patterns. Preserve behavior and accessibility. Keep changes focused and use existing dependencies."
            onChange={(event) =>
              onChange(
                JSON.stringify(
                  { ...policy, agent_instructions: event.target.value },
                  null,
                  2,
                ),
              )
            }
          />
        </label>
        <p className="fine-print">
          These instructions guide the agent. Allowed files, evidence
          requirements, permissions and verification checks still apply.
        </p>
      </fieldset>
      <fieldset>
        <legend>Branches & commits</legend>
        <div className="agent-preferences-grid">
          <label>
            Branch prefix
            <input
              value={rules.branch_prefix}
              maxLength={64}
              placeholder="optimizer"
              onChange={(event) =>
                updateRule("branch_prefix", event.target.value)
              }
            />
          </label>
          <label>
            Branch suffix (optional)
            <input
              value={rules.branch_suffix}
              maxLength={40}
              placeholder="seo"
              onChange={(event) =>
                updateRule("branch_suffix", event.target.value)
              }
            />
          </label>
          <label>
            Commit style
            <select
              value={rules.commit_style}
              onChange={(event) =>
                updateRule("commit_style", event.target.value)
              }
            >
              <option value="plain">Plain language</option>
              <option value="conventional">Conventional Commits</option>
            </select>
          </label>
          {rules.commit_style === "conventional" && (
            <>
              <label>
                Commit type
                <select
                  value={rules.commit_type}
                  onChange={(event) =>
                    updateRule("commit_type", event.target.value)
                  }
                >
                  {["fix", "chore", "perf", "docs", "refactor"].map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Commit scope (optional)
                <input
                  value={rules.commit_scope}
                  maxLength={32}
                  placeholder="seo"
                  onChange={(event) =>
                    updateRule("commit_scope", event.target.value)
                  }
                />
              </label>
            </>
          )}
        </div>
        <div className="agent-convention-preview" aria-live="polite">
          <p>
            New branch <code>{branch}</code>
          </p>
          <p>
            Commit <code>{commit}</code>
          </p>
        </div>
        <p className="fine-print">
          One file per commit. Existing repair PRs keep their branches for
          follow-ups. Your repository’s branch protection and required checks
          still apply.
        </p>
      </fieldset>
    </div>
  );
}
