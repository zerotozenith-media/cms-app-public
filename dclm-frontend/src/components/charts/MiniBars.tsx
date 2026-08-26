export interface BarDatum {
  label: string;
  value: number;
}

interface MiniBarsProps {
  data: BarDatum[];
}

/** Ported exactly from the demo's barsHTML(). */
export function MiniBars({ data }: MiniBarsProps) {
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="minibars">
      {data.map((d, i) => (
        <div className="minibar-col" key={i}>
          <div className="minibar-track">
            <div className="minibar-fill" style={{ height: `${Math.max(6, (d.value / max) * 100)}%` }} />
          </div>
          <div className="minibar-val">{d.value}</div>
          <div className="minibar-label">{d.label}</div>
        </div>
      ))}
    </div>
  );
}
