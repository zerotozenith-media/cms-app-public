import { useEffect, useMemo, useState } from 'react';
import { useReports, useGenerateReport, useDeleteReport, useLastReportText, previewReport, downloadZonalSpreadsheet } from '../../api/reports';
import type { ReportKind } from '../../types/reports';
import { Icon } from '../../components/ui/Icon';
import { useAuth } from '../../context/AuthContext';
import { useMyLocations } from '../../api/locations';
import { Skeleton } from '../../components/ui/Skeleton';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const MAX_MONTHS = 12;
type Ym = { y: number; m: number };
const key = ({ y, m }: Ym) => `${y}-${String(m).padStart(2, '0')}`;
const parse = (k: string): Ym => ({ y: Number(k.slice(0, 4)), m: Number(k.slice(5, 7)) });
const count = (a: Ym, b: Ym) => (b.y - a.y) * 12 + b.m - a.m + 1;

/** The last two years of months, newest first, up to this month. */
function monthOptions(): Ym[] {
  const now = new Date();
  const out: Ym[] = [];
  let y = now.getFullYear(), m = now.getMonth() + 1;
  for (let i = 0; i < 24; i++) {
    out.push({ y, m });
    m -= 1;
    if (!m) { m = 12; y -= 1; }
  }
  return out;
}

/** The same words the server uses for the title. */
function periodWords(a: Ym, b: Ym) {
  const n = count(a, b);
  let label: string;
  if (n === 1) label = `${MONTHS[a.m - 1]} ${a.y}`;
  else if (n === 12 && a.m === 1) label = String(a.y);
  else if (a.y === b.y) label = `${MONTHS[a.m - 1]} to ${MONTHS[b.m - 1]} ${b.y}`;
  else label = `${MONTHS[a.m - 1]} ${a.y} to ${MONTHS[b.m - 1]} ${b.y}`;
  const kind = ({ 1: 'Monthly', 3: 'Quarterly', 6: 'Half-Year', 12: 'Annual' } as Record<number, string>)[n] ?? '';
  return { n, label, kind };
}

const TEXT_BOXES = [
  { key: 'summary', label: 'Summary', help: 'Opens the report, after the headline figures.', rows: 3 },
  { key: 'challenges', label: 'Challenges and responses', help: 'What is hard, and what the church is doing about it.', rows: 3 },
  { key: 'training', label: 'Worker training and assumptions (optional)', help: 'Shown under the goals.', rows: 2 },
  { key: 'conclusion', label: 'Conclusion', help: 'Closes the report.', rows: 2 },
] as const;
type TextKey = typeof TEXT_BOXES[number]['key'];
const EMPTY: Record<TextKey, string> = { summary: '', challenges: '', training: '', conclusion: '' };

export function ReportGenerateTab() {
  // Controls a person cannot use are not shown.
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('reports', 'create');
  const canDelete = hasPermission('reports', 'delete');
  // Whose figures. Somebody covering several locations may choose the
  // whole church or one location; somebody limited to one always gets theirs.
  const { data: myLocations } = useMyLocations();
  const options = useMemo(monthOptions, []);
  const lastMonth = options[1] ?? options[0];
  const [kind, setKind] = useState<ReportKind>('overseer');
  const [from, setFrom] = useState(key(lastMonth));
  const [to, setTo] = useState(key(lastMonth));
  const [scope, setScope] = useState('');
  const [texts, setTexts] = useState<Record<TextKey, string>>(EMPTY);
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState<'' | 'preview' | 'sheet'>('');
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const { data: reports } = useReports();
  const { data: last } = useLastReportText(scope, kind === 'overseer' && canCreate);
  const generateReport = useGenerateReport();
  const deleteReport = useDeleteReport();

  // What was written last time, brought forward, unless already changed here.
  useEffect(() => {
    if (last && !touched) setTexts({ summary: last.summary, challenges: last.challenges, training: last.training, conclusion: last.conclusion });
  }, [last, touched]);

  const a = parse(from), b = parse(to);
  const order = count(a, b);
  const words = periodWords(a, b);
  const rangeError = order < 1 ? 'The first month must come before the last month.'
    : order > MAX_MONTHS ? `A report can cover up to ${MAX_MONTHS} months.` : null;
  const many = order > 1;
  const title = kind === 'overseer'
    ? `DCLM Bahrain ${words.kind ? `${words.kind} ` : ''}Report, ${words.label}`
    : `DCLM Bahrain Monthly Report${many ? 's' : ''}, ${words.label}`;

  function payload() {
    return {
      kind, from_year: a.y, from_month: a.m, to_year: b.y, to_month: b.m,
      ...(scope ? { location: scope } : {}),
      ...(kind === 'overseer' && canCreate ? texts : {}),
    };
  }
  function explain(err: any, fallback: string) {
    const d = err?.response?.data;
    const msg = typeof d?.detail === 'string' ? d.detail : Array.isArray(d?.detail) ? d.detail[0] : null;
    return msg || fallback;
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setError(null); setDone(null);
    if (rangeError) { setError(rangeError); return; }
    try {
      await generateReport.mutateAsync(payload());
      setDone(`${title} is ready. It is at the top of Past reports.`);
    } catch (err: any) {
      setError(explain(err, 'The report could not be made. Please try again.'));
    }
  }
  async function handlePreview() {
    setError(null); setDone(null);
    if (rangeError) { setError(rangeError); return; }
    // A browser that shows PDFs gets it in a new tab, opened straight away
    // so a phone does not block it as a pop-up. One that cannot show PDFs,
    // such as Chrome on Android, saves it under a proper name instead.
    const canShow = (navigator as Navigator & { pdfViewerEnabled?: boolean }).pdfViewerEnabled !== false;
    const win = canShow ? window.open('', '_blank') : null;
    setBusy('preview');
    try {
      const { url, filename } = await previewReport(payload());
      if (win) {
        win.location.href = url;
      } else {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.click();
      }
    } catch (err: any) {
      win?.close();
      setError(explain(err, 'The preview could not be made. Please try again.'));
    } finally { setBusy(''); }
  }
  async function handleSheet() {
    setError(null); setDone(null);
    if (rangeError) { setError(rangeError); return; }
    setBusy('sheet');
    try { await downloadZonalSpreadsheet(from, to, scope || undefined); }
    catch (err: any) { setError(explain(err, 'The spreadsheet could not be made. Please try again.')); }
    finally { setBusy(''); }
  }
  async function handleDelete(id: number) {
    if (!confirm('Delete this report?')) return;
    await deleteReport.mutateAsync(id);
  }

  const filled = kind === 'overseer' ? [
    'At a glance: Friday average, giving, net, members, congregation',
    'Attendance by meeting, with charts by age group',
    "Special programmes: GCK and Ministers' Renewal, with dates and averages",
    'Giving and expenses by fund and category, and key ratios',
    'Membership and outreach: members on the roll, newcomers being followed up, contacts not yet visited, workers',
    'Testimonies recorded in the period',
    'Goals and plans: each goal with its target date and how it is measured, from the Goals page',
    ...(many ? ['Month-by-month tables and the change from first to last month'] : []),
    "Appendix: every service and each month's finances",
  ] : [
    'Weekly fellowship attendance by men, women, youth, children and newcomers',
    'Attendance summary: services, average, highest and lowest',
    'Giving by service and fund',
    "Workers' and leaders' meetings, male and female",
    "GCK and Ministers' Renewal attendance",
    'Expenditures, and the financial summary with amounts sent to the DLBC account',
    ...(many ? ['Monthly totals across the period, with charts'] : []),
  ];

  return (
    <>
      <div className="card report-card">
        <h3>Generate a report</h3>
        <form onSubmit={handleGenerate}>
          <div className="field" style={{ marginTop: 10 }}>
            <label id="report-kind-label">Report type</label>
            <div className="viewtoggle report-kinds" role="group" aria-labelledby="report-kind-label">
              <button type="button" className={kind === 'overseer' ? 'on' : ''} aria-pressed={kind === 'overseer'}
                onClick={() => { setKind('overseer'); setDone(null); setError(null); }}>Overseer report</button>
              <button type="button" className={kind === 'zonal' ? 'on' : ''} aria-pressed={kind === 'zonal'}
                onClick={() => { setKind('zonal'); setDone(null); setError(null); }}>Zonal monthly</button>
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="report-from">From</label>
              <select id="report-from" value={from} onChange={(e) => setFrom(e.target.value)}>
                {options.map((o) => <option key={key(o)} value={key(o)}>{MONTHS[o.m - 1]} {o.y}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="report-to">To</label>
              <select id="report-to" value={to} onChange={(e) => setTo(e.target.value)}>
                {options.map((o) => <option key={key(o)} value={key(o)}>{MONTHS[o.m - 1]} {o.y}</option>)}
              </select>
            </div>
          </div>
          {(myLocations ?? []).length > 1 && (
            <div className="field">
              <label htmlFor="report-scope">Covers</label>
              <select id="report-scope" value={scope} onChange={(e) => { setScope(e.target.value); setTouched(false); }}>
                <option value="">All locations</option>
                {(myLocations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name} only</option>)}
              </select>
            </div>
          )}
          {rangeError ? (
            <p className="form-error" role="alert">{rangeError}</p>
          ) : (
            <div className="report-title"><span>Report title</span><b>{title}</b></div>
          )}

          <h3 className="section-gap">{kind === 'overseer' ? 'Filled in from the system' : 'Filled in from the system, for each month'}</h3>
          <ul className="report-filled">
            {filled.map((f) => <li key={f}><Icon name="check" size={14} />{f}</li>)}
          </ul>
          {kind === 'overseer' && !many && (
            <p className="muted report-note">One month chosen, so the month-by-month tables and the change chart are left out.</p>
          )}
          {kind === 'zonal' && (
            <p className="muted report-note">Nothing to type. Services that gave way to GCK are marked GCK.</p>
          )}

          {kind === 'overseer' && canCreate && (
            <>
              <h3 className="section-gap">Written by you</h3>
              <p className="muted report-note">
                {last?.from_report
                  ? `Brought forward from your last overseer report (${last.from_report}), so you only change what is new. Leave a box empty to leave that part out.`
                  : 'Leave a box empty to leave that part out. What you write is brought forward into your next overseer report.'}
              </p>
              {TEXT_BOXES.map((t) => (
                <div className="field" key={t.key}>
                  <label htmlFor={`report-${t.key}`}>{t.label}</label>
                  <textarea id={`report-${t.key}`} rows={t.rows} maxLength={6000} value={texts[t.key]}
                    onChange={(e) => { setTouched(true); setTexts({ ...texts, [t.key]: e.target.value }); }} />
                  <span className="muted field-note">{t.help}</span>
                </div>
              ))}
            </>
          )}

          {error && <p className="form-error" role="alert">{error}</p>}
          {done && <p className="report-done" role="status">{done}</p>}
          <div className="report-actions">
            <button className="btn outline" type="button" disabled={!!busy} onClick={handlePreview}>
              {busy === 'preview' ? 'Preparing…' : 'Preview'}
            </button>
            {canCreate && (
              <button className="btn red" type="submit" disabled={generateReport.isPending}>
                {generateReport.isPending ? 'Generating…' : 'Generate report'}
              </button>
            )}
            {kind === 'zonal' && (
              <button className="btn outline" type="button" disabled={!!busy} onClick={handleSheet}>
                {busy === 'sheet' ? 'Preparing…' : 'Spreadsheet'}
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="card section-gap report-card">
        <h3>Past reports</h3>
        {reports?.results.length ? (
          <table className="cardtable">
            <thead><tr><th>Report</th><th>Period</th><th>Covers</th><th></th><th></th></tr></thead>
            <tbody>
              {reports.results.map((r) => (
                <tr key={r.id}>
                  <td data-label="Report">{r.kind_label}</td>
                  <td data-label="Period">{r.period_label}</td>
                  <td data-label="Covers">{r.location_name ? `${r.location_name} only` : 'All locations'}</td>
                  <td data-label="">
                    <a href={r.pdf_file} target="_blank" rel="noreferrer" className="btn sm outline">
                      <Icon name="doc" size={14} /> Open PDF
                    </a>
                  </td>
                  <td className="td-actions">
                    {canDelete && (
                      <button className="icon-btn" title="Delete report" onClick={() => handleDelete(r.id)}>
                        <Icon name="trash" size={14} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : !reports ? <Skeleton shape="rows" rows={4} /> : (
          <div className="empty">No reports generated yet.</div>
        )}
      </div>
    </>
  );
}
