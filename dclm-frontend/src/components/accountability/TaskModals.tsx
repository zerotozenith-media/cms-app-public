import { useState } from 'react';
import {
  ATTEMPT_METHODS, AWAY_REASONS, CANCEL_REASONS, REASONS, dayText, refusal, whenText,
  useCancelTask, useChangeDue, useGiveReasons, useRecordResult, useSetAway,
  type PersonType, type ResultPayload, type TaskRow,
} from '../../api/accountability';
import { useFollowUpRules } from '../../api/followupRules';
import { CONTACT_METHODS } from '../../types/members';
import { HelpMark } from '../ui/HelpMark';

function Modal({ label, onClose, children, wide }: { label: string; onClose: () => void; children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="fu-modal fa-modal" role="dialog" aria-modal="true" aria-label={label}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="fu-box" style={wide ? { maxWidth: 720 } : undefined}>{children}</div>
    </div>
  );
}

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const today = () => iso(new Date());
const addDays = (n: number) => { const d = new Date(); d.setDate(d.getDate() + n); return iso(d); };

export function taskTitle(t: Pick<TaskRow, 'missed_meeting_name' | 'missed_date' | 'text' | 'kind'>) {
  if (t.missed_meeting_name && t.missed_date) {
    const d = new Date(`${t.missed_date}T12:00:00`);
    return `Missed ${t.missed_meeting_name}, ${d.getDate()} ${d.toLocaleDateString('en-GB', { month: 'long' })}`;
  }
  return t.text;
}

type Result = ResultPayload['result'];
const RESULTS: [Result, string, string][] = [
  ['reached', 'Reached', 'Visited, called or spoke. The four boxes below are required.'],
  ['tried', 'Tried, could not reach', 'Logged with its date. The task stays open.'],
  ['known-reason', 'Known reason', 'Travelling, sick or working a shift. Closes with the reason.'],
  ['needs-coordinator', 'Needs the Follow-up Coordinator', 'A crisis, a conflict, a family or moral matter.'],
  ['moved-away', 'Moved away or left', 'They no longer attend. No more tasks are made.'],
];

/**
 * Record a result (plan demo 7). One visit closes every open absence task
 * for the person, so the shepherd records it once.
 */
export function RecordResultModal({ task, others, onClose, start = 'reached' }: { task: TaskRow; others: TaskRow[]; onClose: () => void; start?: Result }) {
  const record = useRecordResult();
  const { data: rules } = useFollowUpRules();
  const [result, setResult] = useState<Result>(start);
  const [date, setDate] = useState(today());
  const [how, setHow] = useState('Home visit');
  const [goal, setGoal] = useState('');
  const [scripture, setScripture] = useState('');
  const [root, setRoot] = useState('');
  const [next, setNext] = useState('');
  const [nextDate, setNextDate] = useState('');
  const [method, setMethod] = useState('Phone call');
  const [note, setNote] = useState('');
  const [awayFrom, setAwayFrom] = useState('');
  const [awayTo, setAwayTo] = useState('');
  const [awayReason, setAwayReason] = useState('travelling');
  const [err, setErr] = useState('');
  const [done, setDone] = useState('');

  const closes = [task, ...others.filter((o) => o.id !== task.id && ['absence', 'attendance-falling'].includes(o.kind))];
  const limit = rules?.attempts_before_coordinator ?? 3;

  async function save() {
    setErr('');
    const p: ResultPayload = { result };
    if (result === 'reached') {
      const miss = [!goal.trim() && 'Goal of the visit', !scripture.trim() && 'Scripture shared', !root.trim() && 'Root cause', !next.trim() && 'Next step'].filter(Boolean);
      if (miss.length) { setErr(`Please complete: ${miss.join(', ')}.`); return; }
      Object.assign(p, { contact_date: date, contact_method: how, contact_goal: goal, contact_scripture: scripture, contact_root_cause: root, contact_next_step: next, next_step_date: nextDate || null });
    } else if (result === 'tried') {
      Object.assign(p, { method, note });
    } else {
      p.note = note;
      if (result === 'known-reason' && awayFrom && awayTo) Object.assign(p, { away_from: awayFrom, away_to: awayTo, away_reason: awayReason });
    }
    try {
      const r = await record.mutateAsync({ type: task.type, id: task.id, payload: p });
      if (result === 'tried') {
        const n = r?.attempt_count ?? 0;
        setDone(n >= limit ? `Attempt ${n} logged. After ${limit} attempts the task goes to the Follow-up Coordinator, who has been told.` : `Attempt ${n} of ${limit} logged. The task stays open.`);
        setNote('');
        return;
      }
      onClose();
    } catch (e) { setErr(refusal(e, 'The result could not be saved. Try again.')); }
  }

  return (
    <Modal label={`Record a result: ${task.person}`} onClose={onClose} wide>
      <h3 style={{ margin: '0 0 4px' }}>Record a result: {task.person}</h3>
      {result === 'reached' && closes.length > 1 && (
        <div className="fa-closes">
          <b>This closes {closes.length} open tasks</b><HelpMark topic="faOneVisit" />
          {closes.map((c) => <div key={c.id}>{taskTitle(c)}{c.is_late ? ' (late' + (c.reason ? `, reason given: ${c.reason.reason})` : ')') : ''}</div>)}
        </div>
      )}
      <div className="muted" style={{ fontSize: '.8rem', margin: '6px 0 10px' }}>
        {task.attempts.length
          ? <>Attempts so far: {task.attempts.map((a) => `${a.method.toLowerCase()} on ${whenText(a.at)}`).join('; ')}, no answer. {task.attempts.length} of {limit} before it goes to the Follow-up Coordinator.</>
          : 'No attempts logged yet.'}
      </div>
      <div style={{ fontWeight: 600, fontSize: '.88rem', marginBottom: 6 }}>Result</div>
      <div className="fa-results" role="radiogroup" aria-label="Result">
        {RESULTS.map(([k, t, d]) => (
          <label key={k} className={`fa-opt${result === k ? ' on' : ''}`}>
            <input type="radio" name={`res-${task.id}`} checked={result === k} onChange={() => { setResult(k); setErr(''); setDone(''); }} />
            <span><b>{t}</b><br /><span className="muted">{d}</span></span>
          </label>
        ))}
      </div>
      {result === 'reached' && <>
        <div className="form-row">
          <div className="field"><label htmlFor="rr-how">How</label>
            <select id="rr-how" value={how} onChange={(e) => setHow(e.target.value)}>{CONTACT_METHODS.map((m) => <option key={m}>{m}</option>)}</select></div>
          <div className="field"><label htmlFor="rr-date">When</label><input id="rr-date" type="date" value={date} max={today()} onChange={(e) => setDate(e.target.value)} /></div>
        </div>
        <div className="form-row">
          <div className="field"><label htmlFor="rr-goal">Goal of the visit <span className="req">*</span></label><input id="rr-goal" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="What did you set out to achieve?" /></div>
          <div className="field"><label htmlFor="rr-scr">Scripture shared <span className="req">*</span></label><input id="rr-scr" value={scripture} onChange={(e) => setScripture(e.target.value)} placeholder='Reference, or "None this time"' /></div>
        </div>
        <div className="form-row">
          <div className="field"><label htmlFor="rr-root">Root cause <span className="req">*</span></label><input id="rr-root" value={root} onChange={(e) => setRoot(e.target.value)} placeholder="What is really behind the absence?" /></div>
          <div className="field"><label htmlFor="rr-next">Next step <span className="req">*</span></label><input id="rr-next" value={next} onChange={(e) => setNext(e.target.value)} placeholder="What was agreed, by whom, by when?" /></div>
        </div>
        <div className="field"><label htmlFor="rr-nd">Next step date<HelpMark topic="faNextDate" /></label><input id="rr-nd" type="date" min={today()} value={nextDate} onChange={(e) => setNextDate(e.target.value)} /></div>
      </>}
      {result === 'tried' && (
        <div className="form-row">
          <div className="field"><label htmlFor="rr-m">How you tried</label>
            <select id="rr-m" value={method} onChange={(e) => setMethod(e.target.value)}>{ATTEMPT_METHODS.map((m) => <option key={m}>{m}</option>)}</select></div>
          <div className="field"><label htmlFor="rr-tn">Note (optional)</label><input id="rr-tn" value={note} onChange={(e) => setNote(e.target.value)} placeholder="For example: phone switched off" /></div>
        </div>
      )}
      {result === 'known-reason' && <>
        <div className="field"><label htmlFor="rr-kn">The reason</label><input id="rr-kn" value={note} onChange={(e) => setNote(e.target.value)} placeholder="For example: travelling until 15 November" /></div>
        <div className="muted fr-note" style={{ marginBottom: 6 }}>Away dates are optional. With them, no absence tasks are made while they are away.<HelpMark topic="faAway" /></div>
        <div className="form-row g3">
          <div className="field"><label htmlFor="rr-af">Away from</label><input id="rr-af" type="date" value={awayFrom} onChange={(e) => setAwayFrom(e.target.value)} /></div>
          <div className="field"><label htmlFor="rr-at">Away to</label><input id="rr-at" type="date" min={awayFrom || undefined} value={awayTo} onChange={(e) => setAwayTo(e.target.value)} /></div>
          <div className="field"><label htmlFor="rr-ar">Why away</label>
            <select id="rr-ar" value={awayReason} onChange={(e) => setAwayReason(e.target.value)}>{AWAY_REASONS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
        </div>
      </>}
      {result === 'needs-coordinator' && (
        <div className="field"><label htmlFor="rr-nc">What is the matter? <span className="req">*</span></label>
          <textarea id="rr-nc" rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Briefly, so the Follow-up Coordinator knows what to expect" />
          <div className="muted fr-note">The task goes to the Follow-up Coordinator's Review list, and they are alerted.</div></div>
      )}
      {result === 'moved-away' && (
        <div className="field"><label htmlFor="rr-mv">Note</label><input id="rr-mv" value={note} onChange={(e) => setNote(e.target.value)} placeholder="For example: moved to Saudi Arabia in October" />
          <div className="muted fr-note">{task.type === 'member' ? 'Their status becomes Moved away. They stay in the records for the time they attended.' : 'Their stage becomes Not Interested, which stops follow-up.'}</div></div>
      )}
      {err && <p className="form-error" role="alert">{err}</p>}
      {done && <p className="fr-done" role="status">{done}</p>}
      <div className="form-actions-row" style={{ borderTop: '1px solid var(--line)', paddingTop: 12 }}>
        <button className="btn sm" onClick={save} disabled={record.isPending}>
          {result === 'reached' ? (closes.length > 1 ? `Save and close ${closes.length} tasks` : 'Save and close the task')
            : result === 'tried' ? 'Log the attempt' : 'Save'}
        </button>
        <button className="btn sm ghost" onClick={onClose}>{done ? 'Close' : 'Cancel'}</button>
      </div>
    </Modal>
  );
}

/** Give a reason for each late task (plan demo 8). */
export function GiveReasonsModal({ tasks, onClose }: { tasks: TaskRow[]; onClose: () => void }) {
  const give = useGiveReasons();
  const { data: rules } = useFollowUpRules();
  const [topErr, setTopErr] = useState('');
  const maxDays = rules?.max_new_date_days ?? 7;
  const [rows, setRows] = useState(() => Object.fromEntries(tasks.map((t) => [t.id, { reason: '', note: '', date: addDays(1) }])));
  const [errs, setErrs] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);
  const set = (id: number, k: string, v: string) => setRows((r) => ({ ...r, [id]: { ...r[id], [k]: v } }));

  async function send() {
    const e: Record<number, string> = {};
    tasks.forEach((t) => { if (!rows[t.id].reason) e[t.id] = 'Choose a reason.'; });
    setErrs(e);
    if (Object.keys(e).length) return;
    setBusy(true); setTopErr('');
    try {
      await give.mutateAsync(tasks.map((t) => ({ type: t.type, id: t.id, reason: rows[t.id].reason, note: rows[t.id].note, new_date: rows[t.id].date })));
      onClose();
    } catch (err: any) {
      const items = err?.response?.data?.items ?? {};
      const failed: Record<number, string> = {};
      tasks.forEach((t) => { if (items[`${t.type}-${t.id}`]) failed[t.id] = items[`${t.type}-${t.id}`]; });
      setErrs(failed);
      setTopErr(refusal(err, 'The reasons could not be sent. Try again.'));
    } finally { setBusy(false); }
  }

  return (
    <Modal label="Give a reason for each late task" onClose={onClose}>
      <h3 style={{ margin: '0 0 4px' }}>Give a reason for each late task</h3>
      <p className="muted" style={{ margin: '0 0 12px', fontSize: '.84rem' }}>
        Each late task needs its own reason, even for the same person. Your Follow-up Coordinator sees each one on the Review list.
      </p>
      {tasks.map((t, i) => (
        <div key={t.id} className="fa-reason">
          <b>{t.person}</b>
          <div className="muted" style={{ fontSize: '.82rem', marginBottom: 8 }}>{taskTitle(t)}. Was due {whenText(t.due_at)}</div>
          <div className="field"><label htmlFor={`gr-r-${t.id}`}>Reason</label>
            <select id={`gr-r-${t.id}`} value={rows[t.id].reason} onChange={(e) => set(t.id, 'reason', e.target.value)}>
              <option value="">Choose a reason</option>
              {REASONS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
            </select></div>
          <div className="field"><label htmlFor={`gr-n-${t.id}`}>Short note</label><input id={`gr-n-${t.id}`} value={rows[t.id].note} onChange={(e) => set(t.id, 'note', e.target.value)} /></div>
          <div className="field"><label htmlFor={`gr-d-${t.id}`}>New date{i === 0 && <HelpMark topic="faNewDate" />}</label>
            <input id={`gr-d-${t.id}`} type="date" min={today()} max={addDays(maxDays)} value={rows[t.id].date} onChange={(e) => set(t.id, 'date', e.target.value)} />
            <div className="muted fr-note">Up to {dayText(addDays(maxDays))}</div></div>
          {errs[t.id] && <p className="form-error" role="alert">{errs[t.id]}</p>}
        </div>
      ))}
      {topErr && <p className="form-error" role="alert">{topErr}</p>}
      <div className="form-actions-row">
        <button className="btn sm" onClick={send} disabled={busy}>{tasks.length === 1 ? 'Send the reason' : tasks.length === 2 ? 'Send both reasons' : `Send ${tasks.length} reasons`}</button>
        <button className="btn sm ghost" onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

/** Mark someone away (plan demo 9). */
export function AwayModal({ type, id, name, current, onClose }: {
  type: PersonType; id: number; name: string; onClose: () => void;
  current?: { away_from?: string | null; away_to?: string | null; away_reason?: string; away_note?: string };
}) {
  const setAway = useSetAway();
  const [from, setFrom] = useState(current?.away_from ?? today());
  const [to, setTo] = useState(current?.away_to ?? '');
  const [reason, setReason] = useState(current?.away_reason || 'travelling');
  const [note, setNote] = useState(current?.away_note ?? '');
  const [err, setErr] = useState('');
  const first = name.split(' ')[0];

  async function save() {
    setErr('');
    if (!to) { setErr('Choose the date they are away to.'); return; }
    try { await setAway.mutateAsync({ type, id, away_from: from, away_to: to, away_reason: reason, away_note: note }); onClose(); }
    catch (e) { setErr(refusal(e, 'The away dates could not be saved.')); }
  }
  async function clear() {
    setErr('');
    try { await setAway.mutateAsync({ type, id, clear: true }); onClose(); }
    catch (e) { setErr(refusal(e, 'The away dates could not be cleared.')); }
  }

  return (
    <Modal label={`Mark ${name} as away`} onClose={onClose}>
      <h3 style={{ margin: '0 0 8px' }}>Mark {name} as away<HelpMark topic="faAway" /></h3>
      <div className="form-row">
        <div className="field"><label htmlFor="aw-f">From</label><input id="aw-f" type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></div>
        <div className="field"><label htmlFor="aw-t">To</label><input id="aw-t" type="date" min={from} value={to} onChange={(e) => setTo(e.target.value)} /></div>
      </div>
      <div className="field"><label htmlFor="aw-r">Reason</label>
        <select id="aw-r" value={reason} onChange={(e) => setReason(e.target.value)}>{AWAY_REASONS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
      <div className="field"><label htmlFor="aw-n">Note</label><input id="aw-n" value={note} onChange={(e) => setNote(e.target.value)} placeholder="For example: visiting family in Lagos" /></div>
      {from && to && (
        <div className="fr-box-note">No absence tasks from {dayText(from)} to {dayText(to)}. The Follow-up Coordinator's page lists everyone who is away.</div>
      )}
      {err && <p className="form-error" role="alert">{err}</p>}
      <div className="form-actions-row">
        <button className="btn sm" onClick={save} disabled={setAway.isPending}>Save</button>
        {current?.away_to && <button className="btn sm outline" onClick={clear} disabled={setAway.isPending}>{first} is back</button>}
        <button className="btn sm ghost" onClick={onClose}>Cancel</button>
      </div>
      <div className="muted" style={{ fontSize: '.78rem', marginTop: 8 }}>Their shepherd, a Follow-up Coordinator or an administrator can mark someone away.</div>
    </Modal>
  );
}

/** Cancel a task made in error (plan demo 16). */
export function CancelTaskModal({ task, onClose }: { task: TaskRow; onClose: () => void }) {
  const cancel = useCancelTask();
  const [reason, setReason] = useState('was-at-service');
  const [note, setNote] = useState('');
  const [err, setErr] = useState('');
  async function save() {
    setErr('');
    try { await cancel.mutateAsync({ type: task.type, id: task.id, reason, note }); onClose(); }
    catch (e) { setErr(refusal(e, 'The task could not be cancelled.')); }
  }
  return (
    <Modal label="Cancel this task" onClose={onClose}>
      <h3 style={{ margin: '0 0 4px' }}>Cancel this task</h3>
      <p className="muted" style={{ margin: '0 0 10px', fontSize: '.84rem' }}>{taskTitle(task)}. {task.person}{task.shepherd ? `, shepherd ${task.shepherd}` : ''}.</p>
      <div className="field"><label htmlFor="ct-r">Why was it made in error?</label>
        <select id="ct-r" value={reason} onChange={(e) => setReason(e.target.value)}>{CANCEL_REASONS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
      <div className="field"><label htmlFor="ct-n">Note</label><input id="ct-n" value={note} onChange={(e) => setNote(e.target.value)} placeholder="For example: she sat in the overflow room and was missed" /></div>
      {err && <p className="form-error" role="alert">{err}</p>}
      <div className="form-actions-row">
        <button className="btn sm" onClick={save} disabled={cancel.isPending}>Cancel the task</button>
        <button className="btn sm ghost" onClick={onClose}>Keep it</button>
      </div>
      <div className="muted" style={{ fontSize: '.78rem', marginTop: 8 }}>
        Only a Follow-up Coordinator or an administrator can cancel a task, and a reason is required, because a cancelled task never reaches the shepherd's record. It stays in the Audit Log.
      </div>
    </Modal>
  );
}

/** Change a task's due time (plan demo 18). */
export function ChangeDueForm({ task, onClose }: { task: TaskRow; onClose: () => void }) {
  const change = useChangeDue();
  const now = new Date(Date.now() + 3600_000);
  const [at, setAt] = useState(`${iso(now)}T${String(now.getHours()).padStart(2, '0')}:00`);
  const [why, setWhy] = useState('');
  const [err, setErr] = useState('');
  async function save() {
    setErr('');
    try { await change.mutateAsync({ type: task.type, id: task.id, due_at: at, why }); onClose(); }
    catch (e) { setErr(refusal(e, 'The due time could not be changed.')); }
  }
  return (
    <div className="fa-inline">
      <div className="form-row">
        <div className="field"><label htmlFor={`cd-a-${task.id}`}>New due time<HelpMark topic="faChangeDue" /></label>
          <input id={`cd-a-${task.id}`} type="datetime-local" value={at} onChange={(e) => setAt(e.target.value)} /></div>
        <div className="field"><label htmlFor={`cd-w-${task.id}`}>Why</label>
          <input id={`cd-w-${task.id}`} value={why} onChange={(e) => setWhy(e.target.value)} placeholder="For example: visit agreed for Wednesday evening" /></div>
      </div>
      {err && <p className="form-error" role="alert">{err}</p>}
      <div className="form-actions-row">
        <button className="btn sm" onClick={save} disabled={change.isPending}>Save</button>
        <button className="btn sm ghost" onClick={onClose}>Cancel</button>
      </div>
    </div>
  );
}
