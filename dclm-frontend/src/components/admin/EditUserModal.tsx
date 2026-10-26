import { useState } from 'react';
import { useAddToRoll, useMemberChoices, useRoles, useSendReset, useUpdateUser } from '../../api/admin';
import { useMyLocations } from '../../api/locations';
import { useAuth } from '../../context/AuthContext';
import { HelpMark } from '../ui/HelpMark';
import type { AdminUser } from '../../types/admin';

function firstMessage(e: any, fallback: string) {
  const d = e?.response?.data;
  if (!d) return fallback;
  if (typeof d === 'string') return d;
  if (d.detail) return String(d.detail);
  const first = Object.values(d)[0];
  return first ? String(([] as unknown[]).concat(first as any)[0]) : fallback;
}

/**
 * Edit an account (items 12 and 17, plan demo 4): name, email, role,
 * location, gender, member record, shepherding, the Follow-up Coordinator
 * tick and what it covers, a password reset link, and switching it off.
 */
export function EditUserModal({ user, onClose }: { user: AdminUser; onClose: () => void }) {
  const { user: me } = useAuth();
  const { data: roles } = useRoles();
  const { data: locations } = useMyLocations();
  const { data: memberChoices } = useMemberChoices();
  const update = useUpdateUser();
  const reset = useSendReset();
  const addToRoll = useAddToRoll();

  const [firstName, setFirstName] = useState(user.first_name);
  const [lastName, setLastName] = useState(user.last_name);
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState(user.role ? String(user.role) : '');
  const [location, setLocation] = useState(user.location ?? '');
  const [gender, setGender] = useState(user.gender ?? '');
  const [member, setMember] = useState(user.member ? String(user.member) : '');
  const [shepherd, setShepherd] = useState(!!user.can_shepherd);
  const [coord, setCoord] = useState(!!user.is_followup_coordinator);
  const [covers, setCovers] = useState(user.coordinates_location ?? '');
  const [err, setErr] = useState('');
  const [note, setNote] = useState('');

  const isMe = me?.id === user.id;
  const manyPlaces = new Set((memberChoices ?? []).map((m) => m.location)).size > 1;
  // A location account coordinates its own location only.
  const coverChoices = location ? (locations ?? []).filter((l: any) => l.id === location) : (locations ?? []);

  async function save() {
    setErr(''); setNote('');
    try {
      await update.mutateAsync({
        id: user.id, first_name: firstName, last_name: lastName, email, role: role ? Number(role) : null,
        location: location || null, gender, member: member ? Number(member) : null, can_shepherd: shepherd,
        is_followup_coordinator: coord, coordinates_location: coord ? (location || covers || null) : null,
      });
      onClose();
    } catch (e) { setErr(firstMessage(e, 'The account could not be saved. Try again.')); }
  }
  async function switchOnOff() {
    setErr(''); setNote('');
    const off = user.is_active;
    if (off && !confirm(`Switch off ${user.full_name}? They can no longer sign in, and their open follow-up tasks go to the Follow-up Coordinator. Their records stay.`)) return;
    try {
      await update.mutateAsync({ id: user.id, is_active: !off });
      onClose();
    } catch (e) { setErr(firstMessage(e, 'That change could not be saved.')); }
  }
  async function sendReset() {
    setErr(''); setNote('');
    try { setNote((await reset.mutateAsync(user.id)).detail); }
    catch (e) { setErr(firstMessage(e, 'The link could not be sent. Try again.')); }
  }
  async function onAddToRoll() {
    setErr(''); setNote('');
    try {
      const r = await addToRoll.mutateAsync({ id: user.id });
      setMember(String(r.member));
      setNote(`${r.member_name} is now on the member roll and linked to this account.`);
    } catch (e) { setErr(firstMessage(e, 'They could not be added to the member roll.')); }
  }

  return (
    <div className="fu-modal" role="dialog" aria-modal="true" aria-label={`Edit ${user.full_name}`}
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="fu-box">
        <h3 style={{ margin: '0 0 4px' }}>Edit {user.full_name}</h3>
        <p className="muted" style={{ margin: '0 0 12px', fontSize: '.85rem' }}>
          {user.email}{!user.is_active && <> · <b>Switched off</b></>}
        </p>
        <div className="form-row">
          <div className="field"><label htmlFor="eu-first">First name</label><input id="eu-first" value={firstName} onChange={(e) => setFirstName(e.target.value)} /></div>
          <div className="field"><label htmlFor="eu-last">Last name</label><input id="eu-last" value={lastName} onChange={(e) => setLastName(e.target.value)} /></div>
        </div>
        <div className="field"><label htmlFor="eu-email">Email</label><input id="eu-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        <div className="form-row">
          <div className="field">
            <label htmlFor="eu-role">Role</label>
            <select id="eu-role" value={role} onChange={(e) => setRole(e.target.value)}>
              {!role && <option value="">No role</option>}
              {(roles ?? []).filter((r: any) => r.assignable !== false || String(r.id) === role).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="eu-loc">Location</label>
            <select id="eu-loc" value={location} disabled={!!me?.location} onChange={(e) => { setLocation(e.target.value); if (e.target.value) setCovers(e.target.value); }}>
              {!me?.location && <option value="">All locations</option>}
              {(locations ?? []).map((l: any) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
        </div>
        <div className="form-row">
          <div className="field">
            <label htmlFor="eu-gender">Gender</label>
            <select id="eu-gender" value={gender} onChange={(e) => setGender(e.target.value as any)}>
              <option value="">Not set</option><option>Male</option><option>Female</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="eu-member">Member record</label>
            <select id="eu-member" value={member} onChange={(e) => setMember(e.target.value)}>
              <option value="">Not a member</option>
              {(memberChoices ?? []).filter((m) => !m.linked_to || m.linked_to === user.id || String(m.id) === member).map((m) => (
                <option key={m.id} value={m.id}>{m.name}{manyPlaces && m.location_name ? ` · ${m.location_name}` : ''}</option>
              ))}
            </select>
            {!member && (
              <button type="button" className="linkish" onClick={onAddToRoll} disabled={addToRoll.isPending}>
                Add to member roll<HelpMark topic="userAddToRoll" />
              </button>
            )}
          </div>
        </div>
        <label className="fr-tick"><input type="checkbox" checked={shepherd} onChange={(e) => setShepherd(e.target.checked)} /> Can shepherd others</label>
        {user.can_shepherd && !shepherd && <div className="muted fr-note">Their open follow-up tasks go to the Follow-up Coordinator when you save.</div>}
        <div className="fr-group coord">
          <label className="fr-tick" style={{ fontWeight: 600 }}>
            <input type="checkbox" checked={coord} onChange={(e) => setCoord(e.target.checked)} /> Follow-up Coordinator<HelpMark topic="fuCoordinator" />
          </label>
          <div className="muted" style={{ fontSize: '.8rem', margin: '0 0 8px' }}>
            Reviews late tasks and their reasons, gets alerts on repeated absences, and sees every shepherd's record. Works with any role, so an administrator can be one too.
          </div>
          {coord && (
            <div className="field" style={{ margin: 0 }}>
              <label htmlFor="eu-covers">Coordinates follow-up for<HelpMark topic="fuCoordinates" /></label>
              <select id="eu-covers" value={location || covers} disabled={!!location} onChange={(e) => setCovers(e.target.value)}>
                {!location && <option value="">All locations</option>}
                {coverChoices.map((l: any) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
              {location && <div className="muted fr-note">This account covers one location, so it coordinates that location only.</div>}
            </div>
          )}
        </div>
        {err && <p className="form-error" role="alert">{err}</p>}
        {note && <p className="fr-done" role="status">{note}</p>}
        <div className="form-actions-row" style={{ borderTop: '1px solid var(--line)', paddingTop: 12, flexWrap: 'wrap' }}>
          <button className="btn sm" onClick={save} disabled={update.isPending}>Save changes</button>
          <button className="btn sm outline" onClick={sendReset} disabled={reset.isPending || !user.is_active}>
            Send password reset link
          </button><HelpMark topic="userReset" />
          {!isMe && <button className="btn sm ghost" onClick={switchOnOff} disabled={update.isPending}>
            {user.is_active ? 'Switch off' : 'Switch on'}
          </button>}
          {!isMe && <HelpMark topic="userSwitchOff" />}
          <button className="btn sm ghost" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
