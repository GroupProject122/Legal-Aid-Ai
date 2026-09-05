# Frontend Changelog

Notes on notable frontend changes so the team can see what moved and why.
Only `frontend/src/App.jsx` and `frontend/src/styles.css` are affected by the entries below.

## 2026-09-06 — Home page redesign, new content sections, motion pass

### Layout & visual cleanup (Home)
- Stripped ornament: removed the double inset "frame" borders on the panel, the
  per-card corner brackets, the `⌘` glyphs in the hero, the `◇` dividers, the
  oversized quote-mark footer, and 5 of the 7 scattered background watermark sketches.
- Hero rebuilt as a clean stack: small uppercase kicker → serif title → sans subtitle.
- Search box narrowed to a focused ~640px with flat styling and a single icon.
- "Browse by topic" pills and the four "How Legal Aid AI helps" cards restyled with
  lighter borders and a frosted-glass background that clears on hover.
- Consistent vertical rhythm via one flex `gap` on the centered content column.

### Sidebar & top controls (all pages)
- Sidebar width 300px → 240px. Removed the inset frames, corner brackets, the laurel
  marks around the logo, the large watermark, the `◇` divider, and the heavy shadow.
- Nav links: serif 1.45rem → sans 0.92rem; removed the slide-on-hover; the active
  item is now a flat solid fill instead of a gradient with stacked inset shadows.
- Top-right controls (theme / notifications / avatar): 52px gradient orbs → 36px flat,
  transparent, with a subtle hover tint only. Icons scaled down to match.

### New Home content (built from the real pages)
Below the fold, a run of scroll-revealed sections:
- **What you can do here** — a row of jump chips that smooth-scroll to each of five
  alternating feature sections: Documents, Summarize Document, My Cases,
  Know Your Rights, Schemes. Each has a real description of what that page does, a
  three-point capability list, a CTA button, and (for Know Your Rights) topic chips.
- **How it works** — three steps.
- **Why your privacy matters** / **Need help?** — two larger cards with detail lists
  (session-scoped data; NALSA / Tele-Law / State Legal Services Authority).
- A slow **marquee** strip of legal topics (pauses on hover).
- A proper **footer**: brand mark, about text, and quick links to Ask a Question,
  Know Your Rights, Schemes, and About Us.

### Pages that were empty stubs, now filled
- **About Us** (`#/about`): what the tool is, what you can do (in nav order),
  how it works, and a privacy note.
- **Schemes** (`#/schemes`): NALSA free legal aid, National Consumer Helpline (1915),
  Cyber Crime Reporting Portal (1930), Tele-Law, e-Daakhil, and the State Legal
  Services Authority — each linking out to the official site.
- Both reuse the shared parchment page background and the Know Your Rights panel styles.

### Motion & interaction (Home)
- Masked reveal on the hero title (slides up from a clip on load).
- Scroll-reveal system using `IntersectionObserver` with expo easing; feature
  sections stagger their text then their side panel.
- Background watermark parallax on scroll (`requestAnimationFrame`).
- `scroll-behavior: smooth` plus smooth-scrolling jump chips.
- Hover micro-interactions: CTA lift + arrow slide, magnetic pull on the primary
  CTA buttons, frosted cards/pills that clear on hover, edge-faded marquee.
- **Custom cursor (Home only):** a crisp dot at the exact pointer plus a soft
  trailing circle (radial fill, no border, no shadow) that eases behind it, grows
  over interactive elements, and shrinks on click. The native cursor is hidden on
  Home and restored on every other page; text inputs keep the I-beam.
- All of the above respects `prefers-reduced-motion`; the custom cursor and the
  magnetic effect are also disabled on touch / coarse-pointer devices.
