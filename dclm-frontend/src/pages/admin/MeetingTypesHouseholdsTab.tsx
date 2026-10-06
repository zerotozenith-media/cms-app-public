import { useMyLocations } from '../../api/locations';
import type { MeetingAudience } from '../../types/attendance';
import { useState } from 'react';
import { useUpdateMeetingType, useFellowships, useCreateFellowship, useDeleteFellowship, useMeetingTypes, useCreateMeetingType, useDeleteMeetingType } from '../../api/attendance';
import { useHouseholds, useCreateHousehold, useDeleteHousehold } from '../../api/members';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { useAppSettings, useUpdateAppSetting } from '../../api/settings';
import { HelpMark } from '../../components/ui/HelpMark';

import { useAuth } from '../../context/AuthContext';
const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export function MeetingTypesHouseholdsTab() {
  // Meeting types and the follow-up switch apply to every location, so
  // only somebody covering every location changes them. Households and
  // fellowships follow their own sections' permissions.
  const { user: me, hasPermission } = useAuth();
  const churchWide = !me?.location && hasPermission('admin', 'edit');
  const canAddHousehold = hasPermission('members', 'create');
  const canDeleteHousehold = hasPermission('members', 'delete');
  const canAddFellowship = hasPermission('attendance', 'create');
  const canRemoveFellowship = hasPermission('attendance', 'delete');
  const { data: fellowships } = useFellowships();
  const updateMeeting = useUpdateMeetingType();
  // A refused change is explained, rather than the tick quietly undoing.
  const [meetingError, setMeetingError] = useState('');
  const saveMeeting = (patch: Parameters<typeof updateMeeting.mutate>[0]) => {
    setMeetingError('');
    updateMeeting.mutate(patch, {
      onError: (err: any) => {
        const d = err?.response?.data;
        setMeetingError((d?.day?.[0] ?? d?.detail ?? 'That change could not be saved.') as string);
      },
    });
  };
  const createFellowship = useCreateFellowship();
  const deleteFellowship = useDeleteFellowship();
  const [newFellowship, setNewFellowship] = useState('');
  const [newArea, setNewArea] = useState('');
  // Each fellowship belongs to one location, so it only gets sessions there.
  const { data: locations } = useMyLocations();
  const [newLocation, setNewLocation] = useState('');
  const mainLocation = (locations ?? []).find((l: any) => l.is_core)?.id ?? locations?.[0]?.id ?? '';
  const [fellowshipError, setFellowshipError] = useState('');
  const { data: settings } = useAppSettings();
  const updateSetting = useUpdateAppSetting();
  const { data: meetingTypes } = useMeetingTypes();
  const createMeetingType = useCreateMeetingType();
  const deleteMeetingType = useDeleteMeetingType();
  const { data: households } = useHouseholds();
  const createHousehold = useCreateHousehold();
  const deleteHousehold = useDeleteHousehold();

  const [showMeetingForm, setShowMeetingForm] = useState(false);
  const [mtId, setMtId] = useState('');
  const [mtName, setMtName] = useState('');
  const [mtDay, setMtDay] = useState('');
  const [mtLevel, setMtLevel] = useState('detailed');
  const [mtFreq, setMtFreq] = useState('weekly');

  const [showHouseholdForm, setShowHouseholdForm] = useState(false);
  const [hName, setHName] = useState('');
  const [hAddress, setHAddress] = useState('');
  const [hPhone, setHPhone] = useState('');

  async function handleAddMeeting(e: React.FormEvent) {
    e.preventDefault();
    setMeetingError('');
    try {
      await createMeetingType.mutateAsync({ id: mtId, name: mtName, day: mtDay, frequency: mtFreq, detail_level: mtLevel });
    } catch (err: any) {
      const d = err?.response?.data ?? {};
      const first = Object.values(d)[0];
      setMeetingError(first ? String(([] as any[]).concat(first)[0]) : 'The meeting type could not be added.');
      return;
    }
    setMtId(''); setMtName(''); setMtDay('');
    setShowMeetingForm(false);
  }
  async function handleDeleteMeeting(id: string) {
    if (!confirm('Delete this meeting type?')) return;
    await deleteMeetingType.mutateAsync(id);
  }
  async function handleAddHousehold(e: React.FormEvent) {
    e.preventDefault();
    await createHousehold.mutateAsync({ name: hName, address: hAddress, phone: hPhone });
    setHName(''); setHAddress(''); setHPhone('');
    setShowHouseholdForm(false);
  }
  async function handleDeleteHousehold(id: number) {
    if (!confirm('Delete this household?')) return;
    await deleteHousehold.mutateAsync(id);
  }

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 10 }}>Follow-up assignment<HelpMark topic="autoAssign" /></h3>
        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 9, fontSize: '.85rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            style={{ width: 16, height: 16, marginTop: 2 }}
            checked={settings?.auto_assign_newcomers ?? true}
            disabled={!churchWide}
            onChange={(e) => updateSetting.mutate({ auto_assign_newcomers: e.target.checked })}
          />
          <span>
            <b>Include newcomers in auto-assign</b>
            <div className="muted" style={{ fontSize: '.78rem', marginTop: 2 }}>
              When off, auto-assign only covers members, and newcomers stay assigned by hand.
              Useful if whoever meets a newcomer should keep them.
            </div>
          </span>
        </label>
        <div className="muted" style={{ fontSize: '.78rem', marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--line)' }}>
          Auto-assign pairs households to the same shepherd first, then balances the rest by how many
          people each shepherd already carries. Only accounts ticked Can shepherd others can be shepherds.
          Run it from <b>Members, Auto-assign</b>.
        </div>
      </div>

      <div className="grid g2">
        <div className="card span-all">
          <div className="toolbar" style={{ marginBottom: 10 }}>
            <h3>Meeting types</h3>
            {churchWide && <a className="btn sm" onClick={() => setShowMeetingForm(!showMeetingForm)}><Icon name="plus" size={14} /> Add</a>}
          </div>
          {meetingError && <p className="form-error" role="alert">{meetingError}</p>}
          {showMeetingForm && (
            <div className="form-card editing">
              <form onSubmit={handleAddMeeting}>
                <div className="field">
                  <label htmlFor="mt-id">ID (short code, e.g. fri-worship)</label>
                  <input id="mt-id" value={mtId} onChange={(e) => setMtId(e.target.value)} required />
                </div>
                <div className="field">
                  <label htmlFor="mt-name">Name</label>
                  <input id="mt-name" value={mtName} onChange={(e) => setMtName(e.target.value)} required />
                </div>
                <div className="form-row g3">
                  <div className="field">
                    <label htmlFor="mt-day">Day</label>
                    {/* A dropdown, since a weekly meeting needs a real day of the week. */}
                    <select id="mt-day" value={mtDay} onChange={(e) => setMtDay(e.target.value)}>
                      <option value="">No fixed day</option>
                      {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((d) => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="mt-level">Level</label>
                    <select id="mt-level" value={mtLevel} onChange={(e) => setMtLevel(e.target.value)}>
                      <option value="detailed">Detailed</option>
                      <option value="simple">Simple (M/W)</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="mt-freq">Frequency</label>
                    <select id="mt-freq" value={mtFreq} onChange={(e) => setMtFreq(e.target.value)}>
                      <option value="weekly">Weekly</option>
                      <option value="occasional">Occasional</option>
                    </select>
                  </div>
                </div>
                <button className="btn sm" type="submit" disabled={createMeetingType.isPending}>Add meeting type</button>
                <button className="btn sm ghost" type="button" onClick={() => setShowMeetingForm(false)}>Cancel</button>
              </form>
            </div>
          )}
          <div style={{ overflowX: 'auto' }}>
            <table className="cardtable meeting-table">
              <thead><tr>
                <th>Meeting</th><th>Detail level</th><th>Day</th><th>Usually held</th><th>Who it is for</th>
                <th>Collects an offering</th>
                <th>Follows up absence <HelpMark topic="absenceTracking" /></th><th></th>
              </tr></thead>
              <tbody>
                {(meetingTypes ?? []).map((m) => (
                  <tr key={m.id}>
                    <td data-label="Meeting">
                      {m.name}
                      {!m.generates_sessions && m.frequency === 'weekly' && (
                        <div className="warn-line">
                          <Icon name="alert" size={13} /> No sessions are being generated.
                          Choose the day in the Day column.
                        </div>
                      )}
                    </td>
                    <td data-label="Detail level"><Badge color={m.detail_level === 'detailed' ? 'blue' : 'gray'}>{m.detail_level}</Badge></td>
                    <td data-label="Day">
                      {m.frequency === 'weekly' ? (
                        <select className="selectbox" value={m.day} aria-label={`Day ${m.name} meets`} disabled={!churchWide}
                          onChange={(e) => saveMeeting({ id: m.id, day: e.target.value })}>
                          {/* A day the system cannot read is shown as it is, so the
                              problem is visible and can be corrected here. */}
                          {!WEEKDAYS.includes(m.day) && <option value={m.day}>{m.day || 'Not set'}</option>}
                          {WEEKDAYS.map((d) => <option key={d} value={d}>{d}</option>)}
                        </select>
                      ) : <span className="muted">Occasional</span>}
                    </td>
                    <td data-label="Usually held">
                      {/* Issue 2: weekly sessions are created this way. */}
                      <select className="selectbox" value={m.usual_mode ?? 'online'} aria-label={`How ${m.name} is usually held`} disabled={!churchWide}
                        onChange={(e) => saveMeeting({ id: m.id, usual_mode: e.target.value } as any)}>
                        <option value="in-person-and-online">In person and online</option>
                        <option value="online">Online</option>
                        <option value="in-person">In person</option>
                      </select>
                    </td>
                    <td data-label="Who it is for">
                      <select className="selectbox" value={m.audience} aria-label={`Who ${m.name} is for`} disabled={!churchWide}
                        onChange={(e) => saveMeeting({ id: m.id, audience: e.target.value as MeetingAudience })}>
                        <option value="everyone">Everyone</option>
                        <option value="workers">Workers</option>
                        <option value="leadership">Leadership</option>
                      </select>
                    </td>
                    <td data-label="Collects an offering">
                      <label className="tick">
                        <input type="checkbox" checked={m.collects_offering} disabled={!churchWide} aria-label={`Collect an offering at ${m.name}`}
                          onChange={(e) => saveMeeting({ id: m.id, collects_offering: e.target.checked })} />
                        {m.collects_offering
                          ? <Badge color="green">Yes</Badge>
                          : <span className="muted">No</span>}
                      </label>
                    </td>
                    {/* The switch existed on the server but no screen set it, so
                        only the meeting chosen at installation was followed up. */}
                    <td data-label="Follows up absence">
                      <label className="tick">
                        <input type="checkbox" checked={m.counts_for_absence} disabled={!churchWide}
                          aria-label={`Follow up absence from ${m.name}`}
                          onChange={(e) => saveMeeting({ id: m.id, counts_for_absence: e.target.checked })} />
                        {m.counts_for_absence
                          ? <Badge color="green">Yes</Badge>
                          : <span className="muted">No</span>}
                      </label>
                    </td>
                    <td className="td-actions">{churchWide && <button className="icon-btn" title="Remove meeting" aria-label="Remove meeting" onClick={() => handleDeleteMeeting(m.id)}><Icon name="trash" size={14} /></button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Full width too: alone in half the grid it left the other half
            empty and wrapped each address over four lines. */}
        <div className="card span-all">
          <div className="toolbar" style={{ marginBottom: 10 }}>
            <h3>Households</h3>
            {canAddHousehold && <a className="btn sm" onClick={() => setShowHouseholdForm(!showHouseholdForm)}><Icon name="plus" size={14} /> Add household</a>}
          </div>
          {showHouseholdForm && (
            <div className="form-card editing" style={{ maxWidth: 520 }}>
              <form onSubmit={handleAddHousehold}>
                <div className="field">
                  <label htmlFor="hh-name">Household name</label>
                  <input id="hh-name" value={hName} onChange={(e) => setHName(e.target.value)} placeholder="e.g. Uguru Household" required />
                </div>
                <div className="field">
                  <label htmlFor="hh-address">Address</label>
                  <input id="hh-address" value={hAddress} onChange={(e) => setHAddress(e.target.value)} placeholder="Building, road, area" />
                </div>
                <div className="field">
                  <label htmlFor="hh-phone">Phone</label>
                  <input id="hh-phone" value={hPhone} onChange={(e) => setHPhone(e.target.value)} placeholder="+973 0000 0000" />
                </div>
                <button className="btn sm" type="submit" disabled={createHousehold.isPending}>Add household</button>
                <button className="btn sm ghost" type="button" onClick={() => setShowHouseholdForm(false)}>Cancel</button>
              </form>
            </div>
          )}
          <div style={{ overflowX: 'auto' }}>
            <table className="cardtable">
              <thead><tr><th>Household</th><th>Address</th><th>Phone</th><th>Members</th><th></th></tr></thead>
              <tbody>
                {(households ?? []).map((h) => (
                  <tr key={h.id}>
                    <td data-label="Household"><b>{h.name}</b></td>
                    <td data-label="Address">{h.address || '–'}</td>
                    <td data-label="Phone">{h.phone || '–'}</td>
                    <td data-label="Members">{h.member_count}</td>
                    <td className="td-actions">{canDeleteHousehold && <button className="icon-btn" title="Remove household" aria-label="Remove household" onClick={() => handleDeleteHousehold(h.id)}><Icon name="trash" size={14} /></button>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {households?.length === 0 && <div className="empty">No households yet.</div>}
        </div>
      </div>
    
      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>House fellowships</h3>
        </div>
        <p className="muted" style={{ fontSize: '.8rem', marginBottom: 10 }}>
          Several fellowships meet on the same evening, so a session belongs to a fellowship as
          well as a date. The list is configurable because the number changes as the church grows.
        </p>
        <table className="cardtable">
          <thead><tr><th>Fellowship</th><th>Area</th><th>Location</th><th>Sessions recorded</th><th /></tr></thead>
          <tbody>
            {(fellowships ?? []).map((f) => (
              <tr key={f.id}>
                <td data-label="Fellowship"><b>{f.name}</b></td>
                <td data-label="Area">{f.area || '-'}</td>
                <td data-label="Location">{f.location_name || 'Every location'}</td>
                <td data-label="Sessions recorded">{f.session_count}</td>
                <td className="td-actions">
                  {canRemoveFellowship && (
                  <button className="icon-btn" title="Remove" aria-label={`Remove ${f.name}`}
                    onClick={async () => {
                      setFellowshipError('');
                      try { await deleteFellowship.mutateAsync(f.id); }
                      catch (err: any) {
                        setFellowshipError(err?.response?.data?.detail
                          ?? 'That fellowship could not be removed.');
                      }
                    }}>
                    <Icon name="trash" size={14} />
                  </button>)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {fellowshipError && <p className="form-error">{fellowshipError}</p>}
        {canAddFellowship && <>
        <div className="form-row" style={{ marginTop: 12 }}>
          <div className="field">
            <label htmlFor="new-fellowship">Add a fellowship</label>
            <input id="new-fellowship" value={newFellowship}
              onChange={(e) => setNewFellowship(e.target.value)} placeholder="e.g. HCF Youth" />
          </div>
          <div className="field">
            <label htmlFor="new-fellowship-area">Area</label>
            <input id="new-fellowship-area" value={newArea}
              onChange={(e) => setNewArea(e.target.value)} placeholder="e.g. Isa Town" />
          </div>
          <div className="field">
            <label htmlFor="new-fellowship-location">Location</label>
            <select id="new-fellowship-location" value={newLocation || mainLocation}
              onChange={(e) => setNewLocation(e.target.value)}>
              {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
        </div>
        <button className="btn sm" disabled={!newFellowship.trim() || createFellowship.isPending}
          onClick={async () => {
            await createFellowship.mutateAsync({ name: newFellowship.trim(), area: newArea.trim(),
              location: newLocation || mainLocation || null });
            setNewFellowship(''); setNewArea('');
          }}>
          <Icon name="plus" size={14} /> Add
        </button>
        </>}
      </div>
</>
  );
}
