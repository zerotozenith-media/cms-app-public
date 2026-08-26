import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMeetingTypes, useCreateSession } from '../../api/attendance';
import { useLocations } from '../../api/locations';
import { Button } from '../../components/ui/Button';

const today = new Date().toISOString().slice(0, 10);

export function NewSessionPage() {
  const navigate = useNavigate();
  const { data: meetingTypes } = useMeetingTypes();
  const { data: locations } = useLocations();
  const createSession = useCreateSession();

  const [meetingType, setMeetingType] = useState('');
  const [date, setDate] = useState(today);
  const [location, setLocation] = useState('');
  const [mode, setMode] = useState('in-person');

  if (meetingTypes && !meetingType && meetingTypes.length) setMeetingType(meetingTypes[0].id);
  if (locations && !location && locations.length) setLocation(locations[0].id);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const created = await createSession.mutateAsync({ meeting_type: meetingType, date, location, mode });
    navigate(`/attendance/${created.id}`);
  }

  if (!meetingTypes || !locations) return null;

  return (
    <>
      <a className="backlink" onClick={() => navigate('/attendance')}>← Back to sessions</a>
      <div className="card" style={{ maxWidth: 480, margin: '0 auto' }}>
        <h3>New attendance session</h3>
        <p className="muted" style={{ marginBottom: 14 }}>
          Use this for occasional meetings (like GCK) or to add a session outside the auto-generated weekly schedule.
        </p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="session-meeting">Meeting</label>
            <select id="session-meeting" value={meetingType} onChange={(e) => setMeetingType(e.target.value)}>
              {meetingTypes.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="session-date">Date</label>
              <input id="session-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="session-location">Location</label>
              <select id="session-location" value={location} onChange={(e) => setLocation(e.target.value)}>
                {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label htmlFor="session-mode">Mode</label>
            <select id="session-mode" value={mode} onChange={(e) => setMode(e.target.value)}>
              <option value="in-person">In person</option>
              <option value="online">Online</option>
            </select>
          </div>
          <Button type="submit" disabled={createSession.isPending}>
            {createSession.isPending ? 'Creating…' : 'Create session'}
          </Button>
        </form>
      </div>
    </>
  );
}
