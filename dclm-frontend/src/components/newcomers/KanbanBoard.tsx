import { useState } from 'react';
import type { Newcomer, NewcomerStage } from '../../types/newcomers';
import { Badge } from '../ui/Badge';

const STAGES: [NewcomerStage, string][] = [
  ['new', 'New'], ['contacted', 'Contacted'], ['attending', 'Attending'], ['member', 'Member'],
];

interface KanbanBoardProps {
  newcomers: Newcomer[];
  onCardClick: (id: number) => void;
  onDropToStage: (id: number, stage: NewcomerStage) => void;
  /** Off for somebody who cannot change a newcomer: no dragging, no stage
   *  dropdown, so nothing is offered that the server would refuse. */
  canMove?: boolean;
  /** Where "earlier members" leads. */
  onOpenMembers?: () => void;
}

/** How long a new member stays on the board. Long enough for whoever
 *  walked them through to see they have settled; short enough that the
 *  column stops growing. */
const RECENT_MEMBER_DAYS = 30;

function urgencyBadgeColor(urgency: string): 'green' | 'amber' | 'red' {
  if (urgency === 'red') return 'red';
  if (urgency === 'amber') return 'amber';
  return 'green';
}

export function KanbanBoard({ newcomers, onCardClick, onDropToStage, onOpenMembers, canMove = true }: KanbanBoardProps) {
  const [dragOverStage, setDragOverStage] = useState<NewcomerStage | null>(null);

  return (
    <div className="kanban">
      {STAGES.map(([key, label]) => {
        let cards = newcomers.filter((n) => n.stage === key);
        let earlier = 0;
        if (key === 'member') {
          // A member is no longer being worked on, so a column of every
          // member the church ever had would bury the ones who just joined.
          const recent = cards.filter((n) => n.days_in_stage <= RECENT_MEMBER_DAYS);
          earlier = cards.length - recent.length;
          cards = recent;
        } else {
          // Longest waiting first, so anybody stuck rises rather than sinks.
          cards = [...cards].sort((a, b) => b.days_in_stage - a.days_in_stage);
        }
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
            <h4>{label} <Badge color="gray">{key === 'member' ? `${cards.length} recent` : cards.length}</Badge></h4>
            {cards.map((n) => {
              const openTasksExist = n.open_tasks_count > 0;
              return (
                <div
                  key={n.id}
                  className="kcard"
                  draggable={canMove}
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
                    {key === 'member' ? (
                      <Badge color="green">Joined {n.days_in_stage}d ago</Badge>
                    ) : (
                      <Badge color={urgencyBadgeColor(n.urgency)}>{n.days_in_stage}d in stage</Badge>
                    )}
                  </div>
                  {key !== 'member' && (
                    <div className={`ktask${!openTasksExist ? ' overdue' : ''}`}>
                      {openTasksExist ? `${n.open_tasks_count} open task${n.open_tasks_count > 1 ? 's' : ''}` : 'No follow-up task set'}
                    </div>
                  )}
                  {canMove && key !== 'member' && (
                    <select
                      className="kstage-select"
                      value={n.stage}
                      aria-label={`Move ${n.name} to another stage`}
                      onClick={(ev) => ev.stopPropagation()}
                      onChange={(ev) => onDropToStage(n.id, ev.target.value as NewcomerStage)}
                    >
                      {STAGES.filter(([k]) => k !== 'member').map(([k, l]) => (
                        <option key={k} value={k}>{l}</option>
                      ))}
                      <option value="not-interested">Not interested</option>
                    </select>
                  )}
                </div>
              );
            })}
            {key === 'member' && earlier > 0 && (
              <div className="kcol-foot">
                <p>{earlier} earlier member{earlier === 1 ? '' : 's'}</p>
                {onOpenMembers && <a onClick={onOpenMembers}>Open the member list</a>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
