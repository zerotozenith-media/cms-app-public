import { useState } from 'react';
import type { Newcomer, NewcomerStage } from '../../types/newcomers';
import { Badge } from '../ui/Badge';

const STAGES: [NewcomerStage, string][] = [
  ['new', 'New'], ['contacted', 'Contacted'], ['visiting', 'Visiting'], ['integrated', 'Integrated'],
];

interface KanbanBoardProps {
  newcomers: Newcomer[];
  onCardClick: (id: number) => void;
  onDropToStage: (id: number, stage: NewcomerStage) => void;
}

function urgencyBadgeColor(urgency: string): 'green' | 'amber' | 'red' {
  if (urgency === 'red') return 'red';
  if (urgency === 'amber') return 'amber';
  return 'green';
}

export function KanbanBoard({ newcomers, onCardClick, onDropToStage }: KanbanBoardProps) {
  const [dragOverStage, setDragOverStage] = useState<NewcomerStage | null>(null);

  return (
    <div className="kanban">
      {STAGES.map(([key, label]) => {
        const cards = newcomers.filter((n) => n.stage === key);
        return (
          <div
            key={key}
            className={`kcol${dragOverStage === key ? ' dragover' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragOverStage(key); }}
            onDragLeave={() => setDragOverStage(null)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOverStage(null);
              const id = Number(e.dataTransfer.getData('text/plain'));
              if (id) onDropToStage(id, key);
            }}
          >
            <h4>{label} <Badge color="gray">{cards.length}</Badge></h4>
            {cards.map((n) => {
              const openTasksExist = n.open_tasks_count > 0;
              return (
                <div
                  key={n.id}
                  className="kcard"
                  draggable
                  onDragStart={(e) => e.dataTransfer.setData('text/plain', String(n.id))}
                  onClick={() => onCardClick(n.id)}
                >
                  <b>{n.name}</b>
                  <small>{n.source_name}</small>
                  <div className="kcard-meta">
                    <span
                      className={`kavatar${!n.assigned_to_name ? ' unassigned' : ''}`}
                      title={n.assigned_to_name || 'Unassigned'}
                    >
                      {n.assigned_to_name ? n.assigned_to_name.charAt(0) : '?'}
                    </span>
                    {key === 'integrated' ? (
                      <Badge color="green">Integrated</Badge>
                    ) : (
                      <Badge color={urgencyBadgeColor(n.urgency)}>{n.days_in_stage}d in stage</Badge>
                    )}
                  </div>
                  {key !== 'integrated' && (
                    <div className={`ktask${!openTasksExist ? ' overdue' : ''}`}>
                      {openTasksExist ? `${n.open_tasks_count} open task${n.open_tasks_count > 1 ? 's' : ''}` : 'No follow-up task set'}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
