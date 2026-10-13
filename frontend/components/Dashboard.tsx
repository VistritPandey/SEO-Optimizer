'use client';
import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {useCallback, useEffect, useState} from 'react';
import {onAuthStateChanged, sendEmailVerification, signOut, type User} from 'firebase/auth';
import {firebaseAuth} from '@/lib/firebase';
import {api, type Activity, type Project} from '@/lib/api';
type Account = {email: string; tier: string; jobs_used: number; job_limit: number | null; project_limit: number; github_install_url?: string};
type Repository = {repository: string; branch: string; private: boolean};
export function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project | null>(null);
  const [activity, setActivity] = useState<Activity>({jobs: [], findings: []});
  const [tab, setTab] = useState('findings');
  const [workspace, setWorkspace] = useState('{}'); const [spec, setSpec] = useState('{}');
  const [strategy, setStrategy] = useState<unknown>(null);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [newProject, setNewProject] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const refresh = useCallback(async () => {
    const [profile, list] = await Promise.all([api<Account>('account'), api<Project[]>('projects')]);
    setAccount(profile); setProjects(list);
  }, []);
  useEffect(() => {
    try {return onAuthStateChanged(firebaseAuth(), current => {
      if (!current) {router.replace('/login'); return;}
      setUser(current);
      if (current.emailVerified) refresh().catch(error => setError(error.message));
    });} catch (error) {setError(error instanceof Error ? error.message : 'Authentication unavailable.');}
  }, [refresh, router]);
  useEffect(() => {
    if (!selected) return;
    let alive = true;
    const collect = () => api<Activity>('projects/' + selected.id + '/activity')
      .then(value => {if (alive) setActivity(value);})
      .catch(error => {if (alive) setError(error.message);});
    collect(); const timer = setInterval(collect, 7000);
    return () => {alive = false; clearInterval(timer);};
  }, [selected]);
  async function action(work: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try {await work();} catch (error) {setError(error instanceof Error ? error.message : 'Action failed.');}
    finally {setBusy(false);}
  }
  async function choose(project: Project) {
    setSelected(project); setNewProject(false); setTab('findings');
    const {provider: _provider, ...editable} = project.spec;
    setSpec(JSON.stringify(editable, null, 2));
    await action(async () => {
      const [research, brief] = await Promise.all([api<unknown>('projects/' + project.id + '/research'), api<unknown>('projects/' + project.id + '/strategy')]);
      setWorkspace(JSON.stringify(research, null, 2)); setStrategy(brief);
    });
  }
  async function connect() {await action(async () => {const value = await api<{url: string}>('github/connect', 'POST'); window.location.assign(value.url);});}
  async function loadRepos() {await action(async () => {const value = await api<{repositories: Repository[]}>('github/repositories'); setRepos(value.repositories); if (!value.repositories.length) setNotice('Install the GitHub App on selected repositories, then refresh.');});}
  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    await action(async () => {
      const repo = repos.find(item => item.repository === data.get('repository'));
      if (!repo) throw new Error('Choose a verified repository.');
      const value = await api<Project>('projects', 'POST', {spec: {
        name: data.get('name'), website_url: data.get('url'), repository: repo.repository,
        branch: repo.branch, website_types: [data.get('type')], goals: [String(data.get('goal'))].filter(Boolean),
        allowed_paths: String(data.get('paths')).split(',').map(item => item.trim()).filter(Boolean),
        auto_fix: data.get('auto_fix') === 'on', auto_merge: false,
      }});
      await refresh(); setSelected(value); setNewProject(false); setNotice('Connected. Your first audit is queued.');
    });
  }
  const activeJobs = activity.jobs.filter(job => ['queued', 'running', 'waiting_checks', 'waiting_deployment'].includes(job.status));
  return <div className="workspace-shell"><aside className="sidebar"><Link className="brand" href="/">y<span>Your Optimiser</span></Link><span className="eyebrow">WORKSPACE</span><button className={!selected && !newProject ? 'nav-item active' : 'nav-item'} onClick={() => {setSelected(null); setNewProject(false);}}>◫ Overview</button><button className="nav-item" onClick={() => {setSelected(null); setNewProject(true);}}>＋ Connect website</button><div className="sidebar-note"><span className="dot"/>Evidence before action<p>Your goals. Verified facts.<br/>A record of every change.</p></div><small>{account?.email || user?.email}</small><button className="nav-item" onClick={() => action(async () => {await signOut(firebaseAuth()); router.push('/login');})}>Sign out ↗</button></aside>
    <main className="dashboard-main"><header className="topbar"><span>WORKSPACE / {selected?.spec.name || (newProject ? 'CONNECT WEBSITE' : 'OVERVIEW')}</span><span className="pill">{account?.tier || 'Workspace'}</span></header>
      {error && <p role="alert" className="alert">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
      {user && !user.emailVerified ? <section className="panel"><h1>One small step.</h1><p>Verify your email to connect a repository and begin.</p><button className="button" onClick={() => action(async () => {await sendEmailVerification(user); setNotice('Verification email sent.');})}>Resend verification</button><button className="text-link" onClick={() => action(async () => {await user.reload(); await user.getIdToken(true); setUser({...user} as User); if (user.emailVerified) await refresh();})}>I’ve verified my email ↗</button></section> : !account ? <section className="panel"><p>Loading your workspace…</p><button onClick={() => action(refresh)}>Retry connection</button></section> : newProject ? <>
        <section className="page-heading"><span className="eyebrow">A NEW CONNECTION</span><h1>Give your website<br/><em>a working partner.</em></h1><p>Connect only the repositories you want this workspace to access.</p></section>
        <section className="panel"><h2>01 · Repository access</h2><div className="actions">{account.github_install_url && <a className="button secondary" href={account.github_install_url} target="_blank" rel="noreferrer">Install GitHub App ↗</a>}<button className="button secondary" disabled={busy} onClick={connect}>Connect GitHub account ↗</button><button className="text-link" disabled={busy} onClick={loadRepos}>Refresh repositories ↻</button></div><p>Installation limits access to selected repositories. Account authorization verifies which repositories you can manage.</p></section>
        <form className="panel" onSubmit={create}><h2>02 · Your website</h2><div className="form-grid"><label>Project name<input name="name" required maxLength={100}/></label><label>Deployed website URL<input name="url" type="url" required placeholder="https://example.com"/></label><label>Verified repository<select name="repository" required><option value="">Select repository</option>{repos.map(repo => <option key={repo.repository}>{repo.repository}</option>)}</select></label><label>Website type<select name="type"><option value="generic">General website</option><option value="ecommerce">Ecommerce</option><option value="local">Local business</option><option value="saas">SaaS</option><option value="publishing">Publishing</option><option value="docs">Documentation</option></select></label><label>Directories to monitor<input name="paths" defaultValue="public,web,src,app,pages,content" required/></label><label>What matters to your business?<input name="goal" placeholder="Help qualified customers find our products" maxLength={500}/></label></div><label className="checkbox"><input name="auto_fix" type="checkbox"/>Open PRs for supported, verified repairs</label><p>Content publication starts off. Reviewed facts and original source material are required before enabling content refreshes. You review and merge hosted PRs.</p><button className="button" disabled={busy || !repos.length}>Connect & start audit ↗</button></form>
      </> : selected ? <>
        <section className="page-heading"><span className="eyebrow">YOUR WEBSITE</span><h1>{selected.spec.name}</h1><p>{selected.spec.website_url}</p><div className="actions"><button className="button" disabled={busy} onClick={() => action(async () => {await api('projects/' + selected.id + '/jobs', 'POST'); setNotice('Audit queued.');})}>Run audit ↗</button><button className="text-link" onClick={() => action(async () => {await api('projects/' + selected.id, 'PATCH', {...selected.spec, enabled: !selected.spec.enabled}); await refresh(); setSelected({...selected, spec: {...selected.spec, enabled: !selected.spec.enabled}});})}>{selected.spec.enabled ? 'Pause monitoring' : 'Resume monitoring'}</button></div></section>
        <div className="metrics"><article><span>OBSERVED HEALTH</span><strong>{selected.last_report.score ?? '—'}<small>{selected.last_report.score !== undefined ? '/100' : ''}</small></strong><p>Supported checks only; this is not a ranking score.</p></article><article><span>ACTIVE FINDINGS</span><strong>{activity.findings.filter(item => item.active).length}</strong><p>Evidence-backed defects and unresolved assessments.</p></article><article><span>WORK IN PROGRESS</span><strong>{activeJobs.length}</strong><p>Queued work, checks and deployment verification.</p></article></div>
        <div className="tabs" role="tablist" aria-label="Project details">{['findings', 'activity', 'research', 'policy'].map(item => <button key={item} role="tab" aria-selected={tab === item} onClick={() => setTab(item)}>{item}</button>)}</div>
        {tab === 'findings' && <section className="panel"><h2>Findings & evidence</h2>{!activity.findings.length ? <p>Your first findings appear after an audit. An empty list does not establish that every SEO check passed.</p> : activity.findings.map(item => <details key={item.id}><summary><span>{item.details.check_id}</span><span className="pill">{item.active ? item.details.status : 'resolved'}</span></summary><p>{item.details.url}</p><pre>{JSON.stringify(item.details, null, 2)}</pre></details>)}</section>}
        {tab === 'activity' && <section className="panel"><h2>Activity & pull requests</h2>{!activity.jobs.length && <p>No jobs yet.</p>}{activity.jobs.map(job => <details key={job.id}><summary><span>{job.result.summary || job.kind + ' queued'}</span><span className="pill">{job.status.replaceAll('_', ' ')}</span></summary>{job.result.pr?.url.startsWith('https://github.com/') && <a href={job.result.pr.url} target="_blank" rel="noreferrer" className="text-link">View pull request #{job.result.pr.number} ↗</a>}<p>Verified fixes: {job.result.verified_fixes ?? 'not established'}</p><pre>{JSON.stringify(job.result, null, 2)}</pre></details>)}</section>}
        {tab === 'research' && <section className="panel"><h2>Useful content starts with your evidence.</h2><p>Add owner-reviewed original materials, measured search observations and citation transcripts. Synthetic observations must be labelled. Unsupported claims remain dependencies.</p><label>Research workspace JSON<textarea value={workspace} onChange={event => setWorkspace(event.target.value)} rows={16} spellCheck={false}/></label><button className="button" disabled={busy} onClick={() => action(async () => {await api('projects/' + selected.id + '/research', 'PUT', JSON.parse(workspace)); setStrategy(await api('projects/' + selected.id + '/strategy')); setNotice('Research saved and strategy refreshed.');})}>Save evidence ↗</button><details><summary>Content opportunities & dependencies</summary><pre>{JSON.stringify(strategy, null, 2)}</pre></details></section>}
        {tab === 'policy' && <section className="panel"><h2>Your project policy</h2><p>Configure monitored paths, route mappings, verified facts, crawler preferences and required checks. Application policy preserves private pages and unsupported claims. Build commands need a portable worker with Docker.</p><label>Project settings JSON<textarea value={spec} onChange={event => setSpec(event.target.value)} rows={18} spellCheck={false}/></label><button className="button" disabled={busy} onClick={() => action(async () => {await api('projects/' + selected.id, 'PATCH', JSON.parse(spec)); await refresh(); setNotice('Policy updated.');})}>Save policy ↗</button></section>}
      </> : <><section className="page-heading"><span className="eyebrow">A CLEARER VIEW</span><h1>Your websites,<br/><em>moving forward.</em></h1><p>Evidence-backed updates. A clear record of what happened.</p></section><div className="metrics"><article><span>CONNECTED WEBSITES</span><strong>{projects.length}<small>/{account.project_limit}</small></strong><p>Each with its own goals and policy.</p></article><article><span>THIS MONTH’S JOBS</span><strong>{account.jobs_used}<small>/{account.job_limit ?? '∞'}</small></strong><p>Audits, content jobs and review follow-ups.</p></article><article><span>YOUR PLAN</span><strong className="text-metric">Free</strong><p>No payment required. Paid plans come later.</p></article></div><section className="section"><div className="section-heading"><h2>Your projects</h2><button className="button" onClick={() => setNewProject(true)}>Connect website ＋</button></div><div className="project-grid">{projects.map(project => <button className="project-card" key={project.id} onClick={() => choose(project)}><span className="pill">{project.spec.enabled ? 'Monitoring' : 'Paused'}</span><h3>{project.spec.name}</h3><p>{project.spec.website_url}</p><div className="project-health"><span>OBSERVED HEALTH</span><strong>{project.last_report.score ?? '—'}<small>/100</small></strong></div><span>{project.last_report.pages ?? 0} pages observed ↗</span></button>)}</div>{!projects.length && <div className="empty"><h3>A good place to start.</h3><p>Connect a website and repository. Your first audit will start automatically.</p><button className="button" onClick={() => setNewProject(true)}>Connect your first website ↗</button></div>}</section><section className="panel"><h2>Repository access</h2><p>You can disconnect GitHub at any time. Connected projects pause and their installation credentials are removed from the workspace.</p><button className="text-link" onClick={() => action(async () => {await api('github/connect', 'DELETE'); await refresh(); setNotice('GitHub disconnected; repository projects paused.');})}>Disconnect GitHub</button></section></>}
      <footer>Your Optimiser · Measured improvements, with a record of every change.</footer>
    </main></div>;
}
