import {readFile, writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '../..');
const run = JSON.parse(await readFile(path.join(root, 'videos/public/agent-run.json'), 'utf8'));
const repair = run.repair?.result;
if (run.status !== 'passed' || repair?.stage !== 'verified' || run.github_writes) {
  throw new Error('A real, verified model repair is required for this demo');
}
const trace = repair.report.tool_trace;
const patches = trace.filter(call => call.name === 'apply_patch' && call.success).map(call => call.arguments);
const home = patches.find(patch => patch.path === 'web/index.html');
const product = patches.find(patch => patch.path === 'web/products/cedar-lamp/index.html');
if (!home || !product || !trace.some(call => call.name === 'run_checks' && call.success
  && call.result.scope === 'staged_proposals')) throw new Error('Missing model action evidence');
const price = text => text.match(/"price"\s*:\s*"?([\d.]+)/)?.[1];
const canonicals = text => [...text.matchAll(/<link[^>]*rel="canonical"[^>]*href="([^"]+)"/g)].map(match => match[1]);
const description = home.after.match(/<meta[^>]*name="description"[^>]*content="([^"]+)"/)?.[1];
const duration = file => Number(execFileSync('ffprobe', [
  '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
  path.join(root, 'videos/public', file),
], {encoding: 'utf8'}).trim());
const evidence = {
  generatedAt: run.generated_at, model: run.model, sdk: run.sdk_version,
  requests: run.repair_requests ?? run.requests, toolCalls: run.model_tool_calls,
  runtimeSeconds: run.runtime_seconds, beforeDefects: run.before_defects, afterDefects: run.after_defects,
  files: run.changed_paths, mergedSha: run.merged_sha, modelSummary: repair.report.model_summary,
  description, beforePrice: price(product.before), afterPrice: price(product.after),
  beforeCanonicals: canonicals(product.before), afterCanonicals: canonicals(product.after),
  checks: repair.verification, trace: trace.map(call => ({
    name: call.name, path: call.arguments.path ?? call.arguments.check_id ?? '', success: call.success,
    scope: call.result.scope ?? '', runtimeMs: call.runtime_ms,
  })),
  protectedFilesUnchanged: run.protected_files_unchanged,
  repeatCommit: run.repeat?.created_commit ?? null,
  docsMergeRequests: run.merged_docs_event?.inference_requests ?? null,
  unresolved: repair.findings.filter(finding => finding.status === 'unresolved').map(finding => finding.check_id),
  usage: repair.report.usage,
  beforeSeconds: duration('before.mp4'), afterSeconds: duration('after.mp4'),
};
await writeFile(path.join(root, 'videos/public/demo.json'), JSON.stringify(evidence, null, 2) + '\n');
console.log('Prepared video from actual Gemini actions and verified file changes');
