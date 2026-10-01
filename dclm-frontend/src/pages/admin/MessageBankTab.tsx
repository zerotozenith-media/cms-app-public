import { useMemo, useState } from 'react';
import { useBank, useFollowUpAction, type BankRow } from '../../api/journeys';
import { HelpMark } from '../../components/ui/HelpMark';
import { Skeleton } from '../../components/ui/Skeleton';

/**
 * The shared follow-up message bank (F19, F20). Everyone following people
 * up chooses from it. Only administrators covering every location change
 * it, as with other church-wide settings. A message used by a plan can be
 * reworded but not switched off, so no plan day is left empty.
 */
const GROUPS: [string, string][] = [['online', 'Online contacts'], ['newcomers', 'Newcomers'], ['converts', 'New converts'], ['any', 'Any journey']];
const LABEL = Object.fromEntries(GROUPS);

export function MessageBankTab() {
  const { data, isLoading, isError } = useBank();
  const [group, setGroup] = useState('newcomers');
  const [theme, setTheme] = useState('');
  const [editing, setEditing] = useState<BankRow | 'new' | null>(null);
  const rows = data?.results ?? [];
  const themes = useMemo(() => [...new Set(rows.filter((r) => r.journey === group).map((r) => r.theme))], [rows, group]);
  const current = themes.includes(theme) ? theme : themes[0] ?? '';
  if (isLoading) return <Skeleton shape="list" />;
  if (isError || !data) return <div className="card empty">The message bank could not be loaded.</div>;
  const list = rows.filter((r) => r.journey === group && r.theme === current);
  return (
    <div className="card section-gap">
      <div className="toolbar" style={{ marginBottom: 4 }}>
        <h3 style={{ flex: 1, margin: 0 }}>Message bank</h3>
        {data.can_edit && <button className="btn sm" onClick={() => setEditing('new')}>Add message</button>}
      </div>
      <p className="muted" style={{ marginTop: 0, fontSize: '.86rem' }}>
        Shared by everyone who follows people up. {data.can_edit ? 'Changes apply to everyone at once.' : 'Only administrators covering every location can change it.'} <HelpMark topic="fuEditor" />
      </p>
      <div className="fu-chips">{GROUPS.map(([k, l]) => <button key={k} className={group === k ? 'on' : ''} onClick={() => { setGroup(k); setTheme(''); }}>{l}</button>)}</div>
      <div className="fu-chips">{themes.map((t) => (
        <button key={t} className={current === t ? 'on' : ''} onClick={() => setTheme(t)}>{t} <span className="fu-count">{rows.filter((r) => r.journey === group && r.theme === t).length}</span></button>
      ))}</div>
      {list.map((r) => (
        <div className={`person-row mb-row${r.active ? '' : ' off'}`} key={r.id}>
          <span>
            {r.verse && <><i>"{r.verse}"</i> <b>{r.reference}</b><br /></>}
            {r.body}
            <br /><span className="muted" style={{ fontSize: '.78rem' }}>
              Message {r.number}{r.plan_days.length ? `. Plan: ${r.plan_days.map((d) => `${LABEL[d.journey]} day ${d.day}`).join(', ')}` : ''}{r.active ? '' : '. Switched off'}
            </span>
          </span>
          {data.can_edit && <button className="btn sm ghost" onClick={() => setEditing(r)}>Edit</button>}
        </div>
      ))}
      {editing && <BankEditor row={editing === 'new' ? null : editing} group={group} theme={current} onClose={() => setEditing(null)} />}
    </div>
  );
}

function BankEditor({ row, group, theme, onClose }: { row: BankRow | null; group: string; theme: string; onClose: () => void }) {
  const act = useFollowUpAction();
  const [verse, setVerse] = useState(row?.verse ?? '');
  const [reference, setReference] = useState(row?.reference ?? '');
  const [body, setBody] = useState(row?.body ?? '');
  const [newTheme, setNewTheme] = useState(theme);
  const [err, setErr] = useState('');
  const save = (extra: object = {}) => {
    setErr('');
    const req = row ? { url: `/followup/bank/${row.id}/`, method: 'patch' as const, body: { verse, reference, body, ...extra } }
      : { url: '/followup/bank/', body: { journey: group, theme: newTheme, verse, reference, body } };
    act.mutate(req, { onSuccess: onClose, onError: (e: any) => setErr(e?.response?.data?.detail || 'That could not be saved.') });
  };
  return (
    <div className="fu-modal" role="dialog" aria-modal="true" aria-label={row ? 'Edit message' : 'Add message'} onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="fu-box">
        <h3 style={{ marginTop: 0 }}>{row ? `Edit ${row.theme} message ${row.number}` : `Add a ${LABEL[group]} message`}</h3>
        <div className="fu-tips">Keep it to one or two sentences, end with one easy question, and offer only one next step. Quote any verse exactly from the King James Version.</div>
        {!row && <div className="field"><label htmlFor="mb-theme">Theme</label><input id="mb-theme" value={newTheme} onChange={(e) => setNewTheme(e.target.value)} /></div>}
        <div className="field"><label htmlFor="mb-verse">Verse (optional)</label><textarea id="mb-verse" rows={2} value={verse} onChange={(e) => setVerse(e.target.value)} /></div>
        <div className="field"><label htmlFor="mb-ref">Reference</label><input id="mb-ref" value={reference} onChange={(e) => setReference(e.target.value)} placeholder="For example John 3:16" /></div>
        <div className="field"><label htmlFor="mb-body">Message</label><textarea id="mb-body" rows={3} value={body} onChange={(e) => setBody(e.target.value)} /></div>
        {err && <p className="form-error" role="alert">{err}</p>}
        <div className="fu-acts">
          <button className="btn sm" onClick={() => save()} disabled={act.isPending}>Save changes</button>
          {row && (row.active
            ? <button className="btn sm ghost" onClick={() => save({ active: false })} disabled={act.isPending}>Switch off</button>
            : <button className="btn sm ghost" onClick={() => save({ active: true })} disabled={act.isPending}>Switch on</button>)}
          <button className="btn sm ghost" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
