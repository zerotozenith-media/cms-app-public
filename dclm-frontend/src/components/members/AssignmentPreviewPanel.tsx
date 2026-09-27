import { useMemo, useState } from 'react';
import { Badge } from '../ui/Badge';
import { Icon } from '../ui/Icon';
import type { AssignmentChange, ShepherdLoad } from '../../types/members';
import { HelpMark } from '../ui/HelpMark';

export interface ReviewedChanges {
  overrides: { kind: string; id: number; to_id: number }[];
  skips: { kind: string; id: number }[];
}

interface Props {
  changes: AssignmentChange[];
  load: ShepherdLoad[];
  reassignEveryone: boolean;
  applying: boolean;
  onApply: (edits: ReviewedChanges) => void;
  onCancel: () => void;
  onSwitchToReassignEveryone: () => void;
}

const SKIP = -1;

/**
 * Nothing is saved until Apply is pressed. Each row can be changed or
 * skipped first, because reviewing a proposal you cannot alter means
 * cancelling the whole batch to correct one line.
 *
 * The server still recomputes from fresh data when Apply is pressed; it
 * takes only the edits from here, and ignores any that name somebody who
 * is not a shepherd.
 */
export function AssignmentPreviewPanel({
  changes, load, reassignEveryone, applying, onApply, onCancel, onSwitchToReassignEveryone,
}: Props) {
  const [chosen, setChosen] = useState<Record<string, number>>({});
  const key = (c: AssignmentChange) => `${c.kind}-${c.id}`;
  const pick = (c: AssignmentChange) => chosen[key(c)] ?? c.to_id;

  // The load each shepherd would carry, recalculated as rows are edited,
  // so the numbers always describe what Apply would actually do.
  const projected = useMemo(() => {
    const out = new Map(load.map((s) => [s.id, s.now]));
    changes.forEach((c) => {
      const to = pick(c);
      if (to !== SKIP) out.set(to, (out.get(to) ?? 0) + 1);
    });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [changes, load, chosen]);

  const skipped = changes.filter((c) => pick(c) === SKIP).length;
  const applying_n = changes.length - skipped;

  function submit() {
    const overrides: ReviewedChanges['overrides'] = [];
    const skips: ReviewedChanges['skips'] = [];
    changes.forEach((c) => {
      const to = pick(c);
      if (to === SKIP) skips.push({ kind: c.kind, id: c.id });
      else if (to !== c.to_id) overrides.push({ kind: c.kind, id: c.id, to_id: to });
    });
    onApply({ overrides, skips });
  }

  return (
    <div className="assign-preview">
      <div className="assign-preview-title">
        <Icon name="alert" size={15} /> Review before applying: {changes.length} change
        {changes.length === 1 ? '' : 's'}
      </div>
      <div className="muted" style={{ fontSize: '.8rem', marginBottom: 10 }}>
        {reassignEveryone
          ? 'Reassigning everyone, including people who already have a shepherd.'
          : 'Only filling people who currently have no shepherd. Existing pairings are left alone.'}
        {' '}Change any row before applying.
      </div>

      {load.length > 0 && (
        <div className="load-strip">
          {load.map((s) => {
            const after = projected.get(s.id) ?? s.now;
            return (
              <div className="load-item" key={s.id}>
                <b>{s.name}</b>
                <span>{s.now} now{after !== s.now ? `, ${after} after` : ''}</span>
              </div>
            );
          })}
        </div>
      )}

      <div style={{ maxHeight: 320, overflowY: 'auto' }}>
        <table className="cardtable">
          <thead>
            <tr><th>Who</th><th>Type</th><th>From</th><th>To</th><th>Why</th></tr>
          </thead>
          <tbody>
            {changes.map((c) => {
              const to = pick(c);
              const edited = to !== c.to_id;
              return (
                <tr key={key(c)} className={to === SKIP ? 'row-skipped' : ''}>
                  <td data-label="Who"><b>{c.name}</b></td>
                  <td data-label="Type">
                    <Badge color={c.kind === 'member' ? 'blue' : 'amber'}>
                      {c.kind === 'member' ? 'Member' : 'Newcomer'}
                    </Badge>
                  </td>
                  <td data-label="From">{c.from_name || <span className="muted">Unassigned</span>}</td>
                  <td data-label="To" className="td-stack">
                    <select className="selectbox assign-to" value={to}
                      aria-label={`Shepherd for ${c.name}`}
                      onChange={(e) => setChosen({ ...chosen, [key(c)]: Number(e.target.value) })}>
                      {load.map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                      <option value={SKIP}>Leave unassigned</option>
                    </select>
                  </td>
                  <td data-label="Why">
                    {to === SKIP
                      ? <span className="muted">Skipped</span>
                      : edited
                        ? (
                          <span className="why-edited">
                            <Badge color="blue">Chosen by you</Badge>
                            <span className="muted">Suggested: {c.to_name}</span>
                          </span>
                        )
                        : <span className="muted">{c.reason}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <button className="btn sm" onClick={submit} disabled={applying || applying_n === 0}>
          Apply {applying_n} change{applying_n === 1 ? '' : 's'}
        </button>
        {skipped > 0 && <span className="muted" style={{ fontSize: '.8rem' }}>{skipped} skipped</span>}
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
