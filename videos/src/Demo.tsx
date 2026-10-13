import React from 'react';
import {
  AbsoluteFill, Img, interpolate, OffthreadVideo, Sequence, spring, staticFile,
  useCurrentFrame,
} from 'remotion';
import proof from '../public/demo.json';

const C = {ink: '#20372c', paper: '#f4f2e8', mint: '#cce59a', dark: '#0c211b', dim: '#a5b8a3', red: '#dca68d'};
const mono = 'ui-monospace, SFMono-Regular, Menlo, monospace';
const sans = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
export const FPS = 30;
export const DURATION = 70 * FPS;
const Label: React.FC<{children: React.ReactNode}> = ({children}) =>
  <div style={{font: `21px ${mono}`, letterSpacing: 2.5, textTransform: 'uppercase'}}>{children}</div>;
const Reveal: React.FC<{children: React.ReactNode; delay?: number; style?: React.CSSProperties}> =
  ({children, delay = 0, style}) => {
    const frame = useCurrentFrame();
    const value = spring({frame: frame - delay, fps: FPS, config: {damping: 200}});
    return <div style={{opacity: value, transform: `translateY(${(1 - value) * 28}px)`, ...style}}>{children}</div>;
  };
const Footer: React.FC<{children: React.ReactNode}> = ({children}) =>
  <div style={{position: 'absolute', bottom: 32, left: 80, right: 80, fontSize: 19,
    display: 'flex', justifyContent: 'space-between', opacity: .7}}>
    <span>{children}</span><span>SEO OPTIMIZER / REAL AGENT DEMO</span></div>;
const Browser: React.FC<{children: React.ReactNode; address: string; style?: React.CSSProperties}> =
  ({children, address, style}) => <div style={{borderRadius: 18, overflow: 'hidden',
    border: '1px solid #5b6a53', background: C.paper, boxShadow: '0 25px 70px #0003', ...style}}>
    <div style={{height: 46, background: '#dfe3d4', color: '#55684f', font: `15px ${mono}`,
      display: 'flex', alignItems: 'center', padding: '0 24px', gap: 24}}>
      <span>● ● ●</span><span>{address}</span><span style={{marginLeft: 'auto'}}>LOCAL CAPTURE</span>
    </div>{children}
  </div>;
const Intro = () => <AbsoluteFill style={{background: C.paper, color: C.ink, padding: '78px 90px'}}>
  <Label>A real model repair / fictional store / local worker</Label>
  <div style={{display: 'flex', gap: 70, marginTop: 65, alignItems: 'center'}}>
    <div style={{flex: 1}}>
      <Reveal style={{fontSize: 108, fontWeight: 600, letterSpacing: -5, lineHeight: 1.06}}>
        Inspect the site.<br/>Change the code.<br/><span style={{background: C.mint}}>Verify the result.</span>
      </Reveal>
      <Reveal delay={12} style={{fontSize: 30, lineHeight: 1.65, marginTop: 38}}>
        {proof.model}<br/>Two files repaired by the model. Real tools and isolated checks.
      </Reveal>
    </div>
    <Reveal delay={8} style={{width: 690}}>
      <Img src={staticFile('before-home.png')} style={{width: '100%', borderRadius: 18}}/>
      <div style={{fontSize: 22, marginTop: 20}}>Cedar Workshop · a controlled storefront fixture</div>
    </Reveal>
  </div><Footer>Actual browser and terminal recordings · no live GitHub publication</Footer>
</AbsoluteFill>;

const Before = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: C.dark, color: C.paper, padding: '48px 80px'}}>
    <Label>01 / Before the repair · actual browser recording</Label>
    <div style={{display: 'flex', gap: 44, marginTop: 38, alignItems: 'center'}}>
      <Browser address={frame < 80 ? 'cedar.local/' : 'cedar.local/collections/lighting/'} style={{width: 1312}}>
        {frame < 80 ? <OffthreadVideo src={staticFile('before.mp4')} muted
          style={{width: 1312, height: 820, objectFit: 'cover'}}/>
          : <Img src={staticFile('before-navigation.png')} style={{width: 1312, height: 820}}/>}
      </Browser>
      <div style={{flex: 1, minWidth: 0}}>
        <div style={{fontSize: 58, letterSpacing: -2, lineHeight: 1.08, fontWeight: 600}}>
          The storefront<br/>looks fine.
        </div>
        <div style={{fontSize: 30, lineHeight: 1.5, marginTop: 35}}>
          A customer clicks<br/>“Explore the collection”.
        </div>
        <Reveal delay={80} style={{font: `92px ${mono}`, color: C.red, marginTop: 38}}>404</Reveal>
        <Reveal delay={83} style={{fontSize: 25, lineHeight: 1.5, color: C.dim}}>
          The shopping path is broken. Source inspection also finds metadata and product-data defects.
        </Reveal>
      </div>
    </div><Footer>The missing route is observed, not inferred from the screenshot</Footer>
  </AbsoluteFill>;
};

const Evidence = () => <AbsoluteFill style={{background: C.paper, color: C.ink, padding: '66px 90px'}}>
  <Label>02 / The agent has evidence to act</Label>
  <div style={{fontSize: 72, fontWeight: 600, letterSpacing: -3, marginTop: 30}}>Four defects. Two source files.</div>
  <div style={{display: 'flex', gap: 45, marginTop: 50}}>
    <div style={{width: 1010}}><Img src={staticFile('before-product.png')} style={{width: '100%', borderRadius: 20}}/>
      <div style={{fontSize: 24, marginTop: 25}}>The page displays USD 89.00. Its malformed offer declares USD {proof.beforePrice}.</div>
    </div>
    <div style={{flex: 1}}>
      {['Missing homepage description', 'Collection link returns 404', `${proof.beforeCanonicals.length} conflicting product canonicals`, 'Invalid product JSON-LD'].map((text, i) =>
        <Reveal key={text} delay={i * 12} style={{padding: '24px 26px', background: '#e5e8db',
          marginBottom: 17, borderRadius: 13, fontSize: 30}}><span style={{color: '#966b48', marginRight: 22}}>0{i + 1}</span>{text}</Reveal>)}
      <Reveal delay={45} style={{fontSize: 24, lineHeight: 1.65, marginTop: 25}}>
        HTTP observations, repository files and supplied product facts justify the changes.
      </Reveal>
    </div>
  </div><Footer>Private preview and crawler preferences are explicit owner policy</Footer>
</AbsoluteFill>;

const Agent = () => {
  const frame = useCurrentFrame();
  const count = Math.min(proof.trace.length, Math.floor(frame / 13) + 1);
  const rows = proof.trace.slice(0, count).slice(-8);
  return <AbsoluteFill style={{background: C.dark, color: C.paper, padding: '58px 90px'}}>
    <Label>03 / Recorded Gemini tool trace · timing condensed</Label>
    <div style={{fontSize: 72, fontWeight: 600, letterSpacing: -2, marginTop: 28}}>
      The model inspects, proposes and checks.
    </div>
    <div style={{display: 'flex', gap: 40, marginTop: 45}}>
      <div style={{width: 1120, border: '1px solid #425747', borderRadius: 20, padding: 32,
        fontFamily: mono, height: 630, background: '#122b20'}}>
        <div style={{color: C.mint, fontSize: 21, marginBottom: 26}}>{proof.model} / executed tool calls</div>
        {rows.map((row, i) => <div key={`${count}-${i}`} style={{display: 'flex', gap: 24,
          padding: '15px 0', borderBottom: '1px solid #2a4130', fontSize: 22}}>
          <span style={{color: row.success ? C.mint : C.red, width: 28}}>{row.success ? '✓' : '×'}</span>
          <span style={{width: 180, color: C.mint}}>{row.name}</span>
          <span style={{color: '#c9d7c0', flex: 1, overflowWrap: 'anywhere'}}>{row.path || row.scope}</span>
        </div>)}
      </div>
      <div style={{flex: 1, minWidth: 0}}>
        <div style={{font: `100px ${mono}`, color: C.mint}}>{proof.toolCalls}</div>
        <div style={{fontSize: 31}}>real model tool calls</div>
        <div style={{fontSize: 28, lineHeight: 1.65, color: C.dim, marginTop: 38}}>
          Reads exact source.<br/>Loads relevant private guidance.<br/>Stages two grounded patches.<br/>Checks the staged files in Docker.
        </div>
        <div style={{fontSize: 22, lineHeight: 1.65, marginTop: 30, color: C.red}}>
          Both model-generated patches pass the staged-site checks.
        </div>
      </div>
    </div><Footer>Each action is taken from the real run record; model output is validated locally</Footer>
  </AbsoluteFill>;
};

const HomePatch = () => <AbsoluteFill style={{background: C.paper, color: C.ink, padding: '70px 90px'}}>
  <Label>04 / Model-generated patch / web/index.html</Label>
  <div style={{fontSize: 76, fontWeight: 600, letterSpacing: -3, marginTop: 35}}>Restore the path to the collection.</div>
  <div style={{display: 'flex', gap: 35, marginTop: 60}}>
    <div style={{flex: 1, padding: 40, background: '#e8ddcf', borderRadius: 20}}>
      <Label>Before / 404 destination</Label><div style={{font: `35px ${mono}`, marginTop: 45, lineHeight: 1.7}}>
        href=<br/>&quot;/collections/lighting/&quot;
      </div>
    </div>
    <Reveal delay={35} style={{flex: 1, padding: 40, background: C.mint, borderRadius: 20}}>
      <Label>After / observed working route</Label><div style={{font: `44px ${mono}`, marginTop: 45, lineHeight: 1.7}}>
        href=<br/>&quot;/shop/&quot;
      </div>
    </Reveal>
  </div>
  <Reveal delay={60} style={{background: '#e5e8da', padding: '32px 40px', marginTop: 45, borderRadius: 18}}>
    <Label>The model also adds a factual description</Label>
    <div style={{fontSize: 30, lineHeight: 1.6, marginTop: 20, maxWidth: 1550}}>{proof.description}</div>
  </Reveal><Footer>Exact route and description are extracted from the model's staged replacement</Footer>
</AbsoluteFill>;

const ProductPatch = () => <AbsoluteFill style={{background: C.dark, color: C.paper, padding: '70px 90px'}}>
  <Label>05 / Model-generated patch / web/products/cedar-lamp/index.html</Label>
  <div style={{fontSize: 72, fontWeight: 600, letterSpacing: -3, marginTop: 35}}>Make the declared facts agree.</div>
  <div style={{display: 'flex', gap: 45, marginTop: 65}}>
    <div style={{width: 1010, background: '#152f24', padding: 40, borderRadius: 20, fontFamily: mono}}>
      <div style={{fontSize: 21, color: C.dim, marginBottom: 35}}>ACTUAL PRODUCT OFFER REPAIR</div>
      <div style={{fontSize: 35, lineHeight: 1.8}}>
        <div style={{color: C.red, textDecoration: 'line-through'}}>&quot;price&quot;: &quot;{proof.beforePrice}&quot;</div>
        <Reveal delay={30} style={{color: C.mint}}>&quot;price&quot;: &quot;{proof.afterPrice}&quot;</Reveal>
        <div>&quot;priceCurrency&quot;: &quot;USD&quot;</div>
        <div style={{fontSize: 25}}>&quot;availability&quot;: &quot;https://schema.org/InStock&quot;</div>
      </div>
      <Reveal delay={45} style={{fontSize: 23, color: C.mint, marginTop: 35}}>✓ Invalid trailing comma removed</Reveal>
    </div>
    <div style={{flex: 1}}>
      <div style={{fontSize: 33, lineHeight: 1.5}}>The rendered page says<br/><strong style={{fontSize: 76}}>USD 89.00</strong></div>
      <Reveal delay={55} style={{borderTop: '1px solid #4b5f49', marginTop: 35, paddingTop: 35}}>
        <div style={{fontSize: 25, color: C.dim}}>Product canonical declarations</div>
        <div style={{font: `70px ${mono}`, marginTop: 15}}>{proof.beforeCanonicals.length} → {proof.afterCanonicals.length}</div>
        <div style={{font: `25px ${mono}`, marginTop: 20, color: C.mint}}>/products/cedar-lamp/</div>
      </Reveal>
    </div>
  </div><Footer>Price is checked against supplied owner facts; no invented reviews or offer claims</Footer>
</AbsoluteFill>;

const Verify = () => <AbsoluteFill style={{background: C.paper, color: C.ink, padding: '65px 90px'}}>
  <Label>06 / The application independently verifies the changes</Label>
  <div style={{fontSize: 77, fontWeight: 600, letterSpacing: -3, marginTop: 35}}>A proposed patch becomes a checked result.</div>
  <div style={{display: 'flex', gap: 45, marginTop: 65}}>
    <div style={{width: 1090, borderRadius: 18, background: C.dark, color: C.paper, overflow: 'hidden'}}>
      <OffthreadVideo src={staticFile('terminal-highlights.mp4')} muted
        style={{width: 1090, height: 618, objectFit: 'contain'}}/>
    </div>
    <div style={{flex: 1, paddingTop: 18, fontSize: 30, lineHeight: 1.55}}>
      {['Exact source and policy validation', 'Isolated semantic checks on staged files', 'Independent checks before publishing', 'One file per local Git commit', 'Fetch and verify the served pages'].map((text, i) =>
        <Reveal key={text} delay={i * 12} style={{marginBottom: 29, display: 'flex', gap: 20}}>
          <span style={{color: '#547030'}}>✓</span><span>{text}</span>
        </Reveal>)}
    </div>
  </div><Footer>Actual terminal excerpts: inspection and final controls · local publication only</Footer>
</AbsoluteFill>;

const After = () => {
  const frame = useCurrentFrame();
  return <AbsoluteFill style={{background: C.dark, color: C.paper, padding: '48px 80px'}}>
    <Label>07 / After the repair · actual browser recording</Label>
    <div style={{display: 'flex', gap: 42, marginTop: 35, alignItems: 'center'}}>
      <Browser address="cedar.local / collection → product" style={{width: 1312}}>
        {frame < proof.afterSeconds * FPS ? <OffthreadVideo src={staticFile('after.mp4')} muted
          style={{width: 1312, height: 820, objectFit: 'contain'}}/> : <Img src={staticFile('after-product.png')} style={{width: 1312, height: 820}}/>}
      </Browser>
      <div style={{flex: 1, minWidth: 0}}>
        <div style={{fontSize: 63, fontWeight: 600, letterSpacing: -2, lineHeight: 1.1}}>The collection<br/>now opens.</div>
        <Reveal delay={55} style={{fontSize: 30, lineHeight: 1.6, marginTop: 32}}>The product route works.<br/>The offer and visible price agree.<br/>The page has one preferred canonical.</Reveal>
        <Reveal delay={100} style={{font: `86px ${mono}`, color: C.mint, marginTop: 35}}>{proof.beforeDefects} → {proof.afterDefects}</Reveal>
        <Reveal delay={105} style={{fontSize: 24, color: C.dim}}>confirmed audit defects</Reveal>
      </div>
    </div><Footer>One commerce assessment still needs crawler evidence; owner checks verify the price</Footer>
  </AbsoluteFill>;
};

const End = () => <AbsoluteFill style={{background: C.paper, color: C.ink, padding: '74px 90px'}}>
  <Label>08 / Useful changes. Evidence. Guardrails.</Label>
  <div style={{fontSize: 90, fontWeight: 600, letterSpacing: -4, marginTop: 40}}>The agent did the work.</div>
  <div style={{display: 'flex', gap: 28, marginTop: 55}}>
    {[[`${proof.beforeDefects} → ${proof.afterDefects}`, 'confirmed defects'], [String(proof.files.length), 'model-edited files'],
      [String(proof.toolCalls), 'real tool calls']].map(([value, text], i) => <Reveal key={text} delay={i * 12}
      style={{flex: 1, padding: 35, background: i === 1 ? C.mint : '#e2e7d5', borderRadius: 20}}>
      <div style={{font: `90px ${mono}`, letterSpacing: -5}}>{value}</div>
      <div style={{fontSize: 30, marginTop: 22}}>{text}</div>
    </Reveal>)}
  </div>
  <Reveal delay={45} style={{fontSize: 30, lineHeight: 1.7, marginTop: 40}}>
    Private preview and training opt-out preserved.<br/>
    Repeat model audit: {proof.repeatCommit === false ? 'no new commit' : 'see run record'}.<br/>
    Documentation branch merged: {proof.docsMergeRequests === 0 ? 'zero inference requests' : 'see run record'}.
  </Reveal>
  <Footer>Controlled synthetic site · exact run evidence included · rankings and live GitHub remain unverified</Footer>
</AbsoluteFill>;

export const Demo = () => {
  const frame = useCurrentFrame();
  const fade = interpolate(frame, [0, 9, DURATION - 15, DURATION - 1], [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const scenes: [number, number, React.ReactNode][] = [[0, 5, <Intro/>], [5, 8, <Before/>],
    [13, 6, <Evidence/>], [19, 9, <Agent/>], [28, 7, <HomePatch/>], [35, 7, <ProductPatch/>],
    [42, 7, <Verify/>], [49, 10, <After/>], [59, 11, <End/>]];
  return <AbsoluteFill style={{background: C.dark, fontFamily: sans}}>
    <AbsoluteFill style={{opacity: fade}}>{scenes.map(([from, duration, component]) =>
      <Sequence key={from} from={from * FPS} durationInFrames={duration * FPS}>{component}</Sequence>)}</AbsoluteFill>
    <div style={{position: 'absolute', left: 0, bottom: 0, height: 5, background: C.mint,
      width: `${frame / (DURATION - 1) * 100}%`}}/>
  </AbsoluteFill>;
};
