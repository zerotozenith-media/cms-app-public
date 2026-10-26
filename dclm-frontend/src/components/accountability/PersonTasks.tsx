import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { refusal, taskBase, useDecide, useEligible, useFollowUpAccess, whenText, type PersonType, type TaskRow } from '../../api/accountability';
import { CancelTaskModal, ChangeDueForm, RecordResultModal, taskTitle } from './TaskModals';
import { HelpMark } from '../ui/HelpMark';
import { Skeleton } from '../ui/Skeleton';
import { useAuth } from '../../context/AuthContext';

interface ApiTask {
  id: number;
  text: string;
  kind: string;
  kind_label: string;
  done: boolean;
  created_at: string | null;
  due_at: string | null;
  due_date: string;
  is_late: boolean;
  result: string;
  result_label: string;
  result_note: string;
  closed_at: string | null;
  missed_meeting_name: string;
  missed_date: string | null;
  missed_in_row: number;
  escalation: string;
  escalation_label: string;
  needs_reason: boolean;
  handed_from: number | null;
  assigned_to: number | null;
  assigned_to_name?: string;
  shepherd_name?: string;
  attempts: { id: number; at: string; method: string; note: string; by: string }[];
  reviews: { reason: string; reason_note: string; new_date: string | null; given_by: string; given_at: string | null; choice: string; choice_note: string; handed_to: string; decided_by: string; decided_at: string | null }[];
}

/** The shape the task modals take, from a task as the API lists it. */
function asRow(t: ApiTask, type: PersonType, personId: number, person: string): TaskRow {
  return {
    type, id: t.id, person_id: personId, person, person_kind: '', location: '', text: t.text, kind: t.kind, kind_label: t.kind_label,
    missed_meeting_name: t.missed_meeting_name, missed_date: t.missed_date, missed_in_row: t.missed_in_row, due_at: t.due_at,
    due_date: t.due_date, is_late: t.is_late, needs_reason: t.needs_reason, on_review: false, decide_by: null,
    escalation: t.escalation, escalation_label: t.escalation_label, result_note: t.result_note, shepherd_id: t.assigned_to,
    shepherd: t.assigned_to_name ?? t.shepherd_name ?? '', handed_from: t.handed_from ? 'yes' : '',
    attempts: t.attempts.map((a) => ({ date: a.at, at: a.at, method: a.method, note: a.note })), reason: null, last_choice: null,
  };
}

function HandOn({ row, onClose }: { row: TaskRow; onClose: () => void }) {
  const eligible = useEligible(row.type, row.id, true);
  const decide = useDecide();
  const [to, setTo] = useState('');
  const [err, setErr] = useState('');
  async function save() {
    setErr('');
    try { await decide.mutateAsync({ type: row.type, id: row.id, choice: 'hand-on', handed_to: Number(to) }); onClose(); }
    catch (e) { setErr(refusal(e, 'The task could not be handed on.')); }
  }
  return (
    <div className="fa-inline">
      <div className="field"><label htmlFor={`pho-${row.id}`}>Hand this task to<HelpMark topic="faHandOn" /></label>
        <select id={`pho-${row.id}`} value={to} onChange={(e) => setTo(e.target.value)}>
          <option value="">Choose a shepherd</option>
          {(eligible.data?.results ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
        {eligible.data && <div className="muted fr-note">{eligible.data.why}</div>}
      </div>
      {err && <p className="form-error" role="alert">{err}</p>}
      <div className="form-actions-row">
        <button className="btn sm" onClick={save} disabled={!to || decide.isPending}>Hand on</button>
        <button className="btn sm ghost" onClick={onClose}>Cancel</button>
      </div>
    </div>
  );
}

function Event({ when, children }: { when: string | null; children: React.ReactNode }) {
  return <div className="fa-ev"><span className="muted">{when ? whenText(when) : ''}</span><span>{children}</span></div>;
}

/**
 * Tasks tab on a profile (plan demo 17): every task with its attempts,
 * reasons and decisions kept on it, and for a Follow-up Coordinator or an
 * administrator, Hand to another shepherd, Change due time and Cancel.
 */
export function PersonTasks({ type, personId, person }: { type: PersonType; personId: number; person: string }) {
  const { data: access } = useFollowUpAccess();
  const { user: me } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: [type === 'member' ? 'member-followup-tasks' : 'newcomer-tasks', 'person', personId],
    queryFn: async () => {
      const r = await apiClient.get(`${taskBase(type)}/`, { params: { [type]: personId, page_size: 100 } });
      return (Array.isArray(r.data) ? r.data : r.data.results) as ApiTask[];
    },
  });
  const [open, setOpen] = useState<{ id: number; what: 'hand' | 'due' | 'cancel' | 'record' } | null>(null);
  const manage = !!access?.can_review;

  if (isLoading) return <Skeleton shape="list" />;
  const tasks = [...(data ?? [])].sort((a, b) => Number(a.done) - Number(b.done) || (b.created_at ?? '').localeCompare(a.created_at ?? ''));
  if (!tasks.length) return <div className="empty">No follow-up tasks yet.</div>;
  const openRows = tasks.filter((t) => !t.done).map((t) => asRow(t, type, personId, person));

  return (
    <>
      <p className="muted" style={{ fontSize: '.8rem', margin: '0 0 8px' }}>Every attempt, reason and decision is kept on the task.</p>
      {tasks.map((t) => {
        const row = asRow(t, type, personId, person);
        const color = t.done ? (t.result === 'reached' ? 'green' : 'gray') : t.needs_reason ? 'red' : t.is_late ? 'amber' : 'blue';
        const label = t.done ? `Done, ${t.result_label || 'closed'}` : t.needs_reason ? 'Late: reason needed' : t.is_late ? 'Late' : `Due ${whenText(t.due_at)}`;
        const handed = t.reviews.filter((r) => r.choice === 'Hand to another shepherd').slice(-1)[0];
        return (
          <div key={t.id} className="card fu-card fa-person">
            <div className="fa-person-head"><b>{taskTitle(row)}</b><span className={`badge ${color}`}>{label}</span>
              {handed && !t.done && <span className="badge blue">Handed to {handed.handed_to}</span>}
              {t.escalation && !t.done && <span className="badge amber">{t.escalation_label}</span>}
            </div>
            <Event when={t.created_at}>Made for {t.assigned_to_name || t.shepherd_name || 'nobody yet'}{t.due_at ? `, due ${whenText(t.due_at)}` : ''}</Event>
            {t.attempts.map((a) => <Event key={a.id} when={a.at}>{a.method}, no answer{a.by ? ` (${a.by})` : ''}{a.note ? `. "${a.note}"` : ''}</Event>)}
            {t.reviews.map((r, i) => (
              <div key={i}>
                {r.reason && <Event when={r.given_at}>Reason from {r.given_by}: {r.reason}.{r.reason_note ? ` "${r.reason_note}"` : ''}{r.new_date ? ` New date ${new Date(`${r.new_date}T12:00:00`).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}` : ''}</Event>}
                {r.choice && <Event when={r.decided_at}>{r.decided_by}: {r.choice}{r.handed_to ? ` to ${r.handed_to}. ${person} keeps their shepherd` : ''}{r.choice_note ? `. "${r.choice_note}"` : ''}</Event>}
              </div>
            ))}
            {t.done && <Event when={t.closed_at}>{t.result_label || 'Closed'}{t.result_note ? `. ${t.result_note}` : ''}</Event>}
            {!t.done && (
              <div className="fa-actions">
                {(manage || t.assigned_to === me?.id) && <button className="btn sm outline" onClick={() => setOpen({ id: t.id, what: 'record' })}>Record result</button>}
                {manage && <>
                  <button className="btn sm outline" onClick={() => setOpen(open?.id === t.id && open.what === 'hand' ? null : { id: t.id, what: 'hand' })}>Hand to another shepherd</button>
                  <button className="btn sm outline" onClick={() => setOpen(open?.id === t.id && open.what === 'due' ? null : { id: t.id, what: 'due' })}>Change due time</button>
                  <button className="btn sm ghost" onClick={() => setOpen({ id: t.id, what: 'cancel' })}>Cancel task</button>
                </>}
              </div>
            )}
            {open?.id === t.id && open.what === 'hand' && <HandOn row={row} onClose={() => setOpen(null)} />}
            {open?.id === t.id && open.what === 'due' && <ChangeDueForm task={row} onClose={() => setOpen(null)} />}
            {open?.id === t.id && open.what === 'cancel' && <CancelTaskModal task={row} onClose={() => setOpen(null)} />}
            {open?.id === t.id && open.what === 'record' && <RecordResultModal task={row} others={openRows} onClose={() => setOpen(null)} />}
          </div>
        );
      })}
    </>
  );
}
