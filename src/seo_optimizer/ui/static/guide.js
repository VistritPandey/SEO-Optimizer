'use strict';

const steps = [
  ['SIGNED EVENT / SCHEDULE / MANUAL AUDIT', 'A reason to inspect the site',
    'A signed GitHub push, a periodic reconciliation, or your manual audit queues a project-scoped job. Repeated events reuse existing work.',
    'Repository, branch, revision and project identity', 'A durable queued job',
    'Signature, repository and branch must match the connection'],
  ['INCREMENTAL ROUTE AUDIT', 'Inspect what the change can affect',
    'The worker compares revisions and maps files to routes. Shared layouts and response configuration trigger a broader audit. Known unrelated changes skip model work.',
    'Changed files and the route map', 'Affected URLs or a broader audit',
    'A newer revision supersedes stale work'],
  ['HTTP / RENDERED DOM / OPTIONAL VISION', 'Collect what actually exists',
    'Bounded requests collect responses, directives and links. Optional Chromium observes rendered content. Screenshots supplement text and DOM evidence for visual questions.',
    'Configured website URLs and repository snapshot', 'Dated, scoped observations with evidence IDs',
    'Origin, network, page, response-size and time limits'],
  ['RULES / OPTIONAL MODEL REASONING', 'Choose a supported action',
    'Rules establish directly observable issues. A configured model uses relevant private references and inspection tools. Every finding must refer to real observations and valid sources.',
    'Observations, goals, known facts and allowed actions', 'Findings and exact proposed file replacements',
    'Local schema, evidence and policy validation'],
  ['INDEPENDENT APPLICATION CHECKS', 'A proposal is not permission',
    'The application checks exact source context, paths, privacy and behavior. Static metadata gets direct checks; framework and broader content edits need configured isolated builds.',
    'Proposed changes and current source', 'A checked patch or a recorded dependency',
    'No private-page, training opt-out or executable-behavior bypass'],
  ['LOCAL GIT / GITHUB PULL REQUEST', 'Publish only within your policy',
    'Each changed file gets its own commit. GitHub publication uses a pull request and required-check gates; rebase merging preserves individual file commits. Local changes require a clean, unchanged target branch.',
    'Verified files and the expected base revision', 'A pull request or permitted local merge',
    'Exact PR head, current base, repository checks and merge policy'],
  ['DEPLOYMENT SHA / AFTER OBSERVATIONS', 'Check the result where it is served',
    'For GitHub, the worker waits for a successful deployment of the merged SHA in the configured environment. It fetches affected pages again. A confirmed failure may permit a guarded rollback.',
    'Merged revision and deployment confirmation', 'Verified fixes, confirmed failures or inconclusive evidence',
    'An unavailable site does not prove a regression; newer code prevents rollback'],
  ['FINDING MEMORY / RECONCILIATION', 'Keep the record, avoid the loop',
    'The worker stores outcomes and stable finding identities. Observed fixes resolve relevant findings, repeated wording does not create another issue, and reconciliation catches missed events.',
    'Audit results, revisions and observed URLs', 'Persistent project history and the next reconciliation',
    'Only observed pages can resolve their previous findings'],
];

const scenarioData = {
  title: ['Supported proposal', 'Use the observed heading as a title',
    'The page is public and the title is absent. An actual heading supplies useful text without inventing business claims.',
    'HTTP response, mapped source and observed heading', 'Validate the exact metadata patch before committing it'],
  healthy: ['No change', 'Keep an adequate page intact',
    'The observed page already meets the assessed requirement. Rewriting it just to create activity would add unnecessary risk and cost.',
    'A successful page with appropriate metadata', 'Record the assessment; continue only when new evidence justifies work'],
  private: ['No change', 'Preserve intentional privacy',
    'The project explicitly marks this page private. A missing title or noindex directive does not grant permission to make it publicly discoverable.',
    'Declared private intent and the page response', 'Keep the configured exclusion and privacy boundary'],
  training: ['No change', 'Search access and training are independent',
    'Blocking training while allowing discovery can be the correct owner policy. The worker preserves both preferences rather than removing all crawler restrictions.',
    'Configured bot preferences and effective robots directives', 'Keep the matching policy; do not introduce a training opt-in'],
  facts: ['Needs evidence', 'Record the missing source material',
    'An absent business fact is not permission to invent it. New claims need current owner facts and useful supporting material before publication.',
    'Content requirement with an unavailable or expired authoritative fact', 'Record the dependency; do not publish invented claims'],
  tool: ['Blocked publication', 'A failed prerequisite stays visible',
    'Calling a tool does not prove that it worked. A failed required inspection or build prevents automatic publication that relies on it.',
    'The actual tool failure and its affected dependency', 'Resolve the dependency and retry within the job budget'],
};

const setups = {
  rules: ['Start without model credentials',
    'Rules are the default. Run the dashboard in one terminal and the worker in another. Connect a website through the workspace.',
    'Default local URL: http://127.0.0.1:8000. Local repositories must be inside OPT_REPO_ROOTS.',
    'uv sync --locked\n\n# Terminal 1\nuv run seo-optimizer serve\n\n# Terminal 2\nuv run seo-optimizer worker'],
  ollama: ['Keep inference beside your local worker',
    'Start Ollama separately. Connect the project with provider ollama, an installed model ID and its verified capabilities. The worker calls the local endpoint.',
    'Default endpoint: http://127.0.0.1:11434. Benchmark your chosen model; capability support is not proof of reliable decisions.',
    'ollama list\n\n# Dashboard terminal\nuv run seo-optimizer serve\n\n# Worker terminal\nuv run seo-optimizer worker'],
  hosted: ['Host short requests; keep the worker portable',
    'Deploy the dashboard with PostgreSQL, a stable secret and HTTPS. A scoped token lets your local worker claim only your projects over outbound HTTPS.',
    'Set these values in an ignored environment file or secret manager. The hosted process does not run the repository/build/model loop.',
    '# Worker environment (.env, never committed)\nOPT_CONTROL_URL=https://your-service.example\nOPT_WORKER_TOKEN=your-scoped-token\n\nuv run seo-optimizer worker --remote'],
};

function writeValues(ids, values) {
  ids.forEach((id, index) => { document.getElementById(id).textContent = values[index]; });
}

function selectButton(group, selected) {
  document.querySelectorAll(group).forEach(button => {
    button.setAttribute('aria-pressed', String(button === selected));
  });
}

document.querySelectorAll('[data-step]').forEach(button => {
  button.addEventListener('click', () => {
    writeValues(['step-kind', 'step-title', 'step-description', 'step-input', 'step-output', 'step-gate'], steps[Number(button.dataset.step)]);
    selectButton('[data-step]', button);
  });
});

function updateDecision() {
  const scenario = document.getElementById('scenario').value;
  const values = [...scenarioData[scenario]];
  if (scenario === 'title' && !document.getElementById('auto-fix').checked) {
    values[0] = 'Assessment only';
    values[1] = 'Record the missing title without a patch';
    values[4] = 'Keep the finding visible; automatic fixes are disabled';
  }
  writeValues(['decision-status', 'decision-title', 'decision-reason', 'decision-evidence', 'decision-next'], values);
}
document.getElementById('scenario').addEventListener('change', updateDecision);
document.getElementById('auto-fix').addEventListener('change', updateDecision);
document.querySelectorAll('[data-setup]').forEach(button => {
  button.addEventListener('click', () => {
    writeValues(['setup-title', 'setup-description', 'setup-dependency', 'setup-command'], setups[button.dataset.setup]);
    selectButton('[data-setup]', button);
  });
});
