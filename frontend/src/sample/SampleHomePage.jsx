import React from 'react';
import {
  Bot,
  Check,
  ChevronRight,
  Gavel,
  Gift,
  Home,
  Landmark,
  LockKeyhole,
  MoreHorizontal,
  Paperclip,
  Scale,
  ShieldCheck,
  ShoppingCart,
  Sparkles
} from 'lucide-react';

import { AutoGrowTextarea } from '../AutoGrowTextarea.jsx';
import './sample-home.css';

/*
 * SAMPLE HOME PAGE -- template sandbox, route: #/sample-home
 *
 * A full, independent copy of the Home page. Restyle or restructure anything in this
 * file and in ./sample-home.css freely: none of it is used by the real Home page
 * (HomePage in ../App.jsx), and every CSS class here is prefixed `sh-` so it cannot
 * collide with the live styles.
 *
 * What is deliberately shared with the real app (passed in as `shared` from App.jsx to
 * avoid a circular import): the chat hook and the answer-rendering components, the top
 * header controls, and the watermark illustration. The sidebar, colours and fonts
 * (:root variables) also come from the live app shell.
 */

// ---- Content (copy of the live Home data -- edit here to test different copy) ----------

const categories = [
  { label: 'Consumer Issues', icon: ShoppingCart, rightsCategory: 'consumer' },
  { label: 'Tenant Disputes', icon: Home, rightsCategory: 'tenancy' },
  { label: 'Cyber Issues', icon: LockKeyhole, rightsCategory: 'cyber' },
  { label: 'Fundamental Rights', icon: ShieldCheck, rightsCategory: 'fundamental_rights' },
  { label: 'Other Legal Help', icon: MoreHorizontal, rightsCategory: 'public_services' }
];

const features = [
  {
    title: 'Know Your Rights',
    description: 'Understand your legal rights in simple words.',
    button: 'Explore Now',
    icon: Scale,
    href: '#/rights'
  },
  {
    title: 'Draft Complaints',
    description: 'Create a ready-to-file complaint from a fixed legal template.',
    button: 'Create Now',
    icon: Gavel,
    href: '#/complaints'
  },
  {
    title: 'Follow Procedure',
    description: 'Step-by-step guidance on what to do and where to go.',
    button: 'Learn More',
    icon: Landmark,
    href: '#/ask'
  },
  {
    title: 'Government Schemes',
    description: 'Find schemes and benefits you may be eligible for.',
    button: 'View Schemes',
    icon: Gift,
    href: '#/schemes'
  }
];

const homeSections = [
  {
    id: 'documents',
    kicker: '01',
    label: 'Documents',
    href: '#/documents',
    cta: 'Open Documents',
    summary: 'Upload a legal document and let Legal Aid AI read it for you. It pulls out the facts that matter so you can use them in a question.',
    points: [
      'Upload a PDF, DOCX or TXT file (up to 10 MB)',
      'Extract the text, then the key facts — parties, dates, amounts, notices',
      'Review and confirm the facts, then ask a question that uses them'
    ]
  },
  {
    id: 'summarize',
    kicker: '02',
    label: 'Summarize Document',
    href: '#/summarize-document',
    cta: 'Summarize a document',
    summary: 'A long notice or contract you do not follow? Get a short, plain-language summary of what it says and what it means for you.',
    points: [
      'Pick a document you already uploaded, or add a new one',
      'Get a clear summary written in everyday words',
      'Open the original document alongside the summary'
    ]
  },
  {
    id: 'cases',
    kicker: '03',
    label: 'My Cases',
    href: '#/cases',
    cta: 'View my cases',
    summary: 'Every conversation you have is saved as a case, so you never lose your place. Come back later, rename it, or clear it out.',
    points: [
      'Each question thread is saved automatically',
      'Reopen a case and carry on where you left off',
      'Rename or delete a case, or clear them all'
    ]
  },
  {
    id: 'rights',
    kicker: '04',
    label: 'Know Your Rights',
    href: '#/rights',
    cta: 'Explore rights',
    summary: 'Browse your rights by topic — consumer, cyber, tenancy, public services — with the real laws behind them explained in plain words.',
    points: [
      'Common issues and what usually applies',
      'The actual sections and Acts, with plain-language notes',
      'Clear next steps and where to go'
    ],
    topics: ['Defective product', 'Refund & replacement', 'Online fraud', 'Identity misuse', 'Rent & services', 'RTI application']
  },
  {
    id: 'schemes',
    kicker: '05',
    label: 'Schemes',
    href: '#/schemes',
    cta: 'See schemes',
    summary: 'Government help you may be entitled to — free legal aid, national helplines, and portals to file a complaint without a lawyer.',
    points: [
      'Free Legal Aid (NALSA) if you qualify',
      'Consumer (1915) and Cyber Crime (1930) helplines',
      'Tele-Law advice and online case filing (e-Daakhil)'
    ]
  },
  {
    id: 'complaints',
    kicker: '06',
    label: 'Draft Complaint',
    href: '#/complaints',
    cta: 'Draft a complaint',
    summary: 'Answer a few questions and get a ready-to-file complaint document, filled from a fixed legal template — not written by AI.',
    points: [
      'Tenancy eviction petitions, or consumer complaints for defective goods and misleading ads',
      'Every citation is checked against the actual Act or CCPA guideline before it is used',
      'Download the finished complaint as a DOCX or PDF'
    ]
  }
];

// ---- Sections ---------------------------------------------------------------------------

function SampleHero() {
  return (
    <section className="sh-hero">
      <p className="sh-hero-kicker">Welcome to</p>
      <h2><span className="sh-hero-title-inner">Legal Aid AI</span></h2>
      <p className="sh-hero-subtitle">
        Understand your rights, draft complaints, and know what to do next — explained in plain language.
      </p>
    </section>
  );
}

function SampleQueryBox({ chat }) {
  const hasConversation = chat.messages.length > 0;

  const handleAttachClick = () => {
    const params = new URLSearchParams({ attach: '1' });
    if (chat.caseId) params.set('case', chat.caseId);
    const query = chat.input.trim();
    if (query) params.set('q', query);
    window.location.hash = `#/ask?${params.toString()}`;
  };

  return (
    <form className="sh-query-box" onSubmit={chat.handleSubmit}>
      <div className="sh-query-icon">
        <Sparkles size={20} />
      </div>
      <AutoGrowTextarea
        name="legal-query"
        value={chat.input}
        onChange={(event) => chat.setInput(event.target.value)}
        submitOnEnter
        placeholder={hasConversation ? 'Ask a follow-up question...' : 'Describe your legal issue in simple words...'}
        aria-label="Describe your legal issue"
      />
      <button className="sh-attach-button" type="button" aria-label="Attach document" onClick={handleAttachClick}>
        <Paperclip size={20} />
      </button>
      <button className="sh-ask-button sh-query-submit" type="submit" disabled={chat.isLoading}>
        <Sparkles size={15} />
        <span>Ask AI</span>
      </button>
    </form>
  );
}

function SampleAnswerPanel({ chat, shared }) {
  const { PanelCorners, UserMessage, LoadingMessage, LegalAIResponse } = shared;
  const panelRef = React.useRef(null);
  const messageCount = chat.messages.length;

  React.useEffect(() => {
    if (!messageCount) return;
    panelRef.current?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [messageCount, chat.isLoading]);

  if (!messageCount) return null;

  const continueHref = chat.caseId ? `#/ask?case=${encodeURIComponent(chat.caseId)}` : '#/ask';

  return (
    <section className="chat-panel sh-home-answer-panel" aria-label="Legal AI answer">
      <PanelCorners />
      <div className="chat-panel-toolbar">
        <div>
          <span>◇</span>
          <p>{chat.category ? `Your question · ${chat.category}` : 'Your question'}</p>
        </div>
        <div className="sh-home-answer-actions">
          <button
            type="button"
            className="outline-action"
            disabled={chat.isLoading || !chat.caseId}
            title={chat.caseId ? 'Open this conversation on the Ask Question page' : 'Available once the answer has arrived'}
            onClick={() => { window.location.hash = continueHref; }}
          >
            Open in Ask Question
          </button>
          <button type="button" className="outline-action" onClick={chat.handleClear}>New Question</button>
        </div>
      </div>
      <div className="sh-home-answer-messages" ref={panelRef}>
        {chat.messages.map((message) => (
          message.role === 'user'
            ? <UserMessage text={message.text} key={message.id} />
            : message.role === 'assistant_loading'
              ? <LoadingMessage key={message.id} />
              : <LegalAIResponse response={message.response} onSourceClick={chat.setSelectedSource} key={message.id} />
        ))}
      </div>
    </section>
  );
}

function SampleCategoryPills() {
  return (
    <section className="sh-home-section" aria-label="Legal categories">
      <h3 className="sh-home-section-title">Browse by topic</h3>
      <div className="sh-category-pills">
        {categories.map(({ label, icon: Icon, rightsCategory }) => (
          <button
            type="button"
            className="sh-category-pill"
            key={label}
            onClick={() => { window.location.hash = `#/rights/${rightsCategory}`; }}
          >
            <Icon size={17} strokeWidth={1.65} />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function SampleFeatureCard({ title, description, button, icon: Icon, href }) {
  return (
    <article className="sh-feature-card">
      <div className="sh-feature-icon">
        <Icon size={22} strokeWidth={1.6} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      <a
        className="sh-feature-link"
        href={href}
        onClick={(event) => { event.preventDefault(); window.location.hash = href; }}
      >
        {button}
        <ChevronRight size={15} strokeWidth={2} />
      </a>
    </article>
  );
}

function SampleFeatureCards() {
  return (
    <section className="sh-home-section sh-features-section" aria-label="Homepage feature cards">
      <h3 className="sh-home-section-title">How Legal Aid AI helps</h3>
      <div className="sh-features">
        {features.map((feature) => (
          <SampleFeatureCard {...feature} key={feature.title} />
        ))}
      </div>
    </section>
  );
}

function SampleRevealSection({ className = '', id, children }) {
  const ref = React.useRef(null);
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    if (typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setVisible(true);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -6% 0px' }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <section ref={ref} id={id} className={`sh-reveal ${visible ? 'sh-is-visible' : ''} ${className}`.trim()}>
      {children}
    </section>
  );
}

function jumpToSection(id) {
  const el = typeof document !== 'undefined' ? document.getElementById(id) : null;
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function SampleInfoSections() {
  return (
    <div className="sh-home-info">
      <SampleRevealSection className="sh-home-lead">
        <h3 className="sh-home-section-title">What you can do here</h3>
        <div className="sh-home-jump">
          {homeSections.map((section) => (
            <button
              type="button"
              key={section.id}
              className="sh-home-jump-link"
              onClick={() => jumpToSection(`sh-sec-${section.id}`)}
            >
              {section.label}
            </button>
          ))}
        </div>
      </SampleRevealSection>

      <div className="sh-home-feature-list">
        {homeSections.map((section) => (
          <SampleRevealSection id={`sh-sec-${section.id}`} className="sh-home-feature" key={section.id}>
            <div className="sh-home-feature-text">
              <span className="sh-home-feature-kicker">{section.kicker}</span>
              <h3>{section.label}</h3>
              <p>{section.summary}</p>
              <a className="sh-home-cta" href={section.href}>
                <span>{section.cta}</span>
                <ChevronRight size={16} strokeWidth={2} />
              </a>
            </div>
            <div className="sh-home-feature-panel">
              <ul>
                {section.points.map((point) => (
                  <li key={point}>
                    <Check size={15} strokeWidth={2.6} />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
              {section.topics && (
                <div className="sh-home-feature-topics">
                  {section.topics.map((topic) => (
                    <span key={topic}>{topic}</span>
                  ))}
                </div>
              )}
            </div>
          </SampleRevealSection>
        ))}
      </div>

      <div className="sh-home-marquee" aria-hidden="true">
        <div className="sh-home-marquee-track">
          {[0, 1].map((copy) => (
            <span key={copy}>
              Consumer rights <i>◆</i> Tenancy <i>◆</i> Cyber fraud <i>◆</i> Consumer courts
              <i>◆</i> RTI <i>◆</i> Free legal aid <i>◆</i> Know your rights <i>◆</i>
            </span>
          ))}
        </div>
      </div>

      <SampleRevealSection className="sh-home-steps-section">
        <h3 className="sh-home-section-title">How it works</h3>
        <ol className="sh-home-steps">
          <li><span>1</span>Describe the problem in your own words.</li>
          <li><span>2</span>We search official legal sources and government material.</li>
          <li><span>3</span>You get a short answer, next steps, and where to go.</li>
        </ol>
      </SampleRevealSection>

      <SampleRevealSection className="sh-home-assure">
        <div className="sh-home-assure-card">
          <span className="sh-home-assure-icon"><LockKeyhole size={24} strokeWidth={1.6} /></span>
          <h4>Why your privacy matters</h4>
          <p>
            Legal problems are personal. What you type here is used only to answer your
            question — it is never sold, shared, or used to build a profile of you.
          </p>
          <ul>
            <li>Your questions and uploads stay tied to your session.</li>
            <li>Documents are read to help you, not kept for anyone else.</li>
            <li>You can delete a saved case any time from My Cases.</li>
          </ul>
        </div>
        <div className="sh-home-assure-card">
          <span className="sh-home-assure-icon"><Bot size={24} strokeWidth={1.6} /></span>
          <h4>Need help?</h4>
          <p>
            This tool gives legal information, not a lawyer&rsquo;s advice. For your specific
            situation you can talk to a real advisor — many services are free.
          </p>
          <ul>
            <li>Free Legal Aid (NALSA) if you qualify.</li>
            <li>Tele-Law advice through Common Service Centres.</li>
            <li>State Legal Services Authority for mediation and Lok Adalats.</li>
          </ul>
          <a className="sh-home-assure-cta" href="#/schemes">See all schemes <ChevronRight size={14} strokeWidth={2} /></a>
        </div>
      </SampleRevealSection>
    </div>
  );
}

function SampleFooter() {
  return (
    <footer className="sh-home-footer">
      <div className="sh-home-footer-inner">
        <div className="sh-home-footer-brand">
          <div className="sh-home-footer-mark"><Scale size={22} strokeWidth={1.5} /></div>
          <div>
            <strong>Legal Aid AI</strong>
            <span>Your Rights. Our Guidance.</span>
          </div>
        </div>
        <p className="sh-home-footer-about">
          A free tool that explains your legal rights in simple words, helps you prepare
          complaints, and points you to the right authority. It gives legal information,
          not professional legal advice.
        </p>
        <nav className="sh-home-footer-links" aria-label="Footer">
          <a href="#/ask">Ask a Question</a>
          <a href="#/rights">Know Your Rights</a>
          <a href="#/schemes">Schemes</a>
          <a href="#/about">About Us</a>
        </nav>
      </div>
    </footer>
  );
}

// ---- Motion helpers ---------------------------------------------------------------------

function useSampleParallax(speed = 0.12) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return undefined;
    }
    let raf = 0;
    const update = () => {
      raf = 0;
      const rect = el.getBoundingClientRect();
      const mid = rect.top + rect.height / 2 - window.innerHeight / 2;
      el.style.transform = `translate3d(0, ${(mid * -speed).toFixed(1)}px, 0)`;
    };
    const onScroll = () => {
      if (!raf) raf = window.requestAnimationFrame(update);
    };
    update();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      if (raf) window.cancelAnimationFrame(raf);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, [speed]);
  return ref;
}

function SampleBackgroundArt({ VintageScales }) {
  const parallaxRef = useSampleParallax(0.1);
  return (
    <div className="sh-background-art sh-home-background-art" aria-hidden="true">
      <span className="sh-home-bg-parallax" ref={parallaxRef}>
        <VintageScales className="sh-watermark sh-sketch sh-scale-mark" />
      </span>
    </div>
  );
}

function SampleCursor() {
  const dotRef = React.useRef(null);
  const ringRef = React.useRef(null);

  React.useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined;
    const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (!fine) return undefined;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const dot = dotRef.current;
    const ring = ringRef.current;
    const body = document.body;
    body.classList.add('sh-has-custom-cursor');

    let mx = window.innerWidth / 2;
    let my = window.innerHeight / 2;
    let rx = mx;
    let ry = my;
    let raf = 0;

    const place = (el, x, y) => {
      if (el) el.style.transform = `translate(-50%, -50%) translate3d(${x}px, ${y}px, 0)`;
    };

    const onMove = (event) => {
      mx = event.clientX;
      my = event.clientY;
      place(dot, mx, my);
      if (reduced) place(ring, mx, my);
      body.classList.remove('sh-cursor-hidden');
    };
    const onOut = (event) => {
      if (!event.relatedTarget && !event.toElement) body.classList.add('sh-cursor-hidden');
    };
    const onDown = () => body.classList.add('sh-cursor-down');
    const onUp = () => body.classList.remove('sh-cursor-down');

    const interactiveSel =
      'a, button, input, textarea, select, [role="button"], .sh-feature-card, .sh-category-pill, .sh-home-feature-panel, .sh-home-jump-link, .sh-home-cta, .source-card, .rights-source-card';
    const onOver = (event) => {
      const t = event.target;
      if (t && t.closest && t.closest(interactiveSel)) body.classList.add('sh-cursor-active');
    };
    const onLeaveInteractive = (event) => {
      const t = event.target;
      if (t && t.closest && t.closest(interactiveSel)) body.classList.remove('sh-cursor-active');
    };

    const tick = () => {
      rx += (mx - rx) * 0.16;
      ry += (my - ry) * 0.16;
      place(ring, rx, ry);
      raf = window.requestAnimationFrame(tick);
    };
    if (!reduced) raf = window.requestAnimationFrame(tick);
    place(dot, mx, my);
    place(ring, mx, my);

    // Magnetic pull on primary buttons
    const magnets = Array.from(document.querySelectorAll('.sh-home-cta'));
    const magnetCleanups = magnets.map((el) => {
      const move = (event) => {
        if (reduced) return;
        const r = el.getBoundingClientRect();
        const dx = event.clientX - (r.left + r.width / 2);
        const dy = event.clientY - (r.top + r.height / 2);
        el.style.transform = `translate(${(dx * 0.28).toFixed(1)}px, ${(dy * 0.4).toFixed(1)}px)`;
      };
      const reset = () => {
        el.style.transform = '';
      };
      el.addEventListener('mousemove', move);
      el.addEventListener('mouseleave', reset);
      return () => {
        el.removeEventListener('mousemove', move);
        el.removeEventListener('mouseleave', reset);
        el.style.transform = '';
      };
    });

    window.addEventListener('mousemove', onMove, { passive: true });
    window.addEventListener('mouseout', onOut);
    window.addEventListener('mousedown', onDown);
    window.addEventListener('mouseup', onUp);
    document.addEventListener('mouseover', onOver, true);
    document.addEventListener('mouseout', onLeaveInteractive, true);

    return () => {
      if (raf) window.cancelAnimationFrame(raf);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseout', onOut);
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('mouseup', onUp);
      document.removeEventListener('mouseover', onOver, true);
      document.removeEventListener('mouseout', onLeaveInteractive, true);
      magnetCleanups.forEach((fn) => fn());
      body.classList.remove('sh-has-custom-cursor', 'sh-cursor-hidden', 'sh-cursor-active', 'sh-cursor-down');
    };
  }, []);

  return (
    <>
      <div ref={ringRef} className="sh-cursor-ring" aria-hidden="true" />
      <div ref={dotRef} className="sh-cursor-dot" aria-hidden="true" />
    </>
  );
}

// ---- Page ---------------------------------------------------------------------------------

export function SampleHomePage({ shared }) {
  const { useLegalChat, HeaderControls, SourceExcerptModal, VintageScales } = shared;
  const chat = useLegalChat();
  return (
    <>
      <SampleCursor />
      <SampleBackgroundArt VintageScales={VintageScales} />
      <HeaderControls />
      <div className="sh-sample-badge" role="note">Sample home · template sandbox</div>
      <div className="sh-content-frame">
        <SampleHero />
        <div className="sh-home-ask">
          <SampleQueryBox chat={chat} />
          <SampleAnswerPanel chat={chat} shared={shared} />
        </div>
        <SampleCategoryPills />
        <SampleFeatureCards />
        <SampleInfoSections />
      </div>
      <SampleFooter />
      {chat.selectedSource && (
        <SourceExcerptModal source={chat.selectedSource} onClose={() => chat.setSelectedSource(null)} />
      )}
    </>
  );
}
