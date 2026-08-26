import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  useEnquiry, useChangeEnquiryStage, useConvertEnquiry,
  useEnquiryTasks, useCreateEnquiryTask, useCompleteEnquiryTask, useDeleteEnquiryTask,
} from '../../api/enquiries';
import { useLocations } from '../../api/locations';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { FollowUpCompletionForm } from '../../components/followup/FollowUpCompletionForm';
import { CompletedFollowUpLog } from '../../components/followup/CompletedFollowUpLog';
import { ENQUIRY_STAGES } from '../../types/enquiries';
import type { EnquiryStage } from '../../types/enquiries';

function today() {
  return new Date().toISOString().slice(0, 10);
}

export function EnquiryProfilePage() {
  const { id } = useParams();
  const enquiryId = Number(id);
  const navigate = useNavigate();

  const { data: enquiry, isLoading } = useEnquiry(enquiryId);
  const { data: tasks } = useEnquiryTasks({ enquiry: enquiryId });
  const { data: locations } = useLocations();
  const changeStage = useChangeEnquiryStage();
  const convert = useConvertEnquiry();
  const createTask = useCreateEnquiryTask();
  const completeTask = useCompleteEnquiryTask();
  const deleteTask = useDeleteEnquiryTask();

  const [stage, setStage] = useState<EnquiryStage | ''>('');
  const [completingId, setCompletingId] = useState<number | null>(null);
  const [newTaskText, setNewTaskText] = useState('');
  const [newTaskDue, setNewTaskDue] = useState(today());
  const [convertLocation, setConvertLocation] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return <div className="card">Loading…</div>;
  if (!enquiry) return <div className="card">Enquiry not found.</div>;

  // Narrowed once here: the guards above prove it is defined, but
  // TypeScript cannot carry that into the closures below.
  const record = enquiry;

  async function handleMove() {
    const target = (stage || record.stage) as EnquiryStage;
    if (target === record.stage) return;
    let note = '';
    if (target === 'not-pursuing') {
      const entered = window.prompt('Why are we not pursuing this enquiry?');
      if (!entered) return;
      note = entered;
    }
    await changeStage.mutateAsync({ id: record.id, stage: target, note });
  }

  async function handleConvert() {
    if (!convertLocation) {
      setError('Choose which location they attended.');
      return;
    }
    setError(null);
    await convert.mutateAsync({ id: record.id, location: convertLocation });
  }

  return (
    <>
      <button className="backlink" onClick={() => navigate('/enquiries')}>
        ← Back to enquiries
      </button>

      <div className="grid g2">
        <div className="card">
          <h2 style={{ fontSize: '1.3rem', marginBottom: 2 }}>{enquiry.name}</h2>
          <div className="muted">
            Came through {enquiry.source_name} on {enquiry.received_at}
          </div>
          <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <Badge color="blue">{enquiry.stage.replace('-', ' ')}</Badge>
            {enquiry.converted_newcomer && <Badge color="green">Now a newcomer</Badge>}
          </div>

          <div className="section-gap" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '.9rem' }}>
            <div><span className="muted">Phone</span><div>{enquiry.phone || '–'}</div></div>
            <div><span className="muted">Email</span><div>{enquiry.email || '–'}</div></div>
            <div><span className="muted">Social handle</span><div>{enquiry.social_handle || '–'}</div></div>
            <div><span className="muted">Where they are</span><div>{enquiry.area || 'Not said'}</div></div>
            <div><span className="muted">Assigned to</span><div>{enquiry.assigned_to_name || 'Unassigned'}</div></div>
          </div>

          {enquiry.enquiry_text && (
            <div className="section-gap">
              <div className="muted" style={{ fontSize: '.72rem', textTransform: 'uppercase', letterSpacing: '.04em', fontWeight: 800 }}>
                What they asked
              </div>
              <div style={{ fontSize: '.9rem', marginTop: 3 }}>{enquiry.enquiry_text}</div>
            </div>
          )}

          <div className="field section-gap">
            <label htmlFor="enq-stage">Move to stage</label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <select id="enq-stage" className="selectbox" value={stage || enquiry.stage}
                onChange={(e) => setStage(e.target.value as EnquiryStage)}>
                {ENQUIRY_STAGES.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                <option value="not-pursuing">Not pursuing</option>
              </select>
              <button className="btn sm" onClick={handleMove} disabled={changeStage.isPending}>Move</button>
            </div>
          </div>

          {enquiry.converted_newcomer ? (
            <div className="help-note" style={{ marginTop: 14 }}>
              Added as a newcomer. This enquiry is kept so the church can still see they
              first came through {enquiry.source_name}.
            </div>
          ) : (
            <div className="field section-gap">
              <label htmlFor="enq-convert-loc">They attended, add as a newcomer</label>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <select id="enq-convert-loc" className="selectbox" value={convertLocation}
                  onChange={(e) => setConvertLocation(e.target.value)}>
                  <option value="">Which location…</option>
                  {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
                <button className="btn sm" onClick={handleConvert} disabled={convert.isPending}>
                  <Icon name="check" size={14} /> Add as newcomer
                </button>
              </div>
              <div className="field-hint">
                The enquiry is kept and linked, so the church can still see they first
                came through {enquiry.source_name}.
              </div>
              {error && <div className="form-error" style={{ marginTop: 8 }}>{error}</div>}
            </div>
          )}
        </div>

        <div className="card">
          <h3>Follow-up</h3>

          {(tasks ?? []).map((t) => {
            const isCompleting = completingId === t.id;
            return (
              <div key={t.id} className="followup-row" style={isCompleting ? { flexWrap: 'wrap' } : undefined}>
                <span className="avatar" style={t.done ? { background: 'var(--green-bg)', color: 'var(--green)' } : undefined}>
                  {t.done ? <Icon name="check" size={16} /> : <Icon name="alert" size={16} />}
                </span>
                <div className="followup-row-info">
                  <b style={t.done ? { textDecoration: 'line-through', color: 'var(--muted)' } : undefined}>
                    {t.text}
                  </b>
                  <div className="muted" style={{ fontSize: '.8rem' }}>Due {t.due_date}</div>
                  {t.done && <CompletedFollowUpLog log={t} />}
                </div>
                <div className="followup-row-actions">
                  {t.done && <Badge color="green">Done</Badge>}
                  <button className="btn sm outline" onClick={() => setCompletingId(isCompleting ? null : t.id)}>
                    {t.done ? 'Edit' : 'Mark done'}
                  </button>
                  <button className="icon-btn" title="Delete task"
                    onClick={() => { if (confirm('Delete this task?')) deleteTask.mutate(t.id); }}>
                    <Icon name="trash" size={14} />
                  </button>
                </div>
                {isCompleting && (
                  <div style={{ flexBasis: '100%' }}>
                    <FollowUpCompletionForm
                      idPrefix={`enqtask-${t.id}`}
                      existing={t.done ? t : null}
                      saving={completeTask.isPending}
                      onCancel={() => setCompletingId(null)}
                      onSave={async (payload) => {
                        await completeTask.mutateAsync({ id: t.id, payload });
                        setCompletingId(null);
                      }}
                    />
                  </div>
                )}
              </div>
            );
          })}

          {(tasks ?? []).length === 0 && <div className="empty">No follow-up tasks yet.</div>}

          <div className="form-card section-gap">
            <div className="form-row">
              <div className="field">
                <label htmlFor="enq-task-text">Task</label>
                <input id="enq-task-text" value={newTaskText}
                  onChange={(e) => setNewTaskText(e.target.value)}
                  placeholder="e.g. Reply and invite to Friday service" />
              </div>
              <div className="field">
                <label htmlFor="enq-task-due">Due date</label>
                <input id="enq-task-due" type="date" value={newTaskDue}
                  onChange={(e) => setNewTaskDue(e.target.value)} />
              </div>
            </div>
            <button className="btn sm" disabled={!newTaskText.trim() || createTask.isPending}
              onClick={async () => {
                await createTask.mutateAsync({
                  enquiry: enquiry.id, text: newTaskText.trim(), due_date: newTaskDue,
                });
                setNewTaskText('');
              }}>
              <Icon name="plus" size={14} /> Add task
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
