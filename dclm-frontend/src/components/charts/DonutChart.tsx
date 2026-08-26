import { fmt } from '../../lib/format';

export interface DonutDatum {
  label: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  data: DonutDatum[];
  size?: number;
}

/** Ported exactly from the demo's donutHTML() , CSS conic-gradient donut. */
export function DonutChart({ data, size = 148 }: DonutChartProps) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  let acc = 0;
  const stops = data
    .map((d) => {
      const start = (acc / total) * 100;
      acc += d.value;
      const end = (acc / total) * 100;
      return `${d.color} ${start}% ${end}%`;
    })
    .join(', ');

  return (
    <div className="donut-block">
      <div className="donut" style={{ width: size, height: size, background: `conic-gradient(${stops})` }}>
        <div className="donut-center">
          <b>{fmt(total)}</b>
          <small>Total</small>
        </div>
      </div>
      <div className="legend">
        {data.map((d, i) => (
          <div className="legend-item" key={i}>
            <span className="dot" style={{ background: d.color }} />
            <span>{d.label}</span>
            <b style={{ marginLeft: 'auto' }}>{fmt(d.value)}</b>
          </div>
        ))}
      </div>
    </div>
  );
}
