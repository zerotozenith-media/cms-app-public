import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useMemberFollowUpTasks, useFollowUpStats,
  useCompleteFollowUpTask, useDeleteFollowUpTask,
} from '../../api/followup';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { FollowUpCompletionForm } from '../../components/followup/FollowUpCompletionForm';
import { CompletedFollowUpLog } from '../../components/followup/CompletedFollowUpLog';
import type { MemberFollowUpTask } from '../../types/members';

type StatusFilter = 'open' | 'completed' | 'all';

/** Grey until due, amber once overdue, red after three days. Matches the
 *  urgency language already used on the newcomers pipeline. */
function urgency(task: MemberFollowUpTask): 'green' | 'red' | 'amber' | 'gray' {
  if (task.done) return 'green';
  const days = Math.round(
    (Date.now() - new Date(`${task.due_date}T00:00:00`).getTime()) / 86400000,
  );
  if (days > 3) return 'red';
  if (days > 0) return 'amber';
  return 'gray';
}

export function MemberFollowUpTab() {
  const navigate = useNavigate();
  const [status, setStatus] = useState<StatusFilter>('open');
  const [shepherd, setShepherd] = useState<string>('all');
  const [ordering, setOrdering] = useState('due_date');
  const [completingId, setCompletingId] = useState<number | null>(null);

  const { data: tasks, isLoading } = useMemberFollowUpTasks({
    done: status === 'all' ? undefined : status === 'completed',
    ordering,
  });
  const { data: stats } = useFollowUpStats();
  const complete = useCompleteFollowUpTask();
  const remove = useDeleteFollowUpTask();

  const shepherds = [...new Set((tasks ?? []).map((t) => t.assigned_to_name).filter(Boolean))] as string[];
  const rows = (tasks ?? []).filter((t) => shepherd === 'all' || t.assigned_to_name === shepherd);

  const statItems: StatItem[] = [
    { icon: 'userplus', color: 'blue', label: 'Open follow-ups', value: stats?.open_followups ?? 0 },
    {
      icon: 'alert', color: stats?.overdue ? 'red' : 'gray', label: 'Overdue',
      value: stats?.overdue ?? 0, valueColor: stats?.overdue ? 'var(--red)' : undefined,
    },
    {
      icon: 'user', color: stats?.unassigned ? 'amber' : 'gray', label: 'Unassigned',
      value: stats?.unassigned ?? 0, valueColor: stats?.unassigned ? 'var(--amber)' : undefined,
    },
  ];

  async function handleDelete(id: number) {
    if (!confirm('Delete this follow-up? This cannot be undone.')) return;
    await remove.mutateAsync(id);
  }

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab" onClick={() => navigate('/members')}>Directory</button>
          <button className="tab active">Follow-up</button>
        </div>
      </div>

      <StatRow stats={statItems} columns={3} />

      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>Members needing follow-up</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <label htmlFor="fu-status" className="sr-only">Status</label>
            <select id="fu-status" className="selectbox" value={status}
              onChange={(e) => setStatus(e.target.value as StatusFilter)}>
              <option value="open">Open only</option>
              <option value="completed">Completed only</option>
              <option value="all">All (open + completed)</option>
            </select>

            <label htmlFor="fu-shepherd" className="sr-only">Shepherd</label>
            <select id="fu-shepherd" className="selectbox" value={shepherd}
              onChange={(e) => setShepherd(e.target.value)}>
              <option value="all">All shepherds</option>
              {shepherds.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>

            <label htmlFor="fu-sort" className="sr-only">Sort</label>
            <select id="fu-sort" className="selectbox" value={ordering}
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
                {t.done ? <Icon name="check" size={16} /> : t.member_name.charAt(0)}
              </span>
              <div className="followup-row-info">
                <b style={{ cursor: 'pointer', color: 'var(--blue-deep)' }}
                  onClick={() => navigate(`/members/${t.member}`)}>{t.member_name}</b>
                <div className="muted" style={{ fontSize: '.8rem' }}>
                  Missed {t.missed_meeting_name} on {t.missed_date} · Shepherd: {t.assigned_to_name || 'Unassigned'}
                </div>
                {t.done && <CompletedFollowUpLog log={t} />}
              </div>
              <div className="followup-row-actions">
                <Badge color={urgency(t)}>{t.done ? 'Done' : `Due ${t.due_date}`}</Badge>
                <button className="btn sm outline" onClick={() => setCompletingId(isCompleting ? null : t.id)}>
                  {t.done ? 'Edit' : 'Mark done'}
                </button>
                <button className="icon-btn" title="Delete this follow-up" onClick={() => handleDelete(t.id)}>
                  <Icon name="trash" size={14} />
                </button>
              </div>
              {isCompleting && (
                <div style={{ flexBasis: '100%' }}>
                  <FollowUpCompletionForm
                    idPrefix={`fu-${t.id}`}
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
