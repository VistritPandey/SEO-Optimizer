import React from "react";
import {AbsoluteFill, Img, Sequence, interpolate, staticFile, useCurrentFrame} from "remotion";
import {BrandSymbol} from "../../frontend/components/BrandSymbol";
import proof from "../public/session/session.json";

const ink = "#e9ece3", muted = "#9da9a2", mint = "#d4f4b4", red = "#f2a89a";
const mono = '"SFMono-Regular", Menlo, "DejaVu Sans Mono", monospace';
export const SESSION_SCENES = [
  {seconds: 6, label: "01 / THE PROBLEM", title: "The page looks fine. The next click isn’t.", caption: "A collection link leads visitors to a real 404 on our fictional shop."},
  {seconds: 7, label: "02 / INVESTIGATE", title: "The agent opens the source. Not a guess.", caption: "It reads the actual files behind the confirmed audit findings."},
  {seconds: 10, label: "03 / REPAIR", title: "Fix the cause. Keep the change small.", caption: "Actual patch excerpts: add a description, repair the link and correct the product offer."},
  {seconds: 8, label: "04 / VERIFY", title: "A proposed fix has to pass the checks.", caption: "The agent runs the project’s checks on its staged files. The worker verifies the served pages."},
  {seconds: 8, label: "05 / THE RESULT", title: "Same shop. A working next step.", caption: "Four confirmed defects resolved in two files. No regressions detected in this audit."},
  {seconds: 8, label: "06 / KEEP WATCHING", title: "Healthy pages don’t need busywork.", caption: "A repeat audit creates no commit. A docs-only merge triggers no AI inference."},
  {seconds: 5, label: "YOUR OPTIMISER", title: "Your site moves forward. Your SEO keeps up.", caption: "Discover the issue. Repair the source. Check the result. Keep watching."},
];
export const SESSION_DURATION = SESSION_SCENES.reduce((n, s) => n + s.seconds * 30, 0);

const Terminal: React.FC<{children: React.ReactNode; title: string}> = ({children, title}) => (
  <div style={{height: "100%", background: "#0d1311", border: "1px solid #34423a", borderRadius: 13, overflow: "hidden", boxShadow: "0 22px 65px #0004"}}>
    <div style={{height: 65, display: "flex", alignItems: "center", borderBottom: "1px solid #2b3831", padding: "0 28px", gap: 10, color: muted, font: `19px ${mono}`}}>
      {["#b8877a", "#bdac7d", "#8eac8c"].map(c => <i key={c} style={{width: 11, height: 11, background: c, borderRadius: 10}}/>)}
      <span style={{marginLeft: 20}}>{title}</span><span style={{marginLeft: "auto", fontSize: 16}}>RECORDED SESSION</span>
    </div>
    <div style={{padding: "27px 34px", font: `24px/1.6 ${mono}`, whiteSpace: "pre-wrap", overflowWrap: "anywhere"}}>{children}</div>
  </div>
);
const Line: React.FC<{children: React.ReactNode; color?: string; delay?: number}> = ({children, color = ink, delay = 0}) => {
  const frame = useCurrentFrame();
  return <div style={{color, opacity: interpolate(frame, [delay, delay + 6], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp"}), minHeight: 39}}>{children}</div>;
};
const Browser: React.FC<{image: string; path: string; state: string; bad?: boolean}> = ({image, path, state, bad}) => (
  <div style={{borderRadius: 12, border: "1px solid #526053", overflow: "hidden", background: "#f7f5ee"}}>
    <div style={{height: 48, padding: "0 21px", display: "flex", alignItems: "center", justifyContent: "space-between", background: "#233027", color: ink, font: `17px ${mono}`}}><span>{path}</span><span style={{color: bad ? red : mint}}>{state}</span></div>
    <Img src={staticFile(`session/${image}`)} style={{width: "100%", display: "block"}}/>
  </div>
);

const Scene: React.FC<{index: number}> = ({index}) => {
  const frame = useCurrentFrame();
  const scene = SESSION_SCENES[index];
  const reveal = interpolate(frame, [0, 11], [0, 1], {extrapolateRight: "clamp"});
  const events = proof.events;
  const repeat = events.find(e => e.text.startsWith("REPEAT:"))!;
  const docs = events.find(e => e.text.startsWith("MERGED DOCS BRANCH:"))!;
  return <AbsoluteFill style={{padding: "0 86px", opacity: reveal, transform: `translateY(${(1 - reveal) * 10}px)`}}>
    <div style={{position: "absolute", top: 127, color: mint, letterSpacing: 2.3, fontSize: 17, fontWeight: 600}}>{scene.label}</div>
    <h1 style={{position: "absolute", top: 156, margin: 0, fontSize: 59, letterSpacing: -2.2, fontWeight: 500, lineHeight: 1.12, maxWidth: 1680}}>{scene.title}</h1>
    <div style={{position: "absolute", top: 277, left: 86, right: 86, height: 611}}>
      {index === 0 && <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, alignItems: "start"}}>
        <Browser image="before-home.png" path="/" state="LOOKS READY"/>
        <Browser image="before-navigation.png" path="/collections/lighting/" state="404 · NOT FOUND" bad/>
      </div>}
      {index === 1 && <div style={{display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 38, height: "100%"}}>
        <Terminal title="agent / inspect">
          <Line color={muted}>Actual successful tool calls</Line>
          {proof.inspected.map((t, i) => <React.Fragment key={i}><Line delay={25 + i * 52} color={mint}>{`→ ${t.tool}`}</Line><Line delay={32 + i * 52}>{`  ${t.path}`}</Line><Line delay={47 + i * 52} color={muted}>  source returned · success: true</Line></React.Fragment>)}
        </Terminal>
        <div style={{padding: "23px 0", display: "flex", flexDirection: "column", gap: 26}}>
          <div style={{color: muted, fontSize: 19, letterSpacing: 1.7}}>CONFIRMED BEFORE REPAIR</div>
          {["Missing page description", "Collection link returns 404", "Conflicting canonical URLs", "Product data disagrees with price"].map((s, i) => <div key={s} style={{borderTop: "1px solid #3c4b41", paddingTop: 20, fontSize: 27, opacity: frame > 20 + i * 21 ? 1 : .16}}><span style={{color: red, marginRight: 18}}>↳</span>{s}</div>)}
          <div style={{fontSize: 19, color: muted, lineHeight: 1.5}}>The visible price and configured business facts agree: USD 89.00.</div>
        </div>
      </div>}
      {index === 2 && <Terminal title="agent / apply_patch · exact changed excerpts">
        {proof.patch_excerpts.map((r, i) => <Line key={i} delay={12 + i * 22} color={r.kind === "add" ? mint : r.kind === "remove" ? red : muted}>{`${r.kind === "add" ? "+ " : r.kind === "remove" ? "− " : "\n"}${r.text}`}</Line>)}
        <Line delay={210} color={muted}>Surrounding HTML omitted · canonical conflict also removed</Line>
      </Terminal>}
      {index === 3 && <Terminal title="agent / run_checks → worker verification">
        <Line color={mint}>→ run_checks</Line>
        <Line delay={20}>  scope: staged_proposals</Line>
        <Line delay={40}>  command: python verify_site.py</Line>
        <Line delay={75} color={mint}>{proof.check_stdout}</Line>
        <Line delay={105}>  exit_code: 0</Line>
        <Line delay={133} color={muted}>Independent worker result</Line>
        <Line delay={150}>  stage: verified · served pages re-audited</Line>
        <Line delay={175}>  defects: 4 → 0 · regressions: 0</Line>
        <Line delay={200} color={mint}>  Private preview and crawler policy preserved.</Line>
      </Terminal>}
      {index === 4 && <div style={{display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28}}>
        <Browser image="before-navigation.png" path="BEFORE / collection link" state="404" bad/>
        <Browser image="after-navigation.png" path="AFTER /shop/" state="WORKING COLLECTION"/>
      </div>}
      {index === 5 && <Terminal title="worker / follow-up audits">
        <Line color={muted}>Actual follow-up events</Line>
        <Line delay={23} color={mint}>{repeat.text}</Line>
        <Line delay={90}>{docs.text}</Line>
        <Line delay={145} color={muted}>This run’s boundaries</Line>
        <Line delay={165}>  2 source files changed · local Git only</Line>
        <Line delay={185}>  No GitHub push. No search ranking claim.</Line>
      </Terminal>}
      {index === 6 && <div style={{height: "100%", display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "1px solid #3d4b40", borderBottom: "1px solid #3d4b40"}}>
        <div><div style={{fontSize: 113, letterSpacing: -6, fontWeight: 500, lineHeight: 1.05}}>Your Optimiser<span style={{color: mint}}>.</span></div><div style={{fontSize: 29, color: muted, marginTop: 37}}>An SEO agent that works on your code.</div><div style={{font: `26px ${mono}`, color: mint, marginTop: 48}}>youroptimiser.com ↗</div></div>
        <div style={{color: mint, width: 200, height: 200}}><BrandSymbol/></div>
      </div>}
    </div>
    <div style={{position: "absolute", left: 86, right: 86, top: 928, fontSize: 25, lineHeight: 1.45, color: ink}}>{scene.caption}</div>
  </AbsoluteFill>;
};

export const AgentSession = () => {
  const frame = useCurrentFrame();
  let offset = 0;
  return <AbsoluteFill style={{background: "#19221d", color: ink, fontFamily: 'Arial, Helvetica, sans-serif'}}>
    <style>{`.brand-symbol { width: 100%; height: 100%; display: block; }`}</style>
    <div style={{position: "absolute", left: 86, right: 86, top: 39, display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #3a483e", paddingBottom: 24}}>
      <div style={{display: "flex", alignItems: "center", gap: 12, fontSize: 24, letterSpacing: -.7}}><div style={{width: 35, height: 35, color: mint}}><BrandSymbol/></div>Your Optimiser</div>
      <div style={{font: `17px ${mono}`, color: muted}}>FIELD NOTES / 001 <span style={{color: mint, marginLeft: 34}}>● AGENT AT WORK</span></div>
    </div>
    {SESSION_SCENES.map((scene, i) => {const from = offset; offset += scene.seconds * 30; return <Sequence key={i} from={from} durationInFrames={scene.seconds * 30}><Scene index={i}/></Sequence>;})}
    <div style={{position: "absolute", left: 86, right: 86, bottom: 32, display: "flex", justifyContent: "space-between", font: `16px ${mono}`, color: muted}}><span>Recorded local run · Fictional shop · Edited for time</span><span>{String(Math.floor(frame / 30)).padStart(2, "0")} / 52s · SILENT</span></div>
    <div style={{position: "absolute", bottom: 0, height: 3, background: mint, width: `${frame / (SESSION_DURATION - 1) * 100}%`}}/>
  </AbsoluteFill>;
};
