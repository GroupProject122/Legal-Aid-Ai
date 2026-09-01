import React from 'react';
import {
  ArrowUpRight,
  Bell,
  Bot,
  BriefcaseBusiness,
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
  { label: 'My Cases', icon: BriefcaseBusiness, page: 'cases', href: '#/cases' },
  { label: 'Documents', icon: FileText, page: 'documents', href: '#/documents' },
  { label: 'Summarize Document', icon: Sparkles, page: 'summarize', href: '#/summarize-document' },
  { label: 'Know Your Rights', icon: ShieldCheck, page: 'rights', href: '#/rights' },
  { label: 'Schemes', icon: Gift, page: 'schemes', href: '#/schemes' },
  { label: 'About Us', icon: CircleHelp, page: 'about', href: '#/about' }
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
    icon: Scale,
    href: '#/rights'
  },
  {
    title: 'Draft Complaints',
    description: 'Create professional complaint letters in seconds.',
    button: 'Create Now',
    icon: FilePenLine,
    href: '#/ask'
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
    href: '#/'
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
        <h2>Legal Aid AI</h2>
      </div>
      <LegalMark className="hero-mark" />
      <p className="hero-subtitle">Get clear answers. Know your rights. Take action.</p>
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

function FeatureCard({ title, description, button, icon: Icon, href }) {
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
      <button type="button" className="card-button" onClick={() => { window.location.hash = href; }}>
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

function QuerySummaryPanel({ category, setCategory, onAttach, attachedFactContext, onDetachFactContext }) {
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

        <div className="category-chip-list" aria-label="Select legal category">
          {askCategories.map((item) => (
            <button
              type="button"
              className={`mini-chip ${selectedCategories.includes(item) ? 'selected' : ''}`}
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

function AskQuestionPage({ initialQuery = '', initialCaseId = '' }) {
  const [input, setInput] = React.useState(initialQuery);
  const [messages, setMessages] = React.useState([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [category, setCategory] = React.useState('');
  const [isAttachmentOpen, setIsAttachmentOpen] = React.useState(false);
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
            setCategory={setCategory}
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
      <button type="button" className="browse-button" onClick={() => fileInputRef.current?.click()}>Browse Files</button>
      {selectedFile && <p className="selected-file">Selected: {selectedFile.name}</p>}
      <button type="button" className="browse-button extract-button" disabled={!selectedFile || status === 'uploading'} onClick={handleUpload}>
        {status === 'uploading' ? 'Extracting...' : 'Extract Text'}
      </button>
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

function PersistedDocumentRow({ document, onView, onRename, onDelete }) {
  return (
    <tr>
      <td>
        <div className="document-name-cell">
          <FileTypeIcon type={document.file_type} />
          <div>
            <strong>{document.filename}</strong>
          </div>
        </div>
      </td>
      <td>{formatCaseDate(document.updated_at || document.created_at)}</td>
      <td>
        <div className="persisted-document-actions">
          <button type="button" className="document-outline-button" onClick={() => onView(document.id)}>
            <Eye size={16} strokeWidth={1.7} />
            View
          </button>
          <button type="button" className="document-outline-button" onClick={() => onRename(document)}>
            <Pencil size={16} strokeWidth={1.7} />
            Rename
          </button>
          <button type="button" className="document-delete-button" onClick={() => onDelete(document)}>
            <Trash2 size={16} strokeWidth={1.7} />
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}

function DocumentsPage() {
  const [storedDocuments, setStoredDocuments] = React.useState([]);
  const [status, setStatus] = React.useState('loading');
  const [previewDocument, setPreviewDocument] = React.useState(null);
  const [renameDocument, setRenameDocument] = React.useState(null);
  const [deleteDocument, setDeleteDocument] = React.useState(null);
  const uploadInputRef = React.useRef(null);

  const loadDocuments = React.useCallback(async () => {
    setStatus('loading');
    try {
      const response = await fetch('/api/documents');
      const payload = await safeJsonResponse(response);
      if (!response.ok || !Array.isArray(payload)) {
        throw new Error('Documents could not be loaded.');
      }
      setStoredDocuments(payload);
      setStatus('ready');
    } catch (error) {
      console.error('Could not load documents', error);
      setStatus('error');
    }
  }, []);

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
    await loadDocuments();
  };

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="documents-content-frame">
        <DocumentsPageHeader />
        <section className="documents-panel persisted-documents-panel" aria-label="Uploaded documents">
          <PanelCorners />
          <UploadDocumentCard onUploaded={loadDocuments} externalInputRef={uploadInputRef} />
          <div className="persisted-document-table-wrap">
            {status === 'loading' && <p className="empty-documents">Loading documents...</p>}
            {status === 'error' && <p className="empty-documents">Documents could not be loaded right now.</p>}
            {status === 'ready' && storedDocuments.length === 0 && (
              <div className="empty-documents persisted-empty-documents">
                <FileText size={34} strokeWidth={1.45} />
                <p>No documents uploaded yet.</p>
                <span>Upload a PDF, DOCX, or TXT file to get started.</span>
                <button type="button" className="browse-button" onClick={() => uploadInputRef.current?.click()}>
                  Upload Document
                </button>
              </div>
            )}
            {status === 'ready' && storedDocuments.length > 0 && (
              <table className="document-table persisted-document-table">
                <thead>
                  <tr>
                    <th>Document Name</th>
                    <th>Time</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {storedDocuments.map((document) => (
                    <PersistedDocumentRow
                      document={document}
                      key={document.id}
                      onView={handleView}
                      onRename={setRenameDocument}
                      onDelete={setDeleteDocument}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </div>
      {previewDocument && <DocumentPreviewModal document={previewDocument} onClose={() => setPreviewDocument(null)} />}
      {renameDocument && <DocumentRenameModal document={renameDocument} onClose={() => setRenameDocument(null)} onSave={handleRename} />}
      {deleteDocument && <DocumentDeleteModal document={deleteDocument} onClose={() => setDeleteDocument(null)} onDelete={handleDelete} />}
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
      const response = await fetch('/api/documents');
      const payload = await safeJsonResponse(response);
      if (!response.ok || !Array.isArray(payload)) {
        throw new Error('Documents could not be loaded.');
      }
      setDocuments(payload.filter((document) => ['pdf', 'docx', 'txt'].includes(document.file_type)));
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

function AboutUsPage() {
  return (
    <>
      <HeaderControls />
    </>
  );
}

function SchemesPage() {
  return (
    <>
      <HeaderControls />
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

function MyCasesPage() {
  const [cases, setCases] = React.useState([]);
  const [status, setStatus] = React.useState('loading');
  const [caseToDelete, setCaseToDelete] = React.useState(null);
  const [caseToRename, setCaseToRename] = React.useState(null);
  const [deleteAllRequested, setDeleteAllRequested] = React.useState(false);
  const [deleteStatus, setDeleteStatus] = React.useState('idle');
  const [notice, setNotice] = React.useState('');

  const loadCases = React.useCallback(async () => {
    try {
      const response = await fetch('/api/cases');
      const payload = await safeJsonResponse(response);
      if (!response.ok || !Array.isArray(payload)) {
        throw new Error('Could not load saved cases.');
      }
      setCases(payload);
      setStatus('ready');
    } catch (error) {
      console.error('Could not load cases', error);
      setStatus('error');
    }
  }, []);

  React.useEffect(() => {
    setStatus('loading');
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
      setCases((current) => current.filter((savedCase) => savedCase.id !== caseToDelete.id));
      setCaseToDelete(null);
      setNotice('Case deleted.');
      window.setTimeout(() => setNotice(''), 2200);
      await loadCases();
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
    setCases((current) => current.map((item) => (item.id === savedCase.id ? { ...item, ...payload } : item)));
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
      setCases([]);
      setDeleteAllRequested(false);
      setNotice(`${payload?.deleted_count || 0} case${payload?.deleted_count === 1 ? '' : 's'} deleted.`);
      window.setTimeout(() => setNotice(''), 2200);
      await loadCases();
    } catch (error) {
      console.error('Could not delete all cases', error);
      setNotice(error.message || 'Could not delete saved cases.');
    } finally {
      setDeleteStatus('idle');
    }
  };

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
            <p>Total Cases</p>
            <strong>{cases.length}</strong>
            <span>All your legal conversations in one place</span>
          </div>
        </section>

        <div className="cases-bulk-actions">
          <button
            type="button"
            className="case-delete-all-button"
            disabled={status !== 'ready' || cases.length === 0}
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
          {status === 'ready' && cases.length === 0 && (
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
        <DeleteAllCasesModal
          count={cases.length}
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

function DeleteAllCasesModal({ count, status, onCancel, onDelete }) {
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="attachment-modal document-action-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-all-cases-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button type="button" className="modal-close" aria-label="Close delete all cases dialog" onClick={onCancel}>
          <X size={20} />
        </button>
        <div className="modal-emblem delete-emblem">
          <Trash2 size={30} strokeWidth={1.55} />
        </div>
        <h3 id="delete-all-cases-title">Delete all cases?</h3>
        <p>This will permanently delete {count} saved case{count === 1 ? '' : 's'} and their conversation history.</p>
        <div className="document-dialog-actions">
          <button type="button" className="document-outline-button" onClick={onCancel} disabled={status === 'deleting_all'}>Cancel</button>
          <button type="button" className="document-delete-button" onClick={onDelete} disabled={status === 'deleting_all'}>
            {status === 'deleting_all' ? 'Deleting...' : 'Delete All Cases'}
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
  const activePage = routeSegments[0] === 'ask'
    ? 'ask'
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
        {activePage === 'ask' && <AskQuestionPage initialQuery={initialQuery} initialCaseId={initialCaseId} />}
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
