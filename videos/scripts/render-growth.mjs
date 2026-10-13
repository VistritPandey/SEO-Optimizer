import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia, renderStill} from '@remotion/renderer';
import {mkdir, writeFile} from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const out=path.join(root,'out/workflow');
await mkdir(out,{recursive:true});
const serveUrl=await bundle({entryPoint:path.join(root,'src/index.tsx'),publicDir:path.join(root,'public')});
const composition=await selectComposition({serveUrl,id:'OptimizerWorkflow'});
for (const [name,frame] of [['poster',110],['tools',520],['strategy',1080],['publish',1400],['content',1700],['benchmark',2110],['end',2510]]) {
 await renderStill({serveUrl,composition,output:path.join(out,`${name}.png`),frame});
}
if(process.argv[2]==='stills') process.exit(0);
let reported=-1;
await renderMedia({serveUrl,composition,codec:'h264',pixelFormat:'yuv420p',crf:18,concurrency:3,
 outputLocation:path.join(out,'optimizer-workflow.mp4'),onProgress:({progress})=>{
  const step=Math.floor(progress*10);if(step!==reported){reported=step;console.log(`Render ${step*10}%`);}
 }});
await writeFile(path.join(out,'render.json'),JSON.stringify({composition:composition.id,
 frames:composition.durationInFrames,fps:composition.fps,width:composition.width,height:composition.height,
 source:'Actual browser and terminal recordings; observed benchmark figures; explicitly synthetic content/search inputs'},null,2)+'\n');
