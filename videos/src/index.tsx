import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {YourOptimiser, YOUR_DURATION} from './YourOptimiser';
import {Demo, DURATION, FPS} from './Demo';
import {GrowthDemo, GROWTH_DURATION, GROWTH_FPS} from './GrowthDemo';
import {AgentSession, SESSION_DURATION} from './AgentSession';

const Root = () => <><Composition id="YourOptimiser" component={YourOptimiser} durationInFrames={YOUR_DURATION} fps={30} width={1920} height={1080}/><Composition id="OptimizerDemo" component={Demo}
  durationInFrames={DURATION} fps={FPS} width={1920} height={1080}/>
  <Composition id="OptimizerWorkflow" component={GrowthDemo} durationInFrames={GROWTH_DURATION}
    fps={GROWTH_FPS} width={1920} height={1080}/>
  <Composition id="AgentSession" component={AgentSession} durationInFrames={SESSION_DURATION}
    fps={30} width={1920} height={1080}/></>;
registerRoot(Root);
