import {bundle} from "@remotion/bundler";
import {renderMedia, renderStill, selectComposition} from "@remotion/renderer";
import {mkdir, writeFile} from "node:fs/promises";
import {execFileSync} from "node:child_process";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const output = path.join(root, "out/agent-session");
await mkdir(output, {recursive: true});
const serveUrl = await bundle({entryPoint: path.join(root, "src/index.tsx"), publicDir: path.join(root, "public")});
const composition = await selectComposition({serveUrl, id: "AgentSession"});
for (const [name, seconds] of [["poster", 3], ["inspect", 11], ["patch", 22], ["checks", 30], ["result", 35], ["monitor", 46], ["end", 50]]) {
  await renderStill({serveUrl, composition, output: path.join(output, `${name}.png`), frame: seconds * 30});
}
if (process.argv.includes("--stills")) process.exit(0);
let last = -1;
await renderMedia({
  serveUrl, composition, codec: "h264", muted: true, pixelFormat: "yuv420p", crf: 19,
  concurrency: 3, outputLocation: path.join(output, "session-raw.mp4"),
  onProgress: ({progress}) => {
    const bucket = Math.floor(progress * 10);
    if (bucket !== last) {last = bucket; console.log(`Render ${bucket * 10}%`);}
  },
});
// Browser frames arrive in full range. Export limited-range YUV with the index
// at the start of the file for portable playback and HTTP seeking.
execFileSync("ffmpeg", ["-v", "error", "-i", path.join(output, "session-raw.mp4"),
  "-map", "0:v:0", "-an", "-c:v", "libx264", "-crf", "19", "-preset", "slow",
  "-pix_fmt", "yuv420p", "-vf", "scale=in_range=full:out_range=tv", "-color_range", "tv",
  "-movflags", "+faststart", "-y", path.join(output, "your-optimiser-agent-at-work.mp4")]);
await writeFile(path.join(output, "render.json"), JSON.stringify({
  width: composition.width, height: composition.height, fps: composition.fps,
  frames: composition.durationInFrames, seconds: composition.durationInFrames / composition.fps,
  audio: "none", disclosure: "Recorded local fixture; output reformatted, waits shortened; no GitHub write or ranking claim.",
}, null, 2) + "\n");
