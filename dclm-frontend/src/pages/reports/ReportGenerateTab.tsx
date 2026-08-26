import { useState } from 'react';
import { useReports, useGenerateReport, useDeleteReport } from '../../api/reports';
import { Icon } from '../../components/ui/Icon';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const now = new Date();

export function ReportGenerateTab() {
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [otherAdditions, setOtherAdditions] = useState('');
  const [error, setError] = useState<string | null>(null);
  const { data: reports } = useReports();
  const generateReport = useGenerateReport();
  const deleteReport = useDeleteReport();

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await generateReport.mutateAsync({ period_month: month, period_year: year, other_additions: otherAdditions });
      setOtherAdditions('');
    } catch (err: any) {
      if (err?.response?.status === 409) {
        setError(`A report for ${MONTHS[month - 1]} ${year} already exists below. Delete it first to regenerate.`);
      } else {
        setError('Could not generate the report. Please try again.');
      }
    }
  }
  async function handleDelete(id: number) {
    if (!confirm('Delete this report?')) return;
    await deleteReport.mutateAsync(id);
  }

  return (
    <>
      <div className="card" style={{ maxWidth: 640, margin: '0 auto' }}>
        <form onSubmit={handleGenerate}>
          <div className="form-row">
            <div className="field">
              <label htmlFor="report-month">Month</label>
              <select id="report-month" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
                {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="report-year">Year</label>
              <input id="report-year" type="number" value={year} onChange={(e) => setYear(Number(e.target.value))} />
            </div>
          </div>
          <h3 className="section-gap">Included sections</h3>
          <p className="muted" style={{ fontSize: '.84rem', margin: '4px 0 12px' }}>
            Every report includes Executive Summary, Attendance, Finance, Testimonies, Challenges, Goals &amp;
            Growth, Other Additions, and Conclusion, compiled from live records at the moment you generate it.
          </p>
          <div className="field">
            <label htmlFor="report-other">Other additions / general comments</label>
            <textarea
              id="report-other" value={otherAdditions} onChange={(e) => setOtherAdditions(e.target.value)}
              placeholder="Anything else leadership should see in this report..."
            />
          </div>
          {error && <p style={{ color: 'var(--red)', fontSize: '.85rem', margin: '4px 0 10px' }}>{error}</p>}
          <button className="btn red" type="submit" disabled={generateReport.isPending}>
            {generateReport.isPending ? 'Generating…' : 'Generate report'}
          </button>
        </form>
      </div>

      <div className="card section-gap">
        <h3>Past reports</h3>
        {reports?.results.length ? (
          <table className="cardtable">
            <thead><tr><th>Period</th><th>Generated</th><th>By</th><th></th><th></th></tr></thead>
            <tbody>
              {reports.results.map((r) => (
                <tr key={r.id}>
                  <td data-label="Period">{MONTHS[r.period_month - 1]} {r.period_year}</td>
                  <td data-label="Generated">{r.generated_at.slice(0, 10)}</td>
                  <td data-label="By">{r.generated_by_name}</td>
                  <td data-label="">
                    <a href={r.pdf_file} target="_blank" rel="noreferrer" className="btn sm outline">
                      <Icon name="doc" size={14} /> View PDF
                    </a>
                  </td>
                  <td className="td-actions">
                    <button className="icon-btn" title="Delete report" onClick={() => handleDelete(r.id)}>
                      <Icon name="trash" size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty">No reports generated yet.</div>
        )}
      </div>
    </>
  );
}
