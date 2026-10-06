import { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useFollowUpAction, usePersonFollowUp, type PersonEnrolment } from '../../api/journeys';
import { HelpMark } from '../ui/HelpMark';
import { EditorModal, SwapPanel } from '../../pages/newcomers/FollowUpMessagesPage';
import { blankHTML, cleanHTML, toWhatsApp, waLink } from '../../lib/whatsapp';
import { Skeleton } from '../ui/Skeleton';

/**
 * A person's follow-up messages (F19, F20), on their profile: which journey
 * they are on, the plan, what was sent, and the discipler's steps for a new
 * convert. The same panel serves newcomers, members and online contacts.
 */
const PACE: Record<string, string> = {
  online: 'Days 1, 3, 7, 14 and 21, then monthly for three months, ending with a final gentle message.',
  newcomers: 'The same day, then every three or four days for about six weeks, ending with a final gentle message. From the third visit, Belonging messages.',
  converts: 'Daily for the first two weeks, then twice a week to week 12.',
};
const STATE_LABEL: Record<string, string> = { planned: 'Sent', own: 'Sent', reply: 'Replied', skipped: 'Skipped', today: 'Today' };
const KIND_LABEL: Record<string, string> = { planned: 'Sent', own: 'Own message', reply: 'Personal reply', skipped: 'Skipped' };
const day = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

export function PersonMessages({ kind, id }: { kind: 'newcomer' | 'member' | 'enquiry'; id: number }) {
  const { hasPermission } = useAuth();
  const { data, isLoading, isError, error } = usePersonFollowUp(kind, id);
  const act = useFollowUpAction();
  const canStart = hasPermission('newcomers', 'edit');
  if (isLoading) return <Skeleton shape="list" />;
  // Someone at another location: their messages are handled there.
  if ((error as any)?.response?.status === 404) return <div className="empty">This person is followed up at another location, so their messages are handled there.</div>;
  if (isError || !data) return <div className="empty">Messages could not be loaded. Try again shortly.</div>;
  const list = data.enrolments;
  const current = list.find((e) => e.status === 'active') ?? list.find((e) => e.status === 'stopped');
  const past = list.filter((e) => e !== current);
  const start = (journey: string) => act.mutate({ url: '/followup/start/', body: { journey, [kind]: id } });
  const defaultJourney = kind === 'enquiry' ? 'online' : kind === 'newcomer' ? 'newcomers' : null;

  return (
    <div className="pm">
      {current ? <Current e={current} person={data.person} /> : (
        <div className="pm-none">
          <p className="muted" style={{ marginTop: 0 }}>No follow-up messages are running for this person.</p>
          {canStart && defaultJourney && (
            <button className="btn sm" onClick={() => start(defaultJourney)} disabled={act.isPending}>Start messages</button>
          )}
        </div>
      )}
      {canStart && current?.journey !== 'converts' && (
        <div className="pm-decide">
          <button className="btn sm outline" onClick={() => { if (window.confirm('Record that this person has given their life to Christ? Their messages move to the New converts journey.')) start('converts'); }}
            disabled={act.isPending}>Record a decision for Christ</button>
        </div>
      )}
      {past.length > 0 && (
        <>
          <h4 className="pm-h">Earlier journeys</h4>
          {past.map((e) => (
            <div className="person-row" key={e.id}>
              <span><b>{e.journey_label}</b><br /><span className="muted">{e.ended_reason || 'Ended'}</span></span>
              <span className="muted">{day(e.started)}{e.ended_on ? ` to ${day(e.ended_on)}` : ''}</span>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function Current({ e, person }: { e: PersonEnrolment; person?: { first: string; phone: string } }) {
  const [sending, setSending] = useState(false);
  const act = useFollowUpAction();
  const base = `/followup/enrolments/${e.id}`;
  const running = e.status === 'active';
  return (
    <>
      <div className="pm-head">
        <span className={`fu-chip j-${e.journey}`}>{e.journey_label}</span>
        {e.belonging && <span className="fu-chip ph">Belonging <HelpMark topic="fuBelonging" /></span>}
        <span className="muted">Started {day(e.started)}{running ? `, now on day ${e.day}` : ''}</span>
      </div>
      <div className="pm-plan">
        <span className="muted">Plan</span> <HelpMark topic="fuPlan" />
        <div className="viewtoggle" role="group" aria-label="Plan">
          {(['standard', 'daily'] as const).map((p) => (
            <button key={p} className={e.plan === p ? 'on' : ''} disabled={!e.can_act || act.isPending}
              onClick={() => e.plan !== p && act.mutate({ url: `${base}/plan/`, body: { plan: p } })}>{p === 'standard' ? 'Standard' : 'Daily'}</button>
          ))}
        </div>
        {e.can_act && (running ? (
          <span className="pm-stop">
            <button className="btn sm" onClick={() => setSending(!sending)} aria-expanded={sending}>Send a message</button>
            <button className="btn sm ghost" onClick={() => act.mutate({ url: `${base}/stop/` })} disabled={act.isPending}>Stop messages</button><HelpMark topic="fuStop" />
          </span>
        ) : (
          <button className="btn sm outline pm-stop" onClick={() => act.mutate({ url: `${base}/restart/` })} disabled={act.isPending}>Restart messages</button>
        ))}
      </div>
      {sending && <SendAny e={e} person={person ?? { first: '', phone: '' }} onDone={() => setSending(false)} />}
      <p className="muted pm-pace">{running ? (e.plan === 'daily' ? 'A message every day.' : PACE[e.journey]) : `Stopped. ${e.ended_reason}`}</p>
      {e.strip.length > 0 && (
        <div className="pm-strip">
          {e.strip.map((s) => <div key={s.day} className={`s-${s.state || 'none'}`}>Day {s.day}<br />{STATE_LABEL[s.state] ?? ''}</div>)}
        </div>
      )}
      {e.visits !== null && e.journey === 'newcomers' && (
        <p className="pm-visits">Visits: <b>{e.visits}</b>{e.visits >= 3 ? ', now receiving Belonging messages' : ', Belonging messages start at the third visit'}</p>
      )}
      {e.steps.length > 0 && (
        <>
          <h4 className="pm-h">In-person steps <HelpMark topic="fuSteps" /></h4>
          {e.steps.map((s, i) => (
            <StepBox key={i} when={s.when} what={s.what} done={s.done} disabled={!e.can_act}
              onSave={(done, undo) => act.mutate({ url: `${base}/steps/`, body: { step: i, done } }, { onError: undo })} />
          ))}
        </>
      )}
      <h4 className="pm-h">Sent</h4>
      {e.log.length === 0 ? <div className="empty">Nothing sent yet.</div> : e.log.map((l, i) => (
        <div className="person-row" key={i}>
          <span><b>{KIND_LABEL[l.kind] ?? l.kind}{l.theme && l.kind !== 'reply' ? `, ${l.theme}` : ''}</b>
            {l.text && <><br /><span className="muted pm-text">{l.text.replace(/[*_]/g, '').slice(0, 120)}{l.text.length > 120 ? '…' : ''}</span></>}
          </span>
          <span className="muted">{day(l.on_date)}{l.by ? `, ${l.by}` : ''}</span>
        </div>
      ))}
    </>
  );
}

/** A discipler's step. The tick shows at once, and is undone if saving fails. */
function StepBox({ when, what, done, disabled, onSave }: { when: string; what: string; done: boolean; disabled: boolean; onSave: (done: boolean, undo: () => void) => void }) {
  const [on, setOn] = useState(done);
  useEffect(() => setOn(done), [done]);
  return (
    <label className="pm-step">
      <input type="checkbox" checked={on} disabled={disabled}
        onChange={(ev) => { const v = ev.target.checked; setOn(v); onSave(v, () => setOn(!v)); }} />
      <span><b>{when}</b><br />{what}</span>
    </label>
  );
}

/**
 * Kay: send a message on any day, besides the plan. Choose from the bank, a
 * saved message, or write one, check it, send it in WhatsApp, then confirm.
 * It is recorded in their journey and their plan carries on unchanged.
 */
function SendAny({ e, person, onDone }: { e: PersonEnrolment; person: { first: string; phone: string }; onDone: () => void }) {
  const { user } = useAuth();
  const sender = user?.name || 'Your shepherd';
  const act = useFollowUpAction();
  const [editing, setEditing] = useState<null | { html: string; template: number | null; title: string }>(null);
  const [ready, setReady] = useState<null | { html: string; template: number | null }>(null);
  const [asked, setAsked] = useState(false);
  const [err, setErr] = useState('');
  const vars = { nextService: 'our next service', sender };
  const record = () => {
    if (!ready) return;
    act.mutate({ url: `/followup/enrolments/${e.id}/send/`, body: { text: toWhatsApp(ready.html), template: ready.template } },
      { onSuccess: onDone, onError: (x: any) => setErr(x?.response?.data?.detail || 'That could not be recorded. Try again.') });
  };
  return (
    <div className="pm-send">
      <b>Send a message</b>
      <p className="muted" style={{ margin: '2px 0 8px', fontSize: '.85rem' }}>Any day, as well as their planned messages. It is recorded in their journey and does not move their plan.</p>
      {!ready ? (
        <SwapPanel entry={{ journey: e.journey, person: { first: person.first } }} vars={vars}
          onPick={(html, theme, id) => setEditing({ html, template: id, title: `Edit the ${theme} message for ${person.first}` })}
          onOwn={() => setEditing({ html: blankHTML(person.first, sender), template: null, title: `Write my own for ${person.first}` })} />
      ) : asked ? (
        <div className="fu-confirm" role="status">
          <span>Did you send it on WhatsApp?</span>
          <button className="btn sm" onClick={record} disabled={act.isPending}>Yes, record it</button>
          <button className="btn sm ghost" onClick={() => setAsked(false)}>Not yet</button>
        </div>
      ) : (
        <>
          <div className="fu-bubble" dangerouslySetInnerHTML={{ __html: cleanHTML(ready.html) }} />
          <div className="fu-acts">
            <button className="btn sm fu-wa" onClick={() => { window.open(waLink(person.phone, toWhatsApp(ready.html)), '_blank', 'noopener'); setAsked(true); }}>Send on WhatsApp</button>
            <button className="btn sm outline" onClick={() => setEditing({ html: ready.html, template: ready.template, title: `Edit the message for ${person.first}` })}>Edit</button>
            <button className="btn sm ghost" onClick={() => setReady(null)}>Choose another</button>
          </div>
        </>
      )}
      {err && <p className="form-error" role="alert">{err}</p>}
      <div className="fu-acts"><button className="btn sm ghost" onClick={onDone}>Close</button></div>
      {editing && <EditorModal title={editing.title} start={editing.html} onClose={() => setEditing(null)}
        onUse={(h) => { setReady({ html: h, template: editing.template }); setEditing(null); setAsked(false); }} />}
    </div>
  );
}
