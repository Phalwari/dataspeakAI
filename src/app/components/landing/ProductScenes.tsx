import { useEffect, useRef, useState } from 'react';
import { motion, useInView, useReducedMotion } from 'motion/react';
import { ArrowRight, ArrowUpRight, BarChart3, Check, ChevronDown, Code2, Database, FileSpreadsheet, FileText, Globe2, HeartPulse, Landmark, MessageSquareCode, Pause, Play, RotateCcw, ShieldCheck, Sparkles, X } from 'lucide-react';
import { Link } from 'react-router';
import './ChatShowcase.css';

// These public walkthroughs use a small illustrative dataset, never tenant data.
const monthly = [4200, 5600, 4800, 6900, 6100, 8000];
const total = monthly.reduce((sum, value) => sum + value, 0);
const money = (value: number) => '$' + value.toLocaleString('en-US');

function useWalkthrough(paused: boolean, count: number) {
  const ref = useRef<HTMLDivElement>(null);
  const visible = useInView(ref, { amount: 0.25 });
  const reduced = useReducedMotion();
  const [step, setStep] = useState(count - 1);
  const [running, setRunning] = useState(false);
  const [hidden, setHidden] = useState(document.hidden);
  useEffect(() => {
    const change = () => setHidden(document.hidden);
    document.addEventListener('visibilitychange', change);
    return () => document.removeEventListener('visibilitychange', change);
  }, []);
  useEffect(() => {
    if (!running || paused || hidden || !visible) return;
    if (reduced || step >= count - 1) { setStep(count - 1); setRunning(false); return; }
    const timer = window.setTimeout(() => setStep(value => value + 1), 850);
    return () => window.clearTimeout(timer);
  }, [running, paused, hidden, visible, reduced, step, count]);
  return { ref, step, running, replay: () => { setStep(reduced ? count - 1 : 0); setRunning(!reduced); } };
}

export function RevenueChart({ compact = false }: { compact?: boolean }) {
  return <div className={compact ? 'lp-chart compact' : 'lp-chart'} role="img" aria-label="Sample monthly revenue: January 4,200; February 5,600; March 4,800; April 6,900; May 6,100; June 8,000 dollars.">
    <div className="lp-chart-grid" />
    <svg viewBox="0 0 560 170" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id={compact ? 'area-small' : 'area-main'} x1="0" y1="0" x2="0" y2="1"><stop stopColor="currentColor" stopOpacity=".35"/><stop offset="1" stopColor="currentColor" stopOpacity="0"/></linearGradient></defs><path d="M0 145 L112 104 L224 127 L336 64 L448 88 L560 30 L560 170 L0 170Z" fill={`url(#${compact ? 'area-small' : 'area-main'})`}/><path className="lp-chart-line" d="M0 145 L112 104 L224 127 L336 64 L448 88 L560 30" fill="none" stroke="currentColor" strokeWidth="3"/></svg>
    {!compact && <div className="lp-axis">{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'].map(month => <span key={month}>{month}</span>)}</div>}
  </div>;
}

const insightDashboards = [
  { name:'Finance', source:'POSTGRESQL / SAMPLE FINANCE', title:'Revenue performance', period:'Jan – Jun', table:'transactions', metrics:[['Net revenue','$1.24M','+12.5% vs prior period'],['Transactions','2,453','98.2% settled'],['Gross margin','34.6%','+2.4 pts'],['Cash collected','$984K','79.4% of revenue']], chart:'Revenue over time', bars:[['Direct',82],['Organic',68],['Partners',49]], line:[42,55,51,69,63,84,78,95], mix:[['Direct',46],['Organic',32],['Partners',14],['Other',8]], periods:[['Jan',62],['Feb',71],['Mar',58],['Apr',82],['May',76],['Jun',91]], summary:'Revenue reached $1.24M, led by direct sales. Margin improved 2.4 points as the strongest months also produced healthier order values.' },
  { name:'E-commerce', source:'SHOPIFY / SAMPLE COMMERCE', title:'Store performance', period:'Last 30 days', table:'orders', metrics:[['Gross sales','$428K','+18.4% growth'],['Orders','6,842','+9.8% volume'],['Conversion','4.82%','+0.6 pts'],['Repeat buyers','38.1%','+4.2% loyalty']], chart:'Daily sales trend', bars:[['Apparel',74],['Home goods',61],['Accessories',43]], line:[82,69,74,58,63,46,52,39], mix:[['Completed',68],['Pending',18],['Refunded',9],['Other',5]], periods:[['Mon',76],['Tue',61],['Wed',83],['Thu',68],['Fri',92],['Sat',88]], summary:'The store is growing through repeat buyers and a stronger mobile conversion rate. Apparel contributes the largest share of sales this period.' },
  { name:'Healthcare', source:'CLINIC CSV / SAMPLE PATIENTS', title:'Care operations', period:'This quarter', table:'appointments', metrics:[['Patients served','12,480','+7.2% capacity'],['Avg wait time','18 min','-11.4% faster'],['No-show rate','4.6%','-1.8 pts'],['Satisfaction','92%','+3.1 pts']], chart:'Visits by week', bars:[['Primary care',88],['Diagnostics',64],['Follow-up',52]], line:[48,52,61,57,72,78,74,91], mix:[['Primary care',46],['Diagnostics',28],['Follow-up',18],['Other',8]], periods:[['Jan',54],['Feb',66],['Mar',72],['Apr',61],['May',82],['Jun',88]], summary:'Patient flow is healthiest in primary care, while average wait time continues to fall. Follow-up capacity is the clearest opportunity for the next quarter.' },
  { name:'SaaS', source:'STRIPE / SAMPLE SUBSCRIPTIONS', title:'Subscription health', period:'Q2 overview', table:'subscriptions', metrics:[['MRR','$286K','+14.8% growth'],['Active accounts','1,842','+126 this month'],['Churn','2.1%','-0.7 pts'],['Expansion','$42K','14.7% of MRR']], chart:'MRR growth', bars:[['Enterprise',91],['Growth',72],['Starter',48]], line:[35,44,46,59,63,73,82,96], mix:[['Enterprise',46],['Growth',32],['Starter',15],['Other',7]], periods:[['Jan',48],['Feb',58],['Mar',63],['Apr',72],['May',84],['Jun',94]], summary:'Expansion revenue is outpacing new logo revenue. Churn is trending down across every plan, with Enterprise accounts contributing the strongest retention.' },
  { name:'Marketing', source:'HUBSPOT / SAMPLE CAMPAIGNS', title:'Campaign intelligence', period:'May – Jun', table:'campaigns', metrics:[['Leads','18,420','+26.3% volume'],['Cost per lead','$18.40','-8.6% efficiency'],['Qualified rate','31.8%','+5.2 pts'],['Pipeline','$742K','+21.7% value']], chart:'Qualified leads', bars:[['Search',86],['Content',63],['Social',47]], line:[28,41,38,57,52,74,69,88], mix:[['Search',42],['Content',29],['Social',21],['Other',8]], periods:[['Jan',38],['Feb',52],['Mar',47],['Apr',66],['May',74],['Jun',89]], summary:'Search and content are generating the most qualified demand. Campaign efficiency improved while the pipeline grew by 21.7%.' },
  { name:'Operations', source:'WAREHOUSE / SAMPLE LOGISTICS', title:'Fulfillment control', period:'Week 24', table:'shipments', metrics:[['Orders shipped','8,940','+10.2% throughput'],['On-time rate','96.4%','+2.8 pts'],['Open tickets','128','-34 this week'],['Avg handling','2.4 hr','-0.5 hr faster']], chart:'Fulfillment volume', bars:[['North hub',94],['Central hub',79],['South hub',66]], line:[64,72,68,84,79,91,86,98], mix:[['North hub',44],['Central hub',34],['South hub',16],['Other',6]], periods:[['Jan',71],['Feb',65],['Mar',78],['Apr',83],['May',89],['Jun',96]], summary:'All hubs are above the 95% on-time target except the South hub. Ticket volume is falling as handling time improves across the network.' },
] as const;

function InsightBars({ values }: { values: readonly (readonly [string, number])[] }) {
  return <div className="lp-insight-bars">{values.map(([label, value]) => <div key={label}><span>{label}<b>{value}%</b></span><i style={{ height:`${value}%` }} /></div>)}</div>;
}

function InsightLine({ accent, points, labels }: { accent: string; points: readonly number[]; labels: readonly string[] }) {
  const max = Math.max(...points), min = Math.min(...points), range = Math.max(max - min, 1);
  const coords = points.map((point, index) => `${(index / (points.length - 1)) * 560} ${132 - ((point - min) / range) * 94}`).join(' L');
  return <div className="lp-insight-line" style={{'--chart-accent':accent} as React.CSSProperties}><div className="lp-chart-grid" /><svg viewBox="0 0 560 150" preserveAspectRatio="none" aria-label="Illustrative domain trend"><path d={`M${coords} L560 150 L0 150Z`} fill="currentColor" opacity=".12"/><path d={`M${coords}`} fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/><circle cx={(points.length - 1) / (points.length - 1) * 560} cy={132 - ((points[points.length - 1] - min) / range) * 94} r="5" fill="currentColor"/></svg><div className="lp-mini-axis">{labels.map(label => <span key={label}>{label}</span>)}</div></div>;
}

function InsightDonut({ accent, segments }: { accent: string; segments: readonly (readonly [string, number])[] }) {
  const total = segments.reduce((sum, [, value]) => sum + value, 0);
  let cursor = 0;
  const colors = ['var(--chart-accent)', 'var(--insight-secondary)', 'var(--insight-glow)', '#ffffff66'];
  const stops = segments.map(([, value], index) => { const start = cursor; cursor += (value / total) * 100; return `${colors[index % colors.length]} ${start}% ${cursor}%`; });
  return <div className="lp-insight-donut-wrap"><div className="lp-insight-donut" style={{'--chart-accent':accent, background:`conic-gradient(${stops.join(', ')})`} as React.CSSProperties}><span>100%<small>mix</small></span></div><div className="lp-donut-legend">{segments.map(([label, value], index) => <span key={label}><i style={{opacity:1 - index * .16}} />{label} <b>{value}%</b></span>)}</div></div>;
}

function InsightStackedBars({ accent, periods }: { accent: string; periods: readonly (readonly [string, number])[] }) {
  return <div className="lp-stacked-bars" style={{'--chart-accent':accent} as React.CSSProperties}>{periods.map(([label, value]) => <div key={label}><span><i style={{ height:`${value * .55}%` }}/><i style={{ height:`${value * .3}%` }}/><i style={{ height:`${value * .15}%` }}/></span><small>{label}</small></div>)}</div>;
}

function InsightRanking({ values }: { values: readonly (readonly [string, number])[] }) {
  return <div className="lp-insight-ranking">{values.map(([label, value], index) => <div key={label}><span><b>0{index + 1}</b>{label}</span><i><em style={{ width:`${value}%` }}/></i><strong>{value}%</strong></div>)}</div>;
}

const insightThemes = [
  { accent:'#b7e5f2', secondary:'#7898d9', glow:'#7dd4df' },
  { accent:'#b8e8dc', secondary:'#d2a76d', glow:'#75d2b6' },
  { accent:'#d8c7f5', secondary:'#8fc5b6', glow:'#b99aed' },
  { accent:'#f0d8a4', secondary:'#92bce4', glow:'#e7bd68' },
  { accent:'#f0b8cf', secondary:'#a9d9c9', glow:'#e98eb8' },
  { accent:'#b7d2f2', secondary:'#d5bb8b', glow:'#8eb9ee' },
] as const;

export function DashboardScene({ paused }: { paused: boolean }) {
  const { ref, step, running, replay } = useWalkthrough(paused, 5);
  const reduced = useReducedMotion();
  const [view, setView] = useState<'overview' | 'data'>('overview');
  const [dashboard, setDashboard] = useState(0);
  const [dashboardHover, setDashboardHover] = useState(false);
  const stages = ['Read schema', 'Identify metrics', 'Build charts', 'Write summary', 'Dashboard ready'];
  const active = insightDashboards[dashboard];
  const theme = insightThemes[dashboard];
  useEffect(() => {
    if (paused || reduced || dashboardHover) return;
    const timer = window.setInterval(() => {
      setDashboard(current => (current + 1) % insightDashboards.length);
      setView('overview');
    }, 7000);
    return () => window.clearInterval(timer);
  }, [paused, reduced, dashboardHover]);
  return <div ref={ref} className="lp-dashboard-scene" style={{'--insight-accent':theme.accent,'--insight-secondary':theme.secondary,'--insight-glow':theme.glow} as React.CSSProperties}>
    <div className="lp-scene-toolbar"><span className="lp-demo-label">GUIDED PRODUCT DEMO · SAMPLE DATA</span><button className="lp-button lp-secondary" onClick={replay} disabled={running}><RotateCcw size={14}/>{running ? 'Generating…' : 'Generate sample dashboard'}</button></div>
    <div className="lp-dashboard-domains" aria-label="Sample dashboard domains">{insightDashboards.map((item, index) => <button key={item.name} onClick={() => { setDashboard(index); setView('overview'); }} aria-pressed={dashboard === index}>{item.name}</button>)}</div>
    <div className="lp-pipeline" aria-label="Dashboard generation stages">{stages.map((stage, index) => <span key={stage} className={step >= index ? 'is-done' : ''}>{step >= index ? <Check size={14}/> : <i>{index + 1}</i>}{stage}</span>)}</div>
    <div className="lp-workspace" onMouseEnter={() => setDashboardHover(true)} onMouseLeave={() => setDashboardHover(false)}>
      <div key={dashboard} className="lp-dashboard-body lp-dashboard-slide" aria-busy={running}>
        <div className="lp-dashboard-title"><div><span className="lp-overline">{active.source}</span><h3>{active.title}</h3></div><span className="lp-success"><Check size={13}/> {running ? stages[step] : 'Ready to explore'}</span></div>
        <div className="lp-dashboard-filters"><span><Database size={13}/> {active.table} <ChevronDown size={12}/></span><span>{active.period} <ChevronDown size={12}/></span><div className="lp-segment" aria-label="Dashboard view"><button onClick={() => setView('overview')} aria-pressed={view === 'overview'}>Overview</button><button onClick={() => setView('data')} aria-pressed={view === 'data'}>View data</button></div></div>
        {view === 'overview' ? <>
          <div className={`lp-kpis ${step < 1 ? 'is-pending' : ''}`}>{active.metrics.map(([label,value,note]) => <div key={label}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div>
          <div className={`lp-dashboard-charts ${step < 2 ? 'is-pending' : ''}`}><div className="lp-chart-card lp-chart-wide"><div><strong>{active.chart}</strong><span>{active.period}</span></div><InsightLine accent={theme.accent} points={active.line} labels={active.periods.map(([label]) => label)}/></div><div className="lp-chart-card"><div><strong>{active.name === 'E-commerce' ? 'Payment status' : active.name === 'Healthcare' ? 'Care mix' : active.name === 'Operations' ? 'Hub mix' : 'Channel mix'}</strong><span>Share</span></div><InsightDonut accent={theme.accent} segments={active.mix}/></div><div className="lp-chart-card"><div><strong>{active.name === 'Marketing' ? 'Leads by period' : active.name === 'Operations' ? 'Fulfillment volume' : 'Activity volume'}</strong><span>By period</span></div><InsightStackedBars accent={theme.accent} periods={active.periods}/></div><div className="lp-chart-card"><div><strong>Top performers</strong><span>Ranked</span></div><InsightRanking values={active.bars}/></div></div>
          <div className={`lp-summary ${step < 3 ? 'is-pending' : ''}`}><Sparkles size={19}/><div><strong>Executive summary</strong><p>{active.summary}</p></div></div>
        </> : <div className="lp-data-table"><table><caption>Sample {active.table} used in this preview</caption><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>{active.metrics.map(([label,value])=><tr key={label}><td>{label}</td><td>{value}</td></tr>)}</tbody></table></div>}
        <div className="lp-dashboard-status" role="status">{running ? `Step ${step + 1} of 5: ${stages[step]}` : 'Sample dashboard generated. Connect your data to create your own.'}</div>
      </div>
    </div>
  </div>;
}

const conversations = [
  { name:'Finance', icon:BarChart3, mode:'Database', source:'finance_orders · PostgreSQL', question:'Which month had the strongest revenue, and what changed?', answer:'In this illustrative dataset, June leads with $8,000. Revenue increased from $4,200 in January to $8,000 in June. April was the next strongest month at $6,900.', metric:'$8,000', metricLabel:'Peak monthly revenue', detail:'SELECT month, SUM(revenue) FROM demo_orders GROUP BY month;', values:[42,56,48,69,61,80], tags:['Revenue','Monthly trend','SQL results'] },
  { name:'Banking', icon:Landmark, mode:'Hybrid', source:'banking_transactions + service_guide.pdf', question:'How many transfers settled, and what does our guide say about delays?', answer:'The sample ledger shows 240 settled transfers. The accompanying sample guide says delayed transfers should be reviewed by the operations team after one business day.', metric:'240', metricLabel:'Settled transfers', detail:'Sample service guide · page 3: “Review transfers delayed longer than one business day.”', values:[28,38,44,62,68,81], tags:['Transfers','Policy context','Hybrid'] },
  { name:'Healthcare', icon:HeartPulse, mode:'Documents', source:'clinic_wait_times.csv + intake_notes.pdf', question:'Where are patient waits highest, and what explains them?', answer:'The sample data shows the longest waits in the afternoon clinic. The illustrative intake note links that period to increased walk-in demand. Check the cited passage before making an operational decision.', metric:'42 min', metricLabel:'Peak sample wait', detail:'Sample intake notes · page 2: “Afternoon walk-in arrivals are higher than the morning period.”', values:[25,32,42,36,29,24], tags:['Wait times','Document evidence','Sources'] },
  { name:'Documents', icon:FileText, mode:'Document RAG', source:'returns_policy.pdf', question:'What is the return window for unused items?', answer:'The sample policy allows unused items in their original packaging to be returned within 30 days of purchase. The source passage is available below for review.', metric:'30 days', metricLabel:'Sample return window', detail:'Sample returns policy · page 2: “Unused items in their original packaging may be returned within 30 days of purchase.”', values:[30,30,30,30,30,30], tags:['Policy','Citation','Grounding'] },
];

export function ChatScene({ paused }: { paused: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const conversationRef = useRef<HTMLDivElement>(null);
  const followTail = useRef(true);
  const visible = useInView(ref, { amount: 0.2 });
  const reduced = useReducedMotion();
  const [turns, setTurns] = useState([{ id: 0, scenario: 0 }]);
  const activeTurn = turns[turns.length - 1];
  const selected = activeTurn.scenario;
  const [phase, setPhase] = useState(4);
  const [letters, setLetters] = useState(conversations[0].answer.length);
  const [evidenceId, setEvidenceId] = useState<number | null>(null);
  const [auto, setAuto] = useState(true);
  const [hidden, setHidden] = useState(document.hidden);
  const item = conversations[selected];
  useEffect(() => { const update = () => setHidden(document.hidden); document.addEventListener('visibilitychange', update); return () => document.removeEventListener('visibilitychange', update); }, []);
  useEffect(() => {
    if (!visible || paused || hidden || reduced || !auto) return;
    const timer = window.setInterval(() => {
      setPhase(0);
      setLetters(0);
      setTurns(current => [...current, { id: current[current.length - 1].id + 1, scenario: (current[current.length - 1].scenario + 1) % conversations.length }].slice(-8));
    }, 12000);
    return () => window.clearInterval(timer);
  }, [visible, paused, hidden, reduced, auto]);
  useEffect(() => {
    setEvidenceId(null);
    if (reduced || paused || hidden) { setPhase(4); setLetters(conversations[selected].answer.length); return; }
    setPhase(0); setLetters(0);
    if (!visible) return;
    const timers = [500, 1300, 2200, 2900].map((delay, index) => window.setTimeout(() => setPhase(index + 1), delay));
    return () => timers.forEach(window.clearTimeout);
  }, [activeTurn.id, selected, visible, reduced, paused, hidden]);
  useEffect(() => {
    if (phase < 2 || paused || hidden || reduced || !visible || letters >= item.answer.length) return;
    const timer = window.setTimeout(() => setLetters(value => Math.min(item.answer.length, value + 2)), 22);
    return () => window.clearTimeout(timer);
  }, [phase, paused, hidden, reduced, visible, letters, item.answer.length]);
  useEffect(() => {
    followTail.current = true;
  }, [activeTurn.id]);
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      const conversation = conversationRef.current;
      if (conversation && followTail.current) conversation.scrollTop = conversation.scrollHeight;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [activeTurn.id, phase, letters]);
  const choose = (index: number) => {
    setAuto(false);
    setPhase(0);
    setLetters(0);
    setTurns(current => [...current, { id: current[current.length - 1].id + 1, scenario: index }].slice(-8));
  };
  const transcript = turns.map((turn, index) => {
    const chat = conversations[turn.scenario];
    const current = index === turns.length - 1;
    const stage = current ? phase : 4;
    const answer = current && !reduced ? chat.answer.slice(0, letters) : chat.answer;
    const sourceOpen = evidenceId === turn.id;
    return <div className={current ? 'lp-analyst-turn is-current' : 'lp-analyst-turn is-previous'} key={turn.id}>
      <div className="lp-analyst-question">{chat.question}</div>
      <div className="lp-analyst-response">
        <span className="lp-analyst-avatar"><Sparkles size={19}/></span>
        <div className="lp-analyst-answer">
          <div className="lp-analyst-answer-title"><strong>What the data tells us</strong><span>{chat.mode} synthesis</span></div>
          {stage < 2
            ? <p className="lp-analyst-thinking"><i/> {stage === 0 ? 'Reading the selected source…' : 'Connecting evidence to your question…'}</p>
            : <p>{answer}{current && letters < chat.answer.length && !reduced && <i className="lp-analyst-cursor"/>}</p>}
          {stage >= 3 && <div className="lp-analyst-fact"><span>{chat.metricLabel}</span><strong>{chat.metric}</strong><small>Illustrative result · verify against your own data</small></div>}
          {stage >= 4 && <button className="lp-analyst-source" aria-expanded={sourceOpen} aria-controls={`lp-analyst-evidence-${turn.id}`} onClick={() => setEvidenceId(sourceOpen ? null : turn.id)}><FileText size={14}/>{chat.source}<ChevronDown size={13}/></button>}
          {sourceOpen && <div className="lp-analyst-evidence" id={`lp-analyst-evidence-${turn.id}`}><b>Sample evidence</b><p>{chat.detail}</p></div>}
        </div>
      </div>
    </div>;
  });
  return <div ref={ref} className="lp-analyst-showcase">
    <div className="lp-analyst-tabs" aria-label="Illustrative sample questions">{conversations.map((chat,index)=><button key={chat.name} aria-pressed={selected === index} onClick={() => choose(index)}><chat.icon size={17}/>{chat.name}</button>)}<button className="lp-analyst-auto" aria-pressed={auto} onClick={() => setAuto(!auto)}>{auto ? <Pause size={14}/> : <Play size={14}/>} {auto ? 'Pause tour' : 'Auto tour'}</button></div>
    <div className="lp-analyst-grid">
      <div className="lp-analyst-window">
        <div className="lp-analyst-browser"><span className="lp-analyst-dots"><i/><i/><i/></span><span>dataspeak-cloud / sandbox / analyst</span><span className="lp-analyst-live"><i/> Demo ready</span></div>
        <div className="lp-analyst-header"><span className="lp-analyst-logo"><Sparkles size={20}/></span><div><strong>DataSpeak Analyst</strong><small><Database size={12}/> Connected: {item.source}</small></div><span className="lp-analyst-model">AI demo · sample data</span></div>
        <div className="lp-analyst-subnav"><span className={item.mode === 'Database' ? 'active' : ''}><Database size={14}/> Database</span><span className={item.mode.includes('Document') ? 'active' : ''}><FileText size={14}/> Document RAG</span><span className={item.mode === 'Hybrid' ? 'active' : ''}><Sparkles size={14}/> Hybrid</span></div>
        <div className="lp-analyst-schema"><span><Database size={13}/> Scope:</span>{item.tags.map(tag => <span key={tag}>{tag}</span>)}<b><Check size={13}/> Source selected</b></div>
        <div ref={conversationRef} className="lp-analyst-conversation" aria-label="Illustrative AI chat transcript" onScroll={event => { const view = event.currentTarget; followTail.current = view.scrollHeight - view.scrollTop - view.clientHeight < 60; }}>{transcript}</div>
        <div className="lp-analyst-composer"><div><span><FileText size={15}/> Explore the sample, then connect your data</span><Link to="/signup" aria-label="Sign up to ask your own question"><ArrowRight size={17}/></Link></div><div>{conversations.map((chat,index)=><button key={chat.name} onClick={() => choose(index)}><chat.icon size={14}/>{chat.name} question</button>)}</div></div>
      </div>
      <div className="lp-analyst-intelligence">
        <div className={paused ? "lp-source-orbit is-paused" : "lp-source-orbit"} role="img" aria-label="PostgreSQL, MySQL, documents, MongoDB, SQLite and CSV orbit DataSpeak AI">
          <div className="lp-orbit-halo" aria-hidden="true"/>
          <div className="lp-orbit-ring lp-orbit-ring-outer" aria-hidden="true"/>
          <div className="lp-orbit-ring lp-orbit-ring-inner" aria-hidden="true"/>
          <div className="lp-orbit-stream" aria-hidden="true"><i/><i/></div>
          <div className="lp-orbit-stream lp-orbit-stream-random" aria-hidden="true"><i/><i/><i/></div>
          <div className="lp-orbit-core" aria-hidden="true"><Sparkles size={31}/><strong>DataSpeak<span>AI</span></strong><small>Ask across every source</small></div>
          <div className="lp-orbit-rotor" aria-hidden="true">
            <div className="lp-orbit-node lp-orbit-postgres"><span className="lp-orbit-badge"><img src="/assets/landing/postgresql.svg" alt=""/><b>PostgreSQL</b></span></div>
            <div className="lp-orbit-node lp-orbit-mysql"><span className="lp-orbit-badge"><img src="/assets/landing/mysql.svg" alt=""/><b>MySQL</b></span></div>
            <div className="lp-orbit-node lp-orbit-documents"><span className="lp-orbit-badge"><FileText size={30}/><b>Documents</b></span></div>
            <div className="lp-orbit-node lp-orbit-mongo"><span className="lp-orbit-badge"><img src="/assets/landing/mongodb.svg" alt=""/><b>MongoDB</b></span></div>
            <div className="lp-orbit-node lp-orbit-csv"><span className="lp-orbit-badge"><FileSpreadsheet size={30}/><b>CSV & Excel</b></span></div>
            <div className="lp-orbit-node lp-orbit-sqlite"><span className="lp-orbit-badge"><img src="/assets/landing/sqlite.svg" alt=""/><b>SQLite</b></span></div>
          </div>
        </div>
        <div className="lp-orbit-copy"><span className="lp-overline">CONNECTED INTELLIGENCE · ILLUSTRATIVE</span><h3>Every source.<br/><span>One conversation.</span></h3><p>Ask naturally. DataSpeakAI brings the right database rows and document passages into a grounded answer.</p></div>
      </div>
    </div>
    <p className="lp-analyst-disclaimer">Guided examples use fictional sample data. Your own workspace generates answers from sources you connect and permit.</p>
  </div>;
}

export function WidgetScene({ paused }: { paused: boolean }) {
  const [brand, setBrand] = useState(0);
  const [installed, setInstalled] = useState(true);
  const [open, setOpen] = useState(true);
  const [turns, setTurns] = useState([0]);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  const brands = [{ name:'Atlas', subtitle:'Spaces to do your best work.', title:'Atlas assistant', color:'#4147a8', tint:'#ededff' },{ name:'Forma', subtitle:'Everyday objects. Considered design.', title:'Forma assistant', color:'#286859', tint:'#e4f0e8' },{ name:'Orbit', subtitle:'The next chapter starts here.', title:'Orbit assistant', color:'#9c4526', tint:'#f9ece4' }];
  const supportTurns = [
    { question:'What is your returns policy?', answer:'Unused items can be returned within 30 days, in their original packaging.', source:'Returns policy · page 2' },
    { question:'How long does delivery take?', answer:'Standard delivery usually arrives within 3–5 business days. You can check tracking from your order email.', source:'Delivery guide · page 1' },
    { question:'Which payment methods do you accept?', answer:'You can pay with major credit cards, debit cards and supported digital wallets at checkout.', source:'Payment help · page 1' },
    { question:'How can I reset my password?', answer:'Choose “Forgot password” on the sign-in screen and follow the secure reset link sent to your email.', source:'Account help · page 1' },
    { question:'How do I contact your support team?', answer:'Send us a message through the help center and our team will reply during support hours.', source:'Contact support · page 1' },
    { question:'How is my personal data protected?', answer:'Your account data is protected with secure access controls and is used only to provide the requested service.', source:'Privacy overview · page 2' },
  ];
  const current = brands[brand];
  useEffect(() => {
    if (paused) return;
    const timer = window.setInterval(() => setBrand(value => (value + 1) % brands.length), 4200);
    return () => window.clearInterval(timer);
  }, [paused, brands.length]);
  useEffect(() => {
    if (paused || !open) return;
    const timer = window.setInterval(() => {
      setTurns(currentTurns => {
        const next = (currentTurns[currentTurns.length - 1] + 1) % supportTurns.length;
        return next === 0 ? [0] : [...currentTurns, next];
      });
    }, 4600);
    return () => window.clearInterval(timer);
  }, [paused, open, supportTurns.length]);
  useEffect(() => {
    const messages = messagesRef.current;
    if (messages) messages.scrollTo({ top: messages.scrollHeight, behavior: paused ? 'auto' : 'smooth' });
  }, [turns, paused]);
  async function copy() {
    try { await navigator.clipboard.writeText('<script src="YOUR_DATASPEAK_HOST/widget.js" data-key="YOUR_PUBLISHABLE_KEY"></script>'); setCopied(true);setCopyError(false); }
    catch { setCopyError(true); }
  }
  return <div className="lp-widget-demo" style={{'--widget-brand':current.color,'--widget-tint':current.tint} as React.CSSProperties}>
    <div className="lp-widget-controls"><span className="lp-overline">01 / MAKE IT YOURS</span><div aria-label="Sample website brand">{brands.map((b,index)=><button key={b.name} aria-pressed={brand === index} onClick={()=>{setBrand(index);setTurns([0]);}}>{b.name}</button>)}</div><button className="lp-button" onClick={()=>{setInstalled(!installed);setOpen(true);}}><Code2 size={16}/>{installed ? 'Edit widget design' : 'Preview on website'}<ArrowRight size={16}/></button></div>
    <div className={`lp-website ${installed ? 'is-installed' : ''}`}><div className="lp-browser-bar"><i/><i/><i/><span><Globe2 size={12}/> {current.name.toLowerCase()}.example</span><span>Website preview</span></div><div className="lp-website-nav"><b>{current.name}<span>®</span></b><span>Discover &nbsp; About &nbsp; Journal</span><span>Explore ↗</span></div><div className="lp-website-body"><span className="lp-overline">DESIGNED AROUND YOU</span><h3>{current.subtitle}</h3><div className="lp-website-art" aria-hidden="true"><i/><i/><i/></div><div className="lp-website-bottom"><span>Thoughtfully made.<br/>Ready for what’s next.</span><span>01 — 03</span></div></div>
    <div className={`lp-widget-float ${installed ? 'installed' : ''} ${!open ? 'is-closed' : ''}`}><div className="lp-widget-head"><span><Sparkles size={18}/><b>{current.title}</b></span><button aria-label="Close sample widget" onClick={()=>setOpen(false)}><X size={17}/></button></div><div ref={messagesRef} className="lp-widget-messages" aria-live="polite"><span className="lp-demo-label">ILLUSTRATIVE EMBED PREVIEW</span><p>Hi! I can help you explore our knowledge base. What would you like to know?</p>{turns.map((turn, index) => { const message = supportTurns[turn]; return <motion.div className="lp-widget-turn" key={`${turn}-${index}`} initial={{opacity:paused?1:0,y:paused?0:8}} animate={{opacity:1,y:0}}><button onClick={() => setTurns(currentTurns => [...currentTurns, turn].slice(-6))}>{message.question} <ArrowUpRight size={13}/></button><p>{message.answer}</p><small><FileText size={12}/> {message.source}</small></motion.div>; })}</div><div className="lp-widget-credit">Powered by DataSpeakAI</div></div>
    <button className="lp-widget-launcher" onClick={()=>setOpen(!open)} aria-label={open?'Minimize sample widget':'Open sample widget'} aria-expanded={open}><MessageSquareCode size={24}/></button></div>
    <div className="lp-embed-footer"><span><ShieldCheck size={17}/> Your brand. Your sources. Approved website origins.</span><button onClick={copy}>{copied ? <Check size={15}/> : <Code2 size={15}/>}{copied ? 'Template copied' : 'Copy embed template'}</button></div>{copyError && <p role="alert" className="lp-error">Clipboard access is unavailable. Your dashboard provides the embed code after setup.</p>}<p className="lp-fineprint">The template uses placeholders. Get your actual host, publishable key and allowed origins from widget setup.</p>
  </div>;
}
