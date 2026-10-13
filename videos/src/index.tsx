import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {Demo, DURATION, FPS} from './Demo';

const Root = () => <Composition id="OptimizerDemo" component={Demo}
  durationInFrames={DURATION} fps={FPS} width={1920} height={1080}/>;
registerRoot(Root);
