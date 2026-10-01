import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useFellowships, useMeetingTypes, useCreateSession } from '../../api/attendance';
import { useMyLocations } from '../../api/locations';
import { Button } from '../../components/ui/Button';

const today = new Date().toISOString().slice(0, 10);

export function NewSessionPage() {
  const navigate = useNavigate();
  const { data: meetingTypes } = useMeetingTypes();
  const { data: locations } = useMyLocations();
  const createSession = useCreateSession();

  const [meetingType, setMeetingType] = useState('');
  const [fellowship, setFellowship] = useState<number | ''>('');
  const { data: fellowships } = useFellowships();
  // Several fellowships meet the same evening, so the date alone does
  // not say which session this is.
  const isFellowship = meetingType === 'fri-house';
  const [date, setDate] = useState(today);
  const [location, setLocation] = useState('');
  const [mode, setMode] = useState('in-person');
  // F22: occasional meetings, such as GCK, have their own edition each time.
  const [editionName, setEditionName] = useState('');
  const [editionPlace, setEditionPlace] = useState('');
  const [error, setError] = useState('');

  if (meetingTypes && !meetingType && meetingTypes.length) setMeetingType(meetingTypes[0].id);
  if (locations && !location && locations.length) setLocation(locations[0].id);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    try {
      const created = await createSession.mutateAsync({
        meeting_type: meetingType, date, location, mode,
        ...(isFellowship && fellowship !== '' ? { fellowship } : {}),
        ...(isOccasional ? { edition_name: editionName, edition_place: editionPlace } : {}),
      });
      navigate(`/attendance/${created.id}`);
    } catch (err: any) {
      const d = err?.response?.data ?? {};
      const first = Object.values(d)[0];
      setError(first ? String(([] as any[]).concat(first)[0]) : 'The session could not be created. Try again.');
    }
  }

  const isOccasional = meetingTypes?.find((m) => m.id === meetingType)?.frequency === 'occasional';

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
          {isOccasional && (
            <div className="form-row">
              <div className="field">
                <label htmlFor="session-edition">Edition name</label>
                <input id="session-edition" value={editionName} onChange={(e) => setEditionName(e.target.value)} maxLength={120} placeholder="The theme or title of this edition" />
              </div>
              <div className="field">
                <label htmlFor="session-edition-place">Where it is held</label>
                <input id="session-edition-place" value={editionPlace} onChange={(e) => setEditionPlace(e.target.value)} maxLength={120} placeholder="Host city or venue" />
              </div>
            </div>
          )}
          <div className="form-row">
          {isFellowship && (
            <div className="field">
              <label htmlFor="session-fellowship">Which fellowship</label>
              <select id="session-fellowship" value={fellowship}
                onChange={(e) => setFellowship(e.target.value ? Number(e.target.value) : '')}>
                <option value="">Choose one</option>
                {(fellowships ?? []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
              <div className="field-hint">
                Two fellowships meet the same evening, so the date alone does not identify this one.
              </div>
            </div>
          )}

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
          {error && <p className="form-error" role="alert">{error}</p>}
          <Button type="submit" disabled={createSession.isPending}>
            {createSession.isPending ? 'Creating…' : 'Create session'}
          </Button>
        </form>
      </div>
    </>
  );
}
