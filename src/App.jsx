import React from 'react';
import {
  ArrowUpRight,
  Bell,
  Bot,
  BriefcaseBusiness,
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

const navItems = [
  { label: 'Home', icon: Home, page: 'home', href: '#/' },
  { label: 'Ask Question', icon: MessageCircle, page: 'ask', href: '#/ask' },
  { label: 'My Cases', icon: BriefcaseBusiness, href: '#/' },
  { label: 'Documents', icon: FileText, page: 'documents', href: '#/documents' },
  { label: 'Know Your Rights', icon: ShieldCheck, href: '#/' },
  { label: 'Schemes', icon: Gift, href: '#/' },
  { label: 'About Us', icon: CircleHelp, href: '#/' }
];

const categories = [
  { label: 'Consumer Issues', icon: ShoppingCart },
  { label: 'Tenant Disputes', icon: Home },
  { label: 'Cyber Issues', icon: LockKeyhole },
  { label: 'Fundamental Rights', icon: ShieldCheck },
  { label: 'Other Legal Help', icon: MoreHorizontal }
];

const features = [
  {
    title: 'Know Your Rights',
    description: 'Understand your legal rights in simple words.',
    button: 'Explore Now',
    icon: Scale
  },
  {
    title: 'Draft Complaints',
    description: 'Create professional complaint letters in seconds.',
    button: 'Create Now',
    icon: FilePenLine
  },
  {
    title: 'Follow Procedure',
    description: 'Step-by-step guidance on what to do and where to go.',
    button: 'Learn More',
    icon: Landmark
  },
  {
    title: 'Government Schemes',
    description: 'Find schemes and benefits you may be eligible for.',
    button: 'View Schemes',
    icon: Gift
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

function Sidebar({ activePage = 'home' }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-frame" />
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
          <a href={href} className={`nav-item ${page === activePage ? 'active' : ''}`} key={label}>
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
        <Moon size={24} />
      </button>
      <button aria-label="Notifications">
        <Bell size={24} />
        <span className="notify-dot" />
      </button>
      <div className="avatar" aria-label="Profile" role="img">
        <CircleUserRound size={31} strokeWidth={1.55} />
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero">
      <div className="welcome-line">
        <span />
        <i>⌘</i>
        <p>Welcome to</p>
        <i>⌘</i>
        <span />
      </div>
      <div className="hero-title-wrap">
        <div className="hero-laurel left" aria-hidden="true">❬</div>
        <h2>Legal Aid AI</h2>
        <div className="hero-laurel right" aria-hidden="true">❭</div>
      </div>
      <p className="hero-subtitle">Get clear answers. Know your rights. Take action.</p>
      <LegalMark className="hero-mark" />
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

  return (
    <form className="query-box" onSubmit={handleSubmit}>
      <div className="corner top-left" />
      <div className="corner top-right" />
      <div className="corner bottom-left" />
      <div className="corner bottom-right" />
      <div className="query-icon">
        <Sparkles size={24} />
      </div>
      <input
        name="legal-query"
        type="text"
        placeholder="Describe your legal issue in simple words..."
        aria-label="Describe your legal issue"
      />
      <button className="attach-button" type="button" aria-label="Attach document">
        <Paperclip size={27} />
      </button>
      <button className="ask-button" type="submit">
        <Sparkles size={18} />
        <span>Ask AI</span>
      </button>
    </form>
  );
}

function CategoryPills() {
  return (
    <div className="category-pills" aria-label="Legal categories">
      {categories.map(({ label, icon: Icon }) => (
        <button type="button" className="category-pill" key={label}>
          <Icon size={20} strokeWidth={1.65} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}

function FeatureCard({ title, description, button, icon: Icon }) {
  return (
    <article className="feature-card">
      <div className="ornament corner-a" />
      <div className="ornament corner-b" />
      <div className="ornament corner-c" />
      <div className="ornament corner-d" />
      <div className="feature-icon">
        <Icon size={44} strokeWidth={1.5} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      <div className="card-separator">◇</div>
      <button type="button" className="card-button">
        <span>{button}</span>
        <ChevronRight size={18} />
      </button>
    </article>
  );
}

function FeatureCards() {
  return (
    <section className="features" aria-label="Homepage feature cards">
      {features.map((feature) => (
        <FeatureCard {...feature} key={feature.title} />
      ))}
    </section>
  );
}

function FooterQuote() {
  return (
    <footer className="footer-quote">
      <blockquote>
        <span>“</span>
        Knowledge of your rights empowers you to protect them.
      </blockquote>
      <LegalMark />
    </footer>
  );
}

function BackgroundArt() {
  return (
    <div className="background-art" aria-hidden="true">
      <VintageScales className="watermark sketch scale-mark" />
      <VintageGavel className="watermark sketch gavel-mark" />
      <VintageCourthouse className="watermark sketch court-mark" />
      <VintageDocuments className="watermark sketch doc-mark" />
      <VintageLawBook className="watermark sketch book-mark" />
      <ShieldCheck className="watermark shield-mark" size={112} strokeWidth={0.75} />
      <span className="section-symbol">§</span>
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
  const possibleRights = (answer.possible_rights || []).map(cleanDisplayText).filter(Boolean);
  const nextSteps = (answer.next_steps || []).map(cleanDisplayText).filter(Boolean);

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
        </div>

        <div className="response-section">
          <h4>Your possible rights</h4>
          {possibleRights.length > 0 ? (
            <ul>
              {possibleRights.map((right) => <li key={right}>{right}</li>)}
            </ul>
          ) : (
            <p>The available sources do not provide enough reliable detail to list specific possible rights for this question.</p>
          )}
        </div>

        <div className="response-section">
          <h4>Suggested next steps</h4>
          <ol className="step-list">
            {nextSteps.map((step, index) => (
              <li key={step}><span>{index + 1}</span>{step}</li>
            ))}
          </ol>
        </div>

        <div className="response-section sources-section">
          <h4>Sources used</h4>
          {sources.length > 0 ? (
            <div className="source-list">
              {sources.map((source) => (
                <SourceCard source={source} onClick={onSourceClick} key={`${source.document}-${source.page}-${source.section || 'source'}`} />
              ))}
            </div>
          ) : (
            <p>No source citation was available for this response.</p>
          )}
        </div>

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

      <div className="chat-scroll">
        {messages.length === 0 && !isLoading ? (
          <WelcomeState onSelectExample={onExample} />
        ) : (
          <>
            {messages.map((message) => (
              message.role === 'user'
                ? <UserMessage text={message.text} key={message.id} />
                : <LegalAIResponse response={message.response} onSourceClick={onSourceClick} key={message.id} />
            ))}
            {isLoading && <LoadingState />}
          </>
        )}
      </div>

      <ChatComposer value={input} onChange={setInput} onSubmit={onSubmit} onAttach={onAttach} />
    </section>
  );
}

function QuerySummaryPanel({ category, setCategory, onAttach }) {
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

        <div className="category-chip-list" aria-label="Select legal category">
          {askCategories.map((item) => (
            <button
              type="button"
              className={`mini-chip ${category === item ? 'selected' : ''}`}
              onClick={() => setCategory(item)}
              key={item}
            >
              {item}
            </button>
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
            <h4>Documents attached</h4>
            <p>0</p>
          </div>
        </button>
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

function AskQuestionPage({ initialQuery = '' }) {
  const [input, setInput] = React.useState(initialQuery);
  const [messages, setMessages] = React.useState([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [category, setCategory] = React.useState('');
  const [isAttachmentOpen, setIsAttachmentOpen] = React.useState(false);
  const [selectedSource, setSelectedSource] = React.useState(null);
  const loadingTimer = React.useRef(null);

  React.useEffect(() => {
    setInput(initialQuery);
  }, [initialQuery]);

  React.useEffect(() => () => window.clearTimeout(loadingTimer.current), []);

  const submitQuestion = async (question) => {
    const text = question.trim();
    if (!text || isLoading) return;

    window.clearTimeout(loadingTimer.current);
    setMessages([{ id: `user-${Date.now()}`, role: 'user', text }]);
    setInput('');
    setIsLoading(true);
    loadingTimer.current = window.setTimeout(async () => {
      try {
        const response = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: text })
        });
        const payload = await parseAskResponse(response);
        setMessages((current) => [...current, { id: `ai-${Date.now()}`, role: 'ai', response: payload }]);
      } catch (error) {
        console.error('Ask Legal Aid AI request failed', error);
        setMessages((current) => [
          ...current,
          {
            id: `ai-${Date.now()}`,
            role: 'ai',
            response: createTechnicalErrorResponse(error.message)
          }
        ]);
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
            setCategory={setCategory}
            onAttach={() => setIsAttachmentOpen(true)}
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
      <p>Upload, organize and manage your important legal documents securely.</p>
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
  const Icon = type === 'jpg' ? FileImage : FileText;
  const label = type === 'docx' ? 'DOCX' : type.toUpperCase();

  return (
    <div className={`file-type-icon ${type}`} aria-hidden="true">
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

function UploadDocumentCard() {
  const [selectedFile, setSelectedFile] = React.useState('');
  const fileInputRef = React.useRef(null);

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files?.[0]?.name || '');
  };

  return (
    <section className="documents-side-card upload-card">
      <PanelCorners />
      <h3>Upload Document</h3>
      <button type="button" className="drop-zone" onClick={() => fileInputRef.current?.click()}>
        <UploadCloud size={36} strokeWidth={1.45} />
        <strong>Drag & drop files here</strong>
        <span>or click to browse</span>
        <small>Supported: PDF, JPG, PNG, DOCX<br />Max size: 10 MB</small>
      </button>
      <input
        ref={fileInputRef}
        className="sr-only"
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.docx"
        onChange={handleFileChange}
        aria-label="Browse files"
      />
      <button type="button" className="browse-button" onClick={() => fileInputRef.current?.click()}>Browse Files</button>
      {selectedFile && <p className="selected-file">Selected: {selectedFile}</p>}
      <p className="upload-note">Document processing will be enabled in a later version.</p>
    </section>
  );
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
        <h3 id="document-preview-title">{document.name}</h3>
        <p>{document.description}</p>
        <div className="preview-placeholder">
          <Eye size={28} strokeWidth={1.45} />
          <strong>Document preview will be available here.</strong>
          <span>No document is opened or analyzed in this frontend demo.</span>
        </div>
      </section>
    </div>
  );
}

function DocumentsPage() {
  const [activeTab, setActiveTab] = React.useState('All Documents');
  const [search, setSearch] = React.useState('');
  const [openMenu, setOpenMenu] = React.useState('');
  const [previewDocument, setPreviewDocument] = React.useState(null);

  const filteredDocuments = documents.filter((document) => {
    const matchesTab = activeTab === 'All Documents' || document.tab === activeTab || document.category === activeTab.slice(0, -1);
    const haystack = `${document.name} ${document.description} ${document.category} ${document.linkedTo}`.toLowerCase();
    return matchesTab && haystack.includes(search.trim().toLowerCase());
  });

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="documents-content-frame">
        <DocumentsPageHeader />
        <div className="documents-workspace">
          <DocumentsPanel
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            search={search}
            setSearch={setSearch}
            filteredDocuments={filteredDocuments}
            openMenu={openMenu}
            setOpenMenu={setOpenMenu}
            setPreviewDocument={setPreviewDocument}
          />
          <DocumentsUtilityColumn />
        </div>
      </div>
      {previewDocument && <DocumentPreviewModal document={previewDocument} onClose={() => setPreviewDocument(null)} />}
    </>
  );
}

function HomePage() {
  return (
    <>
      <BackgroundArt />
      <HeaderControls />
      <div className="content-frame">
        <Hero />
        <QueryBox />
        <CategoryPills />
        <FeatureCards />
        <FooterQuote />
      </div>
    </>
  );
}

export default function App() {
  const [route, setRoute] = React.useState(() => window.location.hash || '#/');

  React.useEffect(() => {
    const handleHashChange = () => setRoute(window.location.hash || '#/');
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const [, routePath = '/'] = route.match(/^#([^?]*)/) || [];
  const queryString = route.includes('?') ? route.slice(route.indexOf('?') + 1) : '';
  const initialQuery = new URLSearchParams(queryString).get('q') || '';
  const activePage = routePath === '/ask' ? 'ask' : routePath === '/documents' ? 'documents' : 'home';

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} />
      <main className="main-panel">
        {activePage === 'ask' && <AskQuestionPage initialQuery={initialQuery} />}
        {activePage === 'documents' && <DocumentsPage />}
        {activePage === 'home' && <HomePage />}
      </main>
    </div>
  );
}
