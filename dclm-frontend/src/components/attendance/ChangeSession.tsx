import { useState } from 'react';
import { useChangeSession } from '../../api/attendance';
import type { AttendanceSession, MeetingType } from '../../types/attendance';
import { HelpMark } from '../ui/HelpMark';

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

/**
 * Change a session's meeting or date (5 November 2026). Monday Bible
 * Study was added on Wednesday 14 October and the only way to correct it
 * was to delete it with its numbers. Administrators only. The headcount,
 * names ticked and offering stay with the session.
 */
export function ChangeSession({ session, meetingTypes, onOpen }: {
  session: AttendanceSession; meetingTypes: MeetingType[]; onOpen: (id: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [meeting, setMeeting] = useState(session.meeting_type);
  const [date, setDate] = useState(session.date);
  const [error, setError] = useState('');
  const [otherDay, setOtherDay] = useState(false);
  const [existing, setExisting] = useState<number | null>(null);
  const [done, setDone] = useState('');
  const change = useChangeSession(session.id);

  const chosen = meetingTypes.find((m) => m.id === meeting);
  const picked = date ? DAYS[new Date(`${date}T00:00:00`).getDay()] : '';
  const wrongDay = !!(chosen && chosen.frequency === 'weekly' && DAYS.includes(chosen.day) && picked && picked !== chosen.day);

  function reset() { setError(''); setOtherDay(false); setExisting(null); }
  function save(allowOtherDay = false) {
    reset();
    change.mutate({ meeting_type: meeting, date, ...(allowOtherDay ? { allow_other_day: true } : {}) }, {
      onSuccess: (s) => { setOpen(false); setDone(`Changed to ${s.meeting_type_name}, ${s.date}. The headcount, names and offering are kept.`); },
      onError: (e: any) => {
        const d = e?.response?.data ?? {};
        const first = d.detail ?? d.date ?? d.meeting_type ?? Object.values(d)[0];
        setError(first ? String(([] as unknown[]).concat(first)[0]) : 'It could not be changed. Check your connection and try again.');
        setOtherDay(!!d.other_day);
        setExisting(d.existing_id ? Number(([] as unknown[]).concat(d.existing_id)[0]) : null);
      },
    });
  }

  if (!open) {
    return (
      <div className="change-session-link">
        {done && <p className="fr-done" role="status">{done}</p>}
        <button type="button" className="linkish" onClick={() => { setOpen(true); setDone(''); setMeeting(session.meeting_type); setDate(session.date); reset(); }}>
          Change date or meeting
        </button>
        <HelpMark topic="sessionChange" />
      </div>
    );
  }
  return (
    <div className="form-card change-session">
      <div className="form-row">
        <div className="field">
          <label htmlFor="chg-meeting">Meeting</label>
          <select id="chg-meeting" value={meeting} onChange={(e) => { setMeeting(e.target.value); reset(); }}>
            {meetingTypes.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="chg-date">Date</label>
          <input id="chg-date" type="date" value={date} onChange={(e) => { setDate(e.target.value); reset(); }} />
        </div>
      </div>
      {wrongDay && <div className="gender-warn" role="note">{chosen!.name} meets on {chosen!.day}s. This date is a {picked}.</div>}
      <div className="field-hint">The headcount, names ticked and offering stay with this session. The change is kept in the Audit Log.</div>
      {error && (
        <p className="form-error" role="alert">{error}
          {existing && <> <button type="button" className="linkish" onClick={() => onOpen(existing)}>Open it</button></>}
        </p>
      )}
      <div className="form-actions-row">
        {otherDay
          ? <button type="button" className="btn sm" disabled={change.isPending} onClick={() => save(true)}>Change it anyway, the meeting moved that week</button>
          : <button type="button" className="btn sm" disabled={change.isPending} onClick={() => save()}>{change.isPending ? 'Saving...' : 'Save change'}</button>}
        <button type="button" className="btn sm ghost" onClick={() => { setOpen(false); reset(); }}>Cancel</button>
      </div>
    </div>
  );
}
