import {readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
const root = path.resolve(import.meta.dirname, '..');
const read = async name => JSON.parse(await readFile(path.join(root, 'public', name), 'utf8'));
const growth = await read('growth-run.json');
const repairs = JSON.parse(await readFile(process.argv[2] ?? path.join(root, '..', '.data/matched-benchmark/run-3.json'), 'utf8'));
const technical = await read('agent-run.json');
if (growth.status !== 'passed' || !growth.content.content_verified || !growth.content.verification.every(c => c.passed)) {
  throw new Error('Real content publication and checks must pass before preparing the video');
}
if (technical.status !== 'passed') throw new Error('Technical repair recording must be verified');
const labels = {rules: 'Rules alone', 'local-minimal': 'Local · minimal runner', 'local-full': 'Local · full harness',
  'paid-minimal': 'Paid · minimal runner', 'paid-full': 'Paid · full harness'};
const order = Object.keys(labels);
const proof = {
  generatedAt: growth.generated_at,
  originalPassage: growth.source.materials[0].text,
  syntheticImpressions: growth.source.search[0].impressions,
  syntheticClicks: growth.source.search[0].clicks,
  contentVerified: growth.content.content_verified,
  contentCommit: growth.merged_sha.slice(0, 12),
  repeatChanged: growth.repeat_created_commit,
  buildOutput: growth.content.verification.map(c => c.stdout ?? '').filter(Boolean).join('\n'),
  technicalToolCalls: technical.model_tool_calls,
  technicalBefore: technical.before_defects, technicalAfter: technical.after_defects,
  frozenCommit: repairs.base_sha.slice(0, 12),
  arms: repairs.arms.sort((a, b) => order.indexOf(a.arm) - order.indexOf(b.arm)).map(a => ({
    id: a.arm, label: labels[a.arm], verified: a.observed.verified_fixes,
    published: a.repair_passed, healthy: a.healthy_control?.passed ?? null,
    irrelevant: a.irrelevant_control?.passed ?? null,
    unnecessary: a.unnecessary_changes,
    seconds: Math.round(a.runtime_seconds),
    status: a.repair.status,
    failure: a.repair.result.error_type ?? '',
    cost: a.repair.result.report?.usage?.api_cost_usd ?? null,
  })),
  caveat: 'One development repair case + healthy and irrelevant controls. No ranking or traffic uplift measured.',
};
await writeFile(path.join(root, 'public/growth-proof.json'), JSON.stringify(proof, null, 2)+'\n');
console.log(`Prepared ${proof.arms.length} observed arms and a verified autonomous content recording`);
