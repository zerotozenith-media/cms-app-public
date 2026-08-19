import { Badge } from '../ui/Badge';
import { Icon } from '../ui/Icon';
import type { AssignmentChange } from '../../types/members';
import { HelpMark } from '../ui/HelpMark';

interface Props {
  changes: AssignmentChange[];
  reassignEveryone: boolean;
  applying: boolean;
  onApply: () => void;
  onCancel: () => void;
  onSwitchToReassignEveryone: () => void;
}

/**
 * Nothing is saved until Apply is pressed. The preview is a separate
 * request that writes nothing, so an admin can see every proposed
 * change, and why, before committing. Auto-assigning dozens of people
 * on one unreviewed click would be hard to undo.
 */
export function AssignmentPreviewPanel({
  changes, reassignEveryone, applying, onApply, onCancel, onSwitchToReassignEveryone,
}: Props) {
  return (
    <div className="assign-preview">
      <div className="assign-preview-title">
        <Icon name="alert" size={15} /> Review before applying: {changes.length} change{changes.length === 1 ? '' : 's'}
      </div>
      <div className="muted" style={{ fontSize: '.8rem', marginBottom: 10 }}>
        {reassignEveryone
          ? 'Reassigning everyone, including people who already have a shepherd.'
          : 'Only filling people who currently have no shepherd. Existing pairings are left alone.'}
      </div>

      <div style={{ maxHeight: 300, overflowY: 'auto' }}>
        <table className="cardtable">
          <thead>
            <tr><th>Who</th><th>Type</th><th>From</th><th>To</th><th>Why</th></tr>
          </thead>
          <tbody>
            {changes.map((c) => (
              <tr key={`${c.kind}-${c.id}`}>
                <td data-label="Who"><b>{c.name}</b></td>
                <td data-label="Type">
                  <Badge color={c.kind === 'member' ? 'blue' : 'amber'}>
                    {c.kind === 'member' ? 'Member' : 'Newcomer'}
                  </Badge>
                </td>
                <td data-label="From">{c.from_name || <span className="muted">Unassigned</span>}</td>
                <td data-label="To"><b>{c.to_name}</b></td>
                <td data-label="Why"><span className="muted">{c.reason}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className="btn sm" onClick={onApply} disabled={applying}>
          Apply {changes.length} change{changes.length === 1 ? '' : 's'}
        </button>
        <button className="btn sm ghost" onClick={onCancel} disabled={applying}>Cancel</button>
        {!reassignEveryone && (
          <button className="btn sm outline" onClick={onSwitchToReassignEveryone} disabled={applying}>
            Reassign everyone instead
          </button>
        )}
        {!reassignEveryone && <HelpMark topic="reassignEveryone" />}
      </div>
    </div>
  );
}
