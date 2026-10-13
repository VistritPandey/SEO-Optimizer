import {readFile, writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '../..');
const capture = JSON.parse(await readFile(path.join(root, 'videos/public/capture.json'), 'utf8'));
const run = JSON.parse(await readFile(path.join(root, '.data/demo-recording/run.json'), 'utf8'));
const transcript = capture.events.map(event => event.text).join('');
const suite = transcript.match(/(\d+) passed, (\d+) warning in ([\d.]+)s/);
const repair = run.cases.find(item => item.case === 'rendered-title-repair');
if (!suite || capture.error || capture.commands.some(command => command.exit_code !== 0)
    || repair.status !== 'complete' || repair.result.stage !== 'verified'
    || run.repeat_created_commit || run.github_writes) {
  throw new Error('Capture does not establish the expected demo results');
}
const duration = file => Number(execFileSync('ffprobe', [
  '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
  path.join(root, 'videos/public', file),
], {encoding: 'utf8'}).trim());
const commandTimes = capture.events.filter(event => event.text.startsWith('$ ')).map(event => event.time);
const evidence = {
  generatedAt: run.generated_at,
  repository: run.repository,
  upstreamSha: run.upstream_sha,
  testBranch: run.test_branch,
  mergedSha: repair.result.merged_sha,
  terminalSeconds: duration('terminal.mp4'),
  guideSeconds: duration('guide.mp4'),
  captureLeadSeconds: 1.2,
  playbackRate: 1.5,
  commandTimes,
  passedTests: Number(suite[1]),
  testWarnings: Number(suite[2]),
  suiteSeconds: Number(suite[3]),
  verifiedFixes: repair.result.verified_fixes,
  observedRegressions: repair.result.regressions,
  repeatCreatedCommit: run.repeat_created_commit,
  githubWrites: run.github_writes,
  reactSourcePreserved: run.react_source_preserved,
  changedPaths: run.changed_upstream_paths,
  repairedTitle: run.rendered_title,
  checks: repair.result.verification,
  modelInvoked: false,
  limits: run.limits,
};
await writeFile(path.join(root, 'videos/public/demo.json'), JSON.stringify(evidence, null, 2) + '\n');
console.log('Prepared video evidence from the recorded run');
