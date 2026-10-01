import { fmt } from '../../lib/format';
import { ChartTipBox, useChartTip } from './ChartTip';

export interface DonutDatum {
  label: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  data: DonutDatum[];
  size?: number;
  /** Off where the total is stated elsewhere. A long figure inside the
   *  ring is clipped by it. */
  showCentreTotal?: boolean;
}

/** Ported exactly from the demo's donutHTML() , CSS conic-gradient donut. */
export function DonutChart({ data, size = 148, showCentreTotal = true }: DonutChartProps) {
  const { ref, tip, show, hide } = useChartTip();
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const active = tip ? Number(tip.key) : -1;
  let acc = 0;
  const bounds = data.map((d) => { const a = acc; acc += d.value; return [a / total, acc / total]; });
  // The segment under the pointer stays full colour, the others fade.
  const stops = data
    .map((d, i) => {
      const col = active < 0 || active === i ? d.color : `color-mix(in srgb, ${d.color} 30%, white)`;
      return `${col} ${bounds[i][0] * 100}% ${bounds[i][1] * 100}%`;
    })
    .join(', ');
  const lines = (i: number) => [fmt(data[i].value), `${Math.round((data[i].value / total) * 100)}% of the total`];
  // Which segment the pointer is over, from its angle round the centre.
  function segmentAt(e: React.PointerEvent | React.MouseEvent) {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const x = e.clientX - (r.left + r.width / 2), y = e.clientY - (r.top + r.height / 2);
    if (Math.hypot(x, y) < r.width * 0.3) return -1;
    const turn = ((Math.atan2(x, -y) / (2 * Math.PI)) + 1) % 1;
    return bounds.findIndex(([a, b]) => turn >= a && turn < b);
  }
  function onDonut(e: React.PointerEvent | React.MouseEvent, touch: boolean) {
    const i = segmentAt(e);
    if (i < 0) { if (!touch) hide(); return; }
    show(e, String(i), data[i].label, lines(i), true);
  }

  return (
    <div className="donut-block chart-wrap" ref={ref} onPointerLeave={(e) => { if (e.pointerType === 'mouse') hide(); }}>
      <div className="donut" style={{ width: size, height: size, background: `conic-gradient(${stops})`, cursor: 'pointer' }}
        onPointerMove={(e) => { if (e.pointerType === 'mouse') onDonut(e, false); }}
        onClick={(e) => onDonut(e, true)}>
        <div className="donut-center">
          {showCentreTotal && (
            <>
              <b>{fmt(total)}</b>
              <small>Total</small>
            </>
          )}
        </div>
      </div>
      <ChartTipBox tip={tip} />
      <div className="legend">
        {data.map((d, i) => (
          <div className="legend-item" key={i} style={{ cursor: 'pointer', fontWeight: active === i ? 700 : undefined }}
            onPointerEnter={(e) => { if (e.pointerType === 'mouse') show(e, String(i), d.label, lines(i)); }}
            onClick={(e) => show(e, String(i), d.label, lines(i))}>
            <span className="dot" style={{ background: d.color }} />
            <span>{d.label}</span>
            <b style={{ marginLeft: 'auto' }}>{fmt(d.value)}</b>
          </div>
        ))}
      </div>
    </div>
  );
}
