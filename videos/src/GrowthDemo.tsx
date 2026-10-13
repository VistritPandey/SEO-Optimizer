import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, interpolate} from 'remotion';
import proof from '../public/growth-proof.json';

const ink = '#20372c', paper = '#f4f2e8', dark = '#0c211b', accent = '#cce59a';
const mono = 'ui-monospace, SFMono-Regular, Menlo, monospace';
const sans = '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
export const GROWTH_FPS = 30;
export const GROWTH_DURATION = 90 * GROWTH_FPS;
const Shell: React.FC<{chapter: string; title: string; children: React.ReactNode; light?: boolean; footer?: string}> =
({chapter, title, children, light=false, footer}) => <AbsoluteFill style={{background: light ? paper : dark,
  color: light ? ink : paper, padding: '54px 76px', fontFamily: sans}}>
  <div style={{font: `20px ${mono}`, letterSpacing: 2, opacity: .75}}>SEO OPTIMIZER / {chapter}</div>
  <h1 style={{fontSize: 66, letterSpacing: -2.5, margin: '24px 0 30px', fontWeight: 550, lineHeight: 1.13}}>{title}</h1>
  {children}<div style={{position: 'absolute', bottom: 29, left: 76, right: 76, fontSize: 19,
    display: 'flex', justifyContent: 'space-between', opacity: .75}}>
    <span>{footer ?? 'Actual application evidence · anonymous fixtures · no live GitHub publication'}</span>
    <span>INSPECT → CHANGE → VERIFY</span></div>
</AbsoluteFill>;
const Intro = () => {
 const frame=useCurrentFrame();
 const stages=['Observe the site', 'Use original evidence', 'Change & check the code', 'Verify the served result'];
 return <Shell chapter="A WORKING OPTIMIZATION LOOP" title="A useful change. With proof." light>
  <div style={{display:'flex',gap:55,alignItems:'center'}}>
   <div style={{width:780}}><p style={{fontSize:38,lineHeight:1.5}}>Technical repairs, supported content,<br/>and a model comparison you can inspect.</p>
    {stages.map((stage,i)=><div key={stage} style={{fontSize:28,margin:'26px 0',opacity:interpolate(frame,[i*12,i*12+15],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}}><span style={{background:accent,padding:'6px 15px',marginRight:20}}>0{i+1}</span>{stage}</div>)}
   </div><Img src={staticFile('growth-strategy.png')} style={{width:910,borderRadius:15,boxShadow:'0 15px 45px #0002'}}/>
  </div>
 </Shell>;
};
const Defects = () => <Shell chapter="01 / THE ACTUAL PROBLEM" title="A broken shopping path. Contradictory product data.">
 <div style={{display:'flex',gap:45}}><Img src={staticFile('before-navigation.png')} style={{width:1030,height:650,objectFit:'cover',borderRadius:16}}/>
  <div style={{flex:1,paddingTop:15,fontSize:30,lineHeight:1.6}}><div style={{fontSize:108,color:'#e4ad92',fontFamily:mono}}>404</div><p>The customer cannot reach the collection.</p><p>The visible price is USD 89.<br/>The offer declares USD 129.</p><p>Two canonical URLs disagree.<br/>The homepage lacks a description.</p></div>
 </div>
</Shell>;
const Tools = () => <Shell chapter="02 / REAL MODEL ACTIONS" title="Read source. Stage a patch. Run the checks.">
 <div style={{display:'flex',gap:38}}><div style={{width:1240,borderRadius:16,overflow:'hidden',background:'#061710'}}>
  <OffthreadVideo src={staticFile('terminal-inspection.mp4')} muted loop style={{width:1240,height:660,objectFit:'contain'}}/>
 </div><div style={{flex:1,fontSize:29,lineHeight:1.6}}><p>{proof.technicalToolCalls} recorded tool calls.</p><p>Exact source replacements.<br/>Independent path, fact,<br/>privacy and behavior guards.</p><p>Build the staged copy.<br/>Merge permitted work.<br/>Inspect the served pages.</p><div style={{background:accent,color:ink,padding:20,borderRadius:14}}>The model proposes.<br/>The application verifies.</div></div></div>
</Shell>;
const Repairs = () => <Shell chapter="03 / VERIFIED REPAIR" title="The changes have observable outcomes." light>
 <div style={{display:'flex',gap:50}}><Img src={staticFile('after-product.png')} style={{width:1110,height:675,objectFit:'cover',borderRadius:16}}/>
 <div style={{flex:1,fontSize:28,lineHeight:1.6}}>{['Collection link opens /shop/', 'One correct product canonical', 'Valid offer matches visible USD 89', 'Private preview stays private', 'Training opt-out preserved'].map(t=><p key={t} style={{borderBottom:'1px solid #c9d0bf',paddingBottom:17}}>✓ {t}</p>)}<strong style={{fontSize:60}}>{proof.technicalBefore} → {proof.technicalAfter}</strong><p>Confirmed defects in the recorded repair</p></div></div>
</Shell>;
const Strategy = () => <Shell chapter="04 / EVIDENCE GUIDES THE NEXT CHANGE" title="An original contribution, attached to a real brief." light footer="The owner notebook and search measurements shown here are explicitly synthetic demo inputs.">
 <div style={{display:'flex',gap:42}}><Img src={staticFile('growth-strategy.png')} style={{width:1110,height:705,objectFit:'cover',objectPosition:'top',borderRadius:14}}/>
 <div style={{flex:1,fontSize:28,lineHeight:1.6}}><p>{proof.syntheticImpressions} impressions / {proof.syntheticClicks} clicks<br/><strong>synthetic demonstration data</strong></p><p>Confirmed business relevance.<br/>Reviewed original owner passage.<br/>Current fact reference.<br/>A mapped target page.</p><p>The worker records missing inputs instead of inventing evidence.</p></div></div>
</Shell>;
const Publish = () => <Shell chapter="05 / THE WORKER RUNS THE LOOP" title="Audit → strategy → grounded content publication.">
 <div style={{display:'flex',gap:40}}><OffthreadVideo src={staticFile('growth-workflow.webm')} muted startFrom={10*30}
   style={{width:1090,height:725,objectFit:'contain',borderRadius:14,background:paper}}/>
 <div style={{flex:1,fontSize:27,lineHeight:1.55}}><p>One supported refresh is queued automatically within project policy.</p><p>A real Docker check verifies the staged page before the commit.</p><pre style={{fontSize:20,whiteSpace:'pre-wrap',background:'#183b2c',padding:25,borderRadius:14}}>{proof.buildOutput || 'Independent content verification passed'}</pre><p>Commit {proof.contentCommit}<br/>Repeated job: no extra commit.</p></div></div>
</Shell>;
const Content = () => <Shell chapter="06 / SERVED CONTENT VERIFICATION" title="The owner’s supported passage is now on the page." light footer="Verified publication is observable. Search uplift remains unmeasured.">
 <div style={{display:'flex',gap:26}}>{['growth-before.png','growth-after.png'].map((src,i)=><div key={src} style={{width:866}}><div style={{font:`22px ${mono}`,marginBottom:16}}>{i===0?'BEFORE / NO ORIGINAL PASSAGE':'AFTER / SUPPORTED ORIGINAL PASSAGE'}</div><Img src={staticFile(src)} style={{width:866,height:602,objectFit:'cover',objectPosition:'top',borderRadius:14}}/></div>)}</div>
 <p style={{fontSize:27,marginTop:20}}>Exact owner-verified text · factual support retained · existing page behavior preserved</p>
</Shell>;
const Benchmarks = () => <Shell chapter="07 / MATCHED MODEL EXPERIMENT" title="Same frozen repository. Same outcome checks." footer={proof.caveat}>
 <div style={{font:`22px ${mono}`,opacity:.75,marginBottom:20}}>BASE COMMIT {proof.frozenCommit} / FOUR REPAIR TARGETS / FAILURES RETAINED</div>
 <table style={{width:'100%',borderCollapse:'collapse',fontSize:29}}><thead><tr style={{color:accent,textAlign:'left'}}>{['Run','Verified repairs','Healthy control','Irrelevant merge','Unneeded edits'].map(h=><th key={h} style={{padding:'20px 14px',fontWeight:500,fontSize:24}}>{h}</th>)}</tr></thead>
 <tbody>{proof.arms.map(a=><tr key={a.id} style={{borderTop:'1px solid #42614d'}}><td style={{padding:'25px 14px'}}>{a.label}</td><td style={{fontFamily:mono,color:a.verified===4?accent:'#e4ad92'}}>{a.verified}/4</td><td>{a.healthy===null?'pending':a.healthy?'passed':'failed'}</td><td>{a.irrelevant===null?'pending':a.irrelevant?'passed':'failed'}</td><td>{a.unnecessary}</td></tr>)}</tbody></table>
 <p style={{fontSize:24,lineHeight:1.6,marginTop:28}}>Full harness adds the private skill, rule evidence and focused check guidance.<br/>Both model arms retain the same publication guards. Unknown costs stay unknown.</p>
</Shell>;
const End = () => <Shell chapter="MEASURE THE NEXT OUTCOME" title="Built for evidence. Ready for harder cases." light>
 <div style={{display:'flex',gap:65,marginTop:50}}><div style={{width:940,fontSize:38,lineHeight:1.65}}>A portable Python worker.<br/>Your configured model.<br/>Project-scoped evidence and policy.<br/>A record of every verified change.</div>
 <div style={{flex:1,background:ink,color:paper,padding:40,borderRadius:20,fontSize:29,lineHeight:1.7}}><strong style={{color:accent}}>What is proved here</strong><br/>Local repairs and supported publication.<br/>Actual tools, builds, commits and HTTP checks.<br/><br/><strong style={{color:accent}}>What still needs live data</strong><br/>Search traffic, consumer-engine citations,<br/>conversions and production GitHub outcomes.</div></div>
 <p style={{fontSize:29,marginTop:55}}>No provider promotion. No invented ranking gains.</p>
</Shell>;
export const GrowthDemo = () => <AbsoluteFill>{[
 [0,180,<Intro/>], [180,240,<Defects/>], [420,270,<Tools/>], [690,240,<Repairs/>],
 [930,300,<Strategy/>], [1230,330,<Publish/>], [1560,270,<Content/>],
 [1830,570,<Benchmarks/>], [2400,300,<End/>],
].map(([from,duration,node],i)=><Sequence key={i} from={from as number} durationInFrames={duration as number}>{node as React.ReactNode}</Sequence>)}</AbsoluteFill>;
