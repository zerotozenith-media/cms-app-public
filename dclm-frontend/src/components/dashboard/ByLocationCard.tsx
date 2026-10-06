import { useNavigate } from 'react-router-dom';

/**
 * Issue 3: with every location in view, each location's share of the
 * church's giving, Friday Worship and newcomers, with totals. Locations are
 * listed by name, each bar measured against the largest.
 */
export interface ByLocationRow {
  location: string; giving?: number; expenses?: number; newcomers?: number;
  worship_latest?: number; worship_date?: string | null;
}

const money = (v: number) => `BHD ${v.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const shortDate = (d?: string | null) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '');

function Measure({ title, rows, value, label, colour, total }: {
  title: string; rows: ByLocationRow[]; value: (r: ByLocationRow) => number; label: (r: ByLocationRow) => string; colour: string; total: string;
}) {
  const max = Math.max(1, ...rows.map(value));
  return (
    <div className="bl-measure">
      <b className="bl-title">{title}</b>
      {rows.map((r) => (
        <div className="bl-row" key={r.location}>
          <span className="bl-name">{r.location}</span>
          <span className="bl-track" aria-hidden="true"><span style={{ width: `${(value(r) / max) * 100}%`, background: colour }} /></span>
          <span className="bl-value">{label(r)}</span>
        </div>
      ))}
      <div className="muted bl-total">Total {total}</div>
    </div>
  );
}

export function ByLocationCard({ rows, periodLabel }: { rows: ByLocationRow[]; periodLabel: string }) {
  const navigate = useNavigate();
  if (!rows || rows.length < 2) return null;
  const has = (k: keyof ByLocationRow) => rows.some((r) => r[k] !== undefined);
  const sum = (k: keyof ByLocationRow) => rows.reduce((a, r) => a + Number(r[k] ?? 0), 0);
  return (
    <div className="card section-gap" id="by-location">
      <h3 style={{ marginBottom: 2 }}>By location</h3>
      <div className="muted" style={{ fontSize: '.84rem', marginBottom: 8 }}>{periodLabel}. Each location's share of the church's total.</div>
      <div className="bl-grid">
        {has('giving') && <Measure title="Giving" rows={rows} value={(r) => r.giving ?? 0} label={(r) => money(r.giving ?? 0)} colour="#1C4E9E" total={money(sum('giving'))} />}
        {has('worship_latest') && <Measure title="Friday Worship, latest" rows={rows} value={(r) => r.worship_latest ?? 0}
          label={(r) => (r.worship_latest ? `${r.worship_latest}${r.worship_date ? `, ${shortDate(r.worship_date)}` : ''}` : 'None yet')} colour="#1E9E64" total={String(sum('worship_latest'))} />}
        {has('newcomers') && <Measure title="Newcomers" rows={rows} value={(r) => r.newcomers ?? 0} label={(r) => String(r.newcomers ?? 0)} colour="#B7791F" total={String(sum('newcomers'))} />}
      </div>
      <a className="card-link-hint" onClick={() => navigate('/reports')}>Go to Reports</a>
    </div>
  );
}
