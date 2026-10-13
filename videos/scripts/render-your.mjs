import { bundle } from "@remotion/bundler";
import {
  selectComposition,
  renderMedia,
  renderStill,
} from "@remotion/renderer";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
const root = path.resolve(import.meta.dirname, "..");
const out = path.join(root, "out/your-optimiser");
await mkdir(out, { recursive: true });
const story = JSON.parse(
  await readFile(path.join(root, "public/customer/story.json"), "utf8"),
);
const serveUrl = await bundle({
  entryPoint: path.join(root, "src/index.tsx"),
  publicDir: path.join(root, "public"),
});
const composition = await selectComposition({ serveUrl, id: "YourOptimiser" });
let offset = 0;
for (const [index, scene] of story.entries()) {
  const frame = offset + Math.min(170, scene.frames - 20);
  await renderStill({
    serveUrl,
    composition,
    output: path.join(
      out,
      [
        "poster",
        "update",
        "check",
        "fix",
        "review",
        "after",
        "healthy",
        "watch",
      ][index] + ".png",
    ),
    frame,
  });
  offset += scene.frames;
}
function timestamp(seconds) {
  const ms = Math.round(seconds * 1000);
  return `${String(Math.floor(ms / 3600000)).padStart(2, "0")}:${String(Math.floor(ms / 60000) % 60).padStart(2, "0")}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}.${String(ms % 1000).padStart(3, "0")}`;
}
let caption = "WEBVTT\n\n",
  seconds = 0;
for (const scene of story) {
  const phrases = scene.narration.match(/[^.!?]+[.!?]+/g) || [scene.narration];
  let spoken = 0;
  for (const phrase of phrases) {
    const length =
      (phrase.length / scene.narration.length) * scene.audio_seconds;
    caption += `${timestamp(seconds + spoken)} --> ${timestamp(seconds + spoken + length)}\n${phrase.trim()}\n\n`;
    spoken += length;
  }
  seconds += scene.frames / 30;
}
await writeFile(path.join(out, "demo-captions.vtt"), caption);
if (process.argv[2] === "stills") process.exit(0);
let seen = -1;
await renderMedia({
  serveUrl,
  composition,
  codec: "h264",
  audioCodec: "aac",
  pixelFormat: "yuv420p",
  crf: 20,
  concurrency: 3,
  outputLocation: path.join(out, "your-optimiser.mp4"),
  onProgress: ({ progress }) => {
    const step = Math.floor(progress * 10);
    if (step !== seen) {
      seen = step;
      console.log(`Render ${step * 10}%`);
    }
  },
});
await writeFile(
  path.join(out, "render.json"),
  JSON.stringify(
    {
      width: composition.width,
      height: composition.height,
      frames: composition.durationInFrames,
      fps: composition.fps,
      seconds: composition.durationInFrames / composition.fps,
      narration:
        "System voice; illustrated customer workflow backed by recorded source repairs",
    },
    null,
    2,
  ) + "\n",
);
