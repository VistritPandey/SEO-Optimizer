import {readFile, writeFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '../..');
const capture = JSON.parse(await readFile(path.join(root, 'videos/public/capture.json'), 'utf8'));
const first = capture.events.find(event => event.text.includes('TOOL read_file'));
const last = capture.events.find(event => event.text.includes('MERGED DOCS BRANCH'));
if (capture.error || capture.commands.some(command => command.exit_code !== 0) || !first || !last) {
  throw new Error('A successful real terminal capture is required');
}
const input = path.join(root, '.data/demo-recording/terminal.webm');
const clips = [{start: first.time + 1.5, seconds: 3}, {start: last.time + 1.5, seconds: 4}];
execFileSync('ffmpeg', ['-loglevel', 'error', '-y',
  '-ss', String(clips[0].start), '-t', '3', '-i', input,
  '-ss', String(clips[1].start), '-t', '4', '-i', input,
  '-filter_complex', '[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]',
  '-map', '[v]', '-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
  path.join(root, 'videos/public/terminal-highlights.mp4'),
]);
await writeFile(path.join(root, 'videos/public/highlights.json'), JSON.stringify({
  source: 'Actual PTY output, recorded during live model execution',
  clips, edits: 'Waiting periods cut; source inspection and final control output retained',
}, null, 2) + '\n');
console.log('Cut actual terminal recording into seven seconds of excerpts');
