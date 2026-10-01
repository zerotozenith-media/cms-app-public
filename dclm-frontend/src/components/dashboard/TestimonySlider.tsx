import { useEffect, useRef, useState } from 'react';

export interface TestimonyItem { text: string; by: string; service?: string; date: string }

/**
 * The ten most recent testimonies, one at a time (F15). Swipe on a phone,
 * arrows on a computer, small dots for position. Moves on by itself every
 * six seconds until touched, and not at all when the device asks for
 * reduced motion.
 */
export function TestimonySlider({ items }: { items: TestimonyItem[] }) {
  const track = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  const [auto, setAuto] = useState(
    () => !(typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches));

  function go(n: number) {
    const el = track.current;
    if (!el || !items.length) return;
    const i = (n + items.length) % items.length;
    el.scrollTo({ left: i * el.clientWidth, behavior: 'smooth' });
    setIndex(i);
  }
  useEffect(() => {
    if (!auto || items.length < 2) return;
    const t = setInterval(() => go(index + 1), 6000);
    return () => clearInterval(t);
  });
  const stop = () => setAuto(false);
  const onScroll = () => {
    const el = track.current;
    if (el) setIndex(Math.round(el.scrollLeft / Math.max(1, el.clientWidth)));
  };
  const when = (d: string) =>
    new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });

  if (!items.length) return <div className="empty">None recorded yet.</div>;
  return (
    <div className="ts">
      <div className="ts-track" ref={track} onScroll={onScroll} onPointerDown={stop} onWheel={stop}>
        {items.map((t, i) => (
          <figure className="ts-card" key={i} aria-roledescription="slide" aria-label={`${i + 1} of ${items.length}`}>
            <span className="ts-quote" aria-hidden="true">“</span>
            <blockquote>{t.text}</blockquote>
            <figcaption>{[t.by || 'Unnamed', t.service, when(t.date)].filter(Boolean).join(' · ')}</figcaption>
          </figure>
        ))}
      </div>
      {items.length > 1 && (
        <div className="ts-foot">
          <div className="ts-dots" role="tablist" aria-label="Choose a testimony">
            {items.map((_, i) => (
              <button key={i} role="tab" aria-selected={i === index} aria-label={`Testimony ${i + 1}`}
                className={`ts-dot${i === index ? ' on' : ''}`} onClick={() => { stop(); go(i); }} />
            ))}
          </div>
          <div className="ts-arrows">
            <button aria-label="Previous testimony" onClick={() => { stop(); go(index - 1); }}>‹</button>
            <button aria-label="Next testimony" onClick={() => { stop(); go(index + 1); }}>›</button>
          </div>
        </div>
      )}
    </div>
  );
}
