import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  useNewcomer, useUpdateNewcomer, useDeleteNewcomer, useChangeStage, useSetMilestone,
  useCreateTask, useDeleteTask, useCompleteNewcomerTask, useNewcomerSources, useNewcomerTasks,
} from '../../api/newcomers';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { FollowUpCompletionForm } from '../../components/followup/FollowUpCompletionForm';
import { CompletedFollowUpLog } from '../../components/followup/CompletedFollowUpLog';

function stageBadgeColor(stage: string): 'blue' | 'green' | 'gray' {
  if (stage === 'integrated') return 'green';
  if (stage === 'not-interested') return 'gray';
  return 'blue';
}
function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    new: 'New', contacted: 'Contacted', visiting: 'Visiting', integrated: 'Integrated', 'not-interested': 'Not Interested',
  };
  return map[stage] ?? stage;
}

const today = new Date().toISOString().slice(0, 10);

export function NewcomerProfilePage() {
  const { id } = useParams();
  const newcomerId = Number(id);
  const navigate = useNavigate();
  const { data: n, isLoading } = useNewcomer(newcomerId);
  const { data: sources } = useNewcomerSources();
  const updateNewcomer = useUpdateNewcomer(newcomerId);
  const deleteNewcomer = useDeleteNewcomer();
  const changeStage = useChangeStage(newcomerId);
  const setMilestone = useSetMilestone(newcomerId);
  const createTask = useCreateTask(newcomerId);
  const deleteTask = useDeleteTask(newcomerId);

  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [editSource, setEditSource] = useState<number>(0);
  const [showNotInterested, setShowNotInterested] = useState(false);
  const [niNote, setNiNote] = useState('');
  const [reactivateTarget, setReactivateTarget] = useState('new');
  const [taskText, setTaskText] = useState('');
  const [taskDue, setTaskDue] = useState(today);

  if (isLoading || !n) return <div className="card">Loading…</div>;

  function startEdit() {
    setEditName(n!.name);
    setEditSource(n!.source);
    setEditing(true);
  }
  async function saveEdit() {
    await updateNewcomer.mutateAsync({ name: editName, source: editSource });
    setEditing(false);
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

  return (
    <>
      <a className="backlink" onClick={() => navigate('/newcomers')}>← Back to pipeline</a>
      <div className="grid g2">
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <h3 style={{ fontSize: '1.15rem' }}>{n.name}</h3>
            <div className="row-actions">
              <button className="icon-btn edit" title="Edit" onClick={startEdit}><Icon name="edit" size={15} /></button>
              <button className="icon-btn" title="Delete" onClick={handleDelete}><Icon name="trash" size={15} /></button>
            </div>
          </div>
          <div className="muted" style={{ margin: '4px 0 14px' }}>
            Source: {n.source_name} · Assigned: {n.assigned_to_name || 'Unassigned'} · {n.location}
          </div>

          {editing && sources && (
            <div className="form-card">
              <div className="field"><label htmlFor="nc-edit-name">Name</label><input id="nc-edit-name" value={editName} onChange={(e) => setEditName(e.target.value)} /></div>
              <div className="field">
                <label htmlFor="nc-edit-source">Source</label>
                <select id="nc-edit-source" value={editSource} onChange={(e) => setEditSource(Number(e.target.value))}>
                  {sources.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <button className="btn sm" onClick={saveEdit} disabled={updateNewcomer.isPending}>Save changes</button>
              <button className="btn sm ghost" onClick={() => setEditing(false)}>Cancel</button>
            </div>
          )}

          <Badge color={stageBadgeColor(n.stage)}>{stageLabel(n.stage)}</Badge>

          {n.stage !== 'not-interested' ? (
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
          ) : (
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
                    <option value="visiting">Visiting</option>
                  </select>
                  <button className="btn sm" onClick={reactivate} disabled={changeStage.isPending}>Reactivate</button>
                </div>
              </div>
            </div>
          )}

          <h3 className="section-gap">Follow-up tasks</h3>
          {/* Batch E replaces this with the real four-field completion
              form. Until then the button is disabled rather than left
              wired to a PATCH of { done: true }, which the API now
              ignores: it would look like it worked and change nothing. */}
          <TaskList newcomerId={newcomerId} onDelete={(taskId) => deleteTask.mutate(taskId)} />
          <div className="form-card section-gap">
            <form onSubmit={handleAddTask}>
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
            </form>
          </div>
        </div>

        <div className="card">
          <h3>Spiritual milestones</h3>
          {n.milestones.map((m) => (
            <div className="mrow" key={m.milestone_type_id}>
              <input
                type="checkbox"
                checked={!!m.achieved_date}
                onChange={(e) => setMilestone.mutate({ milestone_type: m.milestone_type_id, achieved: e.target.checked })}
              />
              <span className="mname">{m.name}</span>
              <span className="mdate">{m.achieved_date || ''}</span>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

function TaskList({ newcomerId, onDelete }: { newcomerId: number; onDelete: (id: number) => void }) {
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
                <button className="btn sm outline" onClick={() => setCompletingId(isCompleting ? null : t.id)}>
                  {t.done ? 'Edit' : 'Mark done'}
                </button>
                <button className="icon-btn" title="Delete task" onClick={() => onDelete(t.id)}><Icon name="trash" size={14} /></button>
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
