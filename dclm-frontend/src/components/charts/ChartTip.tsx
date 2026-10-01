import { useEffect, useLayoutEffect, useRef, useState } from 'react';

/**
 * One tooltip for every chart (F13): hover with a mouse, tap on a phone, tap
 * elsewhere or move away to close. The attendance bars used the browser's
 * own hover label, which a phone never shows, and the donut and goal rings
 * had none.
 */
export interface Tip { x: number; y: number; title: string; lines: string[]; key: string; below: boolean }

export function useChartTip() {
  const ref = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<Tip | null>(null);

  function show(e: React.PointerEvent | React.MouseEvent, key: string, title: string, lines: string[], atPointer = false) {
    const box = ref.current?.getBoundingClientRect();
    const target = (e.currentTarget as HTMLElement).getBoundingClientRect();
    if (!box) return;
    // At the point touched for shapes like the donut, above the part for bars.
    let x = atPointer ? e.clientX - box.left : target.left - box.left + target.width / 2;
    const y = atPointer ? e.clientY - box.top : target.top - box.top;
    // Kept inside the card, and turned to open downwards when there is no
    // room above, so it is never cut off by the card's edge.
    const half = 80;
    x = Math.max(half, Math.min(box.width - half, x));
    const below = y < 26 + lines.length * 18;
    setTip({ key, title, lines, x, y: below && !atPointer ? target.bottom - box.top : y, below });
  }
  const hide = () => setTip(null);

  // A tap outside the chart closes it on a phone.
  useEffect(() => {
    if (!tip) return;
    const close = (ev: PointerEvent) => { if (!ref.current?.contains(ev.target as Node)) setTip(null); };
    document.addEventListener('pointerdown', close);
    return () => document.removeEventListener('pointerdown', close);
  }, [tip]);

  return { ref, tip, show, hide };
}

export function ChartTipBox({ tip }: { tip: Tip | null }) {
  const el = useRef<HTMLDivElement>(null);
  const [left, setLeft] = useState<number | null>(null);
  // Measure the tooltip itself and keep all of it inside the chart's card:
  // a long goal name made it wider than the edge guard allowed for.
  useLayoutEffect(() => {
    const box = el.current, parent = box?.parentElement;
    if (!tip || !box || !parent) { setLeft(null); return; }
    const w = box.offsetWidth, pw = parent.clientWidth;
    setLeft(Math.max(4, Math.min(pw - w - 4, tip.x - w / 2)));
  }, [tip]);
  if (!tip) return null;
  return (
    <div ref={el} className={`chart-tip${tip.below ? ' below' : ''}`} role="status"
      style={{ left: left ?? tip.x, top: tip.y, transform: left === null ? undefined : (tip.below ? 'translateY(10px)' : 'translateY(calc(-100% - 8px))'), maxWidth: 'calc(100% - 8px)', whiteSpace: 'normal' }}>
      <b>{tip.title}</b>
      {tip.lines.map((l) => <span key={l}>{l}</span>)}
    </div>
  );
}
