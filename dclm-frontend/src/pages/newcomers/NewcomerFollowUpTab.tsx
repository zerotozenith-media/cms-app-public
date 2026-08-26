import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAllNewcomerTasks, useCompleteNewcomerTask, useDeleteTask } from '../../api/newcomers';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { FollowUpCompletionForm } from '../../components/followup/FollowUpCompletionForm';
import { CompletedFollowUpLog } from '../../components/followup/CompletedFollowUpLog';
import type { NewcomerTask } from '../../types/newcomers';

type StatusFilter = 'open' | 'completed' | 'all';

function urgency(task: NewcomerTask): 'green' | 'red' | 'amber' | 'gray' {
  if (task.done) return 'green';
  const days = Math.round(
    (Date.now() - new Date(`${task.due_date}T00:00:00`).getTime()) / 86400000,
  );
  if (days > 3) return 'red';
  if (days > 0) return 'amber';
  return 'gray';
}

/**
 * The same follow-up pattern as Members, on purpose: a leader who has
 * learned one screen should not have to learn a second. Shares the
 * completion form and the log display rather than duplicating them.
 */
export function NewcomerFollowUpTab() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<StatusFilter>('open');
  const [ordering, setOrdering] = useState('due_date');
  const [completingId, setCompletingId] = useState<number | null>(null);

  const { data: tasks, isLoading } = useAllNewcomerTasks({
    done: status === 'all' ? undefined : status === 'completed',
    ordering,
  });
  // The completion hook invalidates one newcomer's cache; passing 0 is
  // fine here because the list query is invalidated by key below.
  const complete = useCompleteNewcomerTask(0);
  const remove = useDeleteTask(0);

  const rows = tasks ?? [];
  const open = rows.filter((t) => !t.done);
  const today = new Date().toISOString().slice(0, 10);

  const statItems: StatItem[] = [
    { icon: 'userplus', color: 'blue', label: 'Open follow-ups', value: open.length },
    {
      icon: 'alert',
      color: open.some((t) => t.due_date < today) ? 'red' : 'gray',
      label: 'Overdue',
      value: open.filter((t) => t.due_date < today).length,
    },
    {
      icon: 'user',
      color: open.some((t) => !t.assigned_to) ? 'amber' : 'gray',
      label: 'Unassigned',
      value: open.filter((t) => !t.assigned_to).length,
    },
  ];

  async function handleDelete(id: number) {
    if (!confirm('Delete this task? This cannot be undone.')) return;
    await remove.mutateAsync(id);
  }

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab" onClick={() => navigate('/newcomers')}>Pipeline</button>
          <button className="tab active">Follow-up</button>
          <button className="tab" onClick={() => navigate('/newcomers/qr')}>QR Registration</button>
          <button className="tab" onClick={() => navigate('/newcomers/manual')}>Manual Entry</button>
        </div>
      </div>

      <StatRow stats={statItems} columns={3} />

      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>Newcomers needing follow-up</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <label htmlFor="ncfu-status" className="sr-only">Status</label>
            <select id="ncfu-status" className="selectbox" value={status}
              onChange={(e) => setStatus(e.target.value as StatusFilter)}>
              <option value="open">Open only</option>
              <option value="completed">Completed only</option>
              <option value="all">All (open + completed)</option>
            </select>

            <label htmlFor="ncfu-sort" className="sr-only">Sort</label>
            <select id="ncfu-sort" className="selectbox" value={ordering}
              onChange={(e) => setOrdering(e.target.value)}>
              <option value="due_date">Sort: Due soonest</option>
              <option value="-due_date">Sort: Due latest</option>
            </select>
          </div>
        </div>

        {isLoading && <div className="empty">Loading…</div>}

        {!isLoading && rows.map((t) => {
          const isCompleting = completingId === t.id;
          return (
            <div key={t.id} className="followup-row" style={isCompleting ? { flexWrap: 'wrap' } : undefined}>
              <span className="avatar" style={t.done ? { background: 'var(--green-bg)', color: 'var(--green)' } : undefined}>
                {t.done ? <Icon name="check" size={16} /> : 'N'}
              </span>
              <div className="followup-row-info">
                <b style={{ cursor: 'pointer', color: 'var(--blue-deep)' }}
                  onClick={() => navigate(`/newcomers/${t.newcomer}`)}>{t.text}</b>
                <div className="muted" style={{ fontSize: '.8rem' }}>
                  Due {t.due_date}
                </div>
                {t.done && <CompletedFollowUpLog log={t} />}
              </div>
              <div className="followup-row-actions">
                <Badge color={urgency(t)}>{t.done ? 'Done' : `Due ${t.due_date}`}</Badge>
                <button className="btn sm outline" onClick={() => setCompletingId(isCompleting ? null : t.id)}>
                  {t.done ? 'Edit' : 'Mark done'}
                </button>
                <button className="icon-btn" title="Delete this task" onClick={() => handleDelete(t.id)}>
                  <Icon name="trash" size={14} />
                </button>
              </div>
              {isCompleting && (
                <div style={{ flexBasis: '100%' }}>
                  <FollowUpCompletionForm
                    idPrefix={`ncfu-${t.id}`}
                    existing={t.done ? t : null}
                    saving={complete.isPending}
                    onCancel={() => setCompletingId(null)}
                    onSave={async (payload) => {
                      await complete.mutateAsync({ id: t.id, payload });
                      setCompletingId(null);
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}

        {!isLoading && rows.length === 0 && (
          <div className="empty">
            {status === 'completed'
              ? 'No completed follow-ups yet.'
              : 'No open follow-ups. Everyone has been reached.'}
          </div>
        )}
      </div>
    </>
  );
}
