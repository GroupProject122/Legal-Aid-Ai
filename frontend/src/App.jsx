import React from 'react';
import {
  ArrowUpRight,
  Bell,
  Bot,
  BriefcaseBusiness,
  Check,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  CircleUserRound,
  Clock,
  Download,
  Ellipsis,
  Eye,
  FilePenLine,
  FileImage,
  FileText,
  FolderOpen,
  Gavel,
  Gift,
  Globe2,
  HardDrive,
  Home,
  Info,
  Landmark,
  Lightbulb,
  LockKeyhole,
  MessageCircle,
  Mic,
  Moon,
  MoreHorizontal,
  MoreVertical,
  Paperclip,
  Pencil,
  ReceiptText,
  Scale,
  Search,
  Send,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Star,
  Tags,
  Trash2,
  UploadCloud,
  UserRound,
  X
} from 'lucide-react';

import { IntakeForm } from './schemes/IntakeForm.jsx';
import { ResultsList } from './schemes/ResultsList.jsx';
import { ApiError, postMatch } from './schemes/api.js';

import { ScenarioPicker, SCENARIOS } from './complaints/ScenarioPicker.jsx';
import { IntakeForm as ComplaintIntakeForm } from './complaints/IntakeForm.jsx';
import { DraftPreview } from './complaints/DraftPreview.jsx';
import { ApiError as ComplaintApiError, generateDraft } from './complaints/api.js';

const navItems = [
  { label: 'Home', icon: Home, page: 'home', href: '#/' },
  { label: 'Ask Question', icon: MessageCircle, page: 'ask', href: '#/ask' },
  { label: 'Draft Complaint', icon: Gavel, page: 'complaints', href: '#/complaints' },
  { label: 'My Cases', icon: BriefcaseBusiness, page: 'cases', href: '#/cases' },
  { label: 'Documents', icon: FileText, page: 'documents', href: '#/documents' },
  { label: 'Summarize Document', icon: Sparkles, page: 'summarize', href: '#/summarize-document' },
  { label: 'Know Your Rights', icon: ShieldCheck, page: 'rights', href: '#/rights' },
  { label: 'Schemes', icon: Gift, page: 'schemes', href: '#/schemes' },
  { label: 'About Us', icon: CircleHelp, page: 'about', href: '#/about' }
];

// `rightsCategory` is a real Know Your Rights category id (backend/legal_education_config.py's
// CATEGORIES) -- these pills deep-link straight into that category rather than just labeling a
// topic. "Other Legal Help" maps to "public_services" ("Public Services & Remedies": RTI, free
// legal aid, human rights/public-authority concerns) -- the one real KYR category that isn't
// consumer/tenancy/cyber/fundamental rights, and the closest fit for a catch-all "other" pill.
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

const exampleQuestions = [
  {
    text: 'The seller is refusing to refund a defective product.',
    icon: ShoppingCart
  },
  {
    text: 'My landlord has not returned my security deposit.',
    icon: Home
  },
  {
    text: 'Someone is misusing my personal information online.',
    icon: LockKeyhole
  },
  {
    text: 'I received a legal notice and don’t understand it.',
    icon: FileText
  }
];

const demoQuestion = 'I bought a phone online and it stopped working after two days. The seller is refusing to refund me. What can I do?';

const askCategories = ['Consumer', 'Tenant', 'Cyber', 'Fundamental Rights', 'Other'];

function displayCategoryFromRouting(routing) {
  const domains = routing?.domains || [];
  if (!domains.length) {
    if (routing?.status === 'unsupported' || routing?.status === 'out_of_scope') return 'Other';
    return '';
  }
  const labels = {
    consumer: 'Consumer',
    cyber: 'Cyber',
    tenancy: 'Tenant',
    constitutional_public_authority: 'Fundamental Rights'
  };
  return domains.map((domain) => labels[domain]).filter(Boolean).join(', ');
}

function createMessageId(prefix) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function replaceAssistantPlaceholder(messages, placeholderId, assistantMessage) {
  let replaced = false;
  const nextMessages = messages.map((message) => {
    if (message.id !== placeholderId) return message;
    replaced = true;
    return assistantMessage;
  });
  return replaced ? nextMessages : [...nextMessages, assistantMessage];
}

function formatCaseDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  });
}

function messagesFromSavedCase(savedMessages = []) {
  return savedMessages.map((message) => {
    if (message.role === 'user') {
      return {
        id: `saved-user-${message.id}`,
        role: 'user',
        text: message.content || '',
        timestamp: message.created_at
      };
    }
    return {
      id: `saved-ai-${message.id}`,
      role: 'ai',
      response: message.content || createTechnicalErrorResponse('This saved response could not be displayed.'),
      timestamp: message.created_at
    };
  });
}

const documentTabs = [
  { label: 'All Documents', count: 52, icon: FolderOpen },
  { label: 'Cases', count: 18, icon: BriefcaseBusiness },
  { label: 'Contracts', count: 9, icon: FilePenLine },
  { label: 'Notices', count: 7, icon: FileText },
  { label: 'Receipts', count: 11, icon: ReceiptText },
  { label: 'Others', count: 7, icon: Ellipsis }
];

const documents = [
  {
    name: 'Consumer Complaint.pdf',
    description: 'Consumer complaint against seller',
    category: 'Case Related',
    tab: 'Cases',
    linkedTo: 'Case #CA-2024-0152',
    uploadedDate: '12 May 2024',
    uploadedTime: '10:30 AM',
    size: '1.2 MB',
    type: 'pdf'
  },
  {
    name: 'Invoice - Order #5421.pdf',
    description: 'Purchase invoice and payment details',
    category: 'Receipt',
    tab: 'Receipts',
    linkedTo: 'Case #CA-2024-0152',
    uploadedDate: '12 May 2024',
    uploadedTime: '10:28 AM',
    size: '650 KB',
    type: 'pdf'
  },
  {
    name: 'Defective Product.jpg',
    description: 'Image of defective product',
    category: 'Evidence',
    tab: 'Cases',
    linkedTo: 'Case #CA-2024-0152',
    uploadedDate: '12 May 2024',
    uploadedTime: '10:25 AM',
    size: '2.4 MB',
    type: 'jpg'
  },
  {
    name: 'Seller Conversation.pdf',
    description: 'Chat and email conversation',
    category: 'Evidence',
    tab: 'Cases',
    linkedTo: 'Case #CA-2024-0152',
    uploadedDate: '12 May 2024',
    uploadedTime: '10:22 AM',
    size: '3.1 MB',
    type: 'pdf'
  },
  {
    name: 'Legal Notice.pdf',
    description: 'Notice received from seller',
    category: 'Notice',
    tab: 'Notices',
    linkedTo: 'Case #CA-2024-0138',
    uploadedDate: '04 May 2024',
    uploadedTime: '04:45 PM',
    size: '890 KB',
    type: 'pdf'
  },
  {
    name: 'Rental Agreement.docx',
    description: 'Agreement with landlord',
    category: 'Contract',
    tab: 'Contracts',
    linkedTo: 'Case #TD-2024-0087',
    uploadedDate: '28 Apr 2024',
    uploadedTime: '11:15 AM',
    size: '780 KB',
    type: 'docx'
  },
  {
    name: 'Bank Statement.pdf',
    description: 'Relevant bank statement',
    category: 'Evidence',
    tab: 'Cases',
    linkedTo: 'Case #TD-2024-0087',
    uploadedDate: '28 Apr 2024',
    uploadedTime: '11:10 AM',
    size: '1.6 MB',
    type: 'pdf'
  }
];

function LegalMark({ className = '' }) {
  return (
    <div className={`legal-mark ${className}`} aria-hidden="true">
      <span />
      <Scale size={54} strokeWidth={1.45} />
      <span />
    </div>
  );
}

function VintageScales({ className = '' }) {
  return (
    <svg className={className} viewBox="0 0 320 270" fill="none" aria-hidden="true">
      <path d="M160 27v198" />
      <path d="M132 225h56M113 245h94M96 259h128M119 236h82M105 252h110" />
      <path d="M138 40c8-21 36-21 44 0M126 49h68M160 40v-15M151 23h18M148 31h24" />
      <path d="M57 67h206M69 61h182M73 73h174M160 67c-17 12-39 18-66 18s-45-6-58-18M160 67c17 12 39 18 66 18s45-6 58-18" />
      <path d="M84 76l-33 72M84 76l33 72M236 76l-33 72M236 76l33 72" />
      <path d="M43 148c8 19 74 19 82 0H43ZM195 148c8 19 74 19 82 0h-82Z" />
      <path d="M54 154c14 9 52 10 62 0M58 148c7 12 46 12 53 0M210 148c7 12 46 12 53 0M206 154c14 9 52 10 62 0" opacity=".72" />
      <path d="M160 83c13 0 23-7 23-16M160 83c-13 0-23-7-23-16" />
      <path d="M145 117h30M145 137h30M145 157h30M145 177h30M145 197h30M153 96h14M151 216h18" opacity=".5" />
      <path d="M57 132h54M61 124h46M66 116h36M209 132h54M213 124h46M218 116h36" opacity=".34" />
      <path d="M48 151l69 8M199 151l69 8M51 159l59-8M202 159l59-8" opacity=".28" />
      <path d="M151 54c4 12 4 149 0 164M169 54c-4 12-4 149 0 164" opacity=".22" />
    </svg>
  );
}

function VintageCourthouse({ className = '' }) {
  return (
    <svg className={className} viewBox="0 0 360 250" fill="none" aria-hidden="true">
      <path d="M26 88h308L180 18 26 88Z" />
      <path d="M47 80h266M72 70h216M99 58h162M64 88h232M80 103h200M65 206h230M48 224h264M30 240h300" />
      <path d="M88 109v92M122 109v92M156 109v92M190 109v92M224 109v92M258 109v92" />
      <path d="M80 109h16M114 109h16M148 109h16M182 109h16M216 109h16M250 109h16" />
      <path d="M80 201h16M114 201h16M148 201h16M182 201h16M216 201h16M250 201h16" />
      <path d="M95 118v73M129 118v73M163 118v73M197 118v73M231 118v73M265 118v73" opacity=".55" />
      <path d="M158 63c12-17 32-17 44 0M151 68h58M180 42v27M170 51h20M166 58h28" />
      <path d="M55 226h250M72 216h216" opacity=".45" />
      <path d="M180 28 45 83M180 28l135 55" opacity=".48" />
      <path d="M76 94h208M86 97h188M43 232h274M58 235h244" opacity=".34" />
      <path d="M92 118h26M126 118h26M160 118h26M194 118h26M228 118h26M88 128h34M122 128h34M156 128h34M190 128h34M224 128h34" opacity=".28" />
      <path d="M103 122v68M137 122v68M171 122v68M205 122v68M239 122v68" opacity=".24" />
      <path d="M120 35 56 78M140 31 77 72M220 35l64 43M201 31l62 41" opacity=".24" />
      <path d="M151 207v-31c0-16 12-27 29-27s29 11 29 27v31M164 207v-30c0-8 6-15 16-15s16 7 16 15v30" opacity=".38" />
    </svg>
  );
}

function VintageGavel({ className = '' }) {
  return (
    <svg className={className} viewBox="0 0 330 230" fill="none" aria-hidden="true">
      <path d="M85 58 142 19l44 63-57 40-44-64Z" />
      <path d="M128 17 194 110M69 70l72-50M121 133l73-51M78 58l43-30M132 127l51-35" />
      <path d="M173 91 286 203M153 111l110 99M161 99l113 114M180 87l111 110" />
      <path d="M253 188c20-4 38 8 43 24M231 204c27-6 54 6 67 25" />
      <path d="M36 176h124c18 0 32 9 32 20v6H4v-6c0-11 14-20 32-20Z" />
      <path d="M42 160h111c13 0 24 7 24 16H18c0-9 11-16 24-16Z" />
      <path d="M103 71 157 34M116 90l55-38M129 109l54-38M97 61l45 65M111 51l45 65M124 42l45 65" opacity=".5" />
      <path d="M96 72c14-16 42-34 66-41M108 89c15-14 43-32 66-39M120 106c14-13 42-31 57-34" opacity=".27" />
      <path d="M33 169h128M24 184h162M33 194h147M53 160c9 7 9 42 0 42M142 160c-9 7-9 42 0 42" opacity=".28" />
      <path d="M205 122l-19 19M220 137l-19 19M235 152l-19 19M250 167l-19 19M265 182l-19 19" opacity=".24" />
    </svg>
  );
}

function VintageDocuments({ className = '' }) {
  return (
    <svg className={className} viewBox="0 0 310 250" fill="none" aria-hidden="true">
      <path d="M82 17h129l54 54v162H82V17Z" />
      <path d="M211 17v55h54M103 70h78M103 94h124M103 118h124M103 142h92M103 166h58M104 82h116M104 106h102M104 130h119M104 154h75" />
      <path d="M58 47h-22v169h31M238 87h24M50 59h22M50 82h22M50 105h22M50 128h22M50 151h22M50 174h22" opacity=".62" />
      <path d="M176 193c15-20 34-22 44-5 12 20-10 36-25 21-10-10 3-25 17-17" />
      <path d="M126 207h43M102 207h13" />
      <path d="M37 218c27 17 81 15 108-4" opacity=".42" />
      <path d="M223 70h30M91 28h106M92 40h103M92 52h78" opacity=".45" />
      <path d="M224 29c4 16 15 28 31 33M218 40c7 12 17 20 30 24M88 223h170M88 31v190M258 77v145" opacity=".27" />
      <path d="M181 181c11-8 28-10 40-1M187 216c9 7 26 8 38 1M183 188l36 24M220 187l-38 23" opacity=".28" />
      <path d="M117 70v97M191 94v74M228 94v48" opacity=".18" />
    </svg>
  );
}

function VintageLawBook({ className = '' }) {
  return (
    <svg className={className} viewBox="0 0 280 220" fill="none" aria-hidden="true">
      <path d="M54 42c24-13 57-15 88-2 30-13 64-11 88 2v139c-24-11-56-13-88 1-32-14-64-12-88-1V42Z" />
      <path d="M142 40v142M68 55c18-7 43-8 62 0M154 55c20-8 45-7 62 0M68 78h58M68 101h58M68 124h50M68 147h56M156 78h58M156 101h58M156 124h45M156 147h55" />
      <path d="M43 55c-11 6-17 16-17 29v122c26-13 69-17 116-2 47-15 90-11 116 2V84c0-13-6-23-17-29" />
      <path d="M34 198c31-10 68-9 108 4 40-13 77-14 108-4" opacity=".5" />
      <path d="M90 63c8 20 8 39 0 59M104 63c-8 20-8 39 0 59M84 93h27M178 66c8 20 8 39 0 59M192 66c-8 20-8 39 0 59M172 96h27" opacity=".36" />
      <path d="M59 43c25 3 52 10 83 22M225 43c-25 3-52 10-83 22M142 182c-25-12-54-16-88-8M142 182c25-12 54-16 88-8" opacity=".25" />
      <path d="M78 171c14-3 31-2 48 3M157 174c18-5 36-6 55-3M43 68v124M238 68v124" opacity=".24" />
    </svg>
  );
}

function Sidebar({ activePage = 'home', collapsed = false, onToggle }) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-frame" />
      <button
        type="button"
        className="sidebar-toggle"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        onClick={onToggle}
      >
        {collapsed ? <ChevronRight size={20} strokeWidth={1.9} /> : <ChevronLeft size={20} strokeWidth={1.9} />}
      </button>
      <div className="brand">
        <div className="brand-emblem">
          <span className="laurel left">〈</span>
          <Scale size={52} strokeWidth={1.5} />
          <span className="laurel right">〉</span>
        </div>
        <h1>LEGAL AID AI</h1>
        <p>Your Rights. Our Guidance.</p>
        <div className="mini-divider">◇</div>
      </div>

      <nav className="nav-list" aria-label="Main navigation">
        {navItems.map(({ label, icon: Icon, page, href }) => (
          <a
            href={href}
            className={`nav-item ${page === activePage ? 'active' : ''}`}
            key={label}
            title={collapsed ? label : undefined}
            data-tooltip={label}
          >
            <Icon size={23} strokeWidth={1.7} />
            <span>{label}</span>
          </a>
        ))}
      </nav>

      <div className="sidebar-art" aria-hidden="true">
        <Landmark size={98} />
      </div>

      <div className="sidebar-cards">
        <section className="privacy-card">
          <LockKeyhole size={30} strokeWidth={1.5} />
          <div>
            <h2>Your privacy matters</h2>
            <p>We keep your data safe and confidential.</p>
          </div>
        </section>

        <section className="help-card">
          <Bot size={34} strokeWidth={1.6} />
          <div>
            <h2>Need Help?</h2>
            <p>Talk to a legal advisor</p>
          </div>
          <ChevronRight size={22} />
        </section>
      </div>
    </aside>
  );
}

function HeaderControls() {
  return (
    <header className="top-controls" aria-label="Page controls">
      <button aria-label="Toggle theme">
        <Moon size={18} />
      </button>
      <button aria-label="Notifications">
        <Bell size={18} />
        <span className="notify-dot" />
      </button>
      <div className="avatar" aria-label="Profile" role="img">
        <CircleUserRound size={20} strokeWidth={1.6} />
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero">
      <p className="hero-kicker">Welcome to</p>
      <h2><span className="hero-title-inner">Legal Aid AI</span></h2>
      <p className="hero-subtitle">
        Understand your rights, draft complaints, and know what to do next — explained in plain language.
      </p>
    </section>
  );
}

function QueryBox() {
  const handleSubmit = (event) => {
    event.preventDefault();
    const value = new FormData(event.currentTarget).get('legal-query');
    const query = value.trim();
    window.location.hash = query ? `#/ask?q=${encodeURIComponent(query)}` : '#/ask';
  };

  // There's no conversation yet to attach a document to on the homepage -- the only real
  // target for "attach a document" is Ask Question's existing AttachmentModal. Send the user
  // there and open it immediately (`attach=1`, read by AskQuestionPage on mount), carrying over
  // anything they'd already typed the same way the submit button does.
  const handleAttachClick = (event) => {
    const value = new FormData(event.currentTarget.form).get('legal-query');
    const query = value.trim();
    const params = new URLSearchParams({ attach: '1' });
    if (query) params.set('q', query);
    window.location.hash = `#/ask?${params.toString()}`;
  };

  return (
    <form className="query-box" onSubmit={handleSubmit}>
      <div className="query-icon">
        <Sparkles size={20} />
      </div>
      <input
        name="legal-query"
        type="text"
        placeholder="Describe your legal issue in simple words..."
        aria-label="Describe your legal issue"
      />
      <button className="attach-button" type="button" aria-label="Attach document" onClick={handleAttachClick}>
        <Paperclip size={20} />
      </button>
      <button className="ask-button query-submit" type="submit">
        <Sparkles size={15} />
        <span>Ask AI</span>
      </button>
    </form>
  );
}

function CategoryPills() {
  return (
    <section className="home-section" aria-label="Legal categories">
      <h3 className="home-section-title">Browse by topic</h3>
      <div className="category-pills">
        {categories.map(({ label, icon: Icon, rightsCategory }) => (
          <button
            type="button"
            className="category-pill"
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

function FeatureCard({ title, description, button, icon: Icon, href }) {
  return (
    <article className="feature-card">
      <div className="feature-icon">
        <Icon size={22} strokeWidth={1.6} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      <a
        className="feature-link"
        href={href}
        onClick={(event) => { event.preventDefault(); window.location.hash = href; }}
      >
        {button}
        <ChevronRight size={15} strokeWidth={2} />
      </a>
    </article>
  );
}

function FeatureCards() {
  return (
    <section className="home-section features-section" aria-label="Homepage feature cards">
      <h3 className="home-section-title">How Legal Aid AI helps</h3>
      <div className="features">
        {features.map((feature) => (
          <FeatureCard {...feature} key={feature.title} />
        ))}
      </div>
    </section>
  );
}

function FooterQuote() {
  return (
    <footer className="footer-quote">
      <p>“Knowledge of your rights empowers you to protect them.”</p>
    </footer>
  );
}

function useParallax(speed = 0.12) {
  const ref = React.useRef(null);
  React.useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    if (typeof window === 'undefined') return undefined;
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

function BackgroundArt() {
  const parallaxRef = useParallax(0.1);
  return (
    <div className="background-art home-background-art" aria-hidden="true">
      <span className="home-bg-parallax" ref={parallaxRef}>
        <VintageScales className="watermark sketch scale-mark" />
      </span>
    </div>
  );
}

function PageDivider() {
  return (
    <div className="page-divider" aria-hidden="true">
      <span />
      <Scale size={24} strokeWidth={1.45} />
      <span />
    </div>
  );
}

function AskPageHeader() {
  return (
    <section className="ask-page-header">
      <h2>Ask Legal Aid AI</h2>
      <p>Describe your situation in your own words. We’ll help you understand the relevant legal information.</p>
      <PageDivider />
    </section>
  );
}

function AskBackgroundArt() {
  return (
    <div className="background-art ask-background-art" aria-hidden="true">
      <VintageScales className="watermark sketch ask-scale-mark" />
      <VintageGavel className="watermark sketch ask-gavel-mark" />
      <VintageCourthouse className="watermark sketch ask-court-mark" />
      <VintageDocuments className="watermark sketch ask-doc-mark" />
      <VintageLawBook className="watermark sketch ask-book-mark" />
      <span className="ask-section-symbol">§</span>
    </div>
  );
}

function PanelCorners() {
  return (
    <>
      <div className="ornament corner-a" />
      <div className="ornament corner-b" />
      <div className="ornament corner-c" />
      <div className="ornament corner-d" />
    </>
  );
}

function ExampleQuestionCard({ example, onSelect }) {
  const Icon = example.icon;

  return (
    <button type="button" className="example-card" onClick={() => onSelect(example.text)}>
      <Icon size={24} strokeWidth={1.55} />
      <span>{example.text}</span>
      <ChevronRight size={18} strokeWidth={1.65} />
    </button>
  );
}

function WelcomeState({ onSelectExample }) {
  return (
    <section className="chat-welcome">
      <div className="welcome-emblem">
        <Scale size={48} strokeWidth={1.35} />
      </div>
      <div className="welcome-copy">
        <h3>How can we help you today?</h3>
        <p>Tell us what happened in simple words. You don’t need to know any legal terms.</p>
      </div>
      <div className="example-grid">
        {exampleQuestions.map((example) => (
          <ExampleQuestionCard example={example} onSelect={onSelectExample} key={example.text} />
        ))}
      </div>
    </section>
  );
}

function UserMessage({ text }) {
  return (
    <article className="message-row user-message-row">
      <div className="user-message">
        <p>{text}</p>
        <time>10:32 AM</time>
      </div>
      <div className="message-avatar user-message-avatar" aria-hidden="true">
        <UserRound size={23} strokeWidth={1.6} />
      </div>
    </article>
  );
}

function createErrorResponse(message) {
  return {
    answer: {
      issue_summary: message,
      possible_rights: [],
      next_steps: ['Check that the backend is running and the legal PDFs have been ingested.']
    },
    sources: [],
    confidence: 'low',
    insufficient_context: true,
    disclaimer: 'This is legal information, not professional legal advice.'
  };
}

const TECHNICAL_ERROR_MESSAGE = 'Legal Aid AI could not process your request right now. Please check that the backend and Gemini API are configured correctly and try again.';

function cleanDisplayText(value) {
  return String(value || '')
    .replace(/<svg\b[^>]*>.*?<\/svg>/gis, ' ')
    .replace(/\bsvg\b/gi, ' ')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/^\s*(?:step\s*)?\d+\s*[\).:-]\s*/i, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function createTechnicalErrorResponse(message = TECHNICAL_ERROR_MESSAGE) {
  return {
    answer: {
      issue_summary: message,
      possible_rights: [],
      next_steps: [
        'Check that the FastAPI backend is running.',
        'Check that Gemini is configured correctly, then try again.'
      ]
    },
    sources: [],
    confidence: 'low',
    insufficient_context: false,
    technical_error: true,
    disclaimer: 'This is legal information, not professional legal advice.'
  };
}

async function parseAskResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  const rawBody = await response.text();
  let payload = null;

  if (contentType.includes('application/json') && rawBody.trim()) {
    try {
      payload = JSON.parse(rawBody);
    } catch (error) {
      console.error('Failed to parse /api/ask JSON response', { error, status: response.status, rawBody });
      throw new Error(TECHNICAL_ERROR_MESSAGE);
    }
  } else if (rawBody.trim()) {
    console.error('Received non-JSON /api/ask response', { status: response.status, contentType, rawBody });
  }

  if (!response.ok) {
    console.error('Backend returned an error for /api/ask', {
      status: response.status,
      detail: payload?.detail || rawBody || 'No response body'
    });
    throw new Error(TECHNICAL_ERROR_MESSAGE);
  }

  if (!payload) {
    console.error('Received empty /api/ask response body', { status: response.status, contentType });
    throw new Error(TECHNICAL_ERROR_MESSAGE);
  }

  return payload;
}

function SourceCard({ source, onClick }) {
  const detail = [cleanDisplayText(source.section), source.page ? `Page ${source.page}` : null].filter(Boolean).join(' · ');
  const documentTitle = cleanDisplayText(source.document);

  return (
    <button type="button" className="source-card" onClick={() => onClick(source)}>
      <FileText size={19} strokeWidth={1.6} />
      <span>
        <strong>{documentTitle}</strong>
        <small>{detail || 'Source excerpt'}</small>
      </span>
      <ArrowUpRight size={16} strokeWidth={1.7} />
    </button>
  );
}

function LegalAIResponse({ response, onSourceClick }) {
  const answer = response?.answer || {};
  const sources = response?.sources || [];
  const documentEvidence = response?.document_evidence_used || [];
  const possibleRights = (answer.possible_rights || answer.possible_legal_position || []).map(cleanDisplayText).filter(Boolean);
  const nextSteps = (answer.next_steps || answer.suggested_next_steps || []).map(cleanDisplayText).filter(Boolean);
  const whatThisMayInvolve = (answer.what_this_may_involve || []).map(cleanDisplayText).filter(Boolean);
  const evidenceToPreserve = (answer.evidence_to_preserve || []).map(cleanDisplayText).filter(Boolean);
  const whereToApproach = (answer.where_to_approach || []).map(cleanDisplayText).filter(Boolean);
  const limitations = (answer.limitations || []).map(cleanDisplayText).filter(Boolean);
  const clarificationQuestion = cleanDisplayText(response?.clarification?.question);

  if (response?.technical_error) {
    return (
      <article className="message-row ai-message-row">
        <div className="message-avatar ai-message-avatar" aria-hidden="true">
          <Info size={21} strokeWidth={1.7} />
        </div>
        <section className="legal-response-card technical-response-card">
          <div className="response-header">
            <div className="response-brand">
              <div className="response-emblem">
                <Info size={18} strokeWidth={1.7} />
              </div>
              <strong>Legal Aid AI</strong>
            </div>
            <span className="response-pill">Technical issue</span>
          </div>
          <div className="response-section">
            <h4>Request could not be processed</h4>
            <p>{cleanDisplayText(answer.issue_summary) || TECHNICAL_ERROR_MESSAGE}</p>
          </div>
          {nextSteps.length > 0 && (
            <div className="response-section">
              <h4>What to check</h4>
              <ol className="step-list">
                {nextSteps.map((step, index) => (
                  <li key={step}><span>{index + 1}</span>{step}</li>
                ))}
              </ol>
            </div>
          )}
        </section>
      </article>
    );
  }

  return (
    <article className="message-row ai-message-row">
      <div className="message-avatar ai-message-avatar" aria-hidden="true">
        <Scale size={21} strokeWidth={1.45} />
      </div>
      <section className="legal-response-card">
        <div className="response-header">
          <div className="response-brand">
            <div className="response-emblem">
              <Scale size={18} strokeWidth={1.5} />
            </div>
            <strong>Legal Aid AI</strong>
          </div>
          <span className="response-pill">Legal information</span>
        </div>

        <div className="response-section">
          <h4>What this may involve</h4>
          <p>{cleanDisplayText(answer.issue_summary) || 'The available legal sources do not contain enough information to answer this reliably.'}</p>
          {whatThisMayInvolve.length > 0 && (
            <ul>
              {whatThisMayInvolve.map((item) => <li key={item}>{item}</li>)}
            </ul>
          )}
        </div>

        {clarificationQuestion ? (
          <div className="response-section">
            <h4>Clarification needed</h4>
            <p>{clarificationQuestion}</p>
          </div>
        ) : possibleRights.length > 0 ? (
          <div className="response-section">
            <h4>Your possible rights</h4>
            <ul>
              {possibleRights.map((right) => <li key={right}>{right}</li>)}
            </ul>
          </div>
        ) : null}

        {!clarificationQuestion && nextSteps.length > 0 && (
          <div className="response-section">
            <h4>Suggested next steps</h4>
            <ol className="step-list">
              {nextSteps.map((step, index) => (
                <li key={step}><span>{index + 1}</span>{step}</li>
              ))}
            </ol>
          </div>
        )}

        {!clarificationQuestion && evidenceToPreserve.length > 0 && (
          <div className="response-section">
            <h4>Evidence to preserve</h4>
            <ul>
              {evidenceToPreserve.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        )}

        {!clarificationQuestion && whereToApproach.length > 0 && (
          <div className="response-section">
            <h4>Where to approach</h4>
            <ul>
              {whereToApproach.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        )}

        {!clarificationQuestion && limitations.length > 0 && (
          <div className="response-section">
            <h4>Limitations</h4>
            <ul>
              {limitations.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        )}

        {!clarificationQuestion && sources.length > 0 && (
          <div className="response-section sources-section">
            <h4>Sources used</h4>
            <div className="source-list">
              {sources.map((source) => (
                <SourceCard source={source} onClick={onSourceClick} key={`${source.document}-${source.page}-${source.section || 'source'}`} />
              ))}
            </div>
          </div>
        )}

        {!clarificationQuestion && documentEvidence.length > 0 && (
          <div className="response-section document-evidence-section">
            <h4>Document facts used</h4>
            <ul>
              {documentEvidence.map((fact, index) => (
                <li key={`${fact.label}-${index}`}>
                  <strong>{cleanDisplayText(fact.label)}:</strong> {cleanDisplayText(fact.value)}
                  {fact.source_page ? <small> Document page {fact.source_page}</small> : null}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="response-disclaimer">
          <ShieldCheck size={16} strokeWidth={1.7} />
          <span>{response?.disclaimer || 'This is legal information, not professional legal advice.'}</span>
          <time>10:32 AM</time>
        </div>
      </section>
    </article>
  );
}

function LoadingState() {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span />
      <p>Reviewing the available legal sources...</p>
    </div>
  );
}

function LoadingMessage() {
  return (
    <article className="message-row ai-message-row">
      <div className="message-avatar ai-message-avatar" aria-hidden="true">
        <Scale size={21} strokeWidth={1.45} />
      </div>
      <LoadingState />
    </article>
  );
}

function ChatComposer({ value, onChange, onSubmit, onAttach }) {
  return (
    <form className="chat-composer" onSubmit={onSubmit}>
      <button type="button" className="composer-icon-button" aria-label="Attach document" onClick={onAttach}>
        <Paperclip size={25} strokeWidth={1.7} />
      </button>
      <label className="sr-only" htmlFor="legal-chat-input">Describe your legal issue</label>
      <textarea
        id="legal-chat-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Describe your legal issue..."
        rows={1}
        aria-label="Describe your legal issue"
      />
      <button type="button" className="composer-icon-button" aria-label="Use microphone">
        <Mic size={24} strokeWidth={1.7} />
      </button>
      <button type="submit" className="ask-button composer-submit">
        <Send size={18} strokeWidth={1.8} />
        <span>Ask AI</span>
      </button>
    </form>
  );
}

function ChatPanel({ input, setInput, messages, isLoading, onSubmit, onExample, onClear, onAttach, onSourceClick }) {
  const scrollRef = React.useRef(null);

  React.useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTo({ top: node.scrollHeight, behavior: 'smooth' });
  }, [messages, isLoading]);

  return (
    <section className="chat-panel" aria-label="Legal AI chat">
      <PanelCorners />
      <div className="chat-panel-toolbar">
        <div>
          <span>◇</span>
          <p>Legal consultation workspace</p>
        </div>
        <button type="button" className="outline-action" onClick={onClear}>New Question</button>
      </div>

      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 && !isLoading ? (
          <WelcomeState onSelectExample={onExample} />
        ) : (
          <>
            {messages.map((message) => (
              message.role === 'user'
                ? <UserMessage text={message.text} key={message.id} />
                : message.role === 'assistant_loading'
                  ? <LoadingMessage key={message.id} />
                : <LegalAIResponse response={message.response} onSourceClick={onSourceClick} key={message.id} />
            ))}
          </>
        )}
      </div>

      <ChatComposer value={input} onChange={setInput} onSubmit={onSubmit} onAttach={onAttach} />
    </section>
  );
}

function QuerySummaryPanel({ category, onAttach, attachedFactContext, onDetachFactContext }) {
  const selectedCategories = category.split(',').map((item) => item.trim()).filter(Boolean);
  return (
    <aside className="query-summary-panel" aria-label="Your query summary">
      <section className="summary-card query-card">
        <PanelCorners />
        <div className="summary-heading">
          <div>
            <h3>Your Query</h3>
            <PageDivider />
          </div>
          <Scale size={27} strokeWidth={1.35} />
        </div>

        <div className="summary-item">
          <Tags size={21} strokeWidth={1.55} />
          <div>
            <h4>Category</h4>
            <p>{category || 'Not selected'}</p>
          </div>
        </div>

        {/* Read-only: reflects Legal Aid AI's own classification of the question (possibly
            more than one domain at once), it is not a filter the user sets -- there is
            nothing here for a click to send to the backend. */}
        <div className="category-chip-list" aria-label="Legal category, as classified by Legal Aid AI">
          {askCategories.map((item) => (
            <span
              className={`mini-chip ${selectedCategories.includes(item) ? 'selected' : ''}`}
              key={item}
            >
              {item}
            </span>
          ))}
        </div>

        <div className="summary-item">
          <Globe2 size={21} strokeWidth={1.55} />
          <div>
            <h4>Jurisdiction</h4>
            <p>India</p>
          </div>
        </div>

        <button type="button" className="summary-item summary-button" onClick={onAttach}>
          <Paperclip size={22} strokeWidth={1.6} />
          <div>
            <h4>Document facts</h4>
            <p>{attachedFactContext ? 'Confirmed facts attached' : '0'}</p>
          </div>
        </button>
        {attachedFactContext && (
          <button type="button" className="detach-facts-button" onClick={onDetachFactContext}>
            Detach document facts
          </button>
        )}
      </section>

      <section className="summary-card tip-card">
        <PanelCorners />
        <div className="tip-heading">
          <Lightbulb size={26} strokeWidth={1.55} />
          <h3>Tip</h3>
        </div>
        <p>Include dates, receipts, notices, messages, or other relevant details when describing your issue.</p>
      </section>
    </aside>
  );
}

function AttachmentModal({ onClose }) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="attachment-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="attachment-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label="Close upload information" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="modal-emblem">
          <ReceiptText size={30} strokeWidth={1.55} />
        </div>
        <h3 id="attachment-title">Upload supporting document</h3>
        <p>You’ll be able to upload notices, receipts, contracts, or screenshots here.</p>
        <div className="format-list" aria-label="Supported future formats">
          <span>PDF</span>
          <span>JPG</span>
          <span>PNG</span>
        </div>
        <div className="modal-note">
          <Info size={17} strokeWidth={1.7} />
          <span>Document analysis will be enabled in a later version.</span>
        </div>
      </section>
    </div>
  );
}

function SourceExcerptModal({ source, onClose }) {
  const detail = [cleanDisplayText(source.section), source.page ? `Page ${source.page}` : null].filter(Boolean).join(' · ');

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="attachment-modal source-excerpt-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-excerpt-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label="Close source excerpt" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="modal-emblem">
          <FileText size={30} strokeWidth={1.55} />
        </div>
        <h3 id="source-excerpt-title">{cleanDisplayText(source.document)}</h3>
        <p>{detail || 'Retrieved source'}</p>
        <div className="source-excerpt-box">
          <strong>Retrieved excerpt</strong>
          <p>{cleanDisplayText(source.excerpt) || 'No excerpt was returned for this source.'}</p>
        </div>
      </section>
    </div>
  );
}

function AskQuestionPage({ initialQuery = '', initialCaseId = '', initialAttach = false }) {
  const [input, setInput] = React.useState(initialQuery);
  const [messages, setMessages] = React.useState([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [category, setCategory] = React.useState('');
  const [isAttachmentOpen, setIsAttachmentOpen] = React.useState(initialAttach);
  const [selectedSource, setSelectedSource] = React.useState(null);
  const [clarificationStateId, setClarificationStateId] = React.useState(null);
  const [conversationStateId, setConversationStateId] = React.useState(null);
  const [caseId, setCaseId] = React.useState(initialCaseId || null);
  const [attachedFactContext, setAttachedFactContext] = React.useState(null);
  const loadingTimer = React.useRef(null);

  React.useEffect(() => {
    setInput(initialQuery);
  }, [initialQuery]);

  React.useEffect(() => () => window.clearTimeout(loadingTimer.current), []);

  React.useEffect(() => {
    if (!initialCaseId) return;
    let ignore = false;
    const loadCase = async () => {
      try {
        const response = await fetch(`/api/cases/${encodeURIComponent(initialCaseId)}`);
        const payload = await safeJsonResponse(response);
        if (!response.ok || !payload) {
          throw new Error('Could not load this case.');
        }
        if (ignore) return;
        setCaseId(payload.case?.id || initialCaseId);
        setMessages(messagesFromSavedCase(payload.messages || []));
        const stateId = payload.conversation_state?.conversation_state_id || null;
        setConversationStateId(stateId);
        setClarificationStateId(null);
        const restoredCategory = displayCategoryFromRouting({
          status: payload.conversation_state?.domains?.length ? 'classified' : undefined,
          domains: payload.conversation_state?.domains || []
        });
        setCategory(restoredCategory || displayCategoryFromRouting({
          status: payload.case?.primary_domain ? 'classified' : undefined,
          domains: payload.case?.primary_domain ? [payload.case.primary_domain] : []
        }));
        if (payload.confirmed_document_context) {
          setAttachedFactContext(payload.confirmed_document_context);
          window.sessionStorage.setItem('legalAidConfirmedFactContext', JSON.stringify(payload.confirmed_document_context));
        }
      } catch (error) {
        console.error('Could not open saved case', error);
        if (!ignore) {
          setMessages([{
            id: createMessageId('ai-error'),
            role: 'ai',
            response: createTechnicalErrorResponse('Legal Aid AI could not open this saved case right now.'),
            timestamp: new Date().toISOString()
          }]);
        }
      }
    };
    loadCase();
    return () => {
      ignore = true;
    };
  }, [initialCaseId]);

  React.useEffect(() => {
    const stored = window.sessionStorage.getItem('legalAidConfirmedFactContext');
    if (stored) {
      try {
        setAttachedFactContext(JSON.parse(stored));
      } catch (error) {
        console.error('Could not read confirmed fact context', error);
        window.sessionStorage.removeItem('legalAidConfirmedFactContext');
      }
    }
  }, []);

  const submitQuestion = async (question) => {
    const text = question.trim();
    if (!text || isLoading) return;

    window.clearTimeout(loadingTimer.current);
    const activeClarificationStateId = clarificationStateId;
    const activeConversationStateId = conversationStateId;
    const activeCaseId = caseId;
    const assistantMessageId = createMessageId('ai-loading');
    setMessages((current) => [
      ...current,
      { id: createMessageId('user'), role: 'user', text, timestamp: new Date().toISOString() },
      { id: assistantMessageId, role: 'assistant_loading', timestamp: new Date().toISOString() }
    ]);
    setInput('');
    setIsLoading(true);
    loadingTimer.current = window.setTimeout(async () => {
      try {
        const requestBody = activeClarificationStateId
          ? {
              question: text,
              clarification_state_id: activeClarificationStateId,
              ...(activeCaseId ? { case_id: activeCaseId } : {}),
              ...(activeConversationStateId ? { conversation_state_id: activeConversationStateId } : {})
            }
          : {
              question: text,
              ...(activeCaseId ? { case_id: activeCaseId } : {}),
              ...(activeConversationStateId ? { conversation_state_id: activeConversationStateId } : {}),
              ...(attachedFactContext?.confirmed_fact_context_id
                ? { confirmed_fact_context_id: attachedFactContext.confirmed_fact_context_id }
                : {})
            };
        const response = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody)
        });
        const payload = await parseAskResponse(response);
        setClarificationStateId(payload?.clarification?.needed ? payload.clarification.state_id : null);
        setConversationStateId(payload?.conversation_state_id || null);
        if (payload?.case_id) {
          setCaseId(payload.case_id);
        }
        const routedCategory = displayCategoryFromRouting(payload?.routing);
        if (routedCategory) {
          setCategory(routedCategory);
        }
        setMessages((current) => replaceAssistantPlaceholder(current, assistantMessageId, {
          id: createMessageId('ai'),
          role: 'ai',
          response: payload,
          timestamp: new Date().toISOString()
        }));
      } catch (error) {
        console.error('Ask Legal Aid AI request failed', error);
        setMessages((current) => replaceAssistantPlaceholder(current, assistantMessageId, {
          id: createMessageId('ai-error'),
          role: 'ai',
          response: createTechnicalErrorResponse(error.message),
          timestamp: new Date().toISOString()
        }));
      } finally {
        setIsLoading(false);
      }
    }, 500);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    submitQuestion(input);
  };

  const handleExample = (text) => {
    setInput(text);
  };

  const handleClear = () => {
    window.clearTimeout(loadingTimer.current);
    setInput('');
    setMessages([]);
    setIsLoading(false);
    setSelectedSource(null);
    setClarificationStateId(null);
    setConversationStateId(null);
    setCaseId(null);
    setCategory('');
    window.sessionStorage.removeItem('legalAidConfirmedFactContext');
    setAttachedFactContext(null);
    if (window.location.hash.includes('case=')) {
      window.location.hash = '#/ask';
    }
  };

  const handleDetachFactContext = () => {
    window.sessionStorage.removeItem('legalAidConfirmedFactContext');
    setAttachedFactContext(null);
  };

  return (
    <>
      <AskBackgroundArt />
      <HeaderControls />
      <div className="ask-content-frame">
        <AskPageHeader />
        <div className="ask-workspace">
          <ChatPanel
            input={input}
            setInput={setInput}
            messages={messages}
            isLoading={isLoading}
            onSubmit={handleSubmit}
            onExample={handleExample}
            onClear={handleClear}
            onAttach={() => setIsAttachmentOpen(true)}
            onSourceClick={setSelectedSource}
          />
          <QuerySummaryPanel
            category={category}
            onAttach={() => setIsAttachmentOpen(true)}
            attachedFactContext={attachedFactContext}
            onDetachFactContext={handleDetachFactContext}
          />
        </div>
      </div>
      {isAttachmentOpen && <AttachmentModal onClose={() => setIsAttachmentOpen(false)} />}
      {selectedSource && <SourceExcerptModal source={selectedSource} onClose={() => setSelectedSource(null)} />}
    </>
  );
}

function DocumentsBackgroundArt() {
  return (
    <div className="background-art documents-background-art" aria-hidden="true">
      <VintageLawBook className="watermark sketch docs-book-mark" />
      <VintageCourthouse className="watermark sketch docs-court-mark" />
      <VintageGavel className="watermark sketch docs-gavel-mark" />
      <VintageDocuments className="watermark sketch docs-paper-mark" />
      <VintageScales className="watermark sketch docs-scale-mark" />
      <span className="docs-section-symbol">§</span>
    </div>
  );
}

function DocumentsPageHeader() {
  return (
    <section className="documents-page-header">
      <div className="header-ornament-line" aria-hidden="true">
        <span />
        <i>◇</i>
      </div>
      <h2>Documents</h2>
      <div className="header-ornament-line" aria-hidden="true">
        <i>◇</i>
        <span />
      </div>
      <p>Manage your uploaded legal documents securely.</p>
      <PageDivider />
    </section>
  );
}

function DocumentTabs({ activeTab, onChange }) {
  return (
    <div className="document-tabs" aria-label="Document categories">
      {documentTabs.map(({ label, count, icon: Icon }) => (
        <button
          type="button"
          className={`document-tab ${activeTab === label ? 'selected' : ''}`}
          onClick={() => onChange(label)}
          key={label}
        >
          <Icon size={17} strokeWidth={1.65} />
          <span>{label}</span>
          <small>{count}</small>
        </button>
      ))}
    </div>
  );
}

function DocumentSearch({ value, onChange }) {
  return (
    <label className="document-search">
      <Search size={19} strokeWidth={1.7} />
      <span className="sr-only">Search documents</span>
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search documents..."
      />
    </label>
  );
}

function FileTypeIcon({ type }) {
  const normalizedType = type || 'file';
  const Icon = normalizedType === 'jpg' ? FileImage : FileText;
  const label = normalizedType === 'docx' ? 'DOCX' : normalizedType.toUpperCase();

  return (
    <div className={`file-type-icon ${normalizedType}`} aria-hidden="true">
      <Icon size={19} strokeWidth={1.7} />
      <span>{label}</span>
    </div>
  );
}

function CategoryBadge({ category }) {
  return <span className={`document-badge ${category.toLowerCase().replace(/\s+/g, '-')}`}>{category}</span>;
}

function DocumentActions({ document, openMenu, onToggleMenu, onPreview }) {
  const menuId = `document-menu-${document.name.replace(/[^a-z0-9]/gi, '-').toLowerCase()}`;

  return (
    <div className="document-actions">
      <button type="button" className="table-action" aria-label={`View ${document.name}`} onClick={() => onPreview(document)}>
        <Eye size={17} strokeWidth={1.7} />
      </button>
      <button
        type="button"
        className="table-action"
        aria-label={`More actions for ${document.name}`}
        aria-haspopup="menu"
        aria-expanded={openMenu === document.name}
        aria-controls={menuId}
        onClick={() => onToggleMenu(document.name)}
      >
        <MoreVertical size={17} strokeWidth={1.7} />
      </button>
      {openMenu === document.name && (
        <div className="document-menu" id={menuId} role="menu">
          <button type="button" role="menuitem" onClick={() => onPreview(document)}><Eye size={15} />View</button>
          <button type="button" role="menuitem"><Pencil size={15} />Rename</button>
          <button type="button" role="menuitem"><Download size={15} />Download</button>
          <button type="button" role="menuitem"><Trash2 size={15} />Delete</button>
        </div>
      )}
    </div>
  );
}

function DocumentCard({ document, openMenu, onToggleMenu, onPreview }) {
  return (
    <article className="document-mobile-card">
      <div className="document-name-cell">
        <FileTypeIcon type={document.type} />
        <div>
          <strong>{document.name}</strong>
          <p>{document.description}</p>
        </div>
      </div>
      <div className="document-card-meta">
        <span><CategoryBadge category={document.category} /></span>
        <span>{document.linkedTo}</span>
        <span>{document.uploadedDate} · {document.uploadedTime}</span>
        <span>{document.size}</span>
      </div>
      <DocumentActions document={document} openMenu={openMenu} onToggleMenu={onToggleMenu} onPreview={onPreview} />
    </article>
  );
}

function DocumentTable({ documents: rows, openMenu, onToggleMenu, onPreview }) {
  return (
    <>
      <div className="document-table-wrap">
        <table className="document-table">
          <thead>
            <tr>
              <th>Document Name</th>
              <th>Category</th>
              <th>Linked To</th>
              <th>Uploaded On</th>
              <th>Size</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((document) => (
              <tr key={document.name}>
                <td>
                  <div className="document-name-cell">
                    <FileTypeIcon type={document.type} />
                    <div>
                      <strong>{document.name}</strong>
                      <p>{document.description}</p>
                    </div>
                  </div>
                </td>
                <td><CategoryBadge category={document.category} /></td>
                <td>{document.linkedTo}</td>
                <td>
                  <span className="stacked-date">{document.uploadedDate}<small>{document.uploadedTime}</small></span>
                </td>
                <td>{document.size}</td>
                <td>
                  <DocumentActions document={document} openMenu={openMenu} onToggleMenu={onToggleMenu} onPreview={onPreview} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="document-card-list">
        {rows.map((document) => (
          <DocumentCard
            document={document}
            openMenu={openMenu}
            onToggleMenu={onToggleMenu}
            onPreview={onPreview}
            key={document.name}
          />
        ))}
      </div>
    </>
  );
}

function DocumentPagination({ visibleCount }) {
  return (
    <div className="document-pagination">
      <div className="pagination-controls" aria-label="Document pagination">
        <button type="button">Prev</button>
        <button type="button" className="selected">1</button>
        <button type="button">2</button>
        <button type="button">3</button>
        <span>...</span>
        <button type="button">8</button>
        <button type="button">Next</button>
      </div>
      <p>Showing 1 to {visibleCount} of 52 documents</p>
    </div>
  );
}

function DocumentsPanel({ activeTab, setActiveTab, search, setSearch, filteredDocuments, openMenu, setOpenMenu, setPreviewDocument }) {
  return (
    <section className="documents-panel" aria-label="Document management">
      <PanelCorners />
      <div className="documents-toolbar">
        <DocumentTabs activeTab={activeTab} onChange={setActiveTab} />
        <DocumentSearch value={search} onChange={setSearch} />
      </div>
      <DocumentTable
        documents={filteredDocuments}
        openMenu={openMenu}
        onToggleMenu={(name) => setOpenMenu((current) => current === name ? '' : name)}
        onPreview={setPreviewDocument}
      />
      {filteredDocuments.length === 0 && (
        <div className="empty-documents">
          <FileText size={34} strokeWidth={1.45} />
          <p>No mock documents match this view.</p>
        </div>
      )}
      <DocumentPagination visibleCount={filteredDocuments.length} />
    </section>
  );
}

function UploadDocumentCard({ onUploaded, externalInputRef }) {
  const [selectedFile, setSelectedFile] = React.useState(null);
  const [status, setStatus] = React.useState('idle');
  const [message, setMessage] = React.useState('');
  const [extraction, setExtraction] = React.useState(null);
  const [factStatus, setFactStatus] = React.useState('idle');
  const [factMessage, setFactMessage] = React.useState('');
  const [factExtraction, setFactExtraction] = React.useState(null);
  const [editableFacts, setEditableFacts] = React.useState(null);
  const [expanded, setExpanded] = React.useState(false);
  const fileInputRef = React.useRef(null);

  const setFileInputNode = (node) => {
    fileInputRef.current = node;
    if (externalInputRef) {
      externalInputRef.current = node;
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setStatus('idle');
    setMessage('');
    setExtraction(null);
    setFactStatus('idle');
    setFactMessage('');
    setFactExtraction(null);
    setEditableFacts(null);
    setExpanded(false);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setMessage('Choose a PDF, DOCX, or TXT file first.');
      return;
    }
    const formData = new FormData();
    formData.append('file', selectedFile);
    setStatus('uploading');
    setMessage('');
    setExtraction(null);
    try {
      const response = await fetch('/api/documents/extract', {
        method: 'POST',
        body: formData
      });
      const rawBody = await response.text();
      let data = null;
      try {
        data = rawBody ? JSON.parse(rawBody) : null;
      } catch (error) {
        console.error('Failed to parse document extraction response', { error, status: response.status, rawBody });
      }
      if (!response.ok) {
        throw new Error(data?.detail || 'Legal Aid AI could not extract this document right now.');
      }
      if (!data) {
        throw new Error('Legal Aid AI could not read the extraction response.');
      }
      setExtraction(data);
      setStatus(data.status || 'success');
      setMessage(documentExtractionMessage(data));
      setFactStatus('idle');
      setFactMessage('');
      setFactExtraction(null);
      setEditableFacts(null);
      if (data.document_id && onUploaded) {
        onUploaded(data);
      }
    } catch (error) {
      console.error('Document extraction failed', error);
      setStatus('failed');
      setMessage(error.message || 'Legal Aid AI could not extract this document right now.');
    }
  };

  const handleIdentifyFacts = async () => {
    if (!extraction?.text) {
      setFactMessage('Extract text from a document first.');
      return;
    }
    setFactStatus('loading');
    setFactMessage('');
    try {
      const response = await fetch('/api/documents/extract-facts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ extraction })
      });
      const data = await safeJsonResponse(response);
      if (!response.ok) {
        throw new Error(data?.detail || 'Legal Aid AI could not identify facts right now.');
      }
      setFactExtraction(data);
      setEditableFacts(data.facts || null);
      setFactStatus(data.status || 'success');
      setFactMessage(documentFactMessage(data));
    } catch (error) {
      console.error('Document fact extraction failed', error);
      setFactStatus('failed');
      setFactMessage(error.message || 'Legal Aid AI could not identify facts right now.');
    }
  };

  const handleFactChange = (category, index, value) => {
    setEditableFacts((current) => {
      const next = structuredClone(current);
      next[category][index].value = value;
      return next;
    });
  };

  const handleRemoveFact = (category, index) => {
    setEditableFacts((current) => {
      const next = structuredClone(current);
      next[category] = next[category].filter((_, itemIndex) => itemIndex !== index);
      return next;
    });
  };

  const handleConfirmFacts = async () => {
    if (!factExtraction?.fact_extraction_id || !editableFacts) {
      return;
    }
    setFactStatus('confirming');
    try {
      const response = await fetch('/api/documents/confirm-facts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fact_extraction_id: factExtraction.fact_extraction_id,
          confirmed_facts: editableFacts,
          ...(extraction?.document_id ? { document_id: extraction.document_id } : {})
        })
      });
      const data = await safeJsonResponse(response);
      if (!response.ok) {
        throw new Error(data?.detail || 'Legal Aid AI could not confirm these facts right now.');
      }
      setFactStatus('confirmed');
      if (data?.confirmed_fact_context_id) {
        window.sessionStorage.setItem('legalAidConfirmedFactContext', JSON.stringify({
          confirmed_fact_context_id: data.confirmed_fact_context_id,
          document_type: data.confirmed_facts?.document_type || 'unknown'
        }));
      }
      setFactMessage('Facts confirmed. They remain user case facts and are not legal authority.');
    } catch (error) {
      console.error('Document fact confirmation failed', error);
      setFactStatus('failed');
      setFactMessage(error.message || 'Legal Aid AI could not confirm these facts right now.');
    }
  };

  const previewText = extraction?.text || '';
  const previewLimit = expanded ? 5000 : 1200;
  const preview = previewText.slice(0, previewLimit);

  return (
    <section className="documents-side-card upload-card">
      <PanelCorners />
      <h3>Upload Document</h3>
      <button type="button" className="drop-zone" onClick={() => fileInputRef.current?.click()}>
        <UploadCloud size={36} strokeWidth={1.45} />
        <strong>Drag & drop files here</strong>
        <span>or click to browse</span>
        <small>Supported: PDF, DOCX, TXT<br />Max size: 10 MB</small>
      </button>
      <input
        ref={setFileInputNode}
        className="sr-only"
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={handleFileChange}
        aria-label="Browse files"
      />
      {selectedFile && (
        <div className="selected-file-row">
          <FileText size={18} strokeWidth={1.6} aria-hidden="true" />
          <span className="selected-file-meta">
            <strong>{selectedFile.name}</strong>
            <small>{formatBytes(selectedFile.size)}</small>
          </span>
          <button type="button" className="browse-button extract-button" disabled={status === 'uploading'} onClick={handleUpload}>
            {status === 'uploading' ? 'Extracting...' : 'Extract Text'}
          </button>
        </div>
      )}
      {message && <p className={`upload-note extraction-status ${status}`}>{message}</p>}
      {extraction && (
        <div className="extraction-preview">
          <dl>
            <div><dt>Type</dt><dd>{(extraction.file_type || 'unsupported').toUpperCase()}</dd></div>
            <div><dt>Size</dt><dd>{formatBytes(extraction.size_bytes)}</dd></div>
            {extraction.page_count ? <div><dt>Pages</dt><dd>{extraction.page_count}</dd></div> : null}
            <div><dt>Text</dt><dd>{extraction.character_count || 0} chars</dd></div>
          </dl>
          {preview ? (
            <>
              <pre>{preview}{previewText.length > previewLimit ? '...' : ''}</pre>
              {previewText.length > 1200 && (
                <button type="button" className="preview-toggle" onClick={() => setExpanded((value) => !value)}>
                  {expanded ? 'Show Less' : 'Show More'}
                </button>
              )}
            </>
          ) : null}
          {previewText && (
            <button type="button" className="browse-button extract-button" disabled={factStatus === 'loading'} onClick={handleIdentifyFacts}>
              {factStatus === 'loading' ? 'Identifying...' : 'Identify Key Facts'}
            </button>
          )}
        </div>
      )}
      {factMessage && <p className={`upload-note extraction-status ${factStatus}`}>{factMessage}</p>}
      {editableFacts && (
        <div className="document-facts-review">
          <h4>Facts I understood</h4>
          <p>Review these as case facts from your document, not legal sources.</p>
          <div className="fact-type-row">
            <span>Document Type</span>
            <strong>{(editableFacts.document_type || 'unknown').replaceAll('_', ' ')}</strong>
          </div>
          {editableFacts.document_summary && <p className="fact-summary">{editableFacts.document_summary}</p>}
          {factCategoriesForDisplay.map(({ key, label }) => (
            <FactCategory
              key={key}
              label={label}
              items={editableFacts[key] || []}
              onChange={(index, value) => handleFactChange(key, index, value)}
              onRemove={(index) => handleRemoveFact(key, index)}
            />
          ))}
          <button type="button" className="browse-button extract-button" disabled={factStatus === 'confirming'} onClick={handleConfirmFacts}>
            {factStatus === 'confirming' ? 'Confirming...' : 'Confirm Facts'}
          </button>
          {factStatus === 'confirmed' && (
            <button type="button" className="browse-button extract-button" onClick={() => { window.location.hash = '#/ask'; }}>
              Ask a legal question using these facts
            </button>
          )}
        </div>
      )}
    </section>
  );
}

const factCategoriesForDisplay = [
  { key: 'parties', label: 'Parties' },
  { key: 'dates', label: 'Important Dates' },
  { key: 'amounts', label: 'Amounts' },
  { key: 'identifiers', label: 'Identifiers' },
  { key: 'locations', label: 'Locations' },
  { key: 'important_terms', label: 'Important Terms' },
  { key: 'events', label: 'Events' },
  { key: 'notices_or_demands', label: 'Notices or Demands' },
  { key: 'other_facts', label: 'Other Facts' },
  { key: 'uncertain_items', label: 'Uncertain Items' }
];

function FactCategory({ label, items, onChange, onRemove }) {
  if (!items.length) return null;
  return (
    <div className="fact-category">
      <h5>{label}</h5>
      {items.map((item, index) => (
        <div className="fact-item" key={`${item.label}-${index}`}>
          <label>
            <span>{item.label || 'Fact'}</span>
            <input value={item.value || ''} onChange={(event) => onChange(index, event.target.value)} />
          </label>
          <small>{item.source_page ? `Document evidence: page ${item.source_page}` : 'Document evidence'}{item.confidence ? ` - ${item.confidence}` : ''}</small>
          {item.source_excerpt && <blockquote>{item.source_excerpt}</blockquote>}
          <button type="button" className="preview-toggle" onClick={() => onRemove(index)}>Remove</button>
        </div>
      ))}
    </div>
  );
}

async function safeJsonResponse(response) {
  const rawBody = await response.text();
  if (!rawBody) return null;
  try {
    return JSON.parse(rawBody);
  } catch (error) {
    console.error('Failed to parse JSON response', { error, status: response.status, rawBody });
    return null;
  }
}

function documentExtractionMessage(result) {
  if (result.status === 'success') {
    return 'Text extracted successfully. This is a preview only; it has not been added to the legal corpus.';
  }
  if (result.status === 'partial') {
    return result.warnings?.[0] || 'Some text was extracted, but the document may need review.';
  }
  if (result.status === 'ocr_required') {
    return 'This document appears scanned or image-based. OCR is not available in this phase.';
  }
  if (result.status === 'unsupported') {
    return 'This file type is not supported yet. Please upload PDF, DOCX, or TXT.';
  }
  return result.warnings?.[0] || 'Text extraction failed for this document.';
}

function documentFactMessage(result) {
  if (result.status === 'success') {
    return 'Key facts identified. Please review and confirm them before using them elsewhere.';
  }
  if (result.status === 'fact_extraction_unavailable') {
    return result.warnings?.[0] || 'Fact extraction is unavailable right now. The extracted text is still available for review.';
  }
  return result.warnings?.[0] || 'Legal Aid AI could not identify facts from this document.';
}

function formatBytes(bytes = 0) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB'];
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
}

function StorageOverview() {
  return (
    <section className="documents-side-card storage-card">
      <PanelCorners />
      <h3>Storage Overview</h3>
      <div className="storage-body">
        <div className="storage-donut" aria-label="24.8 percent storage used" />
        <div>
          <span>Used</span>
          <strong>2.48 GB</strong>
          <p>of 10 GB</p>
        </div>
      </div>
      <div className="storage-bar"><span /></div>
      <p className="storage-percent">24.8% used</p>
      <button type="button" className="storage-link">Manage Storage <ChevronRight size={16} /></button>
    </section>
  );
}

function QuickFilters() {
  const filters = [
    { label: 'Recently Uploaded', icon: Clock },
    { label: 'Large Files (> 5 MB)', icon: HardDrive },
    { label: 'Important Documents', icon: Star }
  ];

  return (
    <section className="documents-side-card quick-filters-card">
      <PanelCorners />
      <h3>Quick Filters</h3>
      <div className="quick-filter-list">
        {filters.map(({ label, icon: Icon }) => (
          <button type="button" key={label}>
            <Icon size={17} strokeWidth={1.7} />
            <span>{label}</span>
            <ChevronRight size={16} />
          </button>
        ))}
      </div>
    </section>
  );
}

function DocumentsUtilityColumn() {
  return (
    <aside className="documents-utility-column" aria-label="Document utilities">
      <UploadDocumentCard />
      <StorageOverview />
      <QuickFilters />
    </aside>
  );
}

function DocumentPreviewModal({ document, onClose }) {
  const extraction = document?.extraction || {};
  const previewText = extraction.text || '';
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="attachment-modal document-preview-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="document-preview-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label="Close document preview" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="modal-emblem">
          <FileText size={30} strokeWidth={1.55} />
        </div>
        <h3 id="document-preview-title">{document.filename}</h3>
        <p>{formatCaseDate(document.updated_at)}</p>
        {document.file_url && (
          <a className="document-file-link" href={document.file_url} target="_blank" rel="noreferrer">
            Open stored file
            <ArrowUpRight size={16} strokeWidth={1.7} />
          </a>
        )}
        <div className="preview-placeholder document-text-preview">
          <strong>Extracted text preview</strong>
          {previewText ? (
            <pre>{previewText.slice(0, 5000)}{previewText.length > 5000 ? '...' : ''}</pre>
          ) : (
            <span>No extracted text preview is available for this document.</span>
          )}
        </div>
      </section>
    </div>
  );
}

function DocumentRenameModal({ document, onClose, onSave }) {
  const [filename, setFilename] = React.useState(document?.filename || '');
  const [error, setError] = React.useState('');

  const submit = async (event) => {
    event.preventDefault();
    setError('');
    try {
      await onSave(document.id, filename);
      onClose();
    } catch (saveError) {
      setError(saveError.message || 'Could not rename this document.');
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="attachment-modal document-action-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rename-document-title"
        onMouseDown={(event) => event.stopPropagation()}
        onSubmit={submit}
      >
        <button type="button" className="modal-close" aria-label="Close rename dialog" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="modal-emblem">
          <Pencil size={30} strokeWidth={1.55} />
        </div>
        <h3 id="rename-document-title">Rename Document</h3>
        <label className="rename-document-field">
          <span>Document name</span>
          <input value={filename} onChange={(event) => setFilename(event.target.value)} autoFocus />
        </label>
        {error && <p className="document-action-error">{error}</p>}
        <div className="document-dialog-actions">
          <button type="button" className="document-outline-button" onClick={onClose}>Cancel</button>
          <button type="submit" className="case-open-button">Save</button>
        </div>
      </form>
    </div>
  );
}

function DocumentDeleteModal({ document, onClose, onDelete }) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="attachment-modal document-action-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-document-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label="Close delete dialog" onClick={onClose}>
          <X size={20} />
        </button>
        <div className="modal-emblem delete-emblem">
          <Trash2 size={30} strokeWidth={1.55} />
        </div>
        <h3 id="delete-document-title">Delete document?</h3>
        <p>This will permanently remove the uploaded document.</p>
        <div className="document-dialog-actions">
          <button type="button" className="document-outline-button" onClick={onClose}>Cancel</button>
          <button type="button" className="document-delete-button" onClick={() => onDelete(document.id)}>Delete</button>
        </div>
      </section>
    </div>
  );
}

function DocumentListCard({ document, onView, onRename, onDelete }) {
  return (
    <article className="document-list-card">
      <FileTypeIcon type={document.file_type} />
      <div className="document-list-main">
        <h3>{document.filename}</h3>
        <p>
          <Clock size={14} strokeWidth={1.7} />
          {formatCaseDate(document.updated_at || document.created_at)}
          <span className="document-list-size">{formatBytes(document.size_bytes)}</span>
        </p>
      </div>
      <div className="document-list-actions">
        <button
          type="button"
          className="case-rename-icon-button"
          aria-label={`Rename ${document.filename}`}
          onClick={() => onRename(document)}
        >
          <Pencil size={17} strokeWidth={1.8} />
        </button>
        <button
          type="button"
          className="case-delete-icon-button"
          aria-label={`Delete ${document.filename}`}
          onClick={() => onDelete(document)}
        >
          <Trash2 size={17} strokeWidth={1.8} />
        </button>
        <button type="button" className="case-open-button" onClick={() => onView(document.id)}>
          <Eye size={16} strokeWidth={1.8} />
          View
        </button>
      </div>
    </article>
  );
}

const DOCUMENTS_PAGE_SIZE = 20;

function DocumentsPage() {
  const [storedDocuments, setStoredDocuments] = React.useState([]);
  const [total, setTotal] = React.useState(0);
  const [hasMore, setHasMore] = React.useState(false);
  // Same reasoning as My Cases' grandTotal: "Delete All Documents" always deletes everything
  // regardless of the current search, so its button/confirmation must be driven by the true
  // unfiltered count, not a search-narrowed one.
  const [grandTotal, setGrandTotal] = React.useState(null);
  const [page, setPage] = React.useState(0);
  const [searchInput, setSearchInput] = React.useState('');
  const [search, setSearch] = React.useState('');
  const [status, setStatus] = React.useState('loading');
  const [previewDocument, setPreviewDocument] = React.useState(null);
  const [renameDocument, setRenameDocument] = React.useState(null);
  const [deleteDocument, setDeleteDocument] = React.useState(null);
  const [deleteAllRequested, setDeleteAllRequested] = React.useState(false);
  const [deleteStatus, setDeleteStatus] = React.useState('idle');
  const [notice, setNotice] = React.useState('');
  const uploadInputRef = React.useRef(null);

  const isFiltered = Boolean(search);

  React.useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const loadDocuments = React.useCallback(async () => {
    setStatus('loading');
    try {
      const params = new URLSearchParams({ limit: String(DOCUMENTS_PAGE_SIZE), offset: String(page * DOCUMENTS_PAGE_SIZE) });
      if (search) params.set('search', search);
      const requests = [fetch(`/api/documents?${params.toString()}`)];
      if (isFiltered) requests.push(fetch('/api/documents?limit=1'));
      const [response, grandTotalResponse] = await Promise.all(requests);
      const payload = await safeJsonResponse(response);
      if (!response.ok || !payload || !Array.isArray(payload.items)) {
        throw new Error('Documents could not be loaded.');
      }
      setStoredDocuments(payload.items);
      setTotal(payload.total);
      setHasMore(Boolean(payload.has_more));
      if (grandTotalResponse) {
        const grandPayload = await safeJsonResponse(grandTotalResponse);
        setGrandTotal(grandTotalResponse.ok && grandPayload ? grandPayload.total : null);
      } else {
        setGrandTotal(payload.total);
      }
      setStatus('ready');
    } catch (error) {
      console.error('Could not load documents', error);
      setStatus('error');
    }
  }, [page, search, isFiltered]);

  React.useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleView = async (documentId) => {
    try {
      const response = await fetch(`/api/documents/${encodeURIComponent(documentId)}`);
      const payload = await safeJsonResponse(response);
      if (!response.ok || !payload) {
        throw new Error('Could not open this document.');
      }
      setPreviewDocument(payload);
    } catch (error) {
      console.error('Could not view document', error);
    }
  };

  const handleRename = async (documentId, filename) => {
    const response = await fetch(`/api/documents/${encodeURIComponent(documentId)}/rename`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename })
    });
    const payload = await safeJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload?.detail || 'Could not rename this document.');
    }
    await loadDocuments();
  };

  const handleDelete = async (documentId) => {
    const response = await fetch(`/api/documents/${encodeURIComponent(documentId)}`, { method: 'DELETE' });
    const payload = await safeJsonResponse(response);
    if (!response.ok) {
      console.error('Could not delete document', payload?.detail);
      return;
    }
    setDeleteDocument(null);
    if (storedDocuments.length === 1 && page > 0) {
      setPage((current) => current - 1);
    } else {
      await loadDocuments();
    }
  };

  const confirmDeleteAllDocuments = async () => {
    setDeleteStatus('deleting_all');
    try {
      const response = await fetch('/api/documents', { method: 'DELETE' });
      const payload = await safeJsonResponse(response);
      if (!response.ok) {
        throw new Error(payload?.detail || 'Could not delete saved documents.');
      }
      setDeleteAllRequested(false);
      setNotice(`${payload?.deleted_count || 0} document${payload?.deleted_count === 1 ? '' : 's'} deleted.`);
      window.setTimeout(() => setNotice(''), 2200);
      setPage(0);
      setSearchInput('');
      setSearch('');
      await loadDocuments();
    } catch (error) {
      console.error('Could not delete all documents', error);
      setNotice(error.message || 'Could not delete saved documents.');
    } finally {
      setDeleteStatus('idle');
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / DOCUMENTS_PAGE_SIZE));

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="documents-content-frame">
        <DocumentsPageHeader />
        <section className="documents-panel persisted-documents-panel" aria-label="Uploaded documents">
          <PanelCorners />
          <UploadDocumentCard onUploaded={loadDocuments} externalInputRef={uploadInputRef} />

          <section className="persisted-documents-total-card" aria-label="Total uploaded documents">
            <div className="persisted-documents-total-icon">
              <FileText size={30} strokeWidth={1.45} />
            </div>
            <div>
              <p>{isFiltered ? 'Matching Documents' : 'Total Documents'}</p>
              <strong>{total}</strong>
              <span>{isFiltered ? `of ${grandTotal ?? '…'} total` : 'Everything you have uploaded, in one place'}</span>
            </div>
          </section>

          <div className="persisted-documents-search-toolbar">
            <label className="persisted-documents-search-field">
              <Search size={17} strokeWidth={1.8} aria-hidden="true" />
              <input
                type="search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search document filenames..."
                aria-label="Search uploaded documents"
              />
            </label>
          </div>

          <div className="persisted-documents-bulk-actions">
            <button
              type="button"
              className="document-delete-all-button"
              disabled={!grandTotal}
              onClick={() => setDeleteAllRequested(true)}
            >
              <Trash2 size={16} strokeWidth={1.8} />
              Delete All Documents
            </button>
          </div>

          <div className="persisted-documents-list-wrap">
            {notice && <p className="case-toast" role="status">{notice}</p>}
            {status === 'loading' && <p className="empty-documents">Loading documents...</p>}
            {status === 'error' && <p className="empty-documents">Documents could not be loaded right now.</p>}
            {status === 'ready' && storedDocuments.length === 0 && isFiltered && (
              <div className="persisted-documents-empty-state">
                <Search size={34} strokeWidth={1.45} />
                <h3>No documents match this search.</h3>
                <p>Try a different term, or clear the search.</p>
                <button
                  type="button"
                  className="ask-button"
                  onClick={() => { setSearchInput(''); setSearch(''); setPage(0); }}
                >
                  Clear search
                </button>
              </div>
            )}
            {status === 'ready' && storedDocuments.length === 0 && !isFiltered && (
              <div className="persisted-documents-empty-state">
                <FileText size={34} strokeWidth={1.45} />
                <h3>No documents uploaded yet.</h3>
                <p>Upload a PDF, DOCX, or TXT file to get started.</p>
                <button type="button" className="browse-button" onClick={() => uploadInputRef.current?.click()}>
                  Upload Document
                </button>
              </div>
            )}
            {status === 'ready' && storedDocuments.length > 0 && (
              <div className="persisted-documents-list">
                {storedDocuments.map((document) => (
                  <DocumentListCard
                    document={document}
                    key={document.id}
                    onView={handleView}
                    onRename={setRenameDocument}
                    onDelete={setDeleteDocument}
                  />
                ))}
              </div>
            )}
          </div>

          {status === 'ready' && total > DOCUMENTS_PAGE_SIZE && (
            <nav className="persisted-documents-pagination" aria-label="Uploaded documents pages">
              <button
                type="button"
                className="document-outline-button"
                onClick={() => setPage((current) => Math.max(0, current - 1))}
                disabled={page === 0}
              >
                Previous
              </button>
              <span>Page {page + 1} of {totalPages}</span>
              <button
                type="button"
                className="document-outline-button"
                onClick={() => setPage((current) => current + 1)}
                disabled={!hasMore}
              >
                Next
              </button>
            </nav>
          )}
        </section>
      </div>
      {previewDocument && <DocumentPreviewModal document={previewDocument} onClose={() => setPreviewDocument(null)} />}
      {renameDocument && <DocumentRenameModal document={renameDocument} onClose={() => setRenameDocument(null)} onSave={handleRename} />}
      {deleteDocument && <DocumentDeleteModal document={deleteDocument} onClose={() => setDeleteDocument(null)} onDelete={handleDelete} />}
      {deleteAllRequested && (
        <DeleteAllConfirmModal
          noun="document"
          description="including any extracted text and confirmed facts"
          count={grandTotal ?? total}
          filtered={isFiltered}
          status={deleteStatus}
          onCancel={() => setDeleteAllRequested(false)}
          onDelete={confirmDeleteAllDocuments}
        />
      )}
    </>
  );
}

function SummarizeDocumentPage() {
  const [documents, setDocuments] = React.useState([]);
  const [documentStatus, setDocumentStatus] = React.useState('loading');
  const [selectedDocumentId, setSelectedDocumentId] = React.useState('');
  const [selectedFile, setSelectedFile] = React.useState(null);
  const [uploadStatus, setUploadStatus] = React.useState('idle');
  const [uploadMessage, setUploadMessage] = React.useState('');
  const [summaryStatus, setSummaryStatus] = React.useState('idle');
  const [summaryResult, setSummaryResult] = React.useState(null);
  const fileInputRef = React.useRef(null);

  const loadDocuments = React.useCallback(async () => {
    setDocumentStatus('loading');
    try {
      // /api/documents is now paginated (same convention as /api/cases) -- this dropdown wants
      // to offer every document, so it asks for the largest page the API allows. Known
      // limitation, not addressed here: past DOCUMENTS_MAX_PAGE_SIZE documents this dropdown
      // would stop showing everything; a searchable/paginated picker would be a real feature,
      // out of scope for this pass.
      const response = await fetch('/api/documents?limit=100');
      const payload = await safeJsonResponse(response);
      if (!response.ok || !payload || !Array.isArray(payload.items)) {
        throw new Error('Documents could not be loaded.');
      }
      setDocuments(payload.items.filter((document) => ['pdf', 'docx', 'txt'].includes(document.file_type)));
      setDocumentStatus('ready');
    } catch (error) {
      console.error('Could not load documents for summary', error);
      setDocumentStatus('error');
    }
  }, []);

  React.useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const selectedDocument = documents.find((document) => String(document.id) === String(selectedDocumentId));

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setUploadStatus('idle');
    setUploadMessage('');
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadMessage('Choose a PDF, DOCX, or TXT file first.');
      return;
    }
    setUploadStatus('uploading');
    setUploadMessage('');
    setSummaryResult(null);
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
      const response = await fetch('/api/documents/extract', {
        method: 'POST',
        body: formData
      });
      const payload = await safeJsonResponse(response);
      if (!response.ok) {
        throw new Error(payload?.detail || 'This document could not be uploaded.');
      }
      if (payload?.status === 'ocr_required') {
        setUploadStatus('ocr_required');
        setUploadMessage('This appears to be a scanned PDF. OCR is not supported yet.');
      } else if (!payload?.document_id) {
        setUploadStatus('failed');
        setUploadMessage(documentExtractionMessage(payload || {}));
      } else {
        setUploadStatus('success');
        setUploadMessage('Document uploaded. You can now summarize it.');
        await loadDocuments();
        setSelectedDocumentId(String(payload.document_id));
      }
    } catch (error) {
      console.error('Summary document upload failed', error);
      setUploadStatus('failed');
      setUploadMessage(error.message || 'This document could not be uploaded.');
    }
  };

  const handleSummarize = async () => {
    if (!selectedDocumentId) {
      setSummaryStatus('failed');
      setSummaryResult({
        status: 'summary_unavailable',
        message: 'Select or upload a document first.'
      });
      return;
    }
    setSummaryStatus('loading');
    setSummaryResult(null);
    try {
      const response = await fetch(`/api/documents/${encodeURIComponent(selectedDocumentId)}/summarize`, {
        method: 'POST'
      });
      const payload = await safeJsonResponse(response);
      if (!response.ok) {
        throw new Error(payload?.detail || 'The summary could not be generated right now.');
      }
      setSummaryResult({
        ...(payload || {}),
        filename: selectedDocument?.filename || 'Selected document',
        document_id: selectedDocumentId
      });
      setSummaryStatus(payload?.status === 'success' ? 'success' : payload?.status || 'failed');
      if (payload?.status === 'success' && !payload.cached) {
        await loadDocuments();
      }
    } catch (error) {
      console.error('Document summary failed', error);
      setSummaryStatus('failed');
      setSummaryResult({
        status: 'summary_unavailable',
        filename: selectedDocument?.filename || 'Selected document',
        document_id: selectedDocumentId,
        message: error.message || 'The summary could not be generated right now. Please try again later.'
      });
    }
  };

  const resetSelection = () => {
    setSelectedDocumentId('');
    setSelectedFile(null);
    setUploadStatus('idle');
    setUploadMessage('');
    setSummaryStatus('idle');
    setSummaryResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="summary-content-frame">
        <section className="documents-page-header summarize-page-header">
          <div className="header-ornament-line" aria-hidden="true">
            <span />
            <i>◇</i>
          </div>
          <h2>Summarize Document</h2>
          <div className="header-ornament-line" aria-hidden="true">
            <i>◇</i>
            <span />
          </div>
          <p>Get a clear, plain-language summary of your legal document.</p>
          <PageDivider />
        </section>

        <section className="documents-panel summary-work-card" aria-label="Document summarization">
          <PanelCorners />
          <div className="summary-card-heading">
            <div className="summary-card-icon">
              <Sparkles size={28} strokeWidth={1.55} />
            </div>
            <div>
              <h3>Choose a document</h3>
              <p>Select one of your uploaded documents or upload a new PDF, DOCX, or TXT file.</p>
            </div>
          </div>

          <div className="summary-select-block">
            <label htmlFor="summary-document-select">Select an uploaded document</label>
            {documentStatus === 'loading' && <p className="summary-muted">Loading your documents...</p>}
            {documentStatus === 'error' && <p className="summary-error">Documents could not be loaded right now.</p>}
            {documentStatus === 'ready' && documents.length === 0 && (
              <p className="summary-muted">No uploaded documents found. Upload a PDF, DOCX, or TXT file to get started.</p>
            )}
            {documentStatus === 'ready' && documents.length > 0 && (
              <select
                id="summary-document-select"
                value={selectedDocumentId}
                onChange={(event) => {
                  setSelectedDocumentId(event.target.value);
                  setSummaryResult(null);
                  setSummaryStatus('idle');
                }}
              >
                <option value="">Select an uploaded document</option>
                {documents.map((document) => (
                  <option value={document.id} key={document.id}>
                    {document.filename}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="summary-upload-block">
            <span>Upload a new document</span>
            <button type="button" className="summary-upload-drop" onClick={() => fileInputRef.current?.click()}>
              <UploadCloud size={30} strokeWidth={1.45} />
              <strong>{selectedFile ? selectedFile.name : 'Browse PDF, DOCX, or TXT'}</strong>
              <small>Max size follows the existing upload limit.</small>
            </button>
            <input
              ref={fileInputRef}
              className="sr-only"
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              aria-label="Upload document for summary"
            />
            <button
              type="button"
              className="document-outline-button summary-upload-button"
              disabled={!selectedFile || uploadStatus === 'uploading'}
              onClick={handleUpload}
            >
              {uploadStatus === 'uploading' ? 'Uploading...' : 'Upload Document'}
            </button>
            {uploadMessage && <p className={`summary-status-text ${uploadStatus}`}>{uploadMessage}</p>}
          </div>

          <div className="summary-cta-area">
            {summaryStatus === 'loading' ? (
              <div className="summary-loading-state">
                <span className="summary-spinner" aria-hidden="true" />
                <strong>Generating your summary...</strong>
                <p>This may take a few seconds.</p>
              </div>
            ) : (
              <button
                type="button"
                className="ask-button summary-primary-button"
                disabled={!selectedDocumentId}
                onClick={handleSummarize}
              >
                <Sparkles size={17} strokeWidth={1.7} />
                Summarize Document
              </button>
            )}
          </div>
        </section>

        {summaryResult && (
          <section className={`documents-panel summary-result-card ${summaryResult.status === 'success' ? 'success' : 'failed'}`}>
            <PanelCorners />
            <div className="summary-result-header">
              <FileText size={25} strokeWidth={1.55} />
              <div>
                <h3>Document Summary</h3>
                <p>{summaryResult.filename}</p>
              </div>
            </div>
            {summaryResult.status === 'success' && summaryResult.summary ? (
              <div className="summary-result-text">{summaryResult.summary}</div>
            ) : (
              <p className="summary-error">{summaryResult.message || summaryStatusMessage(summaryResult.status)}</p>
            )}
            <div className="summary-disclaimer">
              <Info size={18} strokeWidth={1.7} />
              <p>This summary is based only on the uploaded document and is provided for general understanding. It is not legal advice.</p>
            </div>
            <div className="summary-result-actions">
              {summaryResult.document_id && (
                <a
                  className="document-outline-button"
                  href={`/api/documents/${encodeURIComponent(summaryResult.document_id)}/file`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Eye size={16} strokeWidth={1.7} />
                  View Original Document
                </a>
              )}
              <button type="button" className="document-outline-button" onClick={resetSelection}>
                Choose Another Document
              </button>
            </div>
          </section>
        )}
      </div>
    </>
  );
}

function summaryStatusMessage(status) {
  if (status === 'ocr_required') {
    return 'This appears to be a scanned PDF. OCR is not supported yet.';
  }
  if (status === 'no_extracted_text') {
    return "We couldn't find readable text in this document.";
  }
  if (status === 'document_too_long_for_summary') {
    return 'This document is too long to summarize safely in this version.';
  }
  return 'The summary could not be generated right now. Please try again later.';
}

const aboutFeatures = [
  ['Ask a Question', 'Describe your issue in plain words and get an answer grounded in real legal sources.'],
  ['My Cases', 'Save a conversation and pick it up again later.'],
  ['Documents', 'Upload a notice, receipt, or contract and pull out the key facts.'],
  ['Summarize Document', 'Get a short, plain-language summary of a legal document.'],
  ['Know Your Rights', 'Browse common rights and the laws behind them, by topic.'],
  ['Schemes', 'Find government schemes and services you may be able to use.']
];

function AboutUsPage() {
  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line"><span /><i>◇</i></div>
          <h2>About Us</h2>
          <div className="header-ornament-line"><i>◇</i><span /></div>
          <p>Plain-language legal help for everyday problems in India.</p>
          <PageDivider />
        </header>

        <section className="rights-panel">
          <h3>What is Legal Aid AI?</h3>
          <p>
            A free tool that explains your legal rights in simple words, helps you prepare
            complaints, and points you to the right authority. It provides legal information,
            not professional legal advice.
          </p>
        </section>

        <section className="rights-panel">
  <h3>Why Trust This?</h3>

  <p>
    Legal Aid AI is designed to ground its answers in a curated legal
    corpus rather than relying only on general AI knowledge.
  </p>

  <ul>
    <li>
      <strong>Acts and legislation</strong> — We use applicable Indian
      legislation and legal documents included in our verified corpus.
    </li>

    <li>
      <strong>Government sources</strong> — Where available, we rely on
      official government portals and public legal resources.
    </li>

    <li>
      <strong>Source-backed answers</strong> — Answers can include the
      legal documents and excerpts used by the system.
    </li>
  </ul>

  <p>
    Examples of sources used in the current project include the
    Consumer Protection Act, 2019, Constitution of India,
    Right to Information Act, 2005, and Legal Services Authorities
    Act, 1987.
  </p>
</section>

<section className="rights-panel">
  <h3>Who This Helps</h3>

  <p>
    Legal Aid AI is designed for people who need to understand a
    legal issue before deciding what to do next.
  </p>

  <ul>
    <li>Consumers dealing with defective goods or poor services</li>
    <li>Tenants facing common tenancy-related disputes</li>
    <li>People trying to understand a legal notice</li>
    <li>People looking for information about their legal rights</li>
    <li>People looking for information about legal aid and public services</li>
  </ul>
</section>

<section className="rights-panel">
  <h3>Current Coverage</h3>

  <p>
    Legal Aid AI currently focuses on selected areas of legal
    information rather than attempting to cover every area of Indian law.
  </p>

  <ul>
    <li>Consumer rights and common consumer issues</li>
    <li>Tenancy-related issues</li>
    <li>Cyber-related issues</li>
    <li>Constitutional and public-authority matters</li>
    <li>Legal aid and access-to-justice resources</li>
  </ul>

  <p>
    Coverage may vary by topic and jurisdiction. Additional legal areas
    and sources may be added as the project develops.
  </p>
</section>

        <section className="rights-panel">
          <h3>What you can do here</h3>
          <ul>
            {aboutFeatures.map(([name, detail]) => (
              <li key={name}><strong>{name}</strong> — {detail}</li>
            ))}
          </ul>
        </section>

        <section className="rights-panel">
          <h3>How it works</h3>
          <ol>
            <li>You describe the problem in your own words.</li>
            <li>We search official legal sources and government material.</li>
            <li>You get a short answer, suggested next steps, and where to go.</li>
          </ol>
        </section>

       <section className="rights-panel">
  <h3>Privacy & Data</h3>

  <p>
    We take privacy seriously, especially because legal questions and
    uploaded documents may contain sensitive information.
  </p>

  <ul>
    <li>Only provide information that is necessary for your question.</li>
    <li>Avoid sharing passwords, financial credentials, or unnecessary personal information.</li>
    <li>Uploaded documents should be reviewed before submission to remove information you do not want processed.</li>
  </ul>

  <p>
    See the project's privacy policy and technical documentation for
    details about how data is handled.
  </p>
</section>

        <section className="rights-panel">
  <h3>Frequently Asked Questions</h3>

  <h4>Is Legal Aid AI free?</h4>
  <p>
    Yes. Legal Aid AI is designed to provide accessible legal information
    without requiring you to consult a lawyer for every basic question.
  </p>

  <h4>Does Legal Aid AI replace a lawyer?</h4>
  <p>
    No. It provides general legal information and guidance. It does not
    replace a qualified lawyer or represent you in court.
  </p>

  <h4>Can I use it for every legal problem?</h4>
  <p>
    No. The system covers selected legal areas and sources. It may not
    contain every law, case, or recent amendment.
  </p>

  <h4>Should I rely on its answer for an important legal matter?</h4>
  <p>
    For serious or time-sensitive matters, verify the information with
    an official source or qualified legal professional.
  </p>
</section>
      </div>
    </>
  );
}

const schemes = [
  {
    name: 'Free Legal Aid (NALSA)',
    detail: 'Free legal services for women, children, SC/ST, persons with disabilities, and people below the income limit.',
    href: 'https://nalsa.gov.in'
  },
  {
    name: 'National Consumer Helpline',
    detail: 'Register complaints against sellers and service providers. Helpline 1915.',
    href: 'https://consumerhelpline.gov.in'
  },
  {
    name: 'Cyber Crime Reporting Portal',
    detail: 'Report online fraud, financial scams, and cyber harassment. Helpline 1930.',
    href: 'https://cybercrime.gov.in'
  },
  {
    name: 'Tele-Law',
    detail: 'Free advice from panel lawyers through Common Service Centres.',
    href: 'https://tele-law.in'
  },
  {
    name: 'e-Daakhil',
    detail: 'File consumer cases online without visiting the commission.',
    href: 'https://edaakhil.nic.in'
  },
  {
    name: 'State Legal Services Authority',
    detail: 'District Lok Adalats and mediation for quick, low-cost settlement of disputes.',
    href: ''
  }
];

function OtherLegalAidServices() {
  return (
    <section className="rights-panel">
      <h3>Other free legal-aid services</h3>
      <div className="rights-category-list">
        {schemes.map((scheme) => {
          const Wrapper = scheme.href ? 'a' : 'div';
          const linkProps = scheme.href
            ? { href: scheme.href, target: '_blank', rel: 'noreferrer' }
            : {};
          return (
            <Wrapper className="rights-source-card" key={scheme.name} {...linkProps}>
              <FileText size={22} strokeWidth={1.5} />
              <span>
                <strong>{scheme.name}</strong>
                <small>{scheme.detail}</small>
              </span>
              {scheme.href ? <ArrowUpRight size={16} strokeWidth={1.7} /> : <span />}
            </Wrapper>
          );
        })}
      </div>
    </section>
  );
}

function ComplaintDrafterPage() {
  const [scenario, setScenario] = React.useState(null);
  const [submitting, setSubmitting] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState(null);
  // The field this error concerns, read directly off ApiError.field (the backend's own
  // structured `field` response key -- see complaints/api.js and complaint_drafter_router.py).
  // Not derived from the message text.
  const [errorField, setErrorField] = React.useState(null);
  const [draft, setDraft] = React.useState(null); // { intake, response }

  async function handleSubmit(intake) {
    setSubmitting(true);
    setErrorMessage(null);
    setErrorField(null);
    try {
      const response = await generateDraft(scenario, intake);
      setDraft({ intake, response });
    } catch (error) {
      if (error instanceof ComplaintApiError) {
        setErrorMessage(error.message);
        setErrorField(error.field);
      } else {
        setErrorMessage('Something went wrong while drafting this complaint. Please try again.');
        setErrorField(null);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleChangeScenario(nextScenario) {
    setScenario(nextScenario);
    setDraft(null);
    setErrorMessage(null);
    setErrorField(null);
  }

  function handleBackToForm() {
    setDraft(null);
    setErrorMessage(null);
    setErrorField(null);
  }

  const activeScenario = SCENARIOS.find((item) => item.id === scenario);

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line"><span /><i>◇</i></div>
          <h2>Draft a Complaint</h2>
          <div className="header-ornament-line"><i>◇</i><span /></div>
          <p>
            Answer a few questions and get a ready-to-file complaint document. The wording comes
            from a fixed legal template filled in with your answers — it is not written by AI.
          </p>
          <PageDivider />
        </header>

        {!scenario ? (
          <ScenarioPicker onSelect={handleChangeScenario} />
        ) : draft ? (
          <DraftPreview scenario={scenario} intake={draft.intake} draft={draft.response} onBack={handleBackToForm} />
        ) : (
          <section className="rights-panel">
            <button type="button" className="rights-back-button" onClick={() => handleChangeScenario(null)}>
              ← Choose a different complaint type
            </button>
            <h3>{activeScenario?.title}</h3>
            <ComplaintIntakeForm
              scenario={scenario}
              submitting={submitting}
              errorMessage={errorMessage}
              errorField={errorField}
              onSubmit={handleSubmit}
            />
          </section>
        )}

        <RightsDisclaimerCard text="This tool fills a fixed legal template from what you enter — it does not generate or invent legal wording. Always review the finished document, and consult a lawyer before filing anything beyond routine drafting." />
      </div>
    </>
  );
}

function SchemesPage() {
  const [screen, setScreen] = React.useState('form');
  const [profile, setProfile] = React.useState({});
  const [results, setResults] = React.useState([]);
  const [submitting, setSubmitting] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState(null);

  async function handleSubmit(nextProfile) {
    setProfile(nextProfile);
    setSubmitting(true);
    setErrorMessage(null);
    try {
      const matches = await postMatch(nextProfile);
      setResults(matches);
      setScreen('results');
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError
          ? error.message
          : 'Something went wrong while searching. Please try again.'
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line"><span /><i>◇</i></div>
          <h2>Schemes</h2>
          <div className="header-ornament-line"><i>◇</i><span /></div>
          <p>
            Answer a few optional questions to see which Indian government schemes you may
            qualify for. Nothing is saved and no sign-in is needed.
          </p>
          <PageDivider />
        </header>

        {screen === 'form' ? (
          <>
            <section className="rights-panel">
              <h3>Find schemes for you</h3>
              <IntakeForm
                initialProfile={profile}
                submitting={submitting}
                errorMessage={errorMessage}
                onSubmit={handleSubmit}
              />
            </section>
            <OtherLegalAidServices />
          </>
        ) : (
          <ResultsList results={results} onRefine={() => setScreen('form')} />
        )}

        <RightsDisclaimerCard text="Eligibility shown here is an automated estimate, not an official decision. Always confirm on the scheme's official government website before applying." />
      </div>
    </>
  );
}

function RevealSection({ className = '', id, children }) {
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
    <section ref={ref} id={id} className={`reveal ${visible ? 'is-visible' : ''} ${className}`.trim()}>
      {children}
    </section>
  );
}

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

function jumpToSection(id) {
  const el = typeof document !== 'undefined' ? document.getElementById(id) : null;
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function HomeInfoSections() {
  return (
    <div className="home-info">
      <RevealSection className="home-lead">
        <h3 className="home-section-title">What you can do here</h3>
        <div className="home-jump">
          {homeSections.map((section) => (
            <button
              type="button"
              key={section.id}
              className="home-jump-link"
              onClick={() => jumpToSection(`sec-${section.id}`)}
            >
              {section.label}
            </button>
          ))}
        </div>
      </RevealSection>

      <div className="home-feature-list">
        {homeSections.map((section) => (
          <RevealSection id={`sec-${section.id}`} className="home-feature" key={section.id}>
            <div className="home-feature-text">
              <span className="home-feature-kicker">{section.kicker}</span>
              <h3>{section.label}</h3>
              <p>{section.summary}</p>
              <a className="home-cta" href={section.href}>
                <span>{section.cta}</span>
                <ChevronRight size={16} strokeWidth={2} />
              </a>
            </div>
            <div className="home-feature-panel">
              <ul>
                {section.points.map((point) => (
                  <li key={point}>
                    <Check size={15} strokeWidth={2.6} />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
              {section.topics && (
                <div className="home-feature-topics">
                  {section.topics.map((topic) => (
                    <span key={topic}>{topic}</span>
                  ))}
                </div>
              )}
            </div>
          </RevealSection>
        ))}
      </div>

      <div className="home-marquee" aria-hidden="true">
        <div className="home-marquee-track">
          {[0, 1].map((copy) => (
            <span key={copy}>
              Consumer rights <i>◆</i> Tenancy <i>◆</i> Cyber fraud <i>◆</i> Consumer courts
              <i>◆</i> RTI <i>◆</i> Free legal aid <i>◆</i> Know your rights <i>◆</i>
            </span>
          ))}
        </div>
      </div>

      <RevealSection className="home-steps-section">
        <h3 className="home-section-title">How it works</h3>
        <ol className="home-steps">
          <li><span>1</span>Describe the problem in your own words.</li>
          <li><span>2</span>We search official legal sources and government material.</li>
          <li><span>3</span>You get a short answer, next steps, and where to go.</li>
        </ol>
      </RevealSection>

      <RevealSection className="home-assure">
        <div className="home-assure-card">
          <span className="home-assure-icon"><LockKeyhole size={24} strokeWidth={1.6} /></span>
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
        <div className="home-assure-card">
          <span className="home-assure-icon"><Bot size={24} strokeWidth={1.6} /></span>
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
          <a className="home-assure-cta" href="#/schemes">See all schemes <ChevronRight size={14} strokeWidth={2} /></a>
        </div>
      </RevealSection>
    </div>
  );
}

function HomeFooter() {
  return (
    <footer className="home-footer">
      <div className="home-footer-inner">
        <div className="home-footer-brand">
          <div className="home-footer-mark"><Scale size={22} strokeWidth={1.5} /></div>
          <div>
            <strong>Legal Aid AI</strong>
            <span>Your Rights. Our Guidance.</span>
          </div>
        </div>
        <p className="home-footer-about">
          A free tool that explains your legal rights in simple words, helps you prepare
          complaints, and points you to the right authority. It gives legal information,
          not professional legal advice.
        </p>
        <nav className="home-footer-links" aria-label="Footer">
          <a href="#/ask">Ask a Question</a>
          <a href="#/rights">Know Your Rights</a>
          <a href="#/schemes">Schemes</a>
          <a href="#/about">About Us</a>
        </nav>
      </div>
    </footer>
  );
}

function InteractiveCursor() {
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
    body.classList.add('has-custom-cursor');

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
      body.classList.remove('cursor-hidden');
    };
    const onOut = (event) => {
      if (!event.relatedTarget && !event.toElement) body.classList.add('cursor-hidden');
    };
    const onDown = () => body.classList.add('cursor-down');
    const onUp = () => body.classList.remove('cursor-down');

    const interactiveSel =
      'a, button, input, textarea, select, [role="button"], .feature-card, .category-pill, .home-feature-panel, .home-jump-link, .home-cta, .source-card, .rights-source-card';
    const onOver = (event) => {
      const t = event.target;
      if (t && t.closest && t.closest(interactiveSel)) body.classList.add('cursor-active');
    };
    const onLeaveInteractive = (event) => {
      const t = event.target;
      if (t && t.closest && t.closest(interactiveSel)) body.classList.remove('cursor-active');
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
    const magnets = Array.from(document.querySelectorAll('.home-cta'));
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
      body.classList.remove('has-custom-cursor', 'cursor-hidden', 'cursor-active', 'cursor-down');
    };
  }, []);

  return (
    <>
      <div ref={ringRef} className="cursor-ring" aria-hidden="true" />
      <div ref={dotRef} className="cursor-dot" aria-hidden="true" />
    </>
  );
}

function HomePage() {
  return (
    <>
      <InteractiveCursor />
      <BackgroundArt />
      <HeaderControls />
      <div className="content-frame">
        <Hero />
        <QueryBox />
        <CategoryPills />
        <FeatureCards />
        <HomeInfoSections />
      </div>
      <HomeFooter />
    </>
  );
}

const CASES_PAGE_SIZE = 20;
const CASE_DOMAIN_OPTIONS = [
  { value: 'consumer', label: 'Consumer' },
  { value: 'cyber', label: 'Cyber' },
  { value: 'tenancy', label: 'Tenancy' },
  { value: 'constitutional_public_authority', label: 'Public Authority' }
];

function MyCasesPage() {
  const [cases, setCases] = React.useState([]);
  const [total, setTotal] = React.useState(0);
  const [hasMore, setHasMore] = React.useState(false);
  // grandTotal is the TRUE, unfiltered case count -- kept separate from `total` (which reflects
  // the current search/domain filter) specifically for "Delete All Cases": that action always
  // deletes every case regardless of any active filter, so its button/confirmation must never
  // be driven by a filtered count (a search matching 3 of 957 cases must not make the button
  // look like -- or claim to -- delete only 3).
  const [grandTotal, setGrandTotal] = React.useState(null);
  const [page, setPage] = React.useState(0);
  const [searchInput, setSearchInput] = React.useState('');
  const [search, setSearch] = React.useState('');
  const [domain, setDomain] = React.useState('');
  const [status, setStatus] = React.useState('loading');
  const [caseToDelete, setCaseToDelete] = React.useState(null);
  const [caseToRename, setCaseToRename] = React.useState(null);
  const [deleteAllRequested, setDeleteAllRequested] = React.useState(false);
  const [deleteStatus, setDeleteStatus] = React.useState('idle');
  const [notice, setNotice] = React.useState('');

  const isFiltered = Boolean(search || domain);

  // Debounce the search box so it doesn't fire a request on every keystroke.
  React.useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const loadCases = React.useCallback(async () => {
    setStatus('loading');
    try {
      const params = new URLSearchParams({ limit: String(CASES_PAGE_SIZE), offset: String(page * CASES_PAGE_SIZE) });
      if (search) params.set('search', search);
      if (domain) params.set('domain', domain);
      const requests = [fetch(`/api/cases?${params.toString()}`)];
      // Only fetch the true unfiltered total when actually filtered -- when not filtered,
      // `total` from the main request already IS the grand total, no second request needed.
      if (isFiltered) requests.push(fetch('/api/cases?limit=1'));
      const [response, grandTotalResponse] = await Promise.all(requests);
      const payload = await safeJsonResponse(response);
      if (!response.ok || !payload || !Array.isArray(payload.items)) {
        throw new Error('Could not load saved cases.');
      }
      setCases(payload.items);
      setTotal(payload.total);
      setHasMore(Boolean(payload.has_more));
      if (grandTotalResponse) {
        const grandPayload = await safeJsonResponse(grandTotalResponse);
        setGrandTotal(grandTotalResponse.ok && grandPayload ? grandPayload.total : null);
      } else {
        setGrandTotal(payload.total);
      }
      setStatus('ready');
    } catch (error) {
      console.error('Could not load cases', error);
      setStatus('error');
    }
  }, [page, search, domain, isFiltered]);

  React.useEffect(() => {
    loadCases();
  }, [loadCases]);

  const openCase = (caseId) => {
    window.location.hash = `#/ask?case=${encodeURIComponent(caseId)}`;
  };

  const confirmDeleteCase = async () => {
    if (!caseToDelete) return;
    setDeleteStatus('deleting');
    try {
      const response = await fetch(`/api/cases/${encodeURIComponent(caseToDelete.id)}`, { method: 'DELETE' });
      const payload = await safeJsonResponse(response);
      if (!response.ok) {
        throw new Error(payload?.detail || 'Could not delete this case.');
      }
      setCaseToDelete(null);
      setNotice('Case deleted.');
      window.setTimeout(() => setNotice(''), 2200);
      // If that was the only case left on this page (and it's not the first page), step back a
      // page rather than land on a now-empty one.
      if (cases.length === 1 && page > 0) {
        setPage((current) => current - 1);
      } else {
        await loadCases();
      }
    } catch (error) {
      console.error('Could not delete case', error);
      setNotice(error.message || 'Could not delete this case.');
    } finally {
      setDeleteStatus('idle');
    }
  };

  const renameCase = async (savedCase, title) => {
    const response = await fetch(`/api/cases/${encodeURIComponent(savedCase.id)}/rename`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title })
    });
    const payload = await safeJsonResponse(response);
    if (!response.ok) {
      throw new Error(payload?.detail || 'Could not rename this case.');
    }
    setCaseToRename(null);
    setNotice('Case renamed.');
    window.setTimeout(() => setNotice(''), 2200);
    await loadCases();
  };

  const confirmDeleteAllCases = async () => {
    setDeleteStatus('deleting_all');
    try {
      const response = await fetch('/api/cases', { method: 'DELETE' });
      const payload = await safeJsonResponse(response);
      if (!response.ok) {
        throw new Error(payload?.detail || 'Could not delete saved cases.');
      }
      setDeleteAllRequested(false);
      setNotice(`${payload?.deleted_count || 0} case${payload?.deleted_count === 1 ? '' : 's'} deleted.`);
      window.setTimeout(() => setNotice(''), 2200);
      setPage(0);
      setSearchInput('');
      setSearch('');
      setDomain('');
      await loadCases();
    } catch (error) {
      console.error('Could not delete all cases', error);
      setNotice(error.message || 'Could not delete saved cases.');
    } finally {
      setDeleteStatus('idle');
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / CASES_PAGE_SIZE));

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="cases-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line"><span /><i>⌘</i></div>
          <h2>My Cases</h2>
          <div className="header-ornament-line"><i>⌘</i><span /></div>
          <p>Continue your previous legal conversations.</p>
          <PageDivider />
        </header>

        <section className="cases-total-card" aria-label="Total saved cases">
          <PanelCorners />
          <div className="cases-total-icon">
            <BriefcaseBusiness size={30} strokeWidth={1.45} />
          </div>
          <div>
            <p>{isFiltered ? 'Matching Cases' : 'Total Cases'}</p>
            <strong>{total}</strong>
            <span>
              {isFiltered
                ? `of ${grandTotal ?? '…'} total`
                : 'All your legal conversations in one place'}
            </span>
          </div>
        </section>

        <div className="cases-toolbar">
          <label className="cases-search-field">
            <Search size={17} strokeWidth={1.8} aria-hidden="true" />
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search case titles and first messages..."
              aria-label="Search saved cases"
            />
          </label>
          <select
            className="cases-domain-select"
            value={domain}
            onChange={(event) => { setDomain(event.target.value); setPage(0); }}
            aria-label="Filter by category"
          >
            <option value="">All categories</option>
            {CASE_DOMAIN_OPTIONS.map((option) => (
              <option value={option.value} key={option.value}>{option.label}</option>
            ))}
          </select>
        </div>

        <div className="cases-bulk-actions">
          <button
            type="button"
            className="case-delete-all-button"
            disabled={!grandTotal}
            onClick={() => setDeleteAllRequested(true)}
          >
            <Trash2 size={16} strokeWidth={1.8} />
            Delete All Cases
          </button>
        </div>

        <section className="cases-list" aria-label="Saved cases">
          {notice && <p className="case-toast" role="status">{notice}</p>}
          {status === 'loading' && <p className="cases-empty">Loading saved cases...</p>}
          {status === 'error' && <p className="cases-empty">Saved cases could not be loaded right now.</p>}
          {status === 'ready' && cases.length === 0 && isFiltered && (
            <div className="cases-empty-state">
              <Search size={34} strokeWidth={1.45} />
              <h3>No cases match this search.</h3>
              <p>Try a different term, or clear the search/category filter.</p>
              <button
                type="button"
                className="ask-button"
                onClick={() => { setSearchInput(''); setSearch(''); setDomain(''); setPage(0); }}
              >
                Clear filters
              </button>
            </div>
          )}
          {status === 'ready' && cases.length === 0 && !isFiltered && (
            <div className="cases-empty-state">
              <BriefcaseBusiness size={34} strokeWidth={1.45} />
              <h3>No saved cases yet.</h3>
              <p>Start a legal conversation and it will appear here.</p>
              <button type="button" className="ask-button" onClick={() => { window.location.hash = '#/ask'; }}>
                Ask a Question
              </button>
            </div>
          )}
          {status === 'ready' && cases.map((savedCase) => (
            <article className="case-list-card" key={savedCase.id}>
              <div className="case-list-icon" aria-hidden="true">
                <BriefcaseBusiness size={25} strokeWidth={1.45} />
              </div>
              <div className="case-list-main">
                <h3>{savedCase.title || 'Legal Question'}</h3>
                <p><Clock size={14} strokeWidth={1.7} />{formatCaseDate(savedCase.updated_at)}</p>
              </div>
              <div className="case-card-actions">
                <button
                  type="button"
                  className="case-rename-icon-button"
                  aria-label={`Rename ${savedCase.title || 'case'}`}
                  onClick={() => setCaseToRename(savedCase)}
                >
                  <Pencil size={17} strokeWidth={1.8} />
                </button>
                <button
                  type="button"
                  className="case-delete-icon-button"
                  aria-label={`Delete ${savedCase.title || 'case'}`}
                  onClick={() => setCaseToDelete(savedCase)}
                >
                  <Trash2 size={17} strokeWidth={1.8} />
                </button>
                <button type="button" className="case-open-button" onClick={() => openCase(savedCase.id)}>
                  Open Case
                  <ChevronRight size={16} strokeWidth={1.8} />
                </button>
              </div>
            </article>
          ))}
        </section>

        {status === 'ready' && total > CASES_PAGE_SIZE && (
          <nav className="cases-pagination" aria-label="Saved cases pages">
            <button
              type="button"
              className="document-outline-button"
              onClick={() => setPage((current) => Math.max(0, current - 1))}
              disabled={page === 0}
            >
              Previous
            </button>
            <span>Page {page + 1} of {totalPages}</span>
            <button
              type="button"
              className="document-outline-button"
              onClick={() => setPage((current) => current + 1)}
              disabled={!hasMore}
            >
              Next
            </button>
          </nav>
        )}
      </div>
      {caseToDelete && (
        <CaseDeleteModal
          savedCase={caseToDelete}
          status={deleteStatus}
          onCancel={() => setCaseToDelete(null)}
          onDelete={confirmDeleteCase}
        />
      )}
      {caseToRename && (
        <CaseRenameModal
          savedCase={caseToRename}
          onCancel={() => setCaseToRename(null)}
          onRename={renameCase}
        />
      )}
      {deleteAllRequested && (
        <DeleteAllConfirmModal
          noun="case"
          description="and their conversation history"
          count={grandTotal ?? total}
          filtered={isFiltered}
          status={deleteStatus}
          onCancel={() => setDeleteAllRequested(false)}
          onDelete={confirmDeleteAllCases}
        />
      )}
    </>
  );
}

function CaseRenameModal({ savedCase, onCancel, onRename }) {
  const [title, setTitle] = React.useState(savedCase.title || '');
  const [status, setStatus] = React.useState('idle');
  const [error, setError] = React.useState('');

  const submitRename = async (event) => {
    event.preventDefault();
    const nextTitle = title.trim();
    if (!nextTitle) {
      setError('Enter a case title.');
      return;
    }
    setStatus('saving');
    setError('');
    try {
      await onRename(savedCase, nextTitle);
    } catch (renameError) {
      setError(renameError.message || 'Could not rename this case.');
      setStatus('idle');
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <form
        className="attachment-modal document-action-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rename-case-title"
        onSubmit={submitRename}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label="Close rename case dialog" onClick={onCancel}>
          <X size={20} />
        </button>
        <div className="modal-emblem">
          <Pencil size={30} strokeWidth={1.55} />
        </div>
        <h3 id="rename-case-title">Rename Case</h3>
        <label className="rename-document-field">
          <span>Case title</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} autoFocus maxLength={80} />
        </label>
        {error && <p className="document-error">{error}</p>}
        <div className="document-dialog-actions">
          <button type="button" className="document-outline-button" onClick={onCancel} disabled={status === 'saving'}>Cancel</button>
          <button type="submit" className="case-open-button" disabled={status === 'saving'}>
            {status === 'saving' ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  );
}

function CaseDeleteModal({ savedCase, status, onCancel, onDelete }) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="attachment-modal document-action-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-case-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label="Close delete case dialog" onClick={onCancel}>
          <X size={20} />
        </button>
        <div className="modal-emblem delete-emblem">
          <Trash2 size={30} strokeWidth={1.55} />
        </div>
        <h3 id="delete-case-title">Delete case?</h3>
        <p>This will permanently delete “{savedCase.title || 'Legal Question'}” and its conversation history.</p>
        <div className="document-dialog-actions">
          <button type="button" className="document-outline-button" onClick={onCancel} disabled={status === 'deleting'}>Cancel</button>
          <button type="button" className="document-delete-button" onClick={onDelete} disabled={status === 'deleting'}>
            {status === 'deleting' ? 'Deleting...' : 'Delete Case'}
          </button>
        </div>
      </section>
    </div>
  );
}

/** Generic "delete everything" confirmation, shared by My Cases and Documents rather than
 * duplicating the same modal per page. `noun` is singular ("case" / "document"); plural is
 * formed by appending "s" -- true for both current callers. If a future caller needs irregular
 * pluralization, add an explicit `plural` prop rather than generalizing further speculatively.
 * `description` is the trailing clause explaining what else gets removed (e.g. "and their
 * conversation history" / "including any extracted text and confirmed facts"). */
function DeleteAllConfirmModal({ noun, description, count, filtered, status, onCancel, onDelete }) {
  const plural = `${noun}s`;
  const label = count === 1 ? noun : plural;
  const busy = status === 'deleting_all';
  const titleId = `delete-all-${plural}-title`;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="attachment-modal document-action-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label={`Close delete all ${plural} dialog`} onClick={onCancel}>
          <X size={20} />
        </button>
        <div className="modal-emblem delete-emblem">
          <Trash2 size={30} strokeWidth={1.55} />
        </div>
        <h3 id={titleId}>Delete all {plural}?</h3>
        <p>This will permanently delete {count} {label}{description ? ` ${description}` : ''}.</p>
        {filtered && (
          <p className="document-error">
            This deletes every saved {noun}, not just the ones matching your current search/filter.
          </p>
        )}
        <div className="document-dialog-actions">
          <button type="button" className="document-outline-button" onClick={onCancel} disabled={busy}>Cancel</button>
          <button type="button" className="document-delete-button" onClick={onDelete} disabled={busy}>
            {busy ? 'Deleting...' : `Delete All ${plural.charAt(0).toUpperCase()}${plural.slice(1)}`}
          </button>
        </div>
      </section>
    </div>
  );
}

function rightsIcon(iconName) {
  const icons = {
    shopping_cart: ShoppingCart,
    shield: ShieldCheck,
    home: Home,
    landmark: Landmark,
    file_text: FileText
  };
  return icons[iconName] || Scale;
}

function LegalAwarenessPage({ segments }) {
  if (segments[1] === 'source' && segments[2] && segments[3] === 'provision' && segments[4]) {
    return <RightsProvisionPage sourceId={segments[2]} provisionId={segments[4]} />;
  }
  if (segments[1] === 'source' && segments[2]) {
    return <RightsSourcePage sourceId={segments[2]} />;
  }
  if (segments[1]) {
    return <RightsCategoryPage categoryId={segments[1]} />;
  }
  return <RightsHomePage />;
}

function RightsHomePage() {
  const [categories, setCategories] = React.useState([]);
  const [status, setStatus] = React.useState('loading');
  const [searchInput, setSearchInput] = React.useState('');
  const [searchResults, setSearchResults] = React.useState(null); // null = no search run yet
  const [searchStatus, setSearchStatus] = React.useState('idle');

  React.useEffect(() => {
    let ignore = false;
    const loadCategories = async () => {
      try {
        const response = await fetch('/api/legal-awareness/categories');
        const payload = await safeJsonResponse(response);
        if (!response.ok || !Array.isArray(payload)) throw new Error('Could not load rights categories.');
        if (!ignore) {
          setCategories(payload);
          setStatus('ready');
        }
      } catch (error) {
        console.error('Could not load legal-awareness categories', error);
        if (!ignore) setStatus('error');
      }
    };
    loadCategories();
    return () => {
      ignore = true;
    };
  }, []);

  // Debounced search across every provision -- lets a result link straight to the matched
  // provision, skipping the category -> source -> provision browse.
  React.useEffect(() => {
    const query = searchInput.trim();
    if (!query) {
      setSearchResults(null);
      setSearchStatus('idle');
      return undefined;
    }
    setSearchStatus('loading');
    let ignore = false;
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/api/legal-awareness/search?q=${encodeURIComponent(query)}`);
        const payload = await safeJsonResponse(response);
        if (!response.ok || !payload || !Array.isArray(payload.results)) {
          throw new Error('Search failed.');
        }
        if (!ignore) {
          setSearchResults(payload.results);
          setSearchStatus('ready');
        }
      } catch (error) {
        console.error('Legal-awareness search failed', error);
        if (!ignore) setSearchStatus('error');
      }
    }, 350);
    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [searchInput]);

  const goToSearchResult = (result) => {
    window.location.hash = `#/rights/source/${result.source_id}/provision/${result.provision_id}`;
  };

  const popularTopics = [
    { label: 'Defective Product', category: 'consumer' },
    { label: 'Refund & Replacement', category: 'consumer' },
    { label: 'Online Fraud', category: 'cyber' },
    { label: 'Identity Misuse', category: 'cyber' },
    { label: 'Rent & Essential Services', category: 'tenancy' },
    { label: 'RTI Application', category: 'public_services' },
    { label: 'Free Legal Aid', category: 'public_services' }
  ];

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line"><span /><i>◇</i></div>
          <h2>Know Your Rights</h2>
          <div className="header-ornament-line"><i>◇</i><span /></div>
          <p>Understand important legal rights in simple words.</p>
          <PageDivider />
        </header>

        <section className="rights-section rights-search-section" aria-label="Search legal provisions">
          <h3>Search Provisions</h3>
          <label className="cases-search-field rights-search-field">
            <Search size={17} strokeWidth={1.8} aria-hidden="true" />
            <input
              type="search"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Search legal provisions -- e.g. refund, eviction, RTI..."
              aria-label="Search legal provisions"
            />
          </label>
          {searchStatus === 'loading' && <p className="rights-muted">Searching...</p>}
          {searchStatus === 'error' && <p className="rights-muted">Search could not be completed right now.</p>}
          {searchStatus === 'ready' && searchResults.length === 0 && (
            <p className="rights-muted">No provisions match &ldquo;{searchInput.trim()}&rdquo;.</p>
          )}
          {searchStatus === 'ready' && searchResults.length > 0 && (
            <div className="rights-source-list">
              {searchResults.map((result) => (
                <button
                  type="button"
                  className="rights-source-card"
                  key={`${result.source_id}-${result.provision_id}`}
                  onClick={() => goToSearchResult(result)}
                >
                  <FileText size={23} strokeWidth={1.45} />
                  <span>
                    <strong>{result.provision_label} — {result.provision_title}</strong>
                    <small>{result.category_title} · {result.source_short_title}</small>
                  </span>
                  <ChevronRight size={18} strokeWidth={1.8} />
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="rights-section" aria-label="Explore legal rights by category">
          <h3>Explore by Category</h3>
          <div className="rights-category-list">
            {status === 'loading' && <p className="rights-muted">Loading rights categories...</p>}
            {status === 'error' && <p className="rights-muted">Rights categories could not be loaded right now.</p>}
            {status === 'ready' && categories.map((category) => {
              const Icon = rightsIcon(category.icon);
              return (
                <article className="rights-category-card" key={category.id}>
                  <div className="rights-card-icon"><Icon size={31} strokeWidth={1.45} /></div>
                  <div>
                    <h3>{category.title}</h3>
                    <p>{category.description}</p>
                  </div>
                  <button type="button" className="rights-learn-button" onClick={() => { window.location.hash = `#/rights/${category.id}`; }}>
                    Learn More
                    <ArrowUpRight size={16} strokeWidth={1.8} />
                  </button>
                </article>
              );
            })}
          </div>
        </section>

        <section className="rights-section popular-topics-section">
          <h3>Popular Topics</h3>
          <div className="popular-topic-list">
            {popularTopics.map((topic) => (
              <button type="button" key={topic.label} onClick={() => { window.location.hash = `#/rights/${topic.category}`; }}>
                <FolderOpen size={15} strokeWidth={1.7} />
                {topic.label}
              </button>
            ))}
          </div>
        </section>

        <RightsDisclaimerCard />
      </div>
    </>
  );
}

function RightsCategoryPage({ categoryId }) {
  const [category, setCategory] = React.useState(null);
  const [status, setStatus] = React.useState('loading');

  React.useEffect(() => {
    let ignore = false;
    const loadCategory = async () => {
      try {
        const response = await fetch(`/api/legal-awareness/categories/${encodeURIComponent(categoryId)}`);
        const payload = await safeJsonResponse(response);
        if (!response.ok || !payload) throw new Error('Could not load this rights category.');
        if (!ignore) {
          setCategory(payload);
          setStatus('ready');
        }
      } catch (error) {
        console.error('Could not load legal-awareness category', error);
        if (!ignore) setStatus('error');
      }
    };
    loadCategory();
    return () => {
      ignore = true;
    };
  }, [categoryId]);

  if (status !== 'ready') {
    return <RightsLoadingState message={status === 'error' ? 'This category could not be loaded.' : 'Loading category...'} />;
  }

  const Icon = rightsIcon(category.icon);
  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <button type="button" className="rights-back-button" onClick={() => { window.location.hash = '#/rights'; }}>
          ← Back to Know Your Rights
        </button>
        <section className="rights-detail-hero">
          <div className="rights-card-icon rights-hero-icon"><Icon size={42} strokeWidth={1.35} /></div>
          <div>
            <h2>{category.title}</h2>
            <p>{category.description}</p>
          </div>
        </section>
        <PageDivider />

        {category.limitation && <div className="rights-limitation">{category.limitation}</div>}

        <RightsInfoSection title="What You Should Know" items={category.overview} />

        <section className="rights-panel">
          <h3>Common Issues</h3>
          <div className="rights-issue-grid">
            {category.common_issues.map((issue) => (
              <article key={issue.title}>
                <div className="rights-mini-icon"><Scale size={22} strokeWidth={1.45} /></div>
                <h4>{issue.title}</h4>
                <p>{issue.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="rights-panel">
          <h3>Relevant Legal Sources</h3>
          <div className="rights-source-list">
            {category.sources.map((source) => (
              <button type="button" className="rights-source-card" key={source.id} onClick={() => { window.location.hash = `#/rights/source/${source.id}`; }}>
                <FileText size={24} strokeWidth={1.45} />
                <span>
                  <strong>{source.short_title}</strong>
                  <small>{source.document_type} · {source.jurisdiction}{source.year ? ` · ${source.year}` : ''}</small>
                </span>
                <ChevronRight size={18} strokeWidth={1.8} />
              </button>
            ))}
          </div>
        </section>

        <RightsInfoSection title="What You Can Do" items={category.what_you_can_do} ordered />
        <RightsAskCta label={`Need help with ${category.title.toLowerCase()}?`} />
        <RightsDisclaimerCard text={category.disclaimer} />
      </div>
    </>
  );
}

function RightsSourcePage({ sourceId }) {
  const [source, setSource] = React.useState(null);
  const [status, setStatus] = React.useState('loading');

  React.useEffect(() => {
    let ignore = false;
    const loadSource = async () => {
      try {
        const response = await fetch(`/api/legal-awareness/sources/${encodeURIComponent(sourceId)}`);
        const payload = await safeJsonResponse(response);
        if (!response.ok || !payload) throw new Error('Could not load this source.');
        if (!ignore) {
          setSource(payload);
          setStatus('ready');
        }
      } catch (error) {
        console.error('Could not load legal-awareness source', error);
        if (!ignore) setStatus('error');
      }
    };
    loadSource();
    return () => {
      ignore = true;
    };
  }, [sourceId]);

  if (status !== 'ready') {
    return <RightsLoadingState message={status === 'error' ? 'This source could not be loaded.' : 'Loading source...'} />;
  }

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <button type="button" className="rights-back-button" onClick={() => { window.location.hash = '#/rights'; }}>
          ← Back to Know Your Rights
        </button>
        <section className="rights-panel rights-source-detail">
          <h2>{source.short_title || source.document_title}</h2>
          <p>{source.description}</p>
          <div className="rights-meta-row">
            <span>{source.jurisdiction || 'India'}</span>
            <span>{source.year || 'Current corpus'}</span>
            <span>{source.document_type}</span>
            <span>{source.authority_level}</span>
          </div>
          <a className="rights-source-file-button" href={`/api/legal-awareness/sources/${source.id}/file`} target="_blank" rel="noreferrer">
            View Source
            <ArrowUpRight size={16} strokeWidth={1.7} />
          </a>
        </section>

        <RightsInfoSection title="What this law covers" items={source.what_this_law_covers} />

        <section className="rights-panel">
          <h3>Important Provisions</h3>
          {source.important_provisions.length ? (
            <div className="rights-source-list">
              {source.important_provisions.map((provision) => (
                <button
                  type="button"
                  className="rights-source-card"
                  key={provision.id}
                  onClick={() => { window.location.hash = `#/rights/source/${source.id}/provision/${provision.id}`; }}
                >
                  <FileText size={23} strokeWidth={1.45} />
                  <span>
                    <strong>{provision.label} — {provision.title}</strong>
                    <small>{provision.page ? `Source page ${provision.page}` : 'Source page unavailable'}</small>
                  </span>
                  <ChevronRight size={18} strokeWidth={1.8} />
                </button>
              ))}
            </div>
          ) : (
            <p className="rights-muted">Important provisions are not currently available for this source in the local legal corpus.</p>
          )}
        </section>
        <RightsAskCta label="Need help applying this source?" />
        <RightsDisclaimerCard />
      </div>
    </>
  );
}

function RightsProvisionPage({ sourceId, provisionId }) {
  const [provision, setProvision] = React.useState(null);
  const [status, setStatus] = React.useState('loading');

  React.useEffect(() => {
    let ignore = false;
    const loadProvision = async () => {
      try {
        const response = await fetch(`/api/legal-awareness/sources/${encodeURIComponent(sourceId)}/provisions/${encodeURIComponent(provisionId)}`);
        const payload = await safeJsonResponse(response);
        if (!response.ok || !payload) throw new Error('Could not load this provision.');
        if (!ignore) {
          setProvision(payload);
          setStatus('ready');
        }
      } catch (error) {
        console.error('Could not load legal-awareness provision', error);
        if (!ignore) setStatus('error');
      }
    };
    loadProvision();
    return () => {
      ignore = true;
    };
  }, [sourceId, provisionId]);

  if (status !== 'ready') {
    return <RightsLoadingState message={status === 'error' ? 'This provision is not currently available in the local legal corpus.' : 'Loading provision...'} />;
  }

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <button type="button" className="rights-back-button" onClick={() => { window.location.hash = `#/rights/source/${sourceId}`; }}>
          ← Back to Source
        </button>
        <section className="rights-panel rights-provision-detail">
          <h2>{provision.label} — {provision.title}</h2>
          <h3>Plain-language explanation</h3>
          <p>{provision.plain_language_explanation}</p>
          <h3>Official source excerpt</h3>
          <blockquote>{provision.official_excerpt || 'No excerpt is available for this provision.'}</blockquote>
          <div className="rights-meta-row">
            <span>{provision.source?.short_title}</span>
            {provision.page ? <span>Page {provision.page}</span> : null}
            <span>{provision.source?.jurisdiction}</span>
          </div>
          <a className="rights-source-file-button" href={`/api/legal-awareness/sources/${sourceId}/file`} target="_blank" rel="noreferrer">
            View Source
            <ArrowUpRight size={16} strokeWidth={1.7} />
          </a>
        </section>
        <RightsAskCta label="Want guidance for your situation?" />
        <RightsDisclaimerCard />
      </div>
    </>
  );
}

function RightsInfoSection({ title, items, ordered = false }) {
  if (!items?.length) return null;
  const ListTag = ordered ? 'ol' : 'ul';
  return (
    <section className="rights-panel">
      <h3>{title}</h3>
      <ListTag className={ordered ? 'rights-step-list' : undefined}>
        {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
      </ListTag>
    </section>
  );
}

function RightsAskCta({ label }) {
  return (
    <section className="rights-ask-cta">
      <Scale size={31} strokeWidth={1.4} />
      <div>
        <h3>{label}</h3>
        <p>Describe your situation and get legally grounded guidance.</p>
      </div>
      <button type="button" className="ask-button" onClick={() => { window.location.hash = '#/ask'; }}>
        Ask a Question
        <ArrowUpRight size={16} strokeWidth={1.7} />
      </button>
    </section>
  );
}

function RightsDisclaimerCard({ text }) {
  return (
    <section className="rights-disclaimer">
      <Info size={19} strokeWidth={1.7} />
      <p>{text || 'This information is for general legal awareness and does not constitute professional legal advice. For guidance on your specific situation, ask a question.'}</p>
    </section>
  );
}

function RightsLoadingState({ message }) {
  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <section className="rights-panel">
          <p className="rights-muted">{message}</p>
        </section>
      </div>
    </>
  );
}

export default function App() {
  const [route, setRoute] = React.useState(() => window.location.hash || '#/');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = React.useState(() => {
    try {
      return window.localStorage.getItem('legalAid.sidebarCollapsed') === 'true';
    } catch {
      return false;
    }
  });

  React.useEffect(() => {
    const handleHashChange = () => setRoute(window.location.hash || '#/');
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const [, routePath = '/'] = route.match(/^#([^?]*)/) || [];
  const routeSegments = routePath.split('/').filter(Boolean);
  const queryString = route.includes('?') ? route.slice(route.indexOf('?') + 1) : '';
  const queryParams = new URLSearchParams(queryString);
  const initialQuery = queryParams.get('q') || '';
  const initialCaseId = queryParams.get('case') || '';
  const initialAttach = queryParams.get('attach') === '1';
  const activePage = routeSegments[0] === 'ask'
    ? 'ask'
    : routeSegments[0] === 'complaints'
      ? 'complaints'
      : routeSegments[0] === 'documents'
        ? 'documents'
        : routeSegments[0] === 'summarize-document'
          ? 'summarize'
          : routeSegments[0] === 'cases'
            ? 'cases'
            : routeSegments[0] === 'rights'
              ? 'rights'
              : routeSegments[0] === 'about'
                ? 'about'
                : routeSegments[0] === 'schemes'
                  ? 'schemes'
                  : 'home';

  return (
    <div className={`app-shell ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
      <Sidebar
        activePage={activePage}
        collapsed={isSidebarCollapsed}
        onToggle={() => {
          setIsSidebarCollapsed((current) => {
            const next = !current;
            try {
              window.localStorage.setItem('legalAid.sidebarCollapsed', String(next));
            } catch {
              // Preference persistence is optional.
            }
            return next;
          });
        }}
      />
      <main className={`main-panel ${activePage}-page-panel`}>
        {activePage === 'ask' && <AskQuestionPage initialQuery={initialQuery} initialCaseId={initialCaseId} initialAttach={initialAttach} />}
        {activePage === 'complaints' && <ComplaintDrafterPage />}
        {activePage === 'cases' && <MyCasesPage />}
        {activePage === 'documents' && <DocumentsPage />}
        {activePage === 'summarize' && <SummarizeDocumentPage />}
        {activePage === 'rights' && <LegalAwarenessPage segments={routeSegments} />}
        {activePage === 'about' && <AboutUsPage />}
        {activePage === 'schemes' && <SchemesPage />}
        {activePage === 'home' && <HomePage />}
      </main>
    </div>
  );
}
