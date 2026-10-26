import { Skeleton } from '../../components/ui/Skeleton';
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMember, useUpdateMember, useDeleteMember, useMoveCategory } from '../../api/members';
import { useMyLocations } from '../../api/locations';
import { apiClient } from '../../api/client';
import { useQuery } from '@tanstack/react-query';
import { MemberFormFields, type MemberFormValues } from './MemberFormFields';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { fmt } from '../../lib/format';
import type { Household, Member } from '../../types/members';
import { usePerson } from '../../api/person';
import { PersonMessages } from '../../components/person/PersonMessages';

const longDate = (d?: string | null) =>
  d ? new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '–';
import { AttendanceList, JourneyTimeline, MilestoneChips, OpenFollowUps, PersonStats, PersonTabs, initialsOf } from '../../components/person/PersonParts';
import { useAuth } from '../../context/AuthContext';
import { useLocationName } from '../../api/locations';

import { useEligibleShepherds, useAddMemberTask } from '../../api/followup';
import { canPair } from '../../lib/gender';
import { HelpMark } from '../../components/ui/HelpMark';
import { PersonTasks } from '../../components/accountability/PersonTasks';
import { AwayModal } from '../../components/accountability/TaskModals';
import { dayText } from '../../api/accountability';
const CATEGORIES = ['General Member', 'Worker in Training', 'Worker'];

function categoryBadgeColor(cat: string): 'green' | 'amber' | 'gray' {
  if (cat === 'Worker') return 'green';
  if (cat === 'Worker in Training') return 'amber';
  return 'gray';
}

function toFormValues(m: Member): MemberFormValues {
  return {
    surname: m.surname, first_name: m.first_name, other_names: m.other_names,
    gender: m.gender || 'Male', date_of_birth: m.date_of_birth || '',
    phone: m.phone, email: m.email, category: m.category,
    location: m.location, household: m.household ? String(m.household) : '', joined_date: m.joined_date,
  };
}

export function MemberProfilePage() {
  const { id } = useParams();
  const memberId = Number(id);
  const navigate = useNavigate();
  const { data: member, isLoading, isError } = useMember(memberId);
  const { data: locations } = useMyLocations();
  const updateMember = useUpdateMember(memberId);
  // Who looks after this person, shown on the profile and changeable here.
  // It was missing entirely, so nobody could see it without the list.
  const { data: shepherds } = useEligibleShepherds(member?.location, member?.id);
  const [shepherdError, setShepherdError] = useState('');
  async function changeShepherd(value: string) {
    setShepherdError('');
    try { await updateMember.mutateAsync({ assigned_to: value ? Number(value) : null } as any); }
    catch (err: any) { setShepherdError(err?.response?.data?.assigned_to?.[0] ?? 'That shepherd could not be saved.'); }
  }
  const deleteMember = useDeleteMember();
  const moveCategory = useMoveCategory(memberId);
  const { hasPermission } = useAuth();
  const canEdit = hasPermission('members', 'edit');
  const canDelete = hasPermission('members', 'delete');
  const locationName = useLocationName();

  const [editing, setEditing] = useState(false);
  const [formValues, setFormValues] = useState<MemberFormValues | null>(null);
  const [moveTarget, setMoveTarget] = useState('');
  const [editError, setEditError] = useState('');
  const [awayOpen, setAwayOpen] = useState(false);
  const [losses, setLosses] = useState<Record<string, number> | null>(null);
  const [deleteErr, setDeleteErr] = useState('');
  const [statusEdit, setStatusEdit] = useState<{ status: string; note: string } | null>(null);
  const [statusError, setStatusError] = useState('');
  async function saveStatus() {
    if (!statusEdit) return;
    setStatusError('');
    if (statusEdit.status !== 'active' && !statusEdit.note.trim()) { setStatusError('Add a short note, for example where they moved to.'); return; }
    try {
      await updateMember.mutateAsync({ status: statusEdit.status, status_note: statusEdit.note } as any);
      setStatusEdit(null);
    } catch (err: any) {
      const d = err?.response?.data ?? {};
      setStatusError(String(([] as unknown[]).concat(d.status ?? d.status_note ?? d.detail ?? 'The status could not be saved.')[0]));
    }
  }
  async function toggleLeader(on: boolean) {
    setStatusError('');
    try { await updateMember.mutateAsync({ is_leader: on } as any); }
    catch { setStatusError('The leader tick could not be saved. Try again.'); }
  }

  const { data: household } = useQuery({
    queryKey: ['household', member?.household],
    queryFn: async () => (await apiClient.get<Household>(`/households/${member!.household}/`)).data,
    enabled: !!member?.household,
  });
  const { data: householdMembers } = useQuery({
    queryKey: ['household-members', member?.household, memberId],
    queryFn: async () => {
      const resp = await apiClient.get<{ results: Member[] }>('/members/', { params: { household: member!.household } });
      return resp.data.results.filter((m) => m.id !== memberId);
    },
    enabled: !!member?.household,
  });

  const { data: person } = usePerson('members', memberId);
  // Someone at another location, or deleted: say so, rather than a page that
  // waits for ever.
  if (isError) return (
    <div className="card empty">
      This person could not be found. They may be at another location, or no longer recorded.
      <div style={{ marginTop: 10 }}><button className="btn sm outline" onClick={() => navigate('/members')}>Back to members</button></div>
    </div>
  );
  if (isLoading || !member) return <Skeleton shape="profile" />;

  function startEdit() {
    setFormValues(toFormValues(member!));
    setEditing(true);
  }

  async function saveEdit() {
    if (!formValues) return;
    // Every field the form shows is sent. Other names, gender and date of
    // birth were shown and editable but left out, so changes to them were
    // silently lost while the form closed as if saved.
    setEditError('');
    try {
      await updateMember.mutateAsync({
        surname: formValues.surname,
        first_name: formValues.first_name,
        other_names: formValues.other_names,
        gender: formValues.gender,
        date_of_birth: formValues.date_of_birth || null,
        phone: formValues.phone,
        email: formValues.email,
        location: formValues.location,
        household: formValues.household ? Number(formValues.household) : null,
      });
      setEditing(false);
    } catch (err: any) {
      const d = err?.response?.data ?? {};
      const first = Object.entries(d)[0] as [string, any] | undefined;
      const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
      const msg = first ? String([].concat(first[1])[0]) : '';
      setEditError(first?.[0] === 'phone' && msg.includes('already exists')
        ? 'This phone number already belongs to another member.'
        : first ? `${cap(first[0].replace(/_/g, ' '))}: ${cap(msg)}` : 'Could not save the changes.');
    }
  }

  // P4: deleting removes their history, so the box says what goes and
  // offers a status instead.
  async function handleDelete() {
    setDeleteErr('');
    try { setLosses((await apiClient.get(`/members/${memberId}/delete-preview/`)).data); }
    catch { setLosses({ check_ins: 0, follow_ups: 0, message_plans: 0, category_changes: 0, giving_kept: 0 }); }
  }
  async function deleteAnyway() {
    setDeleteErr('');
    try {
      await deleteMember.mutateAsync(memberId);
      navigate('/members');
    } catch (err: any) {
      setDeleteErr(err?.response?.data?.detail ?? 'This member could not be deleted.');
    }
  }

  async function handleMove() {
    if (!moveTarget) return;
    await moveCategory.mutateAsync(moveTarget);
    setMoveTarget('');
  }

  const availableCategories = CATEGORIES.filter((c) => c !== member.category);

  const phoneDigits = (member.phone || '').replace(/[^0-9]/g, '');
  const householdCard = household ? (
    <>
      <div style={{ fontWeight: 700, color: 'var(--blue-deep)' }}>{household.name}</div>
      <div className="muted" style={{ fontSize: '.86rem', marginTop: 2 }}>{household.address}</div>
      <div className="muted" style={{ fontSize: '.86rem' }}>{household.phone}</div>
      {householdMembers && householdMembers.length > 0 ? (
        <div className="section-gap">
          <div className="muted" style={{ fontSize: '.78rem', marginBottom: 6 }}>Other household members</div>
          {householdMembers.map((hm) => (
            <div key={hm.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)', fontSize: '.9rem' }}>
              <a onClick={() => navigate(`/members/${hm.id}`)} style={{ color: 'var(--blue)', cursor: 'pointer', fontWeight: 600 }}>{hm.full_name}</a>{' '}
              <span className="muted">· {hm.category}</span>
            </div>
          ))}
        </div>
      ) : <div className="muted section-gap" style={{ fontSize: '.85rem' }}>No other members linked to this household yet.</div>}
    </>
  ) : <div className="empty">Not linked to a household. Use the pencil to add one.</div>;

  const tabs = [
    { key: 'overview', label: 'Overview', body: (
      <>
        {person && <PersonStats p={person} since={person.first_came ?? member.joined_date} />}
        {canEdit && (
          <div className="field">
            <label htmlFor="move-category">Move to category</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <select id="move-category" className="selectbox" value={moveTarget || availableCategories[0]} onChange={(e) => setMoveTarget(e.target.value)}>
                {availableCategories.map((cat) => <option key={cat}>{cat}</option>)}
              </select>
              <button className="btn sm" onClick={handleMove} disabled={moveCategory.isPending}>Move</button>
            </div>
          </div>
        )}
        <h4 className="section-gap" style={{ margin: '14px 0 8px' }}>Household</h4>
        {householdCard}
      </>
    ) },
    { key: 'journey', label: 'Journey', body: person ? (<><MilestoneChips p={person} /><JourneyTimeline p={person} /></>) : null },
    { key: 'followups', label: 'Tasks', body: person ? (
      <>
        <PersonTasks type="member" personId={memberId} person={member.full_name} />
        {person.newcomer_id && <OpenFollowUps p={{ ...person, open_follow_ups: (person.open_follow_ups ?? []).filter((t: any) => t.kind === 'newcomer') } as any} onOpen={() => navigate(`/newcomers/${person.newcomer_id}`)} />}
        {hasPermission('members', 'create') && (
          <AddMemberTask memberId={memberId} shepherdId={member.assigned_to ?? null}
            shepherds={(shepherds ?? []).filter((s: any) => canPair(member.gender, s.gender))}
            currentName={member.assigned_to_name ?? ''} />
        )}
      </>
    ) : null },
    { key: 'attendance', label: 'Attendance', body: person ? <AttendanceList p={person} /> : null },
    ...(hasPermission('newcomers', 'view') ? [{ key: 'messages', label: 'Messages', body: <PersonMessages kind="member" id={memberId} /> }] : []),
    ...(hasPermission('finance', 'view') ? [{ key: 'giving', label: 'Giving', body: (
      <>
        <div className="kpi2-value" style={{ fontSize: '1.3rem' }}>{fmt(member.total_given)}</div>
        <div className="muted" style={{ fontSize: '.82rem' }}>Total given, linked to this member</div>
      </>
    ) }] : []),
  ];

  return (
    <>
      <a className="backlink" onClick={() => navigate('/members')}>← Back to members</a>
      {/* F16: one profile for a person, before and after membership. */}
      <div className="person-grid">
        <div className="card person-side">
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <div className="big-av">{initialsOf(member.full_name)}</div>
            <div className="row-actions" style={{ marginLeft: 'auto' }}>
              {canEdit && <button className="icon-btn edit" title="Edit" aria-label="Edit" onClick={startEdit}><Icon name="edit" size={15} /></button>}
              {canDelete && <button className="icon-btn" title="Delete member" aria-label="Delete member" onClick={handleDelete}><Icon name="trash" size={15} /></button>}
            </div>
          </div>
          <div className="pname">
            {member.full_name}
            {member.other_names && <span className="muted" style={{ fontSize: '.85rem', fontWeight: 600 }}> {member.other_names}</span>}
          </div>
          <div className="person-chips">
            <Badge color="green">Member</Badge>
            <Badge color={categoryBadgeColor(member.category)}>{member.category}</Badge>
            <Badge color="blue">{locationName(member.location)}</Badge>
            {member.status && member.status !== 'active' && <Badge color="gray">{member.status === 'left' ? 'Left the church' : 'Moved away'}</Badge>}
            {member.away_to && member.away_to >= new Date().toLocaleDateString('en-CA') && <Badge color="blue">Away until {dayText(member.away_to)}</Badge>}
            {member.is_leader && <Badge color="green">Leader</Badge>}
          </div>

          {editing && formValues && locations && (
            <div className="form-card editing section-gap">
              <MemberFormFields values={formValues} onChange={setFormValues} locations={locations}
                excludeMemberId={memberId} showCategoryAndJoined={false} />
              {editError && <p className="form-error" role="alert">{editError}</p>}
              <div className="form-actions-row">
                <button className="btn sm" onClick={saveEdit} disabled={updateMember.isPending}>Save changes</button>
                <button className="btn sm ghost" onClick={() => setEditing(false)}>Cancel</button>
              </div>
            </div>
          )}

          {phoneDigits && (
            <div className="person-acts">
              <a href={`tel:${member.phone}`}>Call</a>
              <a href={`https://wa.me/${phoneDigits}`} target="_blank" rel="noreferrer">WhatsApp</a>
            </div>
          )}
          <div className="person-facts">
            <div className="pf"><span>Phone</span><span>{member.phone || '–'}</span></div>
            <div className="pf"><span>Email</span><span style={{ wordBreak: 'break-all' }}>{member.email || '–'}</span></div>
            <div className="pf"><span>Gender</span><span>{member.gender || '–'}</span></div>
            <div className="pf"><span>Date of birth</span><span>{member.date_of_birth ? longDate(member.date_of_birth) : '–'}</span></div>
            <div className="pf">
              <label htmlFor="member-shepherd" style={{ color: 'var(--muted)', fontWeight: 400 }}>Shepherd</label>
              {canEdit ? (
                <select id="member-shepherd" className="selectbox" style={{ maxWidth: 170 }} value={member.assigned_to ?? ''}
                  onChange={(e) => changeShepherd(e.target.value)}>
                  <option value="">No shepherd</option>
                  {member.assigned_to && !(shepherds ?? []).some((s: any) => s.id === member.assigned_to && canPair(member.gender, s.gender)) && (
                    <option value={member.assigned_to}>{member.assigned_to_name}</option>
                  )}
                  {/* Men follow up men, women follow up women (Kay). */}
                  {(shepherds ?? []).filter((s: any) => canPair(member.gender, s.gender)).map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              ) : <b>{member.assigned_to_name || 'No shepherd'}</b>}
            </div>
            {!member.gender && member.assigned_to && (
              <span className="gender-warn">Gender not known. Check this shepherd is right, then set the gender.</span>
            )}
            {member.shepherd_problem && (
              <span className="gender-warn" role="status">
                {member.shepherd_problem}. {canEdit ? 'Choose another shepherd.' : 'Someone who can change members can choose another shepherd.'}
              </span>
            )}
            {shepherdError && <p className="form-error" role="alert">{shepherdError}</p>}
            <div className="pf">
              <span>Status<HelpMark topic="faStatusMember" /></span>
              {canEdit && !statusEdit ? (
                <button className="linkish" onClick={() => setStatusEdit({ status: member.status ?? 'active', note: member.status_note ?? '' })}>
                  {member.status === 'left' ? 'Left the church' : member.status === 'moved-away' ? 'Moved away' : 'Active'}
                </button>
              ) : !statusEdit && <b>{member.status === 'left' ? 'Left the church' : member.status === 'moved-away' ? 'Moved away' : 'Active'}</b>}
            </div>
            {statusEdit && (
              <div className="fa-inline">
                <div className="field"><label htmlFor="m-status">Status</label>
                  <select id="m-status" value={statusEdit.status} onChange={(e) => setStatusEdit({ ...statusEdit, status: e.target.value })}>
                    <option value="active">Active</option><option value="moved-away">Moved away</option><option value="left">Left the church</option>
                  </select></div>
                {statusEdit.status !== 'active' && <div className="field"><label htmlFor="m-status-note">Note</label>
                  <input id="m-status-note" value={statusEdit.note} onChange={(e) => setStatusEdit({ ...statusEdit, note: e.target.value })} placeholder="For example: moved to Canada, October 2026" /></div>}
                {statusEdit.status !== 'active' && <div className="muted fr-note">Their open tasks close and no more are made. They stay in the records and reports.</div>}
                <div className="form-actions-row"><button className="btn sm" onClick={saveStatus} disabled={updateMember.isPending}>Save</button><button className="btn sm ghost" onClick={() => setStatusEdit(null)}>Cancel</button></div>
              </div>
            )}
            {member.status && member.status !== 'active' && member.status_note && <div className="muted fr-note">{member.status_note}{member.status_date ? `, ${longDate(member.status_date)}` : ''}</div>}
            <div className="pf">
              <span>Away<HelpMark topic="faAway" /></span>
              <span>
                {member.away_to && member.away_to >= new Date().toLocaleDateString('en-CA') ? `${dayText(member.away_from)} to ${dayText(member.away_to)}` : 'No'}
                {canEdit && <button className="linkish" style={{ marginLeft: 8 }} onClick={() => setAwayOpen(true)}>{member.away_to ? 'Change' : 'Mark away'}</button>}
              </span>
            </div>
            <div className="pf">
              <span>Leader<HelpMark topic="faLeader" /></span>
              {canEdit ? (
                <label className="fr-tick" style={{ margin: 0 }}><input type="checkbox" aria-label="Leader, expected at leadership meetings" checked={!!member.is_leader} onChange={(e) => toggleLeader(e.target.checked)} />Expected at leadership meetings</label>
              ) : <b>{member.is_leader ? 'Yes' : 'No'}</b>}
            </div>
            {statusError && <p className="form-error" role="alert">{statusError}</p>}
            <div className="pf"><span>Household</span><span>{household?.name ?? 'None'}</span></div>
            <div className="pf"><span>Member since</span><span>{longDate(member.joined_date)}</span></div>
            {person?.first_came && <div className="pf"><span>First came</span><span>{longDate(person.first_came)}</span></div>}
            {person?.how_came && <div className="pf"><span>How they came</span><span>{person.how_came}</span></div>}
          </div>
        </div>
        <PersonTabs tabs={tabs} />
      </div>
      {awayOpen && <AwayModal type="member" id={memberId} name={member.full_name} current={member} onClose={() => setAwayOpen(false)} />}
      {losses && (
        <div className="fu-modal" role="dialog" aria-modal="true" aria-label={`Delete ${member.full_name}?`} onMouseDown={(e) => { if (e.target === e.currentTarget) setLosses(null); }}>
          <div className="fu-box" style={{ maxWidth: 380 }}>
            <h3 style={{ margin: '0 0 6px' }}>Delete {member.full_name}?</h3>
            <p style={{ fontSize: '.88rem', margin: '0 0 8px' }}>This also removes for good:</p>
            <ul style={{ fontSize: '.86rem', margin: '0 0 10px', paddingLeft: 18 }}>
              <li>{losses.check_ins} attendance check-in{losses.check_ins === 1 ? '' : 's'}</li>
              <li>{losses.follow_ups} follow-up{losses.follow_ups === 1 ? '' : 's'} and their visit records</li>
              <li>{losses.message_plans} message plan{losses.message_plans === 1 ? '' : 's'}</li>
              <li>their category history{losses.category_changes ? ` (${losses.category_changes} change${losses.category_changes === 1 ? '' : 's'})` : ''}</li>
            </ul>
            {losses.giving_kept > 0 && <p className="muted" style={{ fontSize: '.8rem', margin: '0 0 8px' }}>Their {losses.giving_kept} giving entr{losses.giving_kept === 1 ? 'y stays' : 'ies stay'} in Finance, without their name.</p>}
            <div className="gender-notice" style={{ margin: '0 0 12px', fontSize: '.84rem' }}>If they have moved away or left the church, set their <b>Status</b> instead. That keeps their history.</div>
            {deleteErr && <p className="form-error" role="alert">{deleteErr}</p>}
            <div className="form-actions-row">
              <button className="btn sm" onClick={() => { setLosses(null); setStatusEdit({ status: 'left', note: '' }); }}>Set status instead</button>
              <button className="btn sm ghost" style={{ color: '#B42318' }} onClick={deleteAnyway} disabled={deleteMember.isPending}>Delete anyway</button>
              <button className="btn sm ghost" onClick={() => setLosses(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/** A follow-up added by hand, for anything a member needs, not only a
 *  missed service. Goes to their shepherd unless somebody else is chosen. */
function AddMemberTask({ memberId, shepherdId, shepherds, currentName }: {
  memberId: number; shepherdId: number | null; shepherds: { id: number; name: string }[]; currentName: string;
}) {
  const add = useAddMemberTask(memberId);
  const inTwoDays = () => { const d = new Date(); d.setDate(d.getDate() + 2); return d.toLocaleDateString('en-CA'); };
  const [text, setText] = useState('');
  const [due, setDue] = useState(inTwoDays());
  const [who, setWho] = useState<string>(shepherdId ? String(shepherdId) : '');
  const [error, setError] = useState('');
  const [done, setDone] = useState('');
  const options = [...shepherds];
  if (shepherdId && !options.some((s) => s.id === shepherdId)) options.unshift({ id: shepherdId, name: currentName });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(''); setDone('');
    try {
      await add.mutateAsync({ text: text.trim(), due_date: due, assigned_to: who ? Number(who) : null });
      setDone('Task added. It is also on the Follow-up tab in Members.');
      setText(''); setDue(inTwoDays());
    } catch (err: any) {
      const d = err?.response?.data;
      setError(d?.text?.[0] || d?.assigned_to?.[0] || d?.due_date?.[0] || 'The task could not be added. Please try again.');
    }
  }

  return (
    <form className="form-card section-gap" onSubmit={submit}>
      <div className="form-row">
        <div className="field" style={{ marginBottom: 8 }}>
          <label htmlFor="member-task-text">Task</label>
          <input id="member-task-text" value={text} maxLength={300} onChange={(e) => setText(e.target.value)}
            placeholder="e.g. Call to check on him" required />
        </div>
        <div className="field" style={{ marginBottom: 8 }}>
          <label htmlFor="member-task-due">Due date</label>
          <input id="member-task-due" type="date" value={due} onChange={(e) => setDue(e.target.value)} required />
        </div>
      </div>
      <div className="field" style={{ marginBottom: 8 }}>
        <label htmlFor="member-task-for">For</label>
        <select id="member-task-for" value={who} onChange={(e) => setWho(e.target.value)}>
          <option value="">Nobody yet</option>
          {options.map((s) => <option key={s.id} value={s.id}>{s.name}{s.id === shepherdId ? ' (their shepherd)' : ''}</option>)}
        </select>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {done && <p className="report-done" role="status">{done}</p>}
      <button className="btn sm" type="submit" disabled={add.isPending}><Icon name="plus" size={14} /> Add task</button>
    </form>
  );
}
