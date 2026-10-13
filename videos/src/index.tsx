import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {Demo, DURATION, FPS} from './Demo';
import {GrowthDemo, GROWTH_DURATION, GROWTH_FPS} from './GrowthDemo';

const Root = () => <><Composition id="OptimizerDemo" component={Demo}
  durationInFrames={DURATION} fps={FPS} width={1920} height={1080}/>
  <Composition id="OptimizerWorkflow" component={GrowthDemo} durationInFrames={GROWTH_DURATION}
    fps={GROWTH_FPS} width={1920} height={1080}/></>;
registerRoot(Root);
