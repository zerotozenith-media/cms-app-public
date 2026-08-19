import { useState } from 'react';
import { useMeetingTypes, useCreateMeetingType, useDeleteMeetingType } from '../../api/attendance';
import { useHouseholds, useCreateHousehold, useDeleteHousehold } from '../../api/members';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { useAppSettings, useUpdateAppSetting } from '../../api/settings';
import { HelpMark } from '../../components/ui/HelpMark';

export function MeetingTypesHouseholdsTab() {
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
    await createMeetingType.mutateAsync({ id: mtId, name: mtName, day: mtDay, frequency: mtFreq, detail_level: mtLevel });
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
          people each Worker already carries. Only Workers can be shepherds.
          Run it from <b>Members, Auto-assign</b>.
        </div>
      </div>

      <div className="grid g2">
        <div className="card">
          <div className="toolbar" style={{ marginBottom: 10 }}>
            <h3>Meeting types</h3>
            <a className="btn sm" onClick={() => setShowMeetingForm(!showMeetingForm)}><Icon name="plus" size={14} /> Add</a>
          </div>
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
                    <input id="mt-day" value={mtDay} onChange={(e) => setMtDay(e.target.value)} placeholder="e.g. Sunday or –" />
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
            <table className="cardtable">
              <thead><tr><th>Meeting</th><th>Detail level</th><th></th></tr></thead>
              <tbody>
                {(meetingTypes ?? []).map((m) => (
                  <tr key={m.id}>
                    <td data-label="Meeting">{m.name}</td>
                    <td data-label="Detail level"><Badge color={m.detail_level === 'detailed' ? 'blue' : 'gray'}>{m.detail_level}</Badge></td>
                    <td className="td-actions"><button className="icon-btn" onClick={() => handleDeleteMeeting(m.id)}><Icon name="trash" size={14} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="toolbar" style={{ marginBottom: 10 }}>
            <h3>Households</h3>
            <a className="btn sm" onClick={() => setShowHouseholdForm(!showHouseholdForm)}><Icon name="plus" size={14} /> Add household</a>
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
                    <td className="td-actions"><button className="icon-btn" onClick={() => handleDeleteHousehold(h.id)}><Icon name="trash" size={14} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {households?.length === 0 && <div className="empty">No households yet.</div>}
        </div>
      </div>
    </>
  );
}
