// Layout chrome shared across App.jsx's pages and any page defined in its own file (e.g.
// helplines/Helplines.jsx). Pulled out of App.jsx so a separate page file can reuse the same
// header/background/divider without creating a circular import between App.jsx and that file
// (App.jsx also imports from here, never the other way around).
import React from 'react';
import { Bell, Moon, Scale, Sun } from 'lucide-react';

import { AccountMenu } from '../auth.jsx';

export function VintageScales({ className = '' }) {
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

export function VintageCourthouse({ className = '' }) {
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

export function VintageGavel({ className = '' }) {
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

export function VintageDocuments({ className = '' }) {
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

export function VintageLawBook({ className = '' }) {
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

const THEME_STORAGE_KEY = 'legalAidTheme';

// Dark mode is a whole-page colour inversion (see html[data-theme="dark"] in styles.css): the
// stylesheet hard-codes its parchment palette in thousands of rules rather than in variables, so
// inverting -- with a hue rotation that keeps the browns warm -- themes every page at once.
// The attribute is set on <html> before first paint by the inline script in index.html; every
// HeaderControls (one per page) reads it from there, so all pages agree.
function useTheme() {
  const [theme, setTheme] = React.useState(() => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'));

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch (error) {
      // Storage can be unavailable (private window, blocked site data); the toggle still works
      // for this visit, it just is not remembered.
    }
    setTheme(next);
  };

  return [theme, toggleTheme];
}

export function HeaderControls() {
  const [theme, toggleTheme] = useTheme();
  const isDark = theme === 'dark';
  return (
    <header className="top-controls" aria-label="Page controls">
      <button
        type="button"
        onClick={toggleTheme}
        aria-pressed={isDark}
        aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        title={isDark ? 'Light mode' : 'Dark mode'}
      >
        {isDark ? <Sun size={18} /> : <Moon size={18} />}
      </button>
      <button aria-label="Notifications">
        <Bell size={18} />
        <span className="notify-dot" />
      </button>
      <AccountMenu />
    </header>
  );
}

export function PageDivider() {
  return (
    <div className="page-divider" aria-hidden="true">
      <span />
      <Scale size={24} strokeWidth={1.45} />
      <span />
    </div>
  );
}

export function DocumentsBackgroundArt() {
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
