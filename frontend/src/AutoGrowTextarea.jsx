import React from 'react';

/**
 * A textarea that grows with its content so the whole text stays visible instead of
 * scrolling inside a one-line box. Works controlled (`value`) or uncontrolled.
 *
 * submitOnEnter -- Enter submits the enclosing form; Shift+Enter inserts a new line.
 * singleLine    -- for fields that hold one value (a name, an address line): long text
 *                  wraps so it can be read in full, but Enter and pasted line breaks never
 *                  add a new line, matching the <input type="text"> it replaces.
 *
 * A CSS max-height still applies; past it the box scrolls rather than pushing the page.
 */
export function AutoGrowTextarea({
  submitOnEnter = false,
  singleLine = false,
  className = '',
  rows = 1,
  onInput,
  onKeyDown,
  onChange,
  ...props
}) {
  const ref = React.useRef(null);

  const resize = React.useCallback(() => {
    const node = ref.current;
    if (!node) return;
    node.style.height = 'auto';
    // box-sizing is border-box site-wide, so add the borders scrollHeight leaves out.
    const borders = node.offsetHeight - node.clientHeight;
    node.style.height = `${node.scrollHeight + borders}px`;
    // Only show a scrollbar once a CSS max-height has capped the growth.
    node.style.overflowY = node.scrollHeight > node.clientHeight ? 'auto' : 'hidden';
  }, []);

  // Re-measure whenever the value changes from outside too (prefill, clear after send).
  React.useLayoutEffect(resize, [props.value, resize]);

  // Text re-wraps when the box's width changes (window resize, sidebar toggle).
  React.useEffect(() => {
    const node = ref.current;
    if (!node || typeof ResizeObserver === 'undefined') return undefined;
    let width = node.clientWidth;
    const observer = new ResizeObserver(() => {
      if (node.clientWidth !== width) {
        width = node.clientWidth;
        resize();
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [resize]);

  const handleKeyDown = (event) => {
    onKeyDown?.(event);
    if (event.defaultPrevented) return;
    if (event.key !== 'Enter' || event.shiftKey || event.nativeEvent.isComposing) return;
    if (submitOnEnter) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    } else if (singleLine) {
      event.preventDefault();
    }
  };

  const handleChange = (event) => {
    if (singleLine && /[\r\n]/.test(event.target.value)) {
      event.target.value = event.target.value.replace(/\s*[\r\n]+\s*/g, ' ');
    }
    onChange?.(event);
  };

  return (
    <textarea
      ref={ref}
      rows={rows}
      className={`auto-grow-textarea ${className}`.trim()}
      onInput={(event) => {
        resize();
        onInput?.(event);
      }}
      onKeyDown={handleKeyDown}
      onChange={handleChange}
      {...props}
    />
  );
}
