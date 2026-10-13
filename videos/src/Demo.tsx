import React from 'react';
import {
  AbsoluteFill, interpolate, OffthreadVideo, Sequence, spring, staticFile,
  useCurrentFrame, useVideoConfig,
} from 'remotion';
import proof from '../public/demo.json';

const C = {ink: '#14382b', cream: '#f3f2e7', lime: '#c8e893', dim: '#93ae96', dark: '#0b201a'};
const mono = 'ui-monospace, SFMono-Regular, Menlo, monospace';
const sans = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
export const FPS = 30;
const INTRO = 180;
const TERMINAL = Math.ceil(proof.terminalSeconds / proof.playbackRate * FPS);
const PATCH = 300;
const GUIDE = Math.floor(proof.guideSeconds * FPS);
const END = 210;
export const DURATION = INTRO + TERMINAL + PATCH + GUIDE + END;

const enter = (frame: number, delay = 0) => spring({frame: frame - delay, fps: FPS,
  config: {damping: 200}, durationInFrames: 32});
const Label: React.FC<{children: React.ReactNode; light?: boolean}> = ({children, light}) =>
  <div style={{fontFamily: mono, fontSize: 21, letterSpacing: 3, color: light ? C.dim : C.ink,
    textTransform: 'uppercase'}}>{children}</div>;
const Reveal: React.FC<{children: React.ReactNode; delay?: number; style?: React.CSSProperties}> =
  ({children, delay = 0, style}) => {
    const frame = useCurrentFrame();
    const value = enter(frame, delay);
    return <div style={{opacity: value, transform: `translateY(${(1 - value) * 36}px)`, ...style}}>
      {children}</div>;
  };
const Footer: React.FC<{children: React.ReactNode; light?: boolean}> = ({children, light}) =>
  <div style={{position: 'absolute', bottom: 42, left: 88, right: 88, display: 'flex',
    justifyContent: 'space-between', color: light ? C.dim : C.ink, fontSize: 20}}>
    <span>{children}</span><span style={{fontFamily: mono}}>OPTIMIZER / LOCAL DEMO</span>
  </div>;

const Intro = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: C.cream, padding: '95px 110px', color: C.ink}}>
    <Reveal><Label>SEO Optimizer / an actual working session</Label></Reveal>
    <Reveal delay={8} style={{fontSize: 126, fontWeight: 600, lineHeight: 1.05,
      letterSpacing: -6, marginTop: 58}}>From a code change<br/>to a <span style={{
        background: C.lime, padding: '0 20px'}}>verified fix.</span></Reveal>
    <Reveal delay={18} style={{fontSize: 32, maxWidth: 1160, lineHeight: 1.5, marginTop: 45}}>
      Your React portfolio. A controlled missing title.<br/>
      Real terminal commands, isolated checks, and a local Git merge.
    </Reveal>
    <div style={{display: 'flex', gap: 20, marginTop: 66}}>
      {['OBSERVE', 'VERIFY', 'REMEMBER'].map((text, i) => <Reveal key={text} delay={30 + i * 10}>
        <div style={{fontFamily: mono, fontSize: 23, padding: '20px 36px', border: '1px solid #bdc7b3',
          borderRadius: 100}}>{text} <span style={{marginLeft: 25}}>↗</span></div>
      </Reveal>)}
    </div>
    <div style={{position: 'absolute', right: 120, top: 110, width: 34, height: 34,
      background: C.ink, borderRadius: 50, transform: `scale(${1 + Math.sin(frame / 18) * .08})`}}/>
    <Footer>Rules run shown here · model inference is optional</Footer>
  </AbsoluteFill>;
};

const Terminal = () => {
  const frame = useCurrentFrame();
  const time = frame / FPS * proof.playbackRate - proof.captureLeadSeconds;
  const stage = time >= proof.commandTimes[2] ? 2 : time >= proof.commandTimes[1] ? 1 : 0;
  const notes = [
    ['01 / THE REAL WORKER', 'Run the repair cycle.', 'Observe the rendered page. Check the proposal. Build in Docker. Merge locally. Fetch again.'],
    ['02 / THE REAL DIFF', 'Inspect the commit.', 'One changed file. The title comes from the observed heading. The React application source stays intact.'],
    ['03 / THE FULL SUITE', 'Test the application.', 'Offline contract, policy, tool, incremental-audit, publishing and verification tests.'],
  ][stage];
  return <AbsoluteFill style={{background: C.dark, color: C.cream, padding: '58px 88px'}}>
    <Label light>Actual terminal recording · {proof.playbackRate}× playback</Label>
    <div style={{display: 'flex', gap: 46, marginTop: 42, alignItems: 'center'}}>
      <div style={{width: 1392, height: 789, border: '1px solid #385045', borderRadius: 20,
        overflow: 'hidden', boxShadow: '0 32px 80px #0005', flexShrink: 0}}>
        <OffthreadVideo src={staticFile('terminal.mp4')} muted playbackRate={proof.playbackRate}
          style={{width: '100%', height: '100%', objectFit: 'contain'}}/>
      </div>
      <div style={{width: 310}}>
        <div style={{fontFamily: mono, color: C.lime, fontSize: 18, lineHeight: 1.6}}>{notes[0]}</div>
        <div style={{fontSize: 46, letterSpacing: -1, fontWeight: 600, margin: '25px 0'}}>{notes[1]}</div>
        <div style={{fontSize: 24, lineHeight: 1.6, color: '#b6c8b6'}}>{notes[2]}</div>
        <div style={{height: 2, background: '#375045', marginTop: 45}}/>
        <div style={{fontSize: 19, color: C.dim, lineHeight: 1.6, marginTop: 25}}>
          Captured from subprocess PTY output.<br/>No scripted terminal results.
        </div>
      </div>
    </div>
    <Footer light>Controlled defect · local test branch · GitHub unchanged</Footer>
  </AbsoluteFill>;
};

const Patch = () => {
  const frame = useCurrentFrame();
  const fixed = frame >= 80;
  const line = proof.repairedTitle.replace('&#x27;', "'");
  return <AbsoluteFill style={{background: C.cream, color: C.ink, padding: '82px 110px'}}>
    <Reveal><Label>The observed change / public/index.html</Label></Reveal>
    <Reveal delay={5} style={{fontSize: 78, fontWeight: 600, letterSpacing: -3, marginTop: 30}}>
      Small patch. Checked all the way through.
    </Reveal>
    <div style={{display: 'flex', gap: 50, marginTop: 65}}>
      <div style={{width: 1090, background: C.dark, borderRadius: 22, padding: 42, color: C.cream,
        fontFamily: mono, fontSize: 29, lineHeight: 1.9, position: 'relative', minHeight: 408}}>
        <div style={{fontSize: 19, color: C.dim, letterSpacing: 2, marginBottom: 24}}>
          {fixed ? 'AFTER / REPAIR COMMIT' : 'BEFORE / INTRODUCED TEST DEFECT'}</div>
        <div>&lt;head&gt;</div>
        {fixed ? <div style={{background: '#35533b', margin: '0 -15px', padding: '0 15px', color: C.lime,
          opacity: enter(frame, 80)}}>+ &lt;title&gt;{proof.repairedTitle}&lt;/title&gt;</div>
          : <div style={{color: '#d7a992'}}>  {'<!-- title intentionally removed -->'}</div>}
        <div>  &lt;meta charset=&quot;utf-8&quot;&gt;</div><div>&lt;/head&gt;</div>
        <div style={{fontSize: 19, color: C.dim, marginTop: 28}}>Exact HTML entity encoding retained</div>
      </div>
      <div style={{flex: 1, minWidth: 0, paddingTop: 14}}>
        <Label>Rendered heading</Label>
        <div style={{fontSize: 41, lineHeight: 1.25, marginTop: 24, fontWeight: 600}}>{line}</div>
        <div style={{fontSize: 23, lineHeight: 1.6, marginTop: 40}}>
          {['HTML metadata check', 'Isolated React production build', 'Post-merge page verification'].map((text, i) =>
            <Reveal key={text} delay={110 + i * 25} style={{marginBottom: 12}}>
              <span style={{background: C.lime, borderRadius: 30, padding: '1px 8px', marginRight: 14}}>✓</span>{text}
            </Reveal>)}
        </div>
      </div>
    </div>
    <Reveal delay={180} style={{display: 'flex', gap: 24, marginTop: 42, fontSize: 25}}>
      <span style={{padding: '18px 28px', border: '1px solid #bcc8b4', borderRadius: 12}}>Repeat audit: no new commit</span>
      <span style={{padding: '18px 28px', border: '1px solid #bcc8b4', borderRadius: 12}}>Unrelated README change: model skipped</span>
    </Reveal>
    <Footer>One verified fix in this controlled run · search performance was not measured</Footer>
  </AbsoluteFill>;
};

const Guide = () => <AbsoluteFill style={{background: C.dark, color: C.cream, padding: '50px 88px'}}>
  <Label light>Actual browser recording / interactive guide</Label>
  <div style={{fontSize: 52, fontWeight: 500, letterSpacing: -1.5, margin: '23px 0 26px'}}>
    See the reason behind each step.
  </div>
  <div style={{width: 1380, height: 782, margin: '0 auto', borderRadius: 18, overflow: 'hidden',
    border: '1px solid #415b44'}}>
    <OffthreadVideo src={staticFile('guide.mp4')} muted style={{width: '100%', height: '100%'}}/>
  </div>
  <Footer light>Click through inputs, outputs, policy gates and verification</Footer>
</AbsoluteFill>;

const Results = () => <AbsoluteFill style={{background: C.cream, color: C.ink, padding: '90px 110px'}}>
  <Reveal><Label>Results from the recorded run</Label></Reveal>
  <Reveal delay={8} style={{fontSize: 98, fontWeight: 600, letterSpacing: -4, marginTop: 48}}>
    Evidence you can inspect.
  </Reveal>
  <div style={{display: 'flex', gap: 30, marginTop: 70}}>
    {[[proof.passedTests, 'tests passed'], [proof.verifiedFixes, 'verified title fix'],
      [Number(proof.repeatCreatedCommit), 'repeat-audit commits']].map(([number, text], i) =>
      <Reveal key={text} delay={25 + i * 10} style={{flex: 1, background: i === 1 ? C.lime : '#e6e9db',
        padding: '38px 42px', borderRadius: 20}}>
        <div style={{fontFamily: mono, fontSize: 128, letterSpacing: -8}}>{number}</div>
        <div style={{fontSize: 29, marginTop: 15}}>{text}</div>
      </Reveal>)}
  </div>
  <Reveal delay={70} style={{fontSize: 30, lineHeight: 1.65, marginTop: 58}}>
    Local worker + real repository + locally served React assets.<br/>
    Rules-only demo. Live GitHub publishing and ranking uplift remain unmeasured.
  </Reveal>
  <Footer>Reproducible commands and capture evidence are included in the repository</Footer>
</AbsoluteFill>;

export const Demo = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const fade = interpolate(frame, [0, 10, durationInFrames - 15, durationInFrames - 1],
    [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{background: C.dark, fontFamily: sans}}>
    <AbsoluteFill style={{opacity: fade}}>
      <Sequence durationInFrames={INTRO}><Intro/></Sequence>
      <Sequence from={INTRO} durationInFrames={TERMINAL}><Terminal/></Sequence>
      <Sequence from={INTRO + TERMINAL} durationInFrames={PATCH}><Patch/></Sequence>
      <Sequence from={INTRO + TERMINAL + PATCH} durationInFrames={GUIDE}><Guide/></Sequence>
      <Sequence from={INTRO + TERMINAL + PATCH + GUIDE} durationInFrames={END}><Results/></Sequence>
    </AbsoluteFill>
    <div style={{position: 'absolute', bottom: 0, left: 0, height: 6, background: C.lime,
      width: `${frame / (durationInFrames - 1) * 100}%`}}/>
  </AbsoluteFill>;
};
