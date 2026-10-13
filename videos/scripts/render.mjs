import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia, renderStill} from '@remotion/renderer';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const out = path.join(root, 'out');
await mkdir(out, {recursive: true});
const proof = JSON.parse(await readFile(path.join(root, 'public/demo.json'), 'utf8'));
const serveUrl = await bundle({
  entryPoint: path.join(root, 'src/index.tsx'), publicDir: path.join(root, 'public'),
});
const composition = await selectComposition({serveUrl, id: 'OptimizerDemo'});
const terminal = Math.ceil(proof.terminalSeconds / proof.playbackRate * composition.fps);
const guide = Math.floor(proof.guideSeconds * composition.fps);
const stills = [
  ['poster', 110], ['terminal', 180 + terminal - 40],
  ['patch', 180 + terminal + 220], ['guide', 180 + terminal + 300 + 120],
  ['results', 180 + terminal + 300 + guide + 130],
];
for (const [name, frame] of stills) {
  await renderStill({serveUrl, composition, output: path.join(out, `${name}.png`), frame});
}
if (process.argv[2] === 'stills') process.exit(0);
let reported = -1;
await renderMedia({
  serveUrl, composition, codec: 'h264', pixelFormat: 'yuv420p', crf: 18,
  concurrency: 3, outputLocation: path.join(out, 'optimizer-demo.mp4'),
  onProgress: ({progress}) => {
    const step = Math.floor(progress * 10);
    if (step !== reported) {reported = step; console.log(`Render ${step * 10}%`);}
  },
});
await writeFile(path.join(out, 'render.json'), JSON.stringify({
  composition: composition.id, width: composition.width, height: composition.height,
  frames: composition.durationInFrames, fps: composition.fps,
  seconds: composition.durationInFrames / composition.fps,
  source: 'Actual terminal and browser recordings with evidence-driven explanatory scenes',
}, null, 2) + '\n');
console.log('Rendered optimizer-demo.mp4');
