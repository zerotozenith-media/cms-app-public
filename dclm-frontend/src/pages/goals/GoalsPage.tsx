import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useGoals, useCreateGoal, useUpdateGoalProgress, useDeleteGoal } from '../../api/goals';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import type { Goal, GoalHorizon } from '../../types/goals';

import { useAuth } from '../../context/AuthContext';
const HORIZONS: GoalHorizon[] = ['Short-term', 'Medium-term', 'Long-term', 'Spiritual growth'];

function progressColor(current: number, target: number): 'green' | 'red' | '' {
  if (!target) return '';
  const ratio = current / target;
  if (ratio >= 0.9) return 'green';
  if (ratio < 0.6) return 'red';
  return '';
}

export function GoalsPage() {
  const navigate = useNavigate();
  const { data: goals } = useGoals();
  const createGoal = useCreateGoal();
  // Controls a person cannot use are not shown.
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('goals', 'create');
  const canEdit = hasPermission('goals', 'edit');
  const canDelete = hasPermission('goals', 'delete');
  const deleteGoal = useDeleteGoal();

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [horizon, setHorizon] = useState<GoalHorizon>('Short-term');
  const [target, setTarget] = useState('');
  const [unit, setUnit] = useState('');

  const list = goals ?? [];
  let achieved = 0, behind = 0, onTrack = 0;
  list.forEach((g) => {
    const ratio = g.target ? g.current_value / g.target : 0;
    if (ratio >= 0.9) achieved++;
    else if (ratio < 0.6) behind++;
    else onTrack++;
  });

  const stats: StatItem[] = [
    { icon: 'target', color: 'blue', label: 'Total goals', value: list.length },
    { icon: 'check', color: 'blue', label: 'On track', value: onTrack },
    { icon: 'alert', color: behind ? 'red' : 'gray', label: 'Behind', value: behind, valueColor: behind ? 'var(--red)' : undefined },
    { icon: 'check', color: 'green', label: 'Achieved', value: achieved },
  ];

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    await createGoal.mutateAsync({ name, horizon, target: Number(target), unit });
    setName(''); setTarget(''); setUnit(''); setHorizon('Short-term');
    setShowForm(false);
  }
  async function handleDelete(id: number) {
    if (!confirm('Delete this goal?')) return;
    await deleteGoal.mutateAsync(id);
  }

  return (
    <>
      <StatRow stats={stats} />

      <div className="toolbar">
        <div className="muted" style={{ fontSize: '.85rem', maxWidth: 520 }}>
          Each goal shows how it is tracked: auto-tracked goals are computed live from Attendance, Members, or
          Newcomers data. Manual goals are updated by the team responsible.
        </div>
        {canCreate && (
          <a className="btn sm" onClick={() => setShowForm(!showForm)}>
            <Icon name="plus" size={15} /> Add goal
          </a>
        )}
      </div>

      {showForm && (
        <div className="card form-card editing" style={{ maxWidth: 520, margin: '0 auto 20px' }}>
          <h3>New goal</h3>
          <p className="muted" style={{ fontSize: '.84rem', margin: '-4px 0 12px' }}>
            New goals are manually tracked. Update the progress value on the Goals list as it changes.
          </p>
          <form onSubmit={handleCreate}>
            <div className="field">
              <label htmlFor="goal-name">Goal name</label>
              <input id="goal-name" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="form-row g3">
              <div className="field">
                <label htmlFor="goal-horizon">Horizon</label>
                <select id="goal-horizon" value={horizon} onChange={(e) => setHorizon(e.target.value as GoalHorizon)}>
                  {HORIZONS.map((h) => <option key={h}>{h}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="goal-target">Target</label>
                <input id="goal-target" type="number" value={target} onChange={(e) => setTarget(e.target.value)} required />
              </div>
              <div className="field">
                <label htmlFor="goal-unit">Unit (optional)</label>
                <input id="goal-unit" value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="e.g. % or blank" />
              </div>
            </div>
            <button className="btn sm" type="submit" disabled={createGoal.isPending}>Add goal</button>
            <button className="btn sm ghost" type="button" onClick={() => setShowForm(false)}>Cancel</button>
          </form>
        </div>
      )}

      {HORIZONS.map((h) => {
        const goalsInHorizon = list.filter((g) => g.horizon === h);
        return (
          <div className="card section-gap" key={h}>
            <h3>{h}</h3>
            {goalsInHorizon.length ? goalsInHorizon.map((g) => (
              <GoalRow key={g.id} goal={g} canEdit={canEdit} canDelete={canDelete} onDelete={handleDelete} onNavigate={navigate} />
            )) : <div className="empty">No goals in this category yet.</div>}
          </div>
        );
      })}
    </>
  );
}

function GoalRow({
  goal, canEdit, canDelete, onDelete, onNavigate,
}: {
  goal: Goal;
  canEdit: boolean;
  canDelete: boolean;
  onDelete: (id: number) => void;
  onNavigate: (path: string) => void;
}) {
  // Saves only a real change, and says whether it worked. It used to save
  // on every click away, silently, even when refused.
  const updateProgress = useUpdateGoalProgress();
  const [status, setStatus] = useState<'' | 'saved' | 'failed'>('');
  function saveProgress(el: HTMLInputElement) {
    const value = Number(el.value);
    if (el.value === '' || value === Number(goal.current)) return;
    setStatus('');
    updateProgress.mutate({ id: goal.id, current: value }, {
      onSuccess: () => setStatus('saved'),
      onError: () => { el.value = String(goal.current); setStatus('failed'); },
    });
  }
  const isAuto = goal.tracking === 'auto';
  const displayValue = goal.calculation_error ? null : goal.current_value;
  const pct = goal.target && displayValue !== null ? Math.min(100, Math.round((displayValue / goal.target) * 100)) : 0;

  return (
    <div className="goal-row">
      <div className="goal-row-top">
        <span style={{ fontWeight: 600, flex: 1 }}>
          {goal.name}
          {isAuto ? <Badge color="blue">Auto-tracked</Badge> : <Badge color="gray">Manual</Badge>}
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {isAuto ? (
            <>
              <b style={{ color: 'var(--blue-deep)' }}>{displayValue !== null ? `${displayValue}${goal.unit}` : '–'}</b>
              <span className="muted">/ {goal.target}{goal.unit}</span>
            </>
          ) : (
            <>
              {canEdit ? (
                <input
                  type="number"
                  aria-label={`Current figure for ${goal.name}`}
                  defaultValue={goal.current}
                  className="goal-input"
                  onBlur={(e) => saveProgress(e.currentTarget)}
                  onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur(); }}
                />
              ) : (
                <b style={{ color: 'var(--blue-deep)' }}>{goal.current}{goal.unit}</b>
              )}
              <span className="muted">/ {goal.target}{goal.unit}</span>
            </>
          )}
          {canDelete && (
            <button className="icon-btn" title="Delete goal" onClick={() => onDelete(goal.id)}>
              <Icon name="trash" size={14} />
            </button>
          )}
        </span>
      </div>
      {status === 'saved' && <div className="muted" style={{ fontSize: '.78rem' }}>Saved.</div>}
      {status === 'failed' && <div className="form-error">That figure could not be saved.</div>}
      <div className="bar-track"><div className={`bar-fill ${progressColor(displayValue ?? 0, goal.target)}`} style={{ width: `${pct}%` }} /></div>
      <div className="goal-source">
        {goal.calculation_error ? (
          <span style={{ color: 'var(--red)' }}>{goal.calculation_error}</span>
        ) : (
          goal.source
        )}
        {isAuto && goal.link_route && (
          <a onClick={() => onNavigate(`/${goal.link_route}`)}>View data →</a>
        )}
      </div>
    </div>
  );
}
