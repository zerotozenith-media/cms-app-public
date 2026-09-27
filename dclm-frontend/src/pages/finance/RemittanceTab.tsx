/**
 * Monthly remittance.
 *
 * Remittance happens once a month, not each time money is received, so
 * this is its own tab rather than a field on every giving entry.
 */
import { useEffect, useState } from 'react';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { useAuth } from '../../context/AuthContext';
import { useMyLocations } from '../../api/locations';
import {
  REMIT_DESTINATIONS, useRemittanceProposal, useRemittances, useSaveRemittance,
  type RemitDestination, type RemittanceLine,
} from '../../api/remittance';

const money = (v: string | number) =>
  Number(v).toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 });

function monthLabel(iso: string) {
  const d = new Date(`${iso.slice(0, 7)}-01T00:00:00`);
  return d.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });
}

/** The last twelve months, newest first. */
function recentMonths(): string[] {
  const out: string[] = [];
  const now = new Date();
  for (let i = 0; i < 12; i += 1) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  }
  return out;
}

export function RemittanceTab() {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('finance', 'create');
  const canEdit = hasPermission('finance', 'edit');
  // Somebody covering several locations chooses whose remittance this is.
  const { data: myLocations } = useMyLocations();
  const [location, setLocation] = useState('');
  const chosen = location || myLocations?.find((l) => l.is_core)?.id || myLocations?.[0]?.id || '';
  const { data: recorded } = useRemittances(chosen);
  const [editing, setEditing] = useState<string | null>(null);

  if (editing) {
    return <RemitForm month={editing} location={chosen} onClose={() => setEditing(null)} />;
  }

  const byMonth = new Map((recorded ?? []).map((r) => [r.month.slice(0, 7), r]));

  return (
    <div className="card">
      <div className="toolbar">
        <div>
          <h3 style={{ flex: 'none' }}>Monthly remittance</h3>
          <p className="muted" style={{ fontSize: '.82rem', margin: 0 }}>
            What was actually sent, month by month.
          </p>
        </div>
        {(myLocations ?? []).length > 1 && (
          <select className="selectbox" value={chosen} aria-label="Whose remittance"
            onChange={(e) => setLocation(e.target.value)}>
            {(myLocations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        )}
      </div>
      <table className="cardtable">
        <thead><tr>
          <th>Month</th><th>Sent</th><th>Date sent</th><th>Reference</th><th>Status</th><th />
        </tr></thead>
        <tbody>
          {recentMonths().map((m) => {
            const r = byMonth.get(m);
            return (
              <tr key={m}>
                <td data-label="Month"><b>{monthLabel(m)}</b></td>
                <td data-label="Sent">{r ? money(r.total_sent) : <span className="muted">-</span>}</td>
                <td data-label="Date sent">{r?.sent_on ?? <span className="muted">-</span>}</td>
                <td data-label="Reference">{r?.reference || <span className="muted">-</span>}</td>
                <td data-label="Status">
                  {r ? <Badge color="green">Sent</Badge> : <Badge color="amber">Not yet sent</Badge>}
                </td>
                <td className="td-actions">
                  {(r ? canEdit : canCreate) && (<button className={`btn sm${r ? ' outline' : ''}`} onClick={() => setEditing(m)}>
                    {r ? 'Edit' : 'Record'}
                  </button>)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="muted" style={{ fontSize: '.8rem', marginTop: 10 }}>
        This records a transfer somebody made. It does not move money.
      </p>
    </div>
  );
}

function RemitForm({ month, location, onClose }: { month: string; location: string; onClose: () => void }) {
  const { data: proposal, isLoading } = useRemittanceProposal(month, location);
  const { data: recorded } = useRemittances(location);
  const save = useSaveRemittance();

  const existing = (recorded ?? []).find((r) => r.month.slice(0, 7) === month);
  const [lines, setLines] = useState<RemittanceLine[] | null>(null);
  const [sentOn, setSentOn] = useState('');
  const [reference, setReference] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');

  // Fill the form once, when the record it describes is known. Setting
  // these while drawing kept re-setting an empty reference, and a month
  // recorded without one sent the page into an endless redraw.
  useEffect(() => {
    if (existing) {
      setSentOn(existing.sent_on);
      setReference(existing.reference);
      setNote(existing.note);
    } else {
      setSentOn(new Date().toISOString().slice(0, 10));
    }
  }, [existing?.id]);

  if (isLoading || !proposal) return <div className="card">Loading…</div>;

  // Start from what was recorded if there is any, otherwise from the
  // figure worked out for the month.
  const rows = lines ?? (existing ? existing.lines : proposal.lines);

  const totalSent = rows.reduce((s, l) => s + Number(l.amount_sent || 0), 0);
  const difference = rows.reduce(
    (s, l) => s + (Number(l.amount_sent || 0) - Number(l.amount_due || 0)), 0);

  function setLine(i: number, patch: Partial<RemittanceLine>) {
    setLines(rows.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  }

  async function submit() {
    setError('');
    try {
      await save.mutateAsync({
        id: existing?.id,
        month: `${month}-01`,
        // Whose money this is, for a new record. An existing one keeps its own.
        ...(existing ? {} : { location }),
        sent_on: sentOn,
        reference,
        note,
        lines: rows.map((l) => ({
          fund: l.fund, amount_due: String(l.amount_due),
          amount_sent: String(l.amount_sent), destination: l.destination,
        })),
      });
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.note?.[0]
        ?? err?.response?.data?.detail
        ?? 'That could not be saved.');
    }
  }

  return (
    <>
      <a className="backlink" onClick={onClose}>← Back to remittance</a>
      <div className="card">
        <h3>{monthLabel(month)}</h3>
        <p className="muted" style={{ fontSize: '.82rem', marginBottom: 16 }}>
          Figures are worked out from the month's records. Change what was actually
          sent if it differs.
        </p>

        <div className="statrow remit-stats" style={{ marginBottom: 18 }}>
          <div className="stat">
            <div className="label">Collected</div>
            <div className="value">{money(proposal.collected)}</div>
          </div>
          <div className="stat">
            <div className="label">Less expenses</div>
            <div className="value" style={{ color: 'var(--red)' }}>{money(proposal.expenses)}</div>
          </div>
          <div className="stat">
            <div className="label">Due to send</div>
            <div className="value" style={{ color: 'var(--blue)' }}>{money(proposal.due)}</div>
          </div>
        </div>

        <table className="cardtable">
          <thead><tr>
            <th>Fund</th><th>Due</th><th>Actually sent</th><th>Sent to</th><th />
          </tr></thead>
          <tbody>
            {rows.map((l, i) => {
              const delta = Number(l.amount_sent || 0) - Number(l.amount_due || 0);
              return (
                <tr key={l.fund}>
                  <td data-label="Fund"><b>{l.fund_name}</b></td>
                  <td data-label="Due"><span className="muted">{money(l.amount_due)}</span></td>
                  <td data-label="Actually sent">
                    <input className="cell-input" type="number" step="0.001" min={0} value={l.amount_sent}
                      aria-label={`Amount of ${l.fund_name} actually sent`}
                      onChange={(e) => setLine(i, { amount_sent: e.target.value })} />
                  </td>
                  <td data-label="Sent to">
                    <select className="selectbox" value={l.destination}
                      aria-label={`Where ${l.fund_name} was sent`}
                      onChange={(e) => setLine(i, { destination: e.target.value as RemitDestination })}>
                      {REMIT_DESTINATIONS.map((d) => (
                        <option key={d.value} value={d.value}>{d.label}</option>
                      ))}
                    </select>
                  </td>
                  <td data-label="">
                    {delta ? (
                      <Badge color={delta > 0 ? 'blue' : 'amber'}>
                        {delta > 0 ? '+' : ''}{delta.toFixed(3)}
                      </Badge>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {Math.abs(difference) > 0.0005 && (
          <div className="followup-guide" style={{ marginTop: 14 }}>
            <div className="followup-guide-title">
              <Icon name="alert" size={14} /> This differs from the figure
              worked out by {money(Math.abs(difference))}
            </div>
            <input className="cell-input" value={note} onChange={(e) => setNote(e.target.value)}
              style={{ marginTop: 8 }}
              placeholder="Why? For example, a member covered this month's rent" />
          </div>
        )}

        <div className="form-row" style={{ marginTop: 14 }}>
          <div className="field">
            <label htmlFor="remit-date">Date sent</label>
            <input id="remit-date" type="date" value={sentOn}
              onChange={(e) => setSentOn(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="remit-ref">Transfer reference</label>
            <input id="remit-ref" value={reference} placeholder="Bank reference"
              onChange={(e) => setReference(e.target.value)} />
          </div>
        </div>

        <div className="session-total">
          <span>Total sent</span><span>{money(totalSent)}</span>
        </div>

        {error && <p className="form-error">{error}</p>}

        <button className="btn" onClick={submit} disabled={save.isPending}>
          {existing ? 'Save changes' : 'Record this remittance'}
        </button>
        <p className="muted" style={{ fontSize: '.8rem', marginTop: 10 }}>
          Both figures are kept, so the report says what was actually sent rather
          than what was expected.
        </p>
      </div>
    </>
  );
}
