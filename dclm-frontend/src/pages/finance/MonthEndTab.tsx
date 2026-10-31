/**
 * Month-end balance (Kay, 30 October 2026).
 *
 * 1. Accounts records giving and expenses through the month.
 * 2. Accounts balances the month: what the records say should be held
 *    against what is counted (or on the bank statement), and sends it.
 * 3. A different person with Approve month-end approves and closes it.
 */
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { refusal } from '../../api/accountability';
import { useMyLocations } from '../../api/locations';
import {
  bhd, useApproveMonthEnd, useMonthEnd, useReopenMonthEnd, useSendBackMonthEnd, useSendMonthEnd,
  type MonthEnd,
} from '../../api/monthEnd';
import { Badge } from '../../components/ui/Badge';
import { HelpMark } from '../../components/ui/HelpMark';
import { Skeleton } from '../../components/ui/Skeleton';
import { mediaUrl } from '../../api/client';

const COLOR = { open: 'amber', sent: 'blue', closed: 'green' } as const;

function thisMonth() {
  const d = new Date();
  // The month just ended is the one to balance, until the last day of this one.
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  const m = d.getDate() === last ? d : new Date(d.getFullYear(), d.getMonth() - 1, 1);
  return `${m.getFullYear()}-${String(m.getMonth() + 1).padStart(2, '0')}`;
}

function when(iso: string | null) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Bahrain' });
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function fieldErr(e: any, f: string): string {
  const v = e?.response?.data?.[f];
  return v ? String(([] as unknown[]).concat(v)[0]) : '';
}

function Line({ label, value, sub, tip, total, color }: { label: string; value: string; sub?: string; tip?: string; total?: boolean; color?: string }) {
  return (
    <tr className={total ? 'me-total' : ''}>
      <td>
        <span className="me-label"><span style={{ fontWeight: total ? 800 : 400 }}>{label}</span>{tip && <HelpMark topic={tip} />}</span>
        {sub && <div className="muted me-sub">{sub}</div>}
      </td>
      <td className="me-amt" style={{ fontWeight: total ? 800 : 600, color }}>{value}</td>
    </tr>
  );
}

function Steps({ cur }: { cur: 1 | 2 | 3 }) {
  const s: [number, string, string][] = [[1, 'Record giving and expenses', 'Accounts'], [2, 'Balance and send for approval', 'Accounts'], [3, 'Approve and close', 'Approve month-end']];
  return (
    <div className="me-steps">
      {s.map(([k, t, r]) => (
        <div key={k} className={`me-step${k === cur ? ' on' : ''}`}><b>{k}. {t}</b><div className="muted">{r}</div></div>
      ))}
    </div>
  );
}

function Statement({ d }: { d: MonthEnd }) {
  const f = d.figures;
  const short = d.label.split(' ')[0];
  const openSub = f.opening_from === 'start' ? `Opening balance set in Admin for ${d.settings.start_label}`
    : f.opening_from === 'previous' ? 'Closing balance of the month before, approved' : 'The month before is not closed yet';
  const remitSub = f.remittances.length
    ? f.remittances.map((r) => `${r.month}, sent ${new Date(r.sent_on).toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })}`).join('. ')
    : 'None sent this month';
  return (
    <table className="me-table">
      <tbody>
        <Line label={`Opening balance, 1 ${short}`} value={f.opening === null ? 'Not known yet' : bhd(f.opening)} sub={openSub} tip="meOpening" />
        <Line label="Plus giving received" value={`+ ${bhd(f.giving)}`} sub={`${f.giving_count} ${f.giving_count === 1 ? 'entry' : 'entries'}, offerings from sessions included`} />
        <Line label="Less expenses" value={`− ${bhd(f.expenses)}`} sub={`${f.expenses_count} ${f.expenses_count === 1 ? 'entry' : 'entries'}`} />
        <Line label="Less remittance sent" value={`− ${bhd(f.remittance)}`} sub={remitSub} tip="meRemit" />
        <Line label="Expected closing balance" value={f.expected === null ? 'Not known yet' : bhd(f.expected)} total tip="meExpected" />
      </tbody>
    </table>
  );
}

export function MonthEndTab() {
  const [params, setParams] = useSearchParams();
  const { data: myLocations } = useMyLocations();
  const [location, setLocation] = useState('');
  const chosen = location || myLocations?.find((l) => l.is_core)?.id || myLocations?.[0]?.id || '';
  const month = params.get('month') || thisMonth();
  const { data: d, isLoading } = useMonthEnd(chosen, month);
  const send = useSendMonthEnd(); const approve = useApproveMonthEnd();
  const sendBack = useSendBackMonthEnd(); const reopen = useReopenMonthEnd();
  const [counted, setCounted] = useState(''); const [c1, setC1] = useState(''); const [c2, setC2] = useState('');
  const [note, setNote] = useState(''); const [file, setFile] = useState<File | null>(null);
  const [backNote, setBackNote] = useState(''); const [showBack, setShowBack] = useState(false);
  const [reason, setReason] = useState(''); const [showReopen, setShowReopen] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [err, setErr] = useState<any>(null);

  useEffect(() => {
    const r = d?.record;
    setCounted(r?.counted_amount ? Number(r.counted_amount).toFixed(3) : '');
    setC1(r?.counted_by_1 ?? ''); setC2(r?.counted_by_2 ?? ''); setNote(r?.difference_note ?? '');
    setErr(null); setShowBack(false); setShowReopen(false); setBackNote(''); setReason(''); setFile(null);
  }, [d?.month, d?.location.id, d?.record?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  function go(m: string) { const p = new URLSearchParams(params); p.set('tab', 'monthend'); p.set('month', m); setParams(p); }

  if (isLoading || !d) return <div className="card"><Skeleton shape="rows" rows={6} /></div>;

  const rec = d.record;
  const status = rec?.status ?? 'open';
  const cash = d.settings.kept_as === 'cash';
  const exp = d.figures.expected === null ? null : Number(d.figures.expected);
  const diff = counted !== '' && exp !== null && !Number.isNaN(Number(counted)) ? Number(counted) - exp : null;
  const short = d.label.split(' ')[0];
  const lastDay = new Date(d.last_day).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });

  async function doSend() {
    const fd = new FormData();
    fd.append('location', chosen); fd.append('month', d!.month); fd.append('counted_amount', counted);
    fd.append('counted_by_1', c1); fd.append('counted_by_2', c2); fd.append('difference_note', note);
    if (file) fd.append('attachment', file);
    setErr(null);
    try { await send.mutateAsync(fd); } catch (e) { setErr(e); }
  }
  async function act(fn: () => Promise<unknown>) { setErr(null); try { await fn(); } catch (e) { setErr(e); } }

  const general = err ? refusal(err, 'It could not be saved.') : '';
  const fe = (f: string) => fieldErr(err, f);

  return (
    <>
      <div className="card">
        <div className="toolbar" style={{ flexWrap: 'wrap', gap: 8 }}>
          <div>
            <h3 style={{ flex: 'none' }}>Month-end balance<HelpMark topic="meBalance" /></h3>
            <p className="muted" style={{ fontSize: '.82rem', margin: 0 }}>
              {d.location.name}. Money kept as {d.settings.kept_as_label.toLowerCase()}, balanced each month from {d.settings.start_label}.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {(myLocations ?? []).length > 1 && (
              <select className="selectbox" aria-label="Location" value={chosen} onChange={(e) => setLocation(e.target.value)}>
                {(myLocations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            )}
            <select className="selectbox" aria-label="Month" value={d.month} onChange={(e) => go(e.target.value)}>
              {d.months.map((m) => <option key={m.month} value={m.month}>{m.label}</option>)}
              {!d.months.some((m) => m.month === d.month) && <option value={d.month}>{d.label}</option>}
            </select>
            <Badge color={COLOR[status]}>{rec?.status_label ?? 'Open'}</Badge>
          </div>
        </div>

        {d.before_start ? (
          <div className="empty">Balancing starts in {d.settings.start_label}, so {d.label} is not balanced. An administrator sets the start month in Admin, Config Lists, Money.</div>
        ) : (
          <>
            <Steps cur={status === 'open' ? (d.ended ? 2 : 1) : 3} />
            {status === 'open' && rec?.sent_back_note && (
              <div className="gender-notice me-notice"><b>Sent back by {rec.sent_back_by}:</b> {rec.sent_back_note}</div>
            )}
            {status === 'open' && rec?.reopen_reason && (
              <div className="gender-notice me-notice"><b>Reopened by {rec.reopened_by} on {when(rec.reopened_at)}:</b> {rec.reopen_reason}</div>
            )}
            <Statement d={d} />

            {status === 'open' && !d.ended && (
              <p className="muted me-gap">{d.label} has not ended. It can be balanced from {lastDay}, its last day. Until then, keep recording giving and expenses on the Giving and expenses tab.</p>
            )}

            {status === 'open' && d.ended && d.can.prepare && (
              <div className="me-form">
                <div className="field">
                  <label htmlFor="me-counted">{cash ? `Cash counted on ${lastDay}` : `Closing balance on the bank statement, ${lastDay}`} (BHD)<HelpMark topic="meCounted" /></label>
                  <input id="me-counted" inputMode="decimal" value={counted} onChange={(e) => { setCounted(e.target.value); setErr(null); }} placeholder="For example 665.250" style={{ maxWidth: 240 }} />
                  {fe('counted_amount') && <p className="form-error">{fe('counted_amount')}</p>}
                </div>
                {cash && (
                  <div className="me-two">
                    <div className="field"><label htmlFor="me-c1">Counted by<HelpMark topic="meCountedBy" /></label><input id="me-c1" value={c1} onChange={(e) => { setC1(e.target.value); setErr(null); }} placeholder="First person" /></div>
                    <div className="field"><label htmlFor="me-c2">And by</label><input id="me-c2" value={c2} onChange={(e) => { setC2(e.target.value); setErr(null); }} placeholder="Second person" />
                      {fe('counted_by_2') && <p className="form-error">{fe('counted_by_2')}</p>}</div>
                  </div>
                )}
                <div className="field">
                  <label htmlFor="me-file">{cash ? 'Photo of the count sheet (optional)' : 'Bank statement (optional)'}</label>
                  <input id="me-file" type="file" accept="image/*,.pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
                </div>
                {diff !== null && Math.abs(diff) >= 0.0005 && (
                  <div className="gender-notice me-notice me-warn">
                    <b>Difference: {bhd(Math.abs(diff))} {diff < 0 ? 'less' : 'more'} than expected.</b>
                    <HelpMark topic="meDifference" /> Look for a missing entry first, such as an expense not recorded. If it cannot be found, explain it below.
                  </div>
                )}
                {diff !== null && Math.abs(diff) < 0.0005 && (
                  <div className="gender-notice me-notice me-ok"><b>It balances.</b> The money held matches the records.</div>
                )}
                {(diff === null || Math.abs(diff) >= 0.0005) && (
                  <div className="field">
                    <label htmlFor="me-note">Explain the difference</label>
                    <textarea id="me-note" rows={2} value={note} onChange={(e) => { setNote(e.target.value); setErr(null); }} placeholder="For example: bank charge of BHD 5.00 on 31 October" />
                    {fe('difference_note') && <p className="form-error">{fe('difference_note')}</p>}
                  </div>
                )}
                <button className="btn" type="button" disabled={send.isPending} onClick={doSend}>Send for approval</button>
                <p className="muted me-gap">An approver, a different person from you, then approves and closes {short}.</p>
              </div>
            )}

            {status === 'open' && d.ended && !d.can.prepare && (
              <p className="muted me-gap">Waiting for the Accounts person to balance {d.label}.</p>
            )}

            {status !== 'open' && rec && (
              <table className="me-table" style={{ marginTop: 6 }}>
                <tbody>
                  <Line label={cash ? `Cash counted, ${lastDay}` : `Bank statement, ${lastDay}`} value={bhd(rec.counted_amount)}
                    sub={cash && rec.counted_by_1 ? `Counted by ${rec.counted_by_1} and ${rec.counted_by_2}` : undefined} />
                  <Line label="Difference" value={bhd(rec.difference)} tip="meDifference"
                    color={Number(rec.difference) === 0 ? 'var(--green)' : 'var(--amber)'} sub={rec.difference_note || undefined} />
                </tbody>
              </table>
            )}

            {status !== 'open' && rec && (
              <p className="me-gap" style={{ fontSize: '.86rem' }}>
                Sent by <b>{rec.prepared_by}</b> on {when(rec.sent_at)}.
                {rec.attachment && <> <a href={mediaUrl(rec.attachment) ?? '#'} target="_blank" rel="noreferrer">{cash ? 'Count sheet' : 'Bank statement'}</a>.</>}
                {status === 'closed' && <> Approved by <b>{rec.approved_by}</b> on {when(rec.approved_at)}.</>}
              </p>
            )}

            {status === 'sent' && d.can.approve && !d.is_preparer && (
              <div className="me-actions">
                <button className="btn" type="button" disabled={approve.isPending}
                  onClick={() => act(() => approve.mutateAsync({ location: chosen, month: d.month }))}>Approve and close {short}</button>
                <button className="btn outline" type="button" onClick={() => setShowBack(!showBack)}>Send back with a note</button>
                <p className="muted me-gap">Closing locks {short}: giving, expenses and remittances dated in {short} can no longer be added, changed or deleted.<HelpMark topic="meLock" /></p>
                {showBack && (
                  <div className="field">
                    <label htmlFor="me-back">What needs correcting?</label>
                    <textarea id="me-back" rows={2} value={backNote} onChange={(e) => setBackNote(e.target.value)} placeholder="For example: the 12 October expense has no receipt" />
                    {fe('note') && <p className="form-error">{fe('note')}</p>}
                    <button className="btn outline" type="button" style={{ marginTop: 8 }} disabled={sendBack.isPending}
                      onClick={() => act(() => sendBack.mutateAsync({ location: chosen, month: d.month, note: backNote }))}>Send back</button>
                  </div>
                )}
              </div>
            )}
            {status === 'sent' && d.is_preparer && (
              <p className="muted me-gap">You prepared {d.label}, so a different person approves it. That way every month is checked by two people.<HelpMark topic="meApprove" /></p>
            )}
            {status === 'sent' && !d.can.approve && !d.is_preparer && (
              <p className="muted me-gap">Waiting for someone whose role includes Approve month-end.<HelpMark topic="meApprove" /></p>
            )}

            {status === 'closed' && d.can.reopen && d.latest_closed === d.month && (
              <div className="me-actions">
                <button className="btn outline" type="button" onClick={() => setShowReopen(!showReopen)}>Reopen {short}</button>
                {showReopen && (
                  <div className="me-reopen">
                    <p className="muted" style={{ margin: '0 0 8px', fontSize: '.84rem' }}>The reason is kept in the Audit Log, and {short} must be balanced and approved again.</p>
                    <div className="field">
                      <label htmlFor="me-reason">Why reopen it?</label>
                      <textarea id="me-reason" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="For example: receipt for the 28 October fuel expense handed in late" />
                      {fe('reason') && <p className="form-error">{fe('reason')}</p>}
                    </div>
                    <button className="btn" type="button" disabled={reopen.isPending}
                      onClick={() => act(() => reopen.mutateAsync({ location: chosen, month: d.month, reason }))}>Reopen {short}</button>
                  </div>
                )}
              </div>
            )}
            {status === 'closed' && d.can.reopen && d.latest_closed !== d.month && (
              <p className="muted me-gap">To reopen {short}, reopen every later closed month first, newest first, because each one opens with the month before's closing balance.</p>
            )}
            {general && !['counted_amount', 'counted_by_2', 'difference_note', 'note', 'reason'].some((f) => fe(f)) && (
              <p className="form-error" role="alert" style={{ marginTop: 10 }}>{general}</p>
            )}
          </>
        )}
      </div>

      <div className="card section-gap">
        <h3>Every month</h3>
        <table className="cardtable">
          <thead><tr><th>Month</th><th>Closing balance</th><th>Difference</th><th>Status</th><th /></tr></thead>
          <tbody>
            {d.months.map((m) => (
              <tr key={m.month}>
                <td data-label="Month"><b>{m.label}</b></td>
                <td data-label="Closing balance">{m.closing ? bhd(m.closing) : <span className="muted">-</span>}</td>
                <td data-label="Difference">{m.difference ? bhd(m.difference) : <span className="muted">-</span>}</td>
                <td data-label="Status"><Badge color={COLOR[m.status]}>{m.status_label}</Badge>
                  {m.approved_by && <div className="muted" style={{ fontSize: '.76rem' }}>Approved by {m.approved_by}</div>}</td>
                <td className="td-actions"><button className="btn sm outline" type="button" onClick={() => { go(m.month); window.scrollTo(0, 0); }}>View</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
