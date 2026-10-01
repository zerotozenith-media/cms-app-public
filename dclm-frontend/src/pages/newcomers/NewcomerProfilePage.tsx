import { Skeleton } from '../../components/ui/Skeleton';
import { useState } from 'react';
import { Navigate, useParams, useNavigate } from 'react-router-dom';
import {
  useNewcomer, useUpdateNewcomer, useDeleteNewcomer, useChangeStage, useSetMilestone,
  useCreateTask, useDeleteTask, useCompleteNewcomerTask, useNewcomerSources, useNewcomerTasks,
  useNewcomerReadiness, useNewcomerJourney, useMakeMember, useLogAttempt, ATTEMPT_METHODS,
} from '../../api/newcomers';
import { ReadinessCards } from '../../components/journey/ReadinessCards';
import { JourneyTimeline } from '../../components/journey/JourneyTimeline';
import { usePerson } from '../../api/person';
import { PersonMessages } from '../../components/person/PersonMessages';
import { AttendanceList, PersonStats, PersonTabs, initialsOf } from '../../components/person/PersonParts';

const longDate = (d?: string | null) =>
  d ? new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '–';

import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { FollowUpCompletionForm } from '../../components/followup/FollowUpCompletionForm';
import { CompletedFollowUpLog } from '../../components/followup/CompletedFollowUpLog';
import { useLocationName, useMyLocations } from '../../api/locations';
import { useAuth } from '../../context/AuthContext';

function stageBadgeColor(stage: string): 'blue' | 'green' | 'gray' {
  if (stage === 'member') return 'green';
  if (stage === 'not-interested') return 'gray';
  return 'blue';
}
function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    new: 'New', contacted: 'Contacted', attending: 'Attending', member: 'Member', 'not-interested': 'Not Interested',
  };
  return map[stage] ?? stage;
}

const today = new Date().toISOString().slice(0, 10);

export function NewcomerProfilePage() {
  const locationName = useLocationName();
  const { data: myLocations } = useMyLocations();
  const [editPhone, setEditPhone] = useState('');
  const [editEmail, setEditEmail] = useState('');
  const [editAddress, setEditAddress] = useState('');
  const [editLocation, setEditLocation] = useState('');
  const [editError, setEditError] = useState('');
  const { id } = useParams();
  const newcomerId = Number(id);
  const navigate = useNavigate();
  const { data: n, isLoading, isError } = useNewcomer(newcomerId);
  const { data: sources } = useNewcomerSources();
  const updateNewcomer = useUpdateNewcomer(newcomerId);
  const deleteNewcomer = useDeleteNewcomer();
  const changeStage = useChangeStage(newcomerId);
  const setMilestone = useSetMilestone(newcomerId);
  // Controls a person cannot use are not shown. Making a member also adds
  // them to the member roll, so it needs the Members permission too.
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('newcomers', 'create');
  const canEdit = hasPermission('newcomers', 'edit');
  const canDelete = hasPermission('newcomers', 'delete');
  const canMakeMember = canEdit && hasPermission('members', 'create');
  const createTask = useCreateTask(newcomerId);
  const deleteTask = useDeleteTask(newcomerId);
  const { data: readiness } = useNewcomerReadiness(newcomerId);
  const { data: journey } = useNewcomerJourney(newcomerId);
  const makeMember = useMakeMember(newcomerId);
  const logAttempt = useLogAttempt(newcomerId);
  const [attemptMethod, setAttemptMethod] = useState(ATTEMPT_METHODS[0] as string);
  const [attemptNote, setAttemptNote] = useState('');

  async function handleMakeMember() {
    if (!n) return;
    if (!confirm(
      `Add ${n.name} to the member roll?\n\n` +
      'Their follow-up history stays with them, and their card remains on the board under Member.'
    )) return;
    setMakeError('');
    // A refusal, such as their phone already belonging to a member, says why.
    try { await makeMember.mutateAsync(); }
    catch (e: any) { setMakeError(e?.response?.data?.detail || 'They could not be added to the member roll. Try again.'); }
  }
  const [makeError, setMakeError] = useState('');

  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editSource, setEditSource] = useState<number>(0);
  const [showNotInterested, setShowNotInterested] = useState(false);
  const [niNote, setNiNote] = useState('');
  const [reactivateTarget, setReactivateTarget] = useState('new');
  const [taskText, setTaskText] = useState('');
  const [taskDue, setTaskDue] = useState(today);

  const { data: person } = usePerson('newcomers', newcomerId);
  // Someone at another location, or deleted: say so, rather than a page that
  // waits for ever.
  if (isError) return (
    <div className="card empty">
      This person could not be found. They may be at another location, or no longer recorded.
      <div style={{ marginTop: 10 }}><button className="btn sm outline" onClick={() => navigate('/newcomers')}>Back to newcomers</button></div>
    </div>
  );
  if (isLoading || !n) return <Skeleton shape="profile" />;

  function startEdit() {
    setEditName(n!.name);
    setEditSource(n!.source);
    setEditPhone(n!.phone ?? '');
    setEditEmail(n!.email ?? '');
    setEditAddress(n!.address ?? '');
    setEditLocation(n!.location ?? '');
    setEditError('');
    setEditing(true);
  }
  // Every contact detail can be corrected, and the location changed. Only
  // the name and source could be before, so a mistyped phone number from a
  // paper card could never be fixed.
  async function saveEdit() {
    setEditError('');
    try {
      await updateNewcomer.mutateAsync({
        name: editName, source: editSource, phone: editPhone, email: editEmail,
        address: editAddress, location: editLocation,
      } as any);
      setEditing(false);
    } catch (err: any) {
      const d = err?.response?.data ?? {};
      const first = Object.entries(d)[0] as [string, any] | undefined;
      setEditError(first ? `${first[0]}: ${[].concat(first[1])[0]}` : 'Could not save the changes.');
    }
  }
  async function handleDelete() {
    if (!confirm('Delete this newcomer record?')) return;
    await deleteNewcomer.mutateAsync(newcomerId);
    navigate('/newcomers');
  }
  async function confirmNotInterested() {
    await changeStage.mutateAsync({ to_stage: 'not-interested', note: niNote.trim() });
    setShowNotInterested(false);
    setNiNote('');
  }
  async function reactivate() {
    await changeStage.mutateAsync({ to_stage: reactivateTarget });
  }
  async function handleAddTask(e: React.FormEvent) {
    e.preventDefault();
    if (!taskText.trim()) return;
    await createTask.mutateAsync({ text: taskText, due_date: taskDue });
    setTaskText('');
    setTaskDue(today);
  }

  // F16: one page per person. Once they are a member, their card opens the
  // member profile, which carries this whole story.
  if (n.stage === 'member' && person?.member_id) {
    return <Navigate to={`/members/${person.member_id}`} replace />;
  }
  const phoneDigits = (n.phone || '').replace(/[^0-9]/g, '');
  const tabs = [
    { key: 'overview', label: 'Overview', body: (
      <>
        {person && <PersonStats p={person} />}
        {readiness?.ready && n.stage !== 'member' && (
        <div className="ready-banner">
          <Icon name="check" size={17} />
          <b>Ready for membership.</b> All three conditions are met, so this is proposed for you to confirm.
          {canMakeMember && (
            <button className="btn sm" style={{ marginLeft: 'auto' }}
              onClick={handleMakeMember} disabled={makeMember.isPending}>Make a member</button>
          )}
        </div>
)}
        <div className="toolbar" style={{ margin: '4px 0 12px' }}>
          <h4 style={{ flex: 1, margin: 0 }}>Membership readiness</h4>
          {canMakeMember && n.stage !== 'member' && (
            <button className="btn sm outline" onClick={handleMakeMember} disabled={makeMember.isPending}>
              <Icon name="check" size={14} /> Make a member now
            </button>
          )}
        </div>
        {makeError && <p className="form-error" role="alert">{makeError}</p>}
        {readiness && <ReadinessCards r={readiness} />}
        <div className="muted" style={{ fontSize: '.8rem' }}>
          A newcomer is proposed once the Salvation milestone is recorded, they have attended at
          least half the Friday services at their location since they first came, and they first
          came at least six months ago. An administrator always confirms, and can
          add anyone at any time regardless, for example someone relocating from another church.
        </div>
        <div className="section-gap">
          {n.stage !== 'not-interested' ? (canEdit && (
            <>
              <span style={{ marginLeft: 8 }}>
                <button className="btn sm ghost" onClick={() => setShowNotInterested(!showNotInterested)}>Mark as Not Interested</button>
              </span>
              {showNotInterested && (
                <div className="form-card section-gap">
                  <p className="muted" style={{ fontSize: '.84rem', marginBottom: 10 }}>
                    This moves them out of active follow-up. Their record and history are kept, and they can be reactivated at any time.
                  </p>
                  <div className="field">
                    <label htmlFor="nc-ni-note">Note (optional)</label>
                    <textarea id="nc-ni-note" value={niNote} onChange={(e) => setNiNote(e.target.value)} placeholder="Why are they being marked not interested?" />
                  </div>
                  <button className="btn sm red" onClick={confirmNotInterested} disabled={changeStage.isPending}>Confirm</button>
                  <button className="btn sm ghost" onClick={() => setShowNotInterested(false)}>Cancel</button>
                </div>
              )}
            </>
          )) : (
            <div className="form-card section-gap" style={{ borderColor: 'var(--line)', background: 'var(--sky-2)' }}>
              <div style={{ fontWeight: 700, color: 'var(--blue-deep)', marginBottom: 4 }}>Marked Not Interested</div>
              <div className="muted" style={{ fontSize: '.84rem' }}>
                On {n.stage_since}{n.not_interested_note ? ` · ${n.not_interested_note}` : ''}
              </div>
              <div className="field section-gap" style={{ marginBottom: 0 }}>
                <label htmlFor="nc-reactivate">Reactivate to</label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <select id="nc-reactivate" className="selectbox" value={reactivateTarget} onChange={(e) => setReactivateTarget(e.target.value)}>
                    <option value="new">New</option>
                    <option value="contacted">Contacted</option>
                    <option value="attending">Attending</option>
                  </select>
                  <button className="btn sm" onClick={reactivate} disabled={changeStage.isPending}>Reactivate</button>
                </div>
              </div>
            </div>
          )}
        </div>
      </>
    ) },
    { key: 'journey', label: 'Journey', body: (
      <>
        <h4 style={{ margin: '0 0 8px' }}>Spiritual milestones</h4>
        <div style={{ marginBottom: 14 }}>
          {n.milestones.map((m) => (
            <div className="mrow" key={m.milestone_type_id}>
              <input
                type="checkbox"
                checked={!!m.achieved_date}
                disabled={!canEdit}
                onChange={(e) => setMilestone.mutate({ milestone_type: m.milestone_type_id, achieved: e.target.checked })}
              />
              <span className="mname">{m.name}</span>
              <span className="mdate">{m.achieved_date || ''}</span>
            </div>
          ))}
        </div>
        <div className="muted" style={{ fontSize: '.8rem', marginBottom: 10 }}>
          Every contact, including attempts that did not reach them.
        </div>
        <JourneyTimeline events={journey ?? []} />

        {canCreate && <div className="form-card section-gap">
          <div className="muted" style={{ fontSize: '.8rem', marginBottom: 8 }}>
            Tried and could not reach them? Record it, so the history does not look as though
            nobody tried.
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="attempt-method">How you tried</label>
              <select id="attempt-method" value={attemptMethod}
                onChange={(e) => setAttemptMethod(e.target.value)}>
                {ATTEMPT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="attempt-note">Note</label>
              <input id="attempt-note" value={attemptNote}
                onChange={(e) => setAttemptNote(e.target.value)}
                placeholder="e.g. left a voice note" />
            </div>
          </div>
          <button className="btn sm outline" disabled={logAttempt.isPending}
            onClick={async () => {
              await logAttempt.mutateAsync({ method: attemptMethod, note: attemptNote });
              setAttemptNote('');
            }}>
            <Icon name="plus" size={14} /> Log the attempt
          </button>
        </div>}
      </>
    ) },
    { key: 'followups', label: 'Follow-ups', body: (
      <>
          <TaskList newcomerId={newcomerId} onDelete={(taskId) => deleteTask.mutate(taskId)} />
          <div className="form-card section-gap">
            {canCreate && <form onSubmit={handleAddTask}>
              <div className="form-row">
                <div className="field" style={{ marginBottom: 8 }}>
                  <label htmlFor="nc-task-text">Task</label>
                  <input id="nc-task-text" value={taskText} onChange={(e) => setTaskText(e.target.value)} placeholder="e.g. Call back" required />
                </div>
                <div className="field" style={{ marginBottom: 8 }}>
                  <label htmlFor="nc-task-due">Due date</label>
                  <input id="nc-task-due" type="date" value={taskDue} onChange={(e) => setTaskDue(e.target.value)} required />
                </div>
              </div>
              <button className="btn sm" type="submit"><Icon name="plus" size={14} /> Add task</button>
            </form>}
          </div>
      </>
    ) },
    { key: 'attendance', label: 'Attendance', body: person ? <AttendanceList p={person} /> : null },
    ...(hasPermission('newcomers', 'view') ? [{ key: 'messages', label: 'Messages', body: <PersonMessages kind="newcomer" id={newcomerId} /> }] : []),
  ];

  return (
    <>
      <a className="backlink" onClick={() => navigate('/newcomers')}>← Back to newcomers</a>
      <div className="person-grid">
        <div className="card person-side">
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <div className="big-av">{initialsOf(n.name)}</div>
            <div className="row-actions" style={{ marginLeft: 'auto' }}>
              {canEdit && <button className="icon-btn edit" title="Edit" aria-label="Edit" onClick={startEdit}><Icon name="edit" size={15} /></button>}
              {canDelete && <button className="icon-btn" title="Delete" aria-label="Delete" onClick={handleDelete}><Icon name="trash" size={15} /></button>}
            </div>
          </div>
          <div className="pname">{n.name}</div>
          <div className="person-chips">
            <Badge color="blue">Newcomer</Badge>
            <Badge color={stageBadgeColor(n.stage)}>{stageLabel(n.stage)}</Badge>
            <Badge color="blue">{locationName(n.location)}</Badge>
          </div>
          {/* F9: the edit opens here, under the name, where the pencil is. */}
          <div className="section-gap">
          {editing && sources && (
            <div className="form-card">
              <div className="field"><label htmlFor="nc-edit-name">Name</label><input id="nc-edit-name" value={editName} onChange={(e) => setEditName(e.target.value)} /></div>
              <div className="field">
                <label htmlFor="nc-edit-source">Source</label>
                <select id="nc-edit-source" value={editSource} onChange={(e) => setEditSource(Number(e.target.value))}>
                  {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div className="form-row">
                <div className="field"><label htmlFor="nc-edit-phone">Phone</label><input id="nc-edit-phone" value={editPhone} onChange={(e) => setEditPhone(e.target.value)} /></div>
                <div className="field"><label htmlFor="nc-edit-email">Email</label><input id="nc-edit-email" type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} /></div>
              </div>
              <div className="field"><label htmlFor="nc-edit-address">Address</label><input id="nc-edit-address" value={editAddress} onChange={(e) => setEditAddress(e.target.value)} /></div>
              <div className="field">
                <label htmlFor="nc-edit-location">Location</label>
                <select id="nc-edit-location" value={editLocation} onChange={(e) => setEditLocation(e.target.value)}>
                  {(myLocations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
                <div className="field-hint">Moving them gives them a shepherd at the new location if theirs cannot serve it.</div>
              </div>
              {editError && <p className="form-error" role="alert">{editError}</p>}
              <button className="btn sm" onClick={saveEdit} disabled={updateNewcomer.isPending}>Save changes</button>
              <button className="btn sm ghost" onClick={() => setEditing(false)}>Cancel</button>
            </div>
          )}
          </div>
          {phoneDigits && (
            <div className="person-acts">
              <a href={`tel:${n.phone}`}>Call</a>
              <a href={`https://wa.me/${phoneDigits}`} target="_blank" rel="noreferrer">WhatsApp</a>
            </div>
          )}
          <div className="person-facts">
            <div className="pf"><span>Phone</span><span>{n.phone || '–'}</span></div>
            <div className="pf"><span>Email</span><span style={{ wordBreak: 'break-all' }}>{n.email || '–'}</span></div>
            <div className="pf"><span>Address</span><span>{[n.address, n.city_governorate].filter(Boolean).join(', ') || '–'}</span></div>
            <div className="pf"><span>Shepherd</span>{n.assigned_to_name ? <span>{n.assigned_to_name}</span> : <Badge color="amber">Unassigned</Badge>}</div>
            <div className="pf"><span>How they came</span><span>{n.source_name || '–'}</span></div>
            {person?.first_came && <div className="pf"><span>First came</span><span>{longDate(person.first_came)}</span></div>}
            <div className="pf"><span>First meeting</span><span>{n.meeting_attended_name || '–'}</span></div>
            <div className="pf"><span>Gender and age</span><span>{[n.gender, n.age_group].filter(Boolean).join(', ') || '–'}</span></div>
            <div className="pf"><span>Invited by</span><span>{n.invited_by_member_name || '–'}</span></div>
          </div>
          {n.prayer_request && (
            <div className="section-gap" style={{ fontSize: '.86rem' }}><span className="muted">Prayer request</span><div>{n.prayer_request}</div></div>
          )}
        </div>
        <PersonTabs tabs={tabs} />
      </div>
    </>
  );
}

function TaskList({ newcomerId, onDelete }: { newcomerId: number; onDelete: (id: number) => void }) {
  const { hasPermission } = useAuth();
  const canEdit = hasPermission('newcomers', 'edit');
  const canDelete = hasPermission('newcomers', 'delete');
  const { data: tasks } = useNewcomerTasks(newcomerId);
  const complete = useCompleteNewcomerTask(newcomerId);
  const [completingId, setCompletingId] = useState<number | null>(null);

  if (!tasks || !tasks.length) return <div className="empty">No follow-up tasks yet.</div>;
  return (
    <>
      {tasks.map((t) => {
        const isCompleting = completingId === t.id;
        return (
          <div key={t.id} style={{ padding: '8px 0', borderBottom: '1px solid var(--line)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div style={{ minWidth: 0 }}>
                <b style={t.done ? { textDecoration: 'line-through', color: 'var(--muted)' } : undefined}>{t.text}</b>
                <div className="muted" style={{ fontSize: '.78rem' }}>Due {t.due_date}</div>
                {t.done && <CompletedFollowUpLog log={t} />}
              </div>
              <div className="row-actions">
                {t.done && <Badge color="green">Done</Badge>}
                {canEdit && (
                  <button className="btn sm outline" onClick={() => setCompletingId(isCompleting ? null : t.id)}>
                    {t.done ? 'Edit' : 'Mark done'}
                  </button>
                )}
                {canDelete && <button className="icon-btn" title="Delete task" onClick={() => onDelete(t.id)}><Icon name="trash" size={14} /></button>}
              </div>
            </div>
            {isCompleting && (
              <FollowUpCompletionForm
                idPrefix={`nctask-${t.id}`}
                existing={t.done ? t : null}
                saving={complete.isPending}
                onCancel={() => setCompletingId(null)}
                onSave={async (payload) => {
                  await complete.mutateAsync({ id: t.id, payload });
                  setCompletingId(null);
                }}
              />
            )}
          </div>
        );
      })}
    </>
  );
}
