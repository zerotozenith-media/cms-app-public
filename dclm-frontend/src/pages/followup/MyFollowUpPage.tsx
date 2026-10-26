import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { dayText, useFollowUpAccess, useMyFollowUp, whenText, type PersonGroup, type TaskRow } from '../../api/accountability';
import { useEligibleShepherds } from '../../api/followup';
import { AwayModal, GiveReasonsModal, RecordResultModal, taskTitle } from '../../components/accountability/TaskModals';
import { HelpMark } from '../../components/ui/HelpMark';
import { Skeleton } from '../../components/ui/Skeleton';

function ordinal(n: number) {
  return `${n}${n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'}`;
}

function badge(t: TaskRow): [string, string] {
  if (t.needs_reason) return ['red', 'Late: reason needed'];
  if (t.on_review) return ['amber', 'On the Review list'];
  if (t.is_late && t.reason) return ['amber', `Late, new date ${dayText(t.reason.new_date)}`];
  if (t.is_late) return ['red', 'Late'];
  const due = t.due_at ? new Date(t.due_at) : null;
  if (due && due.toDateString() === new Date().toDateString()) return ['amber', `Due today, ${whenText(t.due_at).split(', ')[1]}`];
  return ['gray', `Due ${whenText(t.due_at)}`];
}

function TaskLine({ t }: { t: TaskRow }) {
  const [color, label] = badge(t);
  const attempts = t.attempts.length
    ? `${t.attempts.length} attempt${t.attempts.length === 1 ? '' : 's'}: ${t.attempts.map((a) => `${a.method.toLowerCase()} on ${whenText(a.at)}`).join('; ')}, no answer`
    : 'No attempts yet';
  return (
    <div className="fa-task">
      <span className={`fa-dot ${color}`} aria-hidden="true" />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="fa-task-title">{taskTitle(t)}</div>
        <div style={{ margin: '3px 0' }}>
          <span className={`badge ${color}`}>{label}</span>
          {t.escalation && <span className="badge blue" style={{ marginLeft: 6 }}>{t.escalation_label}</span>}
          {t.handed_from && <span className="badge blue" style={{ marginLeft: 6 }}>Handed to you by the Follow-up Coordinator</span>}
        </div>
        <div className="muted" style={{ fontSize: '.8rem' }}>
          {t.is_late ? `Was due ${whenText(t.due_at)}` : attempts}
          {t.is_late && t.attempts.length > 0 && <> · {attempts}</>}
          {t.kind === 'first-visit' && ' · First-visit tasks are due within 24 hours, like absence tasks'}
        </div>
        {t.last_choice && <div className="fa-choice">Follow-up Coordinator: {t.last_choice.choice}{t.last_choice.note ? `. "${t.last_choice.note}"` : ''}</div>}
      </div>
    </div>
  );
}

function PersonCard({ p, onRecord, onReasons, onAway }: { p: PersonGroup; onRecord: (t: TaskRow, start?: 'tried') => void; onReasons: (ts: TaskRow[]) => void; onAway: () => void }) {
  const owed = p.tasks.filter((t) => t.needs_reason);
  const link = p.type === 'member' ? `/members/${p.person_id}` : `/newcomers/${p.person_id}`;
  return (
    <div className="card fu-card fa-person">
      <div className="fa-person-head">
        <Link to={link} className="fa-name">{p.person}</Link>
        <span className="badge gray">{p.person_kind}</span>
        {p.priority && <><span className="badge red">Priority</span><HelpMark topic="faPriority" /></>}
      </div>
      {p.run >= 2 && <div className="muted" style={{ fontSize: '.82rem', marginBottom: 2 }}>{ordinal(p.run)} {p.tasks.find((t) => t.missed_meeting_name)?.missed_meeting_name ?? 'service'} missed in a row</div>}
      {p.tasks.map((t) => <TaskLine key={t.id} t={t} />)}
      <div className="fa-actions">
        {owed.length > 0
          ? <button className="btn sm" onClick={() => onReasons(owed)}>Give reason{owed.length > 1 ? 's' : ''}</button>
          : <button className="btn sm" onClick={() => onRecord(p.tasks[0])}>Record result</button>}
        <button className="btn sm outline" onClick={() => onRecord(p.tasks[0], 'tried')} disabled={owed.length > 0}
          title={owed.length ? 'Give the reason first' : undefined}>Log an attempt</button>
        <button className="btn sm ghost" onClick={onAway}>Mark away</button>
      </div>
    </div>
  );
}

/**
 * My follow-up (Kay, 26 October 2026, plan demo 6): one list of a
 * shepherd's members and newcomers, late tasks first. A Follow-up
 * Coordinator or administrator can open any shepherd's list.
 */
export function MyFollowUpPage() {
  const [params, setParams] = useSearchParams();
  const shepherd = params.get('shepherd') ? Number(params.get('shepherd')) : null;
  const { data: access } = useFollowUpAccess();
  const { data: shepherds } = useEligibleShepherds();
  const { data, isLoading } = useMyFollowUp(shepherd);
  const [recording, setRecording] = useState<{ t: TaskRow; others: TaskRow[]; start?: 'tried' } | null>(null);
  const [reasons, setReasons] = useState<TaskRow[] | null>(null);
  const [away, setAway] = useState<{ type: 'member' | 'newcomer'; id: number; name: string } | null>(null);

  const allOwed = (data?.people ?? []).flatMap((p) => p.tasks.filter((t) => t.needs_reason));
  const whose = shepherd ? (shepherds ?? []).find((s: any) => s.id === shepherd)?.name ?? 'this shepherd' : null;

  return (
    <>
      <div className="toolbar">
        <h2 style={{ margin: 0, fontSize: '1.15rem' }}>{whose ? `${whose}'s follow-up` : 'My follow-up'}<HelpMark topic="faMyList" /></h2>
        {access?.can_review && (
          <select className="selectbox" aria-label="Whose list" value={shepherd ?? ''}
            onChange={(e) => setParams(e.target.value ? { shepherd: e.target.value } : {})}>
            <option value="">My own list</option>
            {(shepherds ?? []).map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        )}
      </div>

      {allOwed.length > 0 && !shepherd && (
        <div className="fa-owed" role="alert">
          <b>{allOwed.length} late task{allOwed.length === 1 ? ' needs' : 's need'} a reason.</b> Give a reason for each before recording anything else, because your Follow-up Coordinator reviews them.
          <div style={{ marginTop: 8 }}><button className="btn sm" onClick={() => setReasons(allOwed)}>Give reasons</button></div>
        </div>
      )}

      {isLoading && <div className="card"><Skeleton shape="list" /></div>}
      {data && data.people.length === 0 && (
        <div className="card"><div className="empty">Nothing to follow up. Every task is done.</div></div>
      )}
      {(data?.people ?? []).map((p) => (
        <PersonCard key={`${p.type}-${p.person_id}`} p={p}
          onRecord={(t, start) => setRecording({ t, others: p.tasks, start })}
          onReasons={(ts) => setReasons(ts)}
          onAway={() => setAway({ type: p.type, id: p.person_id, name: p.person })} />
      ))}

      {(data?.away ?? []).length > 0 && (
        <div className="card section-gap">
          <h3 style={{ margin: '0 0 6px' }}>Away<HelpMark topic="faAway" /></h3>
          {data!.away.map((a) => (
            <div key={`${a.type}-${a.person_id}`} className="person-row" style={{ fontSize: '.86rem' }}>
              <span><b>{a.person}</b> <span className="muted">{a.away_reason}</span></span>
              <span className="muted">{a.away_from ? `${dayText(a.away_from)} to ` : 'Until '}{dayText(a.away_to)}. No tasks are made while away.</span>
            </div>
          ))}
        </div>
      )}

      {recording && <RecordResultModal task={recording.t} others={recording.others} start={recording.start} onClose={() => setRecording(null)} />}
      {reasons && <GiveReasonsModal tasks={reasons} onClose={() => setReasons(null)} />}
      {away && <AwayModal {...away} onClose={() => setAway(null)} />}
    </>
  );
}
