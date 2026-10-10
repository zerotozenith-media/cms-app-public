import { useState } from 'react';
import { Badge } from '../ui/Badge';
import { ENQUIRY_STAGES } from '../../types/enquiries';
import type { Enquiry, EnquiryStage } from '../../types/enquiries';

interface Props {
  /** Off for somebody who cannot change an enquiry. */
  canMove?: boolean;
  enquiries: Enquiry[];
  onCardClick: (id: number) => void;
  onDropToStage: (id: number, stage: EnquiryStage) => void;
  onSelectStage: (enquiry: Enquiry, stage: EnquiryStage) => void;
  /** Kay: when set, each card has a tick box for assigning several at once. */
  selected?: Set<number>;
  onToggle?: (id: number) => void;
}

/** "Gloria Afari" -> "GA", so two people sharing a first letter differ. */
export function initials(name?: string | null) {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase() || '?';
}

/**
 * Mirrors the newcomers KanbanBoard deliberately, down to the markup,
 * so both pipelines behave identically and any CSS fix applies to both.
 *
 * The one addition is the stage dropdown on each card. HTML5 drag and
 * drop does not work on touch screens at all, so without it nobody
 * could move a card along from a phone.
 */
export function EnquiryKanbanBoard({ enquiries, onCardClick, onDropToStage, onSelectStage, canMove = true, selected, onToggle }: Props) {
  const [dragOverStage, setDragOverStage] = useState<EnquiryStage | null>(null);

  return (
    <div className="kanban">
      {ENQUIRY_STAGES.map(({ key, label }) => {
        const cards = enquiries.filter((e) => e.stage === key);
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
            {cards.map((e) => (
              <div
                key={e.id}
                className={`kcard${selected?.has(e.id) ? ' kcard-picked' : ''}`}
                draggable={canMove && !selected}
                onDragStart={(ev) => ev.dataTransfer.setData('text/plain', String(e.id))}
                onClick={() => (selected && onToggle ? onToggle(e.id) : onCardClick(e.id))}
              >
                {selected && onToggle && (
                  <input type="checkbox" className="kcard-tick" checked={selected.has(e.id)} aria-label={`Select ${e.name}`}
                    onClick={(ev) => ev.stopPropagation()} onChange={() => onToggle(e.id)} />
                )}
                <b>{e.name}</b>
                <small>{e.source_name}{e.social_handle ? ` · ${e.social_handle}` : ''}</small>
                <div className="kcard-meta">
                  <span
                    className={`kavatar${!e.assigned_to_name ? ' unassigned' : ''}`}
                    title={e.assigned_to_name || 'Unassigned'}
                  >
                    {initials(e.assigned_to_name)}
                  </span>
                  <Badge color={e.days_in_stage > 7 ? 'amber' : 'gray'}>
                    {e.days_in_stage}d in stage
                  </Badge>
                </div>
                <div className={`ktask${e.open_tasks_count === 0 ? ' overdue' : ''}`}>
                  {e.open_tasks_count > 0
                    ? `${e.open_tasks_count} open follow-up${e.open_tasks_count > 1 ? 's' : ''}`
                    : 'No follow-up task set'}
                </div>
                <label className="sr-only" htmlFor={`stage-${e.id}`}>
                  Move {e.name} to another stage
                </label>
                {canMove && (<select
                  id={`stage-${e.id}`}
                  className="kstage-select"
                  value={e.stage}
                  onClick={(ev) => ev.stopPropagation()}
                  onChange={(ev) => onSelectStage(e, ev.target.value as EnquiryStage)}
                >
                  {ENQUIRY_STAGES.map((s) => (
                    <option key={s.key} value={s.key}>{s.label}</option>
                  ))}
                  <option value="not-pursuing">Not pursuing</option>
                </select>)}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
