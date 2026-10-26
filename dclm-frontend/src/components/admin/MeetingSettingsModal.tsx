import { useState } from 'react';
import { useUpdateMeetingType } from '../../api/attendance';
import { useAdminLocations } from '../../api/admin';
import { useFollowUpRules } from '../../api/followupRules';
import { HelpMark } from '../ui/HelpMark';
import type { MeetingType } from '../../types/attendance';

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

function clock(t: string) {
  const [h, m] = t.split(':').map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`;
}

/**
 * Settings for one meeting (Kay, 26 October 2026, plan demo 3): start time,
 * when each session is created, and where it is held. Every value is the
 * administrator's to change, so nothing about a meeting is fixed in code.
 */
export function MeetingSettingsModal({ meeting, onClose, readOnly }: { meeting: MeetingType; onClose: () => void; readOnly: boolean }) {
  const update = useUpdateMeetingType();
  const { data: locations } = useAdminLocations();
  const { data: rules } = useFollowUpRules();
  const [day, setDay] = useState(meeting.day);
  const [start, setStart] = useState((meeting.start_time ?? '').slice(0, 5));
  const [mode, setMode] = useState(meeting.usual_mode ?? 'online');
  const [audience, setAudience] = useState(meeting.audience);
  const [offering, setOffering] = useState(meeting.collects_offering);
  const [tracked, setTracked] = useState(meeting.counts_for_absence);
  const [ahead, setAhead] = useState<number | ''>(meeting.create_days_ahead ?? 0);
  const [heldAt, setHeldAt] = useState<string[]>(meeting.held_at ?? []);
  const [err, setErr] = useState('');

  const weekly = meeting.frequency === 'weekly';
  const everywhere = heldAt.length === 0;
  const checkAt = start && rules ? (() => {
    const [h, m] = start.split(':').map(Number);
    const total = h * 60 + m + rules.check_hours_after_start * 60;
    const hh = Math.floor(total / 60) % 24;
    return clock(`${hh}:${total % 60}`) + (total >= 24 * 60 ? ' the next day' : '');
  })() : '';

  async function save() {
    setErr('');
    if (ahead === '' || ahead < 0) { setErr('Create each session: use a number of days from 0 to 14.'); return; }
    try {
      await update.mutateAsync({
        id: meeting.id, day, start_time: start ? `${start}:00` : null, usual_mode: mode, audience,
        collects_offering: offering, counts_for_absence: tracked, create_days_ahead: ahead, held_at: heldAt,
      } as any);
      onClose();
    } catch (e: any) {
      const d = e?.response?.data ?? {};
      const first = Object.entries(d)[0];
      setErr(first ? String(([] as unknown[]).concat(first[1] as any)[0]) : 'The meeting could not be saved. Try again.');
    }
  }
  const toggleLoc = (id: string, on: boolean) => setHeldAt((h) => on ? [...h, id] : h.filter((x) => x !== id));

  return (
    <div className="fu-modal" role="dialog" aria-modal="true" aria-label={`${meeting.name} settings`}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="fu-box">
        <h3 style={{ margin: '0 0 4px' }}>{meeting.name}</h3>
        <p className="muted" style={{ margin: '0 0 12px', fontSize: '.84rem' }}>
          {weekly ? 'Weekly meeting.' : 'Occasional meeting.'} Changes apply from the next session.
        </p>
        <div className="form-row">
          <div className="field">
            <label htmlFor="ms-day">Day</label>
            <select id="ms-day" value={day} disabled={readOnly || !weekly} onChange={(e) => setDay(e.target.value)}>
              {!WEEKDAYS.includes(day) && <option value={day}>{day || 'No fixed day'}</option>}
              {WEEKDAYS.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="ms-start">Start time<HelpMark topic="mtStart" /></label>
            <input id="ms-start" type="time" value={start} disabled={readOnly} onChange={(e) => setStart(e.target.value)} />
          </div>
        </div>
        <div className="form-row">
          <div className="field">
            <label htmlFor="ms-mode">Usually held</label>
            <select id="ms-mode" value={mode} disabled={readOnly} onChange={(e) => setMode(e.target.value as any)}>
              <option value="in-person-and-online">In person and online</option>
              <option value="online">Online</option>
              <option value="in-person">In person</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="ms-aud">Who it is for</label>
            <select id="ms-aud" value={audience} disabled={readOnly} onChange={(e) => setAudience(e.target.value as any)}>
              <option value="everyone">Everyone</option>
              <option value="workers">Workers</option>
              <option value="leadership">Leadership</option>
            </select>
          </div>
        </div>
        <div style={{ margin: '4px 0 10px' }}>
          <label className="fr-tick"><input type="checkbox" checked={offering} disabled={readOnly} onChange={(e) => setOffering(e.target.checked)} />Collects an offering</label>
          <label className="fr-tick"><input type="checkbox" checked={tracked} disabled={readOnly} onChange={(e) => setTracked(e.target.checked)} />Follows up absence<HelpMark topic="absenceTracking" /></label>
        </div>
        {tracked && !start && (
          <div className="form-error" role="alert">Follows up absence but has no start time, so nobody missing it is followed up. Set a start time.</div>
        )}
        {weekly && (
          <div className="fr-group">
            <div className="field" style={{ marginBottom: 6 }}>
              <label htmlFor="ms-ahead">Create each session<HelpMark topic="mtCreate" /></label>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <input id="ms-ahead" type="number" min={0} max={14} className="fr-num" style={{ width: 70 }} value={ahead} disabled={readOnly}
                  onChange={(e) => setAhead(e.target.value === '' ? '' : Number(e.target.value))} />
                <span style={{ fontSize: '.88rem' }}>days before the meeting</span>
              </div>
            </div>
            <div className="muted" style={{ fontSize: '.8rem' }}>
              {ahead === 0 ? `0 means the day itself: each ${day || 'meeting'}'s session appears at 2:07 am that day.` :
                `Each session appears ${ahead} day${ahead === 1 ? '' : 's'} before, at 2:07 am.`} Until its day a session shows <b>Upcoming</b>, never Pending.
            </div>
          </div>
        )}
        <div className="fr-group">
          <div style={{ fontWeight: 600, fontSize: '.88rem', marginBottom: 6 }}>Held at<HelpMark topic="mtHeldAt" /></div>
          {(locations ?? []).map((l: any) => (
            <label key={l.id} className="fr-tick">
              <input type="checkbox" checked={heldAt.includes(l.id)} disabled={readOnly} onChange={(e) => toggleLoc(l.id, e.target.checked)} />{l.name}
            </label>
          ))}
          <div className="muted" style={{ fontSize: '.8rem', marginTop: 6 }}>
            {everywhere ? 'None ticked: held at every location, including new ones.' : 'A session is created only at the locations ticked.'}
          </div>
        </div>
        {tracked && start && checkAt && (
          <div className="fr-box-note">
            Absence check and attendance reminder: <b>{checkAt}</b>{weekly && day ? ` on ${day}s` : ''}, {rules?.check_hours_after_start} hours after the start time. That gap is set in Admin, Follow-up Rules.
          </div>
        )}
        {err && <p className="form-error" role="alert">{err}</p>}
        <div className="form-actions-row" style={{ borderTop: '1px solid var(--line)', paddingTop: 12 }}>
          {!readOnly && <button className="btn sm" onClick={save} disabled={update.isPending}>Save changes</button>}
          <button className="btn sm ghost" onClick={onClose}>{readOnly ? 'Close' : 'Cancel'}</button>
        </div>
        <div className="muted" style={{ fontSize: '.78rem', marginTop: 8 }}>
          Only an administrator covering All locations can change a meeting, because meetings are shared by every location.
        </div>
      </div>
    </div>
  );
}
