import { Link, useNavigate } from 'react-router';
import { useEffect, useRef, useState } from 'react';
import { motion, MotionConfig, useReducedMotion, useScroll, useTransform } from 'motion/react';
import { ArrowDown, ArrowRight, ArrowUpRight, Check, ChevronDown, Database, FileText, Globe2, Menu, MessageSquareCode, Pause, Play, ShieldCheck, Sparkles, X } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE_URL } from '../config/api';
import { ChatScene, RevenueChart, WidgetScene } from '../components/landing/ProductScenes';
import { IntegrationCards } from '../components/landing/IntegrationCards';
import './LandingPage.css';

const faqs = [
  ['What can I connect?', 'Connect PostgreSQL, MySQL, SQLite, MongoDB or Firebase, and upload CSV/Excel datasets or documents. Analysis capabilities depend on the selected source.'],
  ['Does DataSpeakAI generate a whole dashboard?', 'Business Insights analyzes a selected database and table scope to produce available KPIs, charts, comparisons and summaries. Missing metrics are marked unavailable rather than invented. The walkthrough above uses sample data.'],
  ['How is the chatbot different from a general AI chat?', 'DataSpeakAI answers using selected database and document context. SQL mode queries supported data sources, RAG searches documents, and Hybrid brings both together. You can inspect results and supporting sources.'],
  ['Can I use it on my own website?', 'Yes. Configure your widget title, greeting, color and selected sources, then embed it using the script and publishable key from your dashboard. Approved website origins and verified visitor sessions control access.'],
  ['Can I verify the AI’s answers?', 'Review the underlying data, generated queries and document citations where available. Grounding information helps you inspect evidence; important decisions still need your review.'],
];

function Hero({ paused }: { paused: boolean }) {
  const ref = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end start'] });
  const y = useTransform(scrollYProgress, [0, 1], [0, 140]);
  const rotate = useTransform(scrollYProgress, [0, .7], [-13, 0]);
  const scale = useTransform(scrollYProgress, [0, .7], [1, 1.12]);
  const disabled = paused || reduced;
  return <section ref={ref} className="lp-hero">
    <div className="lp-hero-atmosphere" aria-hidden="true"><div /><div /><div /></div>
    <div className="lp-hero-copy"><span className="lp-overline"><span className="lp-dot" /> INTELLIGENCE, IN YOUR ELEMENT.</span><h1>Your data.<br /><span>Beyond limits.</span></h1><p>Ask bigger questions. See the whole picture.<br />One AI workspace for your databases, documents<br className="lp-desktop" /> and every decision that comes next.</p><div className="lp-actions"><Link className="lp-button" to="/signup">Get started <ArrowUpRight size={18} /></Link><a className="lp-text-link" href="#insights">Explore the experience <ArrowDown size={17} /></a></div></div>
    <motion.div className="lp-hero-art" style={{ y: disabled ? 0 : y }}>
      <div className="lp-metal-ring" aria-hidden="true" /><div className="lp-orbit-path" aria-hidden="true" />
      <motion.div className="lp-hero-card lp-hero-card-main" style={{ rotate: disabled ? -6 : rotate, scale: disabled ? 1 : scale }}><div><span><Sparkles size={17} /> DataSpeakAI</span><span className="lp-overline">INSIGHTS</span></div><small>Clarity. On demand.</small><strong>$35,600</strong><span className="lp-hero-card-sub">Revenue · illustrative dataset</span><RevenueChart compact /><div className="lp-hero-card-bottom"><span>240 orders</span><span>6 months of possibilities ↗</span></div></motion.div>
      <div className="lp-hero-card lp-hero-chat"><div><Sparkles size={16} /><b>Ask your data.</b></div><p>What’s driving our revenue?</p><span><Check size={13} /> Context connected. Ready to explore.</span></div>
      <div className="lp-hero-source"><Database /><span>DATABASES<br /><b>Connected to possibility.</b></span></div>
    </motion.div>
    <div className="lp-hero-bottom"><span>DATABASES. DOCUMENTS. ONE CONVERSATION.</span><a href="#sources" aria-label="Explore data connections"><ArrowDown size={20} /></a><span>SCROLL TO DISCOVER</span></div>
  </section>;
}

export function LandingPage() {
  const navigate = useNavigate();
  const reduced = useReducedMotion();
  const [paused, setPaused] = useState(false);
  const [menu, setMenu] = useState(false);
  const [hasScrolled, setHasScrolled] = useState(false);
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const exchangeStarted = useRef(false);
  const stopMotion = paused || !!reduced;
  useEffect(() => {
    const updateHeader = () => setHasScrolled(window.scrollY > 8);
    updateHeader();
    window.addEventListener('scroll', updateHeader, { passive: true });
    return () => window.removeEventListener('scroll', updateHeader);
  }, []);
  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get('code');
    if (!code || exchangeStarted.current) return;
    exchangeStarted.current = true;
    const exchange = async () => {
      setIsLoggingIn(true);
      try {
        const response = await fetch(`${API_BASE_URL}/api/auth/github-login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code }) });
        if (!response.ok) throw new Error('Login failed');
        const data = await response.json();
        if (!data.access_token) throw new Error('Missing token');
        localStorage.setItem('token', data.access_token);
        window.history.replaceState({}, document.title, window.location.pathname);
        navigate('/dashboard');
      } catch { toast.error('GitHub sign-in could not be completed. Please try again.'); }
      finally { setIsLoggingIn(false); }
    };
    void exchange();
  }, [navigate]);
  useEffect(() => {
    if (!menu) return;
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') { setMenu(false); document.getElementById('landing-menu-toggle')?.focus(); } };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [menu]);
  return <MotionConfig reducedMotion={stopMotion ? 'always' : 'user'}><div className="ds-landing" data-paused={stopMotion}>
    <a className="lp-skip" href="#main">Skip to content</a>
    {isLoggingIn && <div className="lp-login-overlay" role="status"><Sparkles /> Completing secure login…</div>}
    <header className={`lp-nav${hasScrolled ? ' is-scrolled' : ''}`}><Link to="/" className="lp-brand" aria-label="DataSpeakAI home"><MessageSquareCode /><span>DataSpeak<span>AI</span></span></Link><nav id="landing-navigation" className={menu ? 'is-open' : ''} aria-label="Main navigation">{[['Platform', 'sources'], ['AI insights', 'insights'], ['AI chat', 'demo'], ['For your website', 'widget']].map(([label, id]) => <a key={id} href={`#${id}`} onClick={() => setMenu(false)}>{label}</a>)}</nav><div className="lp-nav-actions"><Link to="/login">Log in</Link><Link to="/signup" className="lp-button lp-small">Sign up <ArrowUpRight size={14} /></Link><button id="landing-menu-toggle" className="lp-menu" aria-expanded={menu} aria-controls="landing-navigation" aria-label={menu ? 'Close navigation' : 'Open navigation'} onClick={() => setMenu(!menu)}>{menu ? <X /> : <Menu />}</button></div></header>
    <button className="lp-motion-toggle" aria-pressed={paused} onClick={() => setPaused(!paused)} aria-label={paused ? 'Resume animations' : 'Pause animations'} disabled={!!reduced}>{stopMotion ? <Play size={14} /> : <Pause size={14} />}<span>{reduced ? 'Reduced motion' : paused ? 'Resume motion' : 'Pause motion'}</span></button>
    <main id="main"><Hero paused={stopMotion} />
<section id="sources" className="lp-section lp-connections"><div className="lp-section-heading"><span className="lp-overline">ALL YOUR SOURCES. ALL YOUR POSSIBILITIES.</span><h2>Everything connects.<br /><span>Then everything clicks.</span></h2><p>From your first spreadsheet to your business database.<br />Bring the knowledge. We’ll help you find the answers.</p></div><IntegrationCards paused={stopMotion} /></section>
      <section id="insights" className="lp-section lp-insights"><div className="lp-section-heading"><span className="lp-overline">FROM CONNECTED DATA TO A COMPLETE PICTURE</span><h2>The dashboard.<br /><span>Already thought through.</span></h2><p>Your KPIs. Your trends. Your next question.<br />Explore the approved Business Insights dashboard.</p></div><iframe className="lp-approved-dashboard" title="DataSpeakAI approved five-domain dashboard" src="/dashboards-5-domains.html" loading="lazy" /></section>
      <section id="demo" className="lp-section lp-chat-section"><div className="lp-section-heading"><span className="lp-overline">MEET YOUR DATA’S BETTER HALF</span><h2>A conversation.<br /><span>A world of answers.</span></h2><p>Your chatbot already knows where to look.<br />Explore database answers, document evidence and hybrid context.</p></div><ChatScene paused={stopMotion} /><Link className="lp-button" to="/signup">Start your own conversation <ArrowUpRight size={17} /></Link></section>
      <section id="widget" className="lp-section lp-widget-section"><div className="lp-section-heading"><span className="lp-overline">BUILT BY YOU. POWERED BY YOUR KNOWLEDGE.</span><h2>Your website.<br /><span>Now with answers.</span></h2><p>Make the assistant look at home. Give it your sources.<br />Take your AI from the workspace to your website.</p></div><WidgetScene paused={stopMotion} /></section>
      <section id="security" className="lp-section lp-security"><div className="lp-security-art" aria-hidden="true"><div /><div /><ShieldCheck size={120} strokeWidth={.8} /><span>YOUR DATA, IN YOUR CONTROL</span></div><div><span className="lp-overline">OPEN POSSIBILITIES. DEFINED BOUNDARIES.</span><h2>Curiosity.<br /><span>With confidence.</span></h2><p>Keep conversations within your organization’s data access. Control roles, database permissions and the sources your website visitors can reach.</p><ul><li><Check size={17} /> Tenant-scoped data access</li><li><Check size={17} /> Safe database query controls</li><li><Check size={17} /> Origin-checked widget sessions</li></ul><a href="#faq" className="lp-text-link">Get to know the details <ArrowRight size={16} /></a></div></section>
      <section className="lp-section lp-start"><span className="lp-overline">THREE STEPS. ONE BIG LEAP.</span><h2>Make your next move.</h2><div>{[['01', 'Connect.', 'Add a database, dataset or document.'], ['02', 'Explore.', 'Ask a question. Generate insights. Follow the evidence.'], ['03', 'Share.', 'Bring your team in, or put your assistant on your website.']].map(([n, t, p]) => <article key={n}><span>{n}</span><h3>{t}</h3><p>{p}</p></article>)}</div></section>
      <section id="faq" className="lp-section lp-faq"><div><span className="lp-overline">A LITTLE MORE CLARITY</span><h2>Good questions.</h2></div><div>{faqs.map(([q, a]) => <details key={q}><summary>{q}<ChevronDown size={18} /></summary><p>{a}</p></details>)}</div></section>
      <section className="lp-final"><div className="lp-final-orb" aria-hidden="true" /><span className="lp-overline">THE POSSIBILITIES ARE IN YOUR DATA</span><h2>Let’s find<br /><span>what’s next.</span></h2><Link to="/signup" className="lp-button">Get started with DataSpeakAI <ArrowUpRight size={18} /></Link></section>
    </main><footer className="lp-footer"><div><Link className="lp-brand" to="/"><MessageSquareCode />DataSpeakAI</Link><p>A whole new conversation with your business.</p></div><nav aria-label="Footer"><a href="#sources">Connections</a><a href="#insights">Insights</a><a href="#demo">AI Chat</a><a href="#widget">Widget</a><a href="#faq">FAQs</a></nav><div className="lp-footer-bottom"><span>© {new Date().getFullYear()} DataSpeakAI</span><span><Globe2 size={14} /> Built for curious minds.</span></div></footer>
  </div></MotionConfig>;
}
