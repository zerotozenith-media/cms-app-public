import { ChartTipBox, useChartTip } from './ChartTip';

/**
 * Attendance as grouped bars.
 *
 * Grouped rather than stacked, because these are separate services and
 * not a continuous measurement: a stacked bar makes it impossible to
 * follow one group across weeks.
 *
 * The axis follows the data rather than a target. A target is set for
 * the whole congregation, so an axis running to 150 leaves a Bible
 * Study bar of 18 sitting in the bottom third where week to week
 * differences cannot be seen. The target is stated above the chart
 * instead.
 */
export interface BarGroup {
  label: string;
  values: Record<string, number>;
}

export interface BarSeries {
  key: string;
  name: string;
  color: string;
}

export function GroupedBars({ groups, series }: { groups: BarGroup[]; series: BarSeries[] }) {
  // A group nobody attends is left out entirely. Saturday Workers Meeting
  // showing empty Youth and Children entries was noise.
  const { ref, tip, show, hide } = useChartTip();
  const shown = series.filter((s) => groups.some((g) => (g.values[s.key] ?? 0) > 0));
  if (!groups.length || !shown.length) {
    return <div className="empty">Nothing recorded for this meeting and period.</div>;
  }

  const max = Math.max(1, ...groups.flatMap((g) => shown.map((s) => g.values[s.key] ?? 0)));
  const top = Math.ceil(max * 1.12);

  const groupLines = (g: BarGroup) => [
    ...shown.map((s) => `${s.name} ${g.values[s.key] ?? 0}`),
    `Total ${shown.reduce((n, s) => n + (g.values[s.key] ?? 0), 0)}`,
  ];

  return (
    <div className="gbars chart-wrap" ref={ref} onPointerLeave={(e) => { if (e.pointerType === 'mouse') hide(); }}>
      <div className="gbars-plot">
        <div className="gbars-axis">
          {[top, Math.round(top / 2), 0].map((v) => <span key={v}>{v}</span>)}
        </div>
        <div className="gbars-cols">
          {groups.map((g) => (
            <div className={`gbar-group${tip?.key === g.label ? ' active' : ''}`} key={g.label}
              onPointerEnter={(e) => { if (e.pointerType === 'mouse') show(e, g.label, g.label, groupLines(g)); }}
              onClick={(e) => show(e, g.label, g.label, groupLines(g))}>
              <div className="gbar-set">
                {shown.map((s) => (
                  <span key={s.key} className="gbar"
                    style={{
                      height: `${((g.values[s.key] ?? 0) / top) * 100}%`,
                      background: s.color,
                    }} />
                ))}
              </div>
              <span className="gbar-label">{g.label}</span>
            </div>
          ))}
        </div>
      </div>
      <ChartTipBox tip={tip} />
      <div className="gbars-legend">
        {shown.map((s) => (
          <span className="gbl" key={s.key}>
            <i style={{ background: s.color }} />{s.name}
          </span>
        ))}
      </div>
    </div>
  );
}
