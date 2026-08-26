export interface StackedBarDatum {
  label: string;
  adults: number;
  youth: number;
  children: number;
}

/** Ported exactly from the demo's stackedBarsHTML(). */
export function StackedBars({ data }: { data: StackedBarDatum[] }) {
  const totals = data.map((d) => d.adults + d.youth + d.children);
  const max = Math.max(...totals, 1);

  return (
    <>
      <div className="stackbars">
        {data.map((d, i) => {
          const total = totals[i];
          const trackPct = Math.max(6, (total / max) * 100);
          const aPct = total ? (d.adults / total) * 100 : 0;
          const yPct = total ? (d.youth / total) * 100 : 0;
          const cPct = total ? (d.children / total) * 100 : 0;
          return (
            <div className="stackbar-col" key={i}>
              <div className="stackbar-track" style={{ height: `${trackPct}%` }}>
                <div className="stackbar-seg" style={{ height: `${aPct}%`, background: 'var(--blue)' }} />
                <div className="stackbar-seg" style={{ height: `${yPct}%`, background: 'var(--amber)' }} />
                <div className="stackbar-seg" style={{ height: `${cPct}%`, background: 'var(--green)' }} />
              </div>
              <div className="minibar-val">{total}</div>
              <div className="minibar-label">{d.label}</div>
            </div>
          );
        })}
      </div>
      <div style={{ display: 'flex', gap: 20, marginTop: 14, flexWrap: 'wrap', justifyContent: 'center' }}>
        <div className="legend-item"><span className="dot" style={{ background: 'var(--blue)' }} />Adults</div>
        <div className="legend-item"><span className="dot" style={{ background: 'var(--amber)' }} />Youth</div>
        <div className="legend-item"><span className="dot" style={{ background: 'var(--green)' }} />Children</div>
      </div>
    </>
  );
}
