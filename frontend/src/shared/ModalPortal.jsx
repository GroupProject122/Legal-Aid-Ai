import React from 'react';
import { createPortal } from 'react-dom';

// Renders a modal (backdrop + dialog) straight into document.body, outside the page's own
// layout, and locks page scrolling while it is open. A dialog rendered inside a card is trapped by
// that card: a `transform` (e.g. a hover lift), `filter` or `backdrop-filter` on any ancestor turns
// `position: fixed` into "fixed to that ancestor", so the backdrop covers one card and later cards
// paint over the dialog. The dark-mode filter sits on <html>, so a portal into <body> still gets it.
let openCount = 0;
let previousOverflow = '';

export function ModalPortal({ children }) {
  React.useEffect(() => {
    const root = document.documentElement;
    if (openCount === 0) {
      previousOverflow = root.style.overflow;
      root.style.overflow = 'hidden';
    }
    openCount += 1;
    return () => {
      openCount -= 1;
      if (openCount === 0) root.style.overflow = previousOverflow;
    };
  }, []);

  return createPortal(children, document.body);
}
