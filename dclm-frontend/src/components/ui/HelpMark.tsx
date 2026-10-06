import { useState, useRef, useEffect } from 'react';
import { HELP_TOPICS } from '../../help/topics';

/**
 * A small "?" next to a label. Pressing it opens a short explanation next
 * to the thing being asked about.
 *
 * The explanation is placed from the screen's own edges, so it always
 * stays fully on screen. On a phone it opens as a full-width panel just
 * under the "?", in larger text, with a close button (Kay: tips were cut
 * off at the sides when touched, and hard to read). Pressing elsewhere,
 * scrolling, or Escape closes it.
 */
const GAP = 8;
const EDGE = 12;
const DESKTOP_WIDTH = 300;

export function HelpMark({ topic }: { topic: string }) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number; width: number; phone: boolean } | null>(null);
  const ref = useRef<HTMLSpanElement>(null);
  const popRef = useRef<HTMLSpanElement>(null);
  const t = HELP_TOPICS[topic];

  function place() {
    if (!ref.current) return;
    const r = ref.current.getBoundingClientRect();
    const vw = document.documentElement.clientWidth;
    const phone = vw <= 600;
    const width = phone ? vw - EDGE * 2 : Math.min(DESKTOP_WIDTH, vw - EDGE * 2);
    const left = phone ? EDGE : Math.max(EDGE, Math.min(r.left, vw - width - EDGE));
    setPos({ top: r.bottom + GAP, left, width, phone });
  }

  // Once shown, move it above the "?" if there is no room below.
  useEffect(() => {
    if (!open || !pos || !popRef.current || !ref.current) return;
    const h = popRef.current.getBoundingClientRect().height;
    const vh = window.innerHeight;
    if (pos.top + h > vh - EDGE) {
      const above = ref.current.getBoundingClientRect().top - GAP - h;
      const top = above >= EDGE ? above : Math.max(EDGE, vh - EDGE - h);
      if (Math.abs(top - pos.top) > 1) setPos({ ...pos, top });
    }
  }, [open, pos]);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent | TouchEvent) {
      const target = e.target as Node;
      if (ref.current?.contains(target) || popRef.current?.contains(target)) return;
      setOpen(false);
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    const onScroll = () => setOpen(false);
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('touchstart', onDocClick);
    document.addEventListener('keydown', onKey);
    window.addEventListener('scroll', onScroll, true);
    window.addEventListener('resize', onScroll);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('touchstart', onDocClick);
      document.removeEventListener('keydown', onKey);
      window.removeEventListener('scroll', onScroll, true);
      window.removeEventListener('resize', onScroll);
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
          if (!open) place();
          setOpen(!open);
        }}
      >
        ?
      </button>
      {open && pos && (
        <span ref={popRef} className={`help-pop${pos.phone ? ' phone' : ''}`} role="dialog" aria-label={t.title}
          style={{ position: 'fixed', top: pos.top, left: pos.left, width: pos.width }}>
          <span className="help-pop-title">{t.title}
            {pos.phone && <button type="button" className="help-pop-close" aria-label="Close" onClick={() => setOpen(false)}>&#215;</button>}
          </span>
          <span className="help-pop-body">{t.body}</span>
        </span>
      )}
    </span>
  );
}
