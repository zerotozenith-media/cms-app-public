import { useState, useRef, useEffect } from 'react';
import { HELP_TOPICS } from '../../help/topics';

/**
 * A small "?" next to a label. Clicking opens a short explanation
 * anchored to the marker, so the answer appears next to the thing being
 * asked about rather than at the top of the page.
 *
 * Click-outside and Escape both close it, because a popover that can
 * only be dismissed by finding its own close button is annoying on a
 * phone where the button may be off screen.
 */
export function HelpMark({ topic }: { topic: string }) {
  const [open, setOpen] = useState(false);
  // A marker near the right edge would push its popover off screen, so
  // it flips to right-aligned when there is not enough room. Found by
  // measuring real horizontal overflow, not by eyeballing it.
  const [alignRight, setAlignRight] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const t = HELP_TOPICS[topic];

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!t) return null;

  return (
    <span className="help-mark-wrap" ref={ref}>
      <button
        type="button"
        className="help-mark"
        aria-label={`What is ${t.title}?`}
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          if (!open && ref.current) {
            const left = ref.current.getBoundingClientRect().left;
            setAlignRight(left + 300 > document.documentElement.clientWidth);
          }
          setOpen(!open);
        }}
      >
        ?
      </button>
      {open && (
        <span className={`help-pop${alignRight ? ' align-right' : ''}`} role="dialog" aria-label={t.title}>
          <span className="help-pop-title">{t.title}</span>
          <span className="help-pop-body">{t.body}</span>
        </span>
      )}
    </span>
  );
}
