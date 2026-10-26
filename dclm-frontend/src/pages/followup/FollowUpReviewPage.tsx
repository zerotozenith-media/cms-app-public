import { Fragment, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  dayText, refusal, useDecide, useEligible, useFollowUpAccess, useReviewList, useReviewOverview, useShepherdPeople, whenText,
  type TaskRow,
} from '../../api/accountability';
import { useLocations } from '../../api/locations';
import { CancelTaskModal, ChangeDueForm, taskTitle } from '../../components/accountability/TaskModals';
import { HelpMark } from '../../components/ui/HelpMark';
import { Skeleton } from '../../components/ui/Skeleton';

const CHOICES: [string, string][] = [['accept', 'Accept'], ['hand-on', 'Hand to another shepherd'], ['take', 'Take it myself'], ['ask', 'Ask the shepherd']];

function monthsBack(n: number) {
  const out: { v: string; l: string }[] = [];
  const d = new Date();
  d.setDate(1);
  for (let i = 0; i < n; i++) {
    out.push({ v: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`, l: d.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' }) });
    d.setMonth(d.getMonth() - 1);
  }
  return out;
}

function pctBadge(v: number | null, target: number) {
  if (v === null) return <span className="muted">None due</span>;
  return <span className={`badge ${v >= target ? 'green' : 'amber'}`}>{v}%</span>;
}

function ReviewItem({ t }: { t: TaskRow }) {
  const decide = useDecide();
  const [choice, setChoice] = useState('');
  const [note, setNote] = useState('');
  const [to, setTo] = useState('');
  const [err, setErr] = useState('');
  const [more, setMore] = useState<'' | 'due' | 'cancel'>('');
  const eligible = useEligible(t.type, t.id, choice === 'hand-on');
  const link = t.type === 'member' ? `/members/${t.person_id}` : `/newcomers/${t.person_id}`;

  async function confirm() {
    setErr('');
    try {
      await decide.mutateAsync({ type: t.type, id: t.id, choice, note, handed_to: to ? Number(to) : undefined });
      setChoice('');
    } catch (e) { setErr(refusal(e, 'The decision could not be saved.')); }
  }

  return (
    <div className="card fu-card fa-person">
      <div className="fa-person-head"><Link to={link} className="fa-name">{t.person}</Link><span className="badge gray">{t.person_kind}</span></div>
      <div style={{ fontSize: '.86rem', margin: '4px 0' }}>{taskTitle(t)}</div>
      <div className="muted" style={{ fontSize: '.8rem' }}>
        Shepherd: {t.escalation === 'no-shepherd' ? 'none. Given to you until a shepherd is chosen' : t.shepherd || 'none'}
        {t.shepherd_late_this_quarter ? `, ${t.shepherd_late_this_quarter} late task${t.shepherd_late_this_quarter === 1 ? '' : 's'} this quarter` : ''}
      </div>
      {t.reason ? (
        <div className="fa-reason-box"><b>Reason:</b> {t.reason.reason}.{t.reason.note ? ` "${t.reason.note}"` : ''} New date {dayText(t.reason.new_date)}.</div>
      ) : t.escalation === 'needs-coordinator' ? (
        <div className="fa-reason-box"><b>Needs you:</b> {t.result_note || 'The shepherd asked for your help.'}</div>
      ) : t.escalation === 'attempts' ? (
        <div style={{ marginTop: 8, fontSize: '.82rem' }}><span className="badge amber">{t.attempts.length} attempts, could not reach</span>
          <div className="muted" style={{ marginTop: 4 }}>{t.attempts.map((a) => `${a.method} ${whenText(a.at)}`).join(', ')}</div></div>
      ) : t.needs_reason ? (
        <div style={{ marginTop: 8 }}><span className="badge red">No reason given</span> <span className="muted" style={{ fontSize: '.8rem' }}>Was due {whenText(t.due_at)}</span></div>
      ) : null}
      {t.last_choice && <div className="fa-choice">Last decision: {t.last_choice.choice}{t.last_choice.note ? `. "${t.last_choice.note}"` : ''}</div>}
      {t.decide_by && <div style={{ fontSize: '.8rem', marginTop: 6 }}><b>Decide by {whenText(t.decide_by)}</b></div>}
      <div className="fa-choices">
        {CHOICES.map(([k, l]) => (
          <button key={k} className={`btn sm${choice === k ? '' : ' outline'}`} onClick={() => { setChoice(choice === k ? '' : k); setErr(''); }}
            disabled={k === 'accept' && !t.reason} title={k === 'accept' && !t.reason ? 'There is no reason to accept yet' : undefined}>{l}</button>
        ))}
      </div>
      {choice === 'hand-on' && (
        <div className="field" style={{ marginTop: 10 }}>
          <label htmlFor={`ho-${t.id}`}>Hand this task to<HelpMark topic="faHandOn" /></label>
          <select id={`ho-${t.id}`} className="selectbox" style={{ width: '100%' }} value={to} onChange={(e) => setTo(e.target.value)}>
            <option value="">Choose a shepherd</option>
            {(eligible.data?.results ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          {eligible.data && <div className="muted fr-note">{eligible.data.why}{!eligible.data.results.length && ' Nobody suitable is free, so take it yourself or ask the shepherd.'}</div>}
        </div>
      )}
      {(choice === 'ask' || choice === 'take' || choice === 'accept') && (
        <div className="field" style={{ marginTop: 10 }}>
          <label htmlFor={`dn-${t.id}`}>{choice === 'ask' ? 'Your question to the shepherd' : 'Note (optional)'}</label>
          <input id={`dn-${t.id}`} value={note} onChange={(e) => setNote(e.target.value)} placeholder={choice === 'ask' ? "For example: did you try her husband's number?" : ''} />
        </div>
      )}
      {choice && (
        <div className="form-actions-row" style={{ marginTop: 8 }}>
          <button className="btn sm" onClick={confirm} disabled={decide.isPending || (choice === 'hand-on' && !to)}>Confirm</button>
          <button className="btn sm ghost" onClick={() => setChoice('')}>Cancel</button>
        </div>
      )}
      {err && <p className="form-error" role="alert">{err}</p>}
      <div className="fa-more">
        <button className="linkish" onClick={() => setMore(more === 'due' ? '' : 'due')}>Change due time</button>
        <button className="linkish" onClick={() => setMore('cancel')}>Cancel task</button>
      </div>
      {more === 'due' && <ChangeDueForm task={t} onClose={() => setMore('')} />}
      {more === 'cancel' && <CancelTaskModal task={t} onClose={() => setMore('')} />}
    </div>
  );
}

function ShepherdRows({ id, location }: { id: number; location: string | null }) {
  const { data } = useShepherdPeople(id, location);
  if (!data) return <Skeleton shape="rows" rows={2} />;
  if (!data.length) return <div className="muted" style={{ fontSize: '.84rem' }}>Nobody assigned yet.</div>;
  return (
    <>
      {data.map((p) => (
        <div key={`${p.type}-${p.id}`} className="person-row" style={{ fontSize: '.84rem' }}>
          <span><Link to={p.type === 'member' ? `/members/${p.id}` : `/newcomers/${p.id}`}><b>{p.person}</b></Link> <span className="muted">{p.label}</span></span>
          <span className={`badge ${p.tone}`}>{p.status}</span>
        </div>
      ))}
      <Link to={`/follow-up?shepherd=${id}`} className="linkish">Open this shepherd's list</Link>
    </>
  );
}

/**
 * Follow-up Review (Kay, 26 October 2026, plan demos 10 to 12): the
 * measures against the targets, every shepherd's people and record, and
 * the Review list of late tasks with the four choices.
 */
export function FollowUpReviewPage() {
  const { data: access } = useFollowUpAccess();
  const { data: locations } = useLocations();
  const [tab, setTab] = useState<'overview' | 'review'>('review');
  const [location, setLocation] = useState<string>('');
  const months = monthsBack(12);
  const [month, setMonth] = useState(months[0].v);
  const [open, setOpen] = useState<number | null>(null);
  const loc = access?.coverage ?? (location || null);
  const { data: ov, error: ovErr } = useReviewOverview(loc, month);
  const { data: review, isLoading } = useReviewList(loc);

  if (access && !access.can_review) {
    return <div className="card"><div className="empty">The Follow-up Review page is for Follow-up Coordinators and administrators. Ask an administrator to tick Follow-up Coordinator on your account in Admin, Users.</div></div>;
  }
  const monthName = months.find((m) => m.v === month)?.l.split(' ')[0];

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className={`tab${tab === 'overview' ? ' active' : ''}`} onClick={() => setTab('overview')}>Overview</button>
          <button className={`tab${tab === 'review' ? ' active' : ''}`} onClick={() => setTab('review')}>Review list{review ? ` (${review.length})` : ''}</button>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {access && !access.coverage ? (
            <select className="selectbox" aria-label="Location" value={location} onChange={(e) => setLocation(e.target.value)}>
              <option value="">All locations</option>
              {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          ) : access && <span className="badge blue">{access.coverage_name}</span>}
          {tab === 'overview' && (
            <select className="selectbox" aria-label="Month" value={month} onChange={(e) => setMonth(e.target.value)}>
              {months.map((m) => <option key={m.v} value={m.v}>{m.l}</option>)}
            </select>
          )}
        </div>
      </div>

      {tab === 'review' && <>
        {isLoading && <div className="card"><Skeleton shape="list" /></div>}
        {review && review.length === 0 && <div className="card"><div className="empty">Nothing on the Review list. Every late task has been decided.</div></div>}
        {(review ?? []).map((t) => <ReviewItem key={`${t.type}-${t.id}`} t={t} />)}
        {review && review.length > 0 && <p className="muted" style={{ fontSize: '.78rem' }}>A decision not made by its date goes to the administrators with an alert.<HelpMark topic="faReviewList" /></p>}
      </>}

      {tab === 'overview' && <>
        {ovErr && <p className="form-error" role="alert">{refusal(ovErr, 'The overview could not be loaded.')}</p>}
        {!ov && !ovErr && <div className="card"><Skeleton shape="rows" rows={6} /></div>}
        {ov && <>
          <div className="statcard fa-stats">
            <div className="stat"><div className="label">Open tasks</div><div className="value">{ov.stats.open}</div></div>
            <div className="stat"><div className="label">On your Review list</div><div className="value" style={{ color: 'var(--amber)' }}>{ov.stats.review}</div></div>
            <div className="stat"><div className="label">Late, no reason</div><div className="value" style={{ color: ov.stats.late_no_reason ? 'var(--red)' : undefined }}>{ov.stats.late_no_reason}</div><div className="muted" style={{ fontSize: '.78rem' }}>target 0</div></div>
            <div className="stat"><div className="label">Away</div><div className="value">{ov.stats.away}</div><div className="muted" style={{ fontSize: '.78rem' }}>no tasks made</div></div>
            <div className="stat"><div className="label">Names not taken</div><div className="value" style={{ color: ov.stats.names_not_taken ? 'var(--red)' : 'var(--green)' }}>{ov.stats.names_not_taken}</div></div>
          </div>

          <div className="card section-gap">
            <h3 style={{ margin: '0 0 8px' }}>Measures for {monthName}<HelpMark topic="faMeasures" /></h3>
            <div className="fa-measures">
              <div><div className="fa-m-label">On time</div><div className="fa-m-val">{pctBadge(ov.measures.on_time, ov.targets.on_time)}</div><div className="muted fr-note">target {ov.targets.on_time}%, {ov.measures.due} due</div></div>
              <div><div className="fa-m-label">First contact</div><div className="fa-m-val">{ov.measures.first_contact_hours === null ? <span className="muted">None yet</span> : <span className={`badge ${ov.measures.first_contact_hours <= ov.targets.first_contact_hours ? 'green' : 'amber'}`}>{ov.measures.first_contact_hours} hours</span>}</div><div className="muted fr-note">target {ov.targets.first_contact_hours} hours</div></div>
              <div><div className="fa-m-label">Reached</div><div className="fa-m-val">{pctBadge(ov.measures.reached, ov.targets.reached)}</div><div className="muted fr-note">target {ov.targets.reached}%</div></div>
              <div><div className="fa-m-label">Late with no reason</div><div className="fa-m-val"><span className={`badge ${ov.measures.late_no_reason ? 'red' : 'green'}`}>{ov.measures.late_no_reason}</span></div><div className="muted fr-note">target 0</div></div>
              <div><div className="fa-m-label">{ov.targets.run_at} in a row or more</div><div className="fa-m-val"><span className="badge blue">{ov.measures.run}</span></div><div className="muted fr-note">each has your visit task</div></div>
            </div>
          </div>

          <div className="card section-gap">
            <h3 style={{ margin: '0 0 8px' }}>Shepherds<HelpMark topic="faShepherds" /></h3>
            <div style={{ overflowX: 'auto' }}>
              <table className="cardtable">
                <thead><tr><th>Shepherd</th><th>People</th><th>Open tasks</th><th>On time</th><th>Reached</th><th>Late, no reason</th></tr></thead>
                <tbody>
                  {ov.shepherds.map((s) => (
                    <Fragment key={s.id}>
                      <tr className="fa-srow" onClick={() => setOpen(open === s.id ? null : s.id)} aria-expanded={open === s.id}>
                        <td data-label="Shepherd"><b>{s.name}</b> <span aria-hidden="true">{open === s.id ? '▴' : '▾'}</span></td>
                        <td data-label="People"><span className={s.people > s.limit ? 'badge amber' : ''}>{s.people} of {s.limit}</span></td>
                        <td data-label="Open tasks">{s.open}</td>
                        <td data-label="On time">{pctBadge(s.on_time, ov.targets.on_time)}</td>
                        <td data-label="Reached">{pctBadge(s.reached, ov.targets.reached)}</td>
                        <td data-label="Late, no reason">{s.late_no_reason ? <span className="badge red">{s.late_no_reason}</span> : 0}</td>
                      </tr>
                      {open === s.id && <tr className="fa-open"><td colSpan={6}><ShepherdRows id={s.id} location={loc} /></td></tr>}
                    </Fragment>
                  ))}
                </tbody>
              </table>
              {!ov.shepherds.length && <div className="empty">No shepherds yet. Tick Can shepherd others on accounts in Admin, Users.</div>}
            </div>
          </div>

          {ov.away.length > 0 && (
            <div className="card section-gap">
              <h3 style={{ margin: '0 0 6px' }}>Away</h3>
              {ov.away.map((a) => (
                <div key={`${a.type}-${a.id}`} className="person-row" style={{ fontSize: '.86rem' }}>
                  <span><b>{a.person}</b> <span className="muted">{a.shepherd ? `Shepherd ${a.shepherd}` : 'No shepherd'}</span></span>
                  <span className="muted">{a.away_from ? `${dayText(a.away_from)} to ` : ''}{dayText(a.away_to)}{a.reason ? `, ${a.reason.toLowerCase()}` : ''}</span>
                </div>
              ))}
            </div>
          )}
          {ov.names_not_taken.length > 0 && (
            <div className="card section-gap">
              <h3 style={{ margin: '0 0 6px' }}>Names not taken</h3>
              {ov.names_not_taken.map((s) => (
                <div key={s.id} className="person-row" style={{ fontSize: '.86rem' }}>
                  <span>{s.name}</span><Link className="btn sm" to={`/attendance/${s.id}`}>Tick names</Link>
                </div>
              ))}
            </div>
          )}
        </>}
      </>}
    </>
  );
}
