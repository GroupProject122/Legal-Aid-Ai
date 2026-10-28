// Every number and URL here was checked against an official government source before being
// added (a .gov.in/.nic.in page, a DoT short-code allocation record, or the service's own
// official site) -- see CHANGELOG.md for the specific source used per entry. Nothing here is
// from memory. If a fact can't be verified, it's left out rather than guessed.
export const LAST_VERIFIED = "2026-10-28";

// Matches the app's four supported legal domains (see backend/domain_router.py's
// SUPPORTED_DOMAINS), plus "urgent" for life-safety numbers that aren't specific to any one
// domain. Filter chips use this list; "tenancy" is deliberately not a chip (see Helplines.jsx --
// there is no tenancy helpline to filter to, only an honest explanation of that gap).
export const HELPLINE_DOMAINS = [
  { id: "urgent", label: "Urgent" },
  { id: "cyber", label: "Cyber" },
  { id: "consumer", label: "Consumer" },
  { id: "rights", label: "Legal aid & rights" }
];

const helplines = [
  // --- Urgent help (always shown first, regardless of filter) ---
  {
    id: "erss-112",
    domain: "urgent",
    name: "Emergency Response Support System (ERSS)",
    number: "112",
    website: null,
    handles: "Any life-threatening emergency -- police, fire, or medical.",
    whenToUse: "Call this first if you or someone else is in immediate danger.",
    sourceUrl: "https://112.gov.in/about",
    lastVerified: LAST_VERIFIED
  },
  {
    id: "women-helpline-181",
    domain: "urgent",
    name: "Women Helpline",
    number: "181",
    website: null,
    handles: "24x7 support for women facing violence or abuse, run by the Ministry of Women and Child Development.",
    whenToUse: "Use this if you or someone you know is a woman in distress or danger.",
    sourceUrl: "https://112.gov.in/about",
    lastVerified: LAST_VERIFIED
  },
  {
    id: "child-helpline-1098",
    domain: "urgent",
    name: "Child Helpline",
    number: "1098",
    website: "https://www.childlineindia.org",
    handles: "24x7 free helpline for children in need of care and protection -- anyone can call on a child's behalf.",
    whenToUse: "Use this to report a child in distress, abuse, or trafficking.",
    sourceUrl: "https://www.childlineindia.org/a/about/childline-india",
    lastVerified: LAST_VERIFIED
  },
  {
    id: "elderline-14567",
    domain: "urgent",
    name: "Elderline (Senior Citizens Helpline)",
    number: "14567",
    website: null,
    handles: "National helpline for senior citizens -- information, guidance, emotional support, and field intervention in abuse cases.",
    whenToUse: "Use this for elder abuse, neglect, or a senior citizen needing assistance. Runs 8 AM to 8 PM.",
    sourceUrl: "https://dot.gov.in/node/17445",
    lastVerified: LAST_VERIFIED
  },

  // --- Cyber ---
  {
    id: "cyber-crime-helpline-1930",
    domain: "cyber",
    name: "National Cyber Crime Helpline",
    number: "1930",
    website: "https://cybercrime.gov.in",
    handles: "Reporting online financial fraud -- UPI scams, unauthorized transactions, phishing.",
    whenToUse: "Call immediately after losing money to online fraud -- speed matters for recovering funds.",
    sourceUrl: "https://cybercrime.gov.in",
    lastVerified: LAST_VERIFIED
  },
  {
    id: "cyber-crime-portal",
    domain: "cyber",
    name: "National Cyber Crime Reporting Portal",
    number: null,
    website: "https://cybercrime.gov.in",
    handles: "Filing a full complaint for any cybercrime -- fraud, hacking, harassment, identity misuse.",
    whenToUse: "Use this to formally register a cybercrime complaint, not just report urgent financial fraud.",
    sourceUrl: "https://cybercrime.gov.in",
    lastVerified: LAST_VERIFIED
  },

  // --- Consumer ---
  {
    id: "national-consumer-helpline",
    domain: "consumer",
    name: "National Consumer Helpline",
    number: "1915",
    website: "https://consumerhelpline.gov.in",
    handles: "Complaints about defective goods, deficient service, refunds, and unfair trade practices. Also reachable at 1800-11-4000.",
    whenToUse: "Use this before or alongside filing a formal consumer complaint, for free guidance and grievance redressal.",
    sourceUrl: "https://consumerhelpline.gov.in/public/about",
    lastVerified: LAST_VERIFIED
  },
  {
    id: "rbi-complaint-management-system",
    domain: "consumer",
    name: "RBI Complaint Management System",
    number: null,
    website: "https://cms.rbi.org.in",
    handles: "Complaints against banks, NBFCs, and payment companies -- charges, failed transactions, loan or credit card issues.",
    whenToUse: "Use this only after complaining to your bank first and not getting a response within 30 days, or an unsatisfactory one.",
    sourceUrl: "https://cms.rbi.org.in",
    lastVerified: LAST_VERIFIED
  },

  // --- Free legal aid / rights ---
  {
    id: "nalsa-helpline",
    domain: "rights",
    name: "NALSA Free Legal Services Helpline",
    number: "15100",
    website: "https://nalsa.gov.in",
    handles: "Free legal aid and advice from the National Legal Services Authority.",
    whenToUse: "Use this if you need a lawyer or legal guidance and cannot afford one, or to find your nearest legal aid office.",
    sourceUrl: "https://nalsa.gov.in",
    lastVerified: LAST_VERIFIED
  },
  {
    id: "rti-online",
    domain: "rights",
    name: "RTI Online Portal",
    number: null,
    website: "https://rtionline.gov.in",
    handles: "Filing a Right to Information request or first appeal online.",
    whenToUse:
      "Central public authorities only -- Ministries/Departments and other Public Authorities of the Central Government. Do not use this for state government bodies; each state runs its own RTI portal.",
    sourceUrl: "https://rtionline.gov.in",
    lastVerified: LAST_VERIFIED
  }
];

export default helplines;

// There is no national tenancy helpline -- rather than invent one, this is said plainly on the
// page (Helplines.jsx), pointing instead to free legal aid: NALSA's 15100 above, and (Delhi
// only, per the task's explicit scope -- no other state-specific numbers) the Delhi State Legal
// Services Authority.
export const TENANCY_NOTE = {
  heading: "Tenancy",
  body: "There is no dedicated national helpline for tenancy disputes. For a landlord-tenant issue, free legal aid is the right place to start:",
  links: [
    {
      id: "nalsa-helpline-tenancy",
      name: "NALSA Free Legal Services Helpline",
      number: "15100",
      website: "https://nalsa.gov.in",
      sourceUrl: "https://nalsa.gov.in"
    },
    {
      id: "dslsa-helpline",
      name: "Delhi State Legal Services Authority (DSLSA)",
      number: "1516",
      website: "https://dslsa.org",
      sourceUrl: "https://dslsa.org/legal-aid-wing/operation-of-help-line-no-1516/"
    }
  ],
  lastVerified: LAST_VERIFIED
};
