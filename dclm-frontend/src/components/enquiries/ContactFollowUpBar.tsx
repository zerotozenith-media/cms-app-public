import { useMemo, useState } from 'react';
import type { Enquiry } from '../../types/enquiries';
import {
  useApplyContactAutoAssign, useBulkAssignContacts, useContactAutoAssignPreview, useFollowUpPeople,
} from '../../api/enquiries';
import { StartPanel } from '../../pages/newcomers/FollowUpMessagesPage';

/**
 * Kay, October 2026: a named follow-up person for every online contact.
 * Filter by person, tick several and assign them, auto-assign evenly, and
 * start messages for contacts. Only contacts still being followed up count.
 */
export type ContactFilter = 'everyone' | 'mine' | 'unassigned' | `person-${number}`;

const ACTIVE = (e: Enquiry) => e.stage !== 'attended' && e.stage !== 'not-pursuing';

export function applyContactFilter(all: Enquiry[], filter: ContactFilter, me?: number) {
  if (filter === 'everyone') return all;
  if (filter === 'mine') return all.filter((e) => e.assigned_to === me);
  if (filter === 'unassigned') return all.filter((e) => !e.assigned_to);
  const id = Number(filter.slice(7));
  return all.filter((e) => e.assigned_to === id);
}

export function ContactFollowUpBar({ all, filter, setFilter, me, canEdit, selecting, setSelecting, selected, setSelected }: {
  all: Enquiry[]; filter: ContactFilter; setFilter: (f: ContactFilter) => void; me?: number; canEdit: boolean;
  selecting: boolean; setSelecting: (v: boolean) => void; selected: Set<number>; setSelected: (s: Set<number>) => void;
}) {
  const { data: people = [] } = useFollowUpPeople();
  const active = all.filter(ACTIVE);
  const mine = active.filter((e) => e.assigned_to === me).length;
  const unassigned = active.filter((e) => !e.assigned_to).length;
  const [panel, setPanel] = useState<null | 'auto' | 'start'>(null);
  const [assignTo, setAssignTo] = useState('');
  const [msg, setMsg] = useState('');
  const bulk = useBulkAssignContacts();

  return (
    <>
      <div className="card section-gap cfu-bar">
        <div className="cfu-left">
          <label htmlFor="cfu-filter" className="cfu-label">Follow-up person</label>
          <select id="cfu-filter" className="selectbox" value={filter} onChange={(e) => setFilter(e.target.value as ContactFilter)}>
            <option value="everyone">Everyone ({active.length})</option>
            <option value="mine">Mine ({mine})</option>
            <option value="unassigned">Unassigned ({unassigned})</option>
            {people.map((p) => <option key={p.id} value={`person-${p.id}`}>{p.name} ({p.contacts})</option>)}
          </select>
          <div className="cfu-quick" role="group" aria-label="Quick filters">
            <button className={`btn sm${filter === 'mine' ? '' : ' outline'}`} aria-pressed={filter === 'mine'} onClick={() => setFilter(filter === 'mine' ? 'everyone' : 'mine')}>Mine ({mine})</button>
            <button className={`btn sm${filter === 'unassigned' ? '' : ' outline'}`} aria-pressed={filter === 'unassigned'} onClick={() => setFilter(filter === 'unassigned' ? 'everyone' : 'unassigned')}>Unassigned ({unassigned})</button>
          </div>
        </div>
        {canEdit && (
          <div className="cfu-actions">
            <button className="btn sm outline" aria-pressed={selecting} onClick={() => { setSelecting(!selecting); setSelected(new Set()); setMsg(''); }}>
              {selecting ? 'Done selecting' : 'Select contacts'}
            </button>
            <button className="btn sm outline" onClick={() => setPanel(panel === 'auto' ? null : 'auto')} aria-expanded={panel === 'auto'}>Auto-assign</button>
            <button className="btn sm" onClick={() => setPanel(panel === 'start' ? null : 'start')} aria-expanded={panel === 'start'}>Start messages</button>
          </div>
        )}
      </div>

      {selecting && (
        <div className="bulk-bar cfu-bulk">
          <span><b>{selected.size}</b> selected</span>
          <label htmlFor="cfu-assign" className="sr-only">Follow-up person</label>
          <select id="cfu-assign" className="selectbox" value={assignTo} onChange={(e) => setAssignTo(e.target.value)}>
            <option value="">Choose follow-up person…</option>
            {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            <option value="none">No follow-up person</option>
          </select>
          <button className="btn sm" disabled={!selected.size || !assignTo || bulk.isPending}
            onClick={() => bulk.mutate({ enquiries: [...selected], assigned_to: assignTo === 'none' ? null : Number(assignTo) }, {
              onSuccess: (r) => { setMsg(`${r.changed} contact${r.changed === 1 ? '' : 's'} updated.`); setSelected(new Set()); },
              onError: (e: any) => setMsg(e?.response?.data?.detail || 'They could not be assigned. Try again.'),
            })}>Assign</button>
          <button className="btn sm ghost" onClick={() => setSelected(new Set())}>Clear</button>
          {msg && <span className="cfu-msg" role="status">{msg}</span>}
        </div>
      )}
      {!people.length && canEdit && (
        <p className="filter-note">Nobody can be given contacts yet. In Admin, tick <b>Can shepherd others</b> on the follow-up people.</p>
      )}
      {panel === 'auto' && <AutoAssignPanel onClose={() => setPanel(null)} />}
      {panel === 'start' && <div className="section-gap"><StartPanel kind="contacts" onClose={() => setPanel(null)} /></div>}
    </>
  );
}

function AutoAssignPanel({ onClose }: { onClose: () => void }) {
  const [everyone, setEveryone] = useState(false);
  const { data, isLoading, isError } = useContactAutoAssignPreview(everyone);
  const { data: people = [] } = useFollowUpPeople();
  const apply = useApplyContactAutoAssign();
  const [edits, setEdits] = useState<Record<number, string>>({});
  const [err, setErr] = useState('');
  const rows = data?.rows ?? [];
  const choice = (r: { enquiry: number; proposed: number }) => edits[r.enquiry] ?? String(r.proposed);
  const after = useMemo(() => {
    const load: Record<number, number> = {};
    for (const p of data?.people ?? []) load[p.id] = everyone ? 0 : p.now;
    for (const r of rows) { const c = choice(r); if (c !== 'none') load[Number(c)] = (load[Number(c)] ?? 0) + 1; }
    return load;
  }, [data, edits, everyone]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="assign-preview section-gap">
      <b className="cfu-title">{everyone ? 'Reassign every contact' : `Auto-assign ${rows.length} unassigned contact${rows.length === 1 ? '' : 's'}`}</b>
      <p className="muted cfu-help">Each contact goes to the follow-up person with the fewest. Change any row, or leave it unassigned. Nothing is saved until you press Apply.</p>
      {isLoading ? <p className="muted">Working it out.</p> : isError ? <p className="form-error">The proposal could not be loaded. Try again.</p> : data?.error ? (
        <p className="form-error" role="alert">{data.error}</p>
      ) : rows.length === 0 ? <p className="muted">Every contact already has a follow-up person.</p> : (
        <>
          <div className="cfu-load">
            {(data?.people ?? []).map((p) => <span key={p.id}><b>{p.name}</b> {everyone ? 0 : p.now} to {after[p.id] ?? 0}</span>)}
          </div>
          <div className="cfu-rows">
            {rows.map((r) => (
              <div className="cfu-row" key={r.enquiry}>
                <span className="cfu-name">{r.name}{r.current && <small className="muted"> now {r.current}</small>}</span>
                <label className="sr-only" htmlFor={`cfu-p-${r.enquiry}`}>Follow-up person for {r.name}</label>
                <select id={`cfu-p-${r.enquiry}`} className="selectbox" value={choice(r)} onChange={(e) => setEdits({ ...edits, [r.enquiry]: e.target.value })}>
                  {people.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  <option value="none">Leave unassigned</option>
                </select>
              </div>
            ))}
          </div>
        </>
      )}
      {err && <p className="form-error" role="alert">{err}</p>}
      <div className="fu-acts">
        {rows.length > 0 && !data?.error && (
          <button className="btn sm" disabled={apply.isPending}
            onClick={() => apply.mutate(rows.map((r) => ({ enquiry: r.enquiry, assigned_to: choice(r) === 'none' ? null : Number(choice(r)) })), {
              onSuccess: onClose, onError: (e: any) => setErr(e?.response?.data?.detail || 'It could not be applied. Try again.'),
            })}>Apply</button>
        )}
        <button className="btn sm ghost" onClick={onClose}>Close</button>
        {!everyone && <button className="btn sm outline" onClick={() => { setEdits({}); setEveryone(true); }}>Reassign everyone instead</button>}
      </div>
    </div>
  );
}
