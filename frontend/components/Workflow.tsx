'use client';
import {useState} from 'react';
const steps = [
  {title: 'Observe', text: 'Collect the live page, HTTP responses, relevant source files and configured business facts. Separate production pages from intentional previews.', detail: 'A screenshot can answer a visual question. It cannot establish indexing or field performance.'},
  {title: 'Decide', text: 'Use deterministic checks and the private research skill to establish a finding. Match severity and evidence strength to a permitted action.', detail: 'Unknown business hours, unsupported claims and missing evidence become dependencies.'},
  {title: 'Change & test', text: 'Stage precise replacements in an isolated checkout. Enforce path and content policy, then run configured checks before publishing a PR.', detail: 'The model cannot grant itself permission, execute arbitrary host commands or overwrite product behavior.'},
  {title: 'Verify', text: 'After a reviewed merge, wait for deployment and recollect the served page. Confirm the targeted fix and check for regressions.', detail: 'A passing build is a build result. A verified deployed fix is a separate result.'},
];
export function Workflow() {
  const [active, setActive] = useState(0);
  return <div className="workflow"><div role="tablist" aria-label="Agent workflow">{steps.map((step, index) => <button key={step.title} role="tab" id={'step-' + index} aria-controls={'panel-' + index} aria-selected={active === index} onClick={() => setActive(index)}><span>0{index + 1}</span>{step.title}<span>↗</span></button>)}</div><article role="tabpanel" id={'panel-' + active} aria-labelledby={'step-' + active}><span className="eyebrow">STEP 0{active + 1}</span><h3>{steps[active].title}</h3><p>{steps[active].text}</p><small>{steps[active].detail}</small></article></div>;
}
