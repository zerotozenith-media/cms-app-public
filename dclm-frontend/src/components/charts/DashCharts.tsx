import { useEffect, useRef, useState, type ReactNode } from 'react';

/**
 * The dashboard's charts (redesign approved 10 November 2026, as on DCLM
 * Canada). Drawn at the card's own width, so the text stays the same size
 * on a computer, a tablet and a phone. Every mark has a hover or
 * press-and-hold title with its figures.
 */
export const C = { blue: '#2a78d6', orange: '#eb6834', green: '#1baf7a', yellow: '#eda100', pink: '#e87ba4', grid: '#E8EDF4', ink: '#0F1B2E', muted: '#5A667C', lastYear: '#8A94A6' };
export const SERIES = [C.blue, C.orange, C.green, C.yellow, C.pink];
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
export const mon = (ym: string) => MON[Number(ym.slice(5, 7)) - 1];
export const monLong = (ym: string) => `${LONG[Number(ym.slice(5, 7)) - 1]} ${ym.slice(0, 4)}`;
export const bhd = (n: number | string | null | undefined) => {
  const v = Number(n ?? 0);
  return (Math.abs(v) < 0.005 ? 0 : v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
export const whole = (n: number | null | undefined) => (Math.round(Number(n ?? 0)) || 0).toLocaleString('en-US');

function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [w, setW] = useState(600);
  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const set = () => setW(Math.max(240, Math.round(el.getBoundingClientRect().width)));
    set();
    const ro = new ResizeObserver(set);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

function short(n: number) {
  return Math.abs(n) >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${Math.round(n)}`;
}
function nice(max: number) {
  if (max <= 0) return 1;
  const p = 10 ** Math.floor(Math.log10(max));
  const f = max / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}

function Bar({ x, y, w, h, fill, title }: { x: number; y: number; w: number; h: number; fill: string; title: string }) {
  if (h <= 0) return null;
  const r = Math.min(4, w / 2, h);
  return <path d={`M${x},${y + h}V${y + r}q0,-${r} ${r},-${r}h${w - 2 * r}q${r},0 ${r},${r}V${y + h}z`} fill={fill}><title>{title}</title></path>;
}

/** Giving and expenses by month, with a dark mark at the giving of the same month a year earlier when there are records for it. */
export function MoneyBars({ rows }: { rows: { month: string; giving: string; expenses: string; giving_last_year: string | null; so_far: boolean }[] }) {
  const [ref, W] = useWidth<HTMLDivElement>();
  const H = 220, L = 46, B = 24, T = 8;
  const max = nice(Math.max(1, ...rows.flatMap((r) => [Number(r.giving), Number(r.expenses), Number(r.giving_last_year ?? 0)])) * 1.05);
  const y = (v: number) => T + (H - T - B) * (1 - v / max);
  const cw = (W - L - 4) / rows.length;
  const bw = Math.max(3, Math.min(26, cw * 0.32));
  const every = cw < 34 ? 2 : 1;
  return (
    <div ref={ref} className="dv-chart">
      <svg width={W} height={H} role="img" aria-label="Giving and expenses by month">
        {[0, 1, 2, 3, 4].map((i) => { const v = (max / 4) * i; return <g key={i}><line x1={L} x2={W} y1={y(v)} y2={y(v)} stroke={C.grid} /><text x={L - 6} y={y(v) + 4} textAnchor="end" fontSize="11" fill={C.muted}>{short(v)}</text></g>; })}
        {rows.map((r, i) => {
          const cx = L + i * cw + cw / 2, g = Number(r.giving), x = Number(r.expenses), ly = r.giving_last_year === null ? null : Number(r.giving_last_year);
          const tip = `${monLong(r.month)}${r.so_far ? ' so far' : ''}: giving BHD ${bhd(g)}, expenses BHD ${bhd(x)}${ly !== null ? `, giving a year earlier BHD ${bhd(ly)}` : ''}`;
          return (
            <g key={r.month}>
              <Bar x={cx - bw - 1} y={y(g)} w={bw} h={y(0) - y(g)} fill={C.blue} title={tip} />
              <Bar x={cx + 1} y={y(x)} w={bw} h={y(0) - y(x)} fill={C.orange} title={tip} />
              {ly !== null && ly > 0 && <rect x={cx - bw - 4} y={y(ly) - 1.5} width={bw + 6} height={3} rx={1} fill={C.ink} stroke="#fff" strokeWidth={1}><title>{tip}</title></rect>}
              {i % every === 0 && <text x={cx} y={H - 6} textAnchor="middle" fontSize="11" fill={C.muted}>{mon(r.month)}{r.so_far && cw >= 70 ? ' (so far)' : ''}</text>}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** Average attendance by month as a line. A month with nothing recorded is a shaded gap marked "Not recorded", never 0. */
export function AttendanceLine({ months, today }: { months: { month: string; attendance: number | null }[]; today: string }) {
  const [ref, W] = useWidth<HTMLDivElement>();
  const H = 190, L = 40, B = 22, T = 16, R = 14;
  const max = nice(Math.max(1, ...months.map((m) => m.attendance ?? 0)) * 1.1);
  const y = (v: number) => T + (H - T - B) * (1 - v / max);
  const step = months.length > 1 ? (W - L - R) / (months.length - 1) : 0;
  const X = (i: number) => (months.length > 1 ? L + i * step : (L + W - R) / 2);
  const every = step && step < 30 ? 2 : 1;
  const now = today.slice(0, 7);
  const segs: [number, number][][] = [];
  let cur: [number, number][] = [];
  months.forEach((m, i) => { if (m.attendance === null) { if (cur.length) segs.push(cur); cur = []; } else cur.push([X(i), y(m.attendance)]); });
  if (cur.length) segs.push(cur);
  const gaps: [number, number][] = [];
  months.forEach((m, i) => {
    if (m.attendance !== null || m.month > now) return;
    const g = gaps[gaps.length - 1];
    if (g && g[1] === i - 1) g[1] = i; else gaps.push([i, i]);
  });
  let last = -1;
  months.forEach((m, i) => { if (m.attendance !== null) last = i; });
  return (
    <div ref={ref} className="dv-chart">
      <svg width={W} height={H} role="img" aria-label="Average attendance by month">
        {[0, 1, 2, 3].map((i) => { const v = (max / 3) * i; return <g key={i}><line x1={L} x2={W} y1={y(v)} y2={y(v)} stroke={C.grid} /><text x={L - 6} y={y(v) + 4} textAnchor="end" fontSize="11" fill={C.muted}>{whole(v)}</text></g>; })}
        {months.map((m, i) => i % every === 0 && <text key={m.month} x={X(i)} y={H - 5} textAnchor="middle" fontSize="11" fill={C.muted}>{mon(m.month)}</text>)}
        {gaps.map(([a, z]) => {
          const half = step / 2 || 20;
          const x0 = Math.max(L, X(a) - half), x1 = Math.min(W, X(z) + half), wide = x1 - x0 >= 64;
          return (
            <g key={`gap${a}`}>
              <rect x={x0} y={T} width={Math.max(6, x1 - x0)} height={H - T - B} fill="#F4F8FE" />
              {wide && <text x={(x0 + x1) / 2} y={y(max / 2)} textAnchor="middle" fontSize="11" fill={C.muted}>Not recorded</text>}
              <title>{a === z ? `${monLong(months[a].month)}: nothing recorded` : `${monLong(months[a].month)} to ${monLong(months[z].month)}: nothing recorded`}</title>
            </g>
          );
        })}
        {segs.map((s, i) => s.length > 1 && <polyline key={i} points={s.map((p) => p.join(',')).join(' ')} fill="none" stroke={C.blue} strokeWidth={2.5} strokeLinejoin="round" />)}
        {months.map((m, i) => m.attendance !== null && (
          <circle key={m.month} cx={X(i)} cy={y(m.attendance)} r={i === last ? 5 : 3.5} fill={C.blue} stroke="#fff" strokeWidth={i === last ? 2 : 1}>
            <title>{`${monLong(m.month)}: ${whole(m.attendance)} on average`}</title>
          </circle>))}
        {last >= 0 && <text x={X(last)} y={y(months[last].attendance ?? 0) - 10} textAnchor="middle" fontSize="12" fontWeight="700" fill="#082C69">{whole(months[last].attendance)}</text>}
      </svg>
    </div>
  );
}

/** Small bars with their figure on top (newcomers by month). */
export function CountBars({ rows, color = C.green, label }: { rows: { month: string; n: number }[]; color?: string; label: string }) {
  const [ref, W] = useWidth<HTMLDivElement>();
  const H = 140, B = 20, T = 18, L = 4;
  const max = Math.max(1, ...rows.map((r) => r.n));
  const cw = (W - L * 2) / Math.max(1, rows.length);
  const bw = Math.min(28, cw * 0.6);
  const every = cw < 26 ? 2 : 1;
  return (
    <div ref={ref} className="dv-chart">
      <svg width={W} height={H} role="img" aria-label={label}>
        <line x1={L} x2={W - L} y1={H - B} y2={H - B} stroke={C.grid} />
        {rows.map((r, i) => {
          const h = ((H - B - T) * r.n) / max, x = L + i * cw + (cw - bw) / 2;
          return (
            <g key={r.month}>
              <Bar x={x} y={H - B - h} w={bw} h={h} fill={color} title={`${monLong(r.month)}: ${whole(r.n)}`} />
              {r.n > 0 && <text x={x + bw / 2} y={H - B - h - 5} textAnchor="middle" fontSize="10.5" fill={C.muted}>{r.n}</text>}
              {i % every === 0 && <text x={x + bw / 2} y={H - 5} textAnchor="middle" fontSize="11" fill={C.muted}>{mon(r.month)}</text>}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/** A donut of up to 5 shares, with the total in the middle and the list beside it. */
export function Donut({ parts, centre, sub, amounts }: { parts: { label: string; amount: number }[]; centre: string; sub: string; amounts?: boolean }) {
  const total = parts.reduce((a, p) => a + p.amount, 0);
  const shown = parts.filter((p) => p.amount > 0);
  const cx = 80, cy = 80, r = 62, ri = 40;
  let a = -Math.PI / 2;
  const pt = (rad: number, ang: number) => `${cx + rad * Math.cos(ang)},${cy + rad * Math.sin(ang)}`;
  const gap = shown.length > 1 ? 0.03 : 0;
  return (
    <div className={`dv-donut${amounts ? ' amounts' : ''}`}>
      <svg viewBox="0 0 160 160" width="140" height="140" role="img" aria-label="Share of giving by fund">
        {shown.length === 1 ? <circle cx={cx} cy={cy} r={(r + ri) / 2} fill="none" stroke={SERIES[parts.indexOf(shown[0])]} strokeWidth={r - ri}><title>{`${shown[0].label}: 100%`}</title></circle>
          : shown.map((p) => {
            const share = p.amount / total, e = a + share * Math.PI * 2 - gap, lg = e - a > Math.PI ? 1 : 0;
            const d = `M${pt(r, a)}A${r},${r} 0 ${lg} 1 ${pt(r, e)}L${pt(ri, e)}A${ri},${ri} 0 ${lg} 0 ${pt(ri, a)}z`;
            a = e + gap;
            return <path key={p.label} d={d} fill={SERIES[parts.indexOf(p) % SERIES.length]}><title>{`${p.label}: BHD ${bhd(p.amount)} (${Math.round(share * 100)}%)`}</title></path>;
          })}
        <text x="80" y="78" textAnchor="middle" fontSize="15" fontWeight="700" fill="#082C69">{centre}</text>
        <text x="80" y="95" textAnchor="middle" fontSize="10.5" fill={C.muted}>{sub}</text>
      </svg>
      <div className="dv-donut-list">
        {parts.map((p, i) => (
          <div key={p.label} className="dv-donut-row"><i style={{ background: SERIES[i % SERIES.length] }} /><span className="nm">{p.label}</span>
            {amounts && <span className="amt">{bhd(p.amount)}</span>}<b>{total > 0 ? `${Math.round((p.amount / total) * 100)}%` : '0%'}</b></div>
        ))}
        {amounts && <div className="dv-donut-row tot"><i aria-hidden="true" /><span className="nm">Total</span><span className="amt">{bhd(total)}</span><b>100%</b></div>}
      </div>
    </div>
  );
}

/** Rows of a label, a bar and a figure. */
export function BarRows({ rows }: { rows: { label: ReactNode; value: number; max: number; figure: string; color?: string; title?: string }[] }) {
  return (
    <div className="dv-rows">
      {rows.map((r, i) => (
        <div className="dv-row" key={i} title={r.title}>
          <span className="dv-row-label">{r.label}</span>
          <span className="dv-track"><i style={{ width: `${r.max > 0 ? Math.min(100, (r.value / r.max) * 100) : 0}%`, background: r.color ?? C.blue }} /></span>
          <b>{r.figure}</b>
        </div>
      ))}
    </div>
  );
}

export function Legend({ items }: { items: { label: string; kind?: 'box' | 'tick'; color?: string }[] }) {
  return (
    <div className="dv-legend">
      {items.map((it) => <span key={it.label}><i className={`dv-key ${it.kind ?? 'box'}`} style={it.kind === 'tick' ? undefined : { background: it.color }} />{it.label}</span>)}
    </div>
  );
}
