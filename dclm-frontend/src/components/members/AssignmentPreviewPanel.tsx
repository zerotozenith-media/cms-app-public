import { useMemo, useState } from 'react';
import { Badge } from '../ui/Badge';
import { Icon } from '../ui/Icon';
import type { AssignmentChange, ShepherdLoad } from '../../types/members';
import { HelpMark } from '../ui/HelpMark';
import { GenderTag } from '../ui/GenderTag';
import { canPair } from '../../lib/gender';

export interface ReviewedChanges {
  overrides: { kind: string; id: number; to_id: number }[];
  skips: { kind: string; id: number }[];
}

interface Props {
  /** Shepherds with no gender set, whom auto-assign gives nobody. */
  notice?: string;
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
  notice, changes, load, reassignEveryone, applying, onApply, onCancel, onSwitchToReassignEveryone,
}: Props) {
  const [chosen, setChosen] = useState<Record<string, number>>({});
  const key = (c: AssignmentChange) => `${c.kind}-${c.id}`;
  // A row with no suitable shepherd (to_id null) starts as Leave unassigned.
  const pick = (c: AssignmentChange): number => chosen[key(c)] ?? c.to_id ?? SKIP;

  // The load each shepherd would carry, recalculated as rows are edited,
  // so the numbers always describe what Apply would actually do.
  const projected = useMemo(() => {
    const out = new Map(load.map((s) => [s.id, s.now]));
    changes.forEach((c) => {
      const to = pick(c);
      if (to !== SKIP) {
        out.set(to, (out.get(to) ?? 0) + 1);
        // Someone moving to a new shepherd leaves their old one.
        if (c.from_id && out.has(c.from_id)) out.set(c.from_id, (out.get(c.from_id) ?? 0) - 1);
      }
    });
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [changes, load, chosen]);

  const skipped = changes.filter((c) => pick(c) === SKIP).length;
  // Shepherds who break a rule, being replaced rather than gaps filled.
  const corrections = changes.filter((c) => c.correction).length;
  const onlyCorrections = corrections > 0 && corrections === changes.length && !reassignEveryone;
  const applying_n = changes.length - skipped;

  function submit() {
    const overrides: ReviewedChanges['overrides'] = [];
    const skips: ReviewedChanges['skips'] = [];
    changes.forEach((c) => {
      const to = pick(c);
      if (to === SKIP) skips.push({ kind: c.kind, id: c.id });
      else if (to !== c.to_id) overrides.push({ kind: c.kind, id: c.id, to_id: to });
      // A row with nobody suitable that is left alone is simply not applied.
    });
    onApply({ overrides, skips });
  }

  return (
    <div className="assign-preview">
      <div className="assign-preview-title">
        <Icon name="alert" size={15} /> Review before applying: {changes.length}{' '}
        {onlyCorrections ? `correction${changes.length === 1 ? '' : 's'}` : `change${changes.length === 1 ? '' : 's'}`}
      </div>
      <div className="muted" style={{ fontSize: '.8rem', marginBottom: 10 }}>
        {onlyCorrections
          ? `Nobody is waiting for a shepherd. ${corrections === 1 ? 'This one breaks' : `These ${corrections} break`} the rules, so ${corrections === 1 ? 'it is' : 'each is'} given a new shepherd: men go to men, women to women, and nobody shepherds themselves. Change any row before applying.`
          : <>
            {reassignEveryone
              ? 'Reassigning everyone, including people who already have a shepherd.'
              : 'Only filling people who currently have no shepherd. Existing pairings are left alone.'}
            {!reassignEveryone && corrections > 0 && ` The exception is ${corrections === 1 ? 'one shepherd who breaks' : `${corrections} shepherds who break`} the rules, replaced below.`}
            {' '}Men go to men, women to women, and nobody shepherds themselves. A family stays with one shepherd only where the gender matches. Change any row before applying.
          </>}
      </div>
      {notice && <div className="gender-notice" role="status">{notice}</div>}

      {load.length > 0 && (
        <div className="load-strip">
          {load.map((s) => {
            const after = projected.get(s.id) ?? s.now;
            return (
              <div className="load-item" key={s.id}>
                <b>{s.name}</b>
                {s.gender ? <GenderTag gender={s.gender} /> : <span className="gender-tag g-unknown">No gender set</span>}
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
              const edited = to !== (c.to_id ?? SKIP);
              return (
                <tr key={key(c)} className={`${to === SKIP ? 'row-skipped' : ''}${c.warn ? ' row-warn' : ''}`}>
                  <td data-label="Who"><span className="name-tags"><b>{c.name}</b><GenderTag gender={c.gender} /></span></td>
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
                      {load.filter((s) => (canPair(c.gender, s.gender) || s.id === c.to_id) && !(c.never ?? []).includes(s.id)).map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                      <option value={SKIP}>{c.correction ? 'Leave as it is' : 'Leave unassigned'}</option>
                    </select>
                  </td>
                  <td data-label="Why">
                    {to === SKIP
                      ? <span className={c.to_id ? 'muted' : 'gender-warn'}>{c.to_id ? 'Skipped' : c.reason}</span>
                      : edited
                        ? (
                          <span className="why-edited">
                            <Badge color="blue">Chosen by you</Badge>
                            <span className="muted">Suggested: {c.to_name}</span>
                          </span>
                        )
                        : <span className={c.warn ? 'gender-warn' : 'muted'}>{c.reason}</span>}
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
