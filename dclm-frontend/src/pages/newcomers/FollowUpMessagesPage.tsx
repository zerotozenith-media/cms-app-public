import { forwardRef, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { useBank, useFollowUpAction, useSaved, useToday, type BankRow, type TodayEntry } from '../../api/journeys';
import { HelpMark } from '../../components/ui/HelpMark';
import { Skeleton } from '../../components/ui/Skeleton';
import { blankHTML, cleanHTML, escapeHTML, messageHTML, toWhatsApp, waLink } from '../../lib/whatsapp';

/**
 * Today's messages (F19, F20). Everyone due a follow-up message today, for
 * the person signed in. Messages go from their own WhatsApp: the app opens
 * WhatsApp with the message ready, then records what was sent once they
 * confirm, because it cannot see WhatsApp itself.
 */
const JOURNEY_ORDER = ['online', 'newcomers', 'converts'] as const;
const LABEL: Record<string, string> = { online: 'Online contacts', newcomers: 'Newcomers', converts: 'New converts', any: 'Any journey' };
const OPENERS = ['Thank you for sharing that.', "I'm praying for you.", "That's wonderful news!", "I'm sorry to hear that.", "Let's talk soon."];


/**
 * A box to type a message in. Its starting text is set once, then left to
 * the person typing: redrawing it from props wiped what they had typed.
 */
const Editable = forwardRef<HTMLDivElement, { start: string; onInput?: () => void }>(({ start, onInput }, ref) => {
  const inner = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (inner.current) inner.current.innerHTML = start;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="fu-editor" contentEditable suppressContentEditableWarning onInput={onInput}
      ref={(el) => { (inner as any).current = el; if (typeof ref === 'function') ref(el); else if (ref) (ref as any).current = el; }} />
  );
});

export function NewcomerTabs({ active }: { active: string }) {
  const navigate = useNavigate();
  const tabs: [string, string][] = [['Pipeline', '/newcomers'], ['Follow-up', '/newcomers/follow-up'], ['Messages', '/newcomers/messages'], ['QR Registration', '/newcomers/qr'], ['Manual Entry', '/newcomers/manual']];
  return (
    <div className="toolbar"><div className="tabs">
      {tabs.map(([l, to]) => <button key={to} className={`tab${l === active ? ' active' : ''}`} onClick={() => navigate(to)}>{l}</button>)}
    </div></div>
  );
}

export function FollowUpMessagesPage() {
  const { data, isLoading, isError } = useToday();
  const [filter, setFilter] = useState<string>('all');
  const { hasPermission } = useAuth();
  const canStart = hasPermission('newcomers', 'edit');
  const [starting, setStarting] = useState(false);
  const rows = data?.results ?? [];
  const count = (k: string) => rows.filter((r) => !r.done && (k === 'all' || r.journey === k)).length;
  const shown = rows.filter((r) => filter === 'all' || r.journey === filter);
  return (
    <>
      <NewcomerTabs active="Messages" />
      <div className="fu-headrow">
        <h2 className="section-gap" style={{ marginBottom: 2 }}>Today's messages</h2>
        {canStart && <button className="btn sm outline" onClick={() => setStarting(!starting)} aria-expanded={starting}>Start messages</button>}
      </div>
      <p className="muted" style={{ marginTop: 0 }}>
        {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' })}. Sent from your own WhatsApp.
      </p>
      {starting && <StartPanel onClose={() => setStarting(false)} />}
      <div className="fu-chips" role="group" aria-label="Show a journey">
        {(['all', ...JOURNEY_ORDER] as string[]).map((k) => (
          <button key={k} className={filter === k ? 'on' : ''} onClick={() => setFilter(k)}>
            {k === 'all' ? 'All' : LABEL[k]} <span className="fu-count">{count(k)}</span>
          </button>
        ))}
        <HelpMark topic="fuCounts" />
      </div>
      {isLoading ? <Skeleton shape="list" /> : isError ? (
        <div className="card empty">Today's messages could not be loaded. Check your connection and try again.</div>
      ) : shown.length === 0 ? (
        <div className="card empty">No messages due today. New people appear here on their planned days.</div>
      ) : shown.map((e) => <MessageCard key={e.enrolment} entry={e} />)}
    </>
  );
}

function MessageCard({ entry }: { entry: TodayEntry }) {
  const { user } = useAuth();
  const sender = user?.name || 'Your shepherd';
  const vars = { nextService: entry.next_service, sender };
  const planned = entry.template ? messageHTML(entry.template, entry.person.first, vars) : '';
  const [html, setHtml] = useState(planned);
  const [theme, setTheme] = useState(entry.template?.theme ?? '');
  const [templateId, setTemplateId] = useState<number | null>(entry.template?.id ?? null);
  const [kind, setKind] = useState<'planned' | 'own'>('planned');
  const [replied, setReplied] = useState(false);
  const [panel, setPanel] = useState(false);
  const [editing, setEditing] = useState<null | 'edit' | 'own'>(null);
  const [confirm, setConfirm] = useState<null | 'planned' | 'reply'>(null);
  // The text is kept when WhatsApp opens: the reply box is gone by the time
  // they confirm, and the record must be exactly what was sent.
  const [pending, setPending] = useState('');
  const [err, setErr] = useState('');
  const replyRef = useRef<HTMLDivElement>(null);
  const act = useFollowUpAction();
  const url = `/followup/enrolments/${entry.enrolment}/record/`;

  const record = (k: string, text = '') => {
    setErr('');
    act.mutate({ url, body: { kind: k, text, template: k === 'planned' ? templateId : null } },
      { onError: (e: any) => setErr(e?.response?.data?.detail || 'That could not be recorded. Try again.') });
  };
  const openWhatsApp = (text: string, then: 'planned' | 'reply') => { setPending(text); window.open(waLink(entry.person.phone, text), '_blank', 'noopener'); setConfirm(then); };

  const head = (
    <div className="fu-head">
      <b className="fu-name">{entry.person.name}</b>
      <span className={`fu-chip j-${entry.journey}`}>{entry.journey_label}</span>
      {entry.belonging && <span className="fu-chip ph">Belonging <HelpMark topic="fuBelonging" /></span>}
      <span className="fu-chip">Day {entry.day}</span>
      {theme && !(entry.belonging && theme === 'Belonging') && <span className="fu-chip th">{theme}{entry.template?.final && theme === entry.template.theme ? <HelpMark topic="fuFinal" /> : null}</span>}
    </div>
  );

  if (entry.done) {
    const words = { planned: 'Sent', own: 'Sent', reply: 'Replied personally', skipped: 'Skipped today' }[entry.done.kind];
    return (
      <div className="card fu-card done">{head}
        <div className="fu-state">{words}</div>
        {entry.done.text && <div className="fu-bubble fu-plain">{entry.done.text}</div>}
      </div>
    );
  }

  return (
    <div className="card fu-card">
      {head}
      {confirm ? (
        <div className="fu-confirm" role="status">
          <span>Did you send it on WhatsApp?</span>
          <button className="btn sm" onClick={() => { record(confirm === 'reply' ? 'reply' : kind, pending); setConfirm(null); }}>Yes, record it</button>
          <button className="btn sm ghost" onClick={() => setConfirm(null)}>Not yet</button>
        </div>
      ) : replied ? (
        <>
          <div className="fu-label">Reply personally to {entry.person.first}</div>
          <div className="fu-openers">{OPENERS.map((o) => (
            <button key={o} onClick={() => { const p = replyRef.current?.querySelectorAll('p')[1]; if (p) p.textContent = `${(p.textContent ?? '').trim()} ${o}`.trim(); }}>{o}</button>
          ))}</div>
          <Editable ref={replyRef} start={blankHTML(entry.person.first, sender)} />
          <p className="muted fu-note">Today's planned message moves to the next day.</p>
          <div className="fu-acts">
            <button className="btn sm fu-wa" onClick={() => openWhatsApp(toWhatsApp(replyRef.current?.innerHTML ?? ''), 'reply')}>Send reply on WhatsApp</button>
            <button className="btn sm ghost" onClick={() => setReplied(false)}>Back to today's message</button>
          </div>
        </>
      ) : (
        <>
          <div className="fu-bubble" dangerouslySetInnerHTML={{ __html: html }} />
          <div className="fu-replyq">
            <span>Have they replied since your last message?</span> <HelpMark topic="fuReplied" />
            <div className="viewtoggle" role="group" aria-label="Have they replied?">
              <button className="on">No</button><button onClick={() => setReplied(true)}>Yes</button>
            </div>
          </div>
          <div className="fu-acts">
            <button className="btn sm fu-wa" onClick={() => openWhatsApp(toWhatsApp(html), 'planned')}>Send on WhatsApp</button>
            <button className="btn sm outline" onClick={() => setPanel(!panel)}>Use another message</button><HelpMark topic="fuSwap" />
            <button className="btn sm outline" onClick={() => setEditing('edit')}>Edit</button>
            <button className="btn sm ghost" onClick={() => record('skipped')}>Skip today</button><HelpMark topic="fuSkip" />
          </div>
          {panel && <SwapPanel entry={entry} vars={vars} onPick={(h, t, id, k) => { setHtml(h); setTheme(t); setTemplateId(id); setKind(k); setPanel(false); }} onOwn={() => { setPanel(false); setEditing('own'); }} />}
        </>
      )}
      {err && <p className="form-error" role="alert">{err}</p>}
      {editing && <EditorModal title={`${editing === 'own' ? 'Write my own' : 'Edit message'} for ${entry.person.first}`}
        start={editing === 'own' ? blankHTML(entry.person.first, sender) : html}
        onClose={() => setEditing(null)} onUse={(h) => { setHtml(h); if (editing === 'own') { setTheme('My own'); setKind('own'); setTemplateId(null); } setEditing(null); }} />}
    </div>
  );
}

export function SwapPanel({ entry, vars, onPick, onOwn }: {
  entry: { journey: string; person: { first: string } }; vars: { nextService: string; sender: string };
  onPick: (html: string, theme: string, id: number | null, kind: 'planned' | 'own') => void; onOwn: () => void;
}) {
  const { data: bank } = useBank();
  const { data: saved } = useSaved();
  const groups = useMemo(() => {
    const out: { key: string; label: string; rows: BankRow[] }[] = [];
    const rows = (bank?.results ?? []).filter((r) => r.active && (r.journey === entry.journey || r.journey === 'any'));
    for (const r of rows) {
      let g = out.find((x) => x.key === r.theme);
      if (!g) { g = { key: r.theme, label: r.theme, rows: [] }; out.push(g); }
      g.rows.push(r);
    }
    return out;
  }, [bank, entry.journey]);
  const [tab, setTab] = useState<string>('');
  const current = tab || groups[0]?.key || '';
  return (
    <div className="fu-panel">
      <div className="fu-chips">
        {groups.map((g) => <button key={g.key} className={current === g.key ? 'on' : ''} onClick={() => setTab(g.key)}>{g.label}</button>)}
        <button className={current === '__saved' ? 'on' : ''} onClick={() => setTab('__saved')}>My saved messages</button>
        <button onClick={onOwn}>Write my own</button>
      </div>
      {current === '__saved' ? (
        (saved?.results ?? []).length ? saved!.results.map((s) => (
          <button key={s.id} className="fu-opt" onClick={() => onPick(cleanHTML(s.html), 'Saved', null, 'own')} dangerouslySetInnerHTML={{ __html: cleanHTML(s.html) }} />
        )) : <div className="empty">Nothing saved yet. Edit a message and tick Save to My saved messages.</div>
      ) : (groups.find((g) => g.key === current)?.rows ?? []).map((r) => {
        const h = messageHTML(r, entry.person.first, vars);
        return <button key={r.id} className="fu-opt" onClick={() => onPick(h, r.theme, r.id, 'planned')} dangerouslySetInnerHTML={{ __html: h }} />;
      })}
    </div>
  );
}

export function EditorModal({ title, start, onClose, onUse }: { title: string; start: string; onClose: () => void; onUse: (html: string) => void }) {
  const ed = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState(start);
  const [save, setSave] = useState(false);
  const { data: bank } = useBank();
  const act = useFollowUpAction();
  const verses = useMemo(() => {
    const seen = new Map<string, BankRow>();
    (bank?.results ?? []).forEach((r) => { if (r.verse && !seen.has(r.reference)) seen.set(r.reference, r); });
    return [...seen.values()].sort((a, b) => a.reference.localeCompare(b.reference));
  }, [bank]);
  const sync = () => setPreview(ed.current?.innerHTML ?? '');
  const cmd = (c: 'bold' | 'italic') => { document.execCommand(c); sync(); };
  return (
    <div className="fu-modal" role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="fu-box">
        <h3 style={{ marginTop: 0 }}>{title}</h3>
        <div className="fu-tips">Keep it to one or two sentences, end with one easy question, and offer only one next step.</div>
        <div className="fu-acts" style={{ marginTop: 0 }}>
          <button className="btn sm outline" onMouseDown={(e) => { e.preventDefault(); cmd('bold'); }}><b>B</b> Bold</button>
          <button className="btn sm outline" onMouseDown={(e) => { e.preventDefault(); cmd('italic'); }}><i>I</i> Italic</button>
          <select className="selectbox" aria-label="Add a verse" value="" onChange={(e) => {
            // Added after any selected words, never in place of them.
            const v = verses.find((x) => String(x.id) === e.target.value); if (!v) return;
            ed.current?.focus(); window.getSelection()?.collapseToEnd(); document.execCommand('insertHTML', false, `<p><i>"${escapeHTML(v.verse)}"</i> <b>${escapeHTML(v.reference)}</b></p>`); sync();
          }}>
            <option value="">Add a verse</option>
            {verses.map((v) => <option key={v.id} value={v.id}>{v.reference}</option>)}
          </select>
        </div>
        <Editable ref={ed} start={start} onInput={sync} />
        <label className="fu-tick"><input type="checkbox" checked={save} onChange={(e) => setSave(e.target.checked)} /> Save to My saved messages</label>
        <div className="fu-label">How it arrives on WhatsApp</div>
        <div className="fu-chat"><div className="fu-bubble" dangerouslySetInnerHTML={{ __html: preview }} /></div>
        <div className="fu-acts">
          <button className="btn sm" onClick={() => { const h = cleanHTML(ed.current?.innerHTML ?? ''); if (save) act.mutate({ url: '/followup/saved/', body: { html: h } }); onUse(h); }}>Use this message</button>
          <button className="btn sm ghost" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

/** Kay: choose which newcomers start receiving messages. */
export function StartPanel({ onClose, kind = 'newcomers' }: { onClose: () => void; kind?: 'newcomers' | 'contacts' }) {
  const qc = useQueryClient();
  const contacts = kind === 'contacts';
  const { data, isLoading } = useQuery({ queryKey: ['followup-startable', kind],
    queryFn: async () => (await apiClient.get<{ results: { id: number; name: string; stage: string; shepherd: string; has_phone: boolean }[] }>('/followup/start-many/', { params: contacts ? { kind: 'contacts' } : {} })).data });
  const rows = data?.results ?? [];
  const [picked, setPicked] = useState<Set<number> | null>(null);
  const chosen = picked ?? new Set(rows.map((r) => r.id));
  const [err, setErr] = useState('');
  const start = useMutation({
    mutationFn: async () => (await apiClient.post('/followup/start-many/', contacts ? { enquiries: [...chosen] } : { newcomers: [...chosen] })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['followup-today'] }); qc.invalidateQueries({ queryKey: ['followup-startable'] }); qc.invalidateQueries({ queryKey: ['notifications'] }); qc.invalidateQueries({ queryKey: ['enquiry'] }); onClose(); },
    onError: (e: any) => setErr(e?.response?.data?.detail || 'Messages could not be started. Try again.'),
  });
  const toggle = (id: number) => { const s = new Set(chosen); if (s.has(id)) s.delete(id); else s.add(id); setPicked(s); };
  return (
    <div className="card fu-start">
      <h3 style={{ marginBottom: 2 }}>Start messages</h3>
      <p className="muted" style={{ marginTop: 0, fontSize: '.86rem' }}>{contacts
        ? "Online contacts not yet on a journey. Each starts on day 1 today, sent from their follow-up person's WhatsApp."
        : "Newcomers not yet on a journey. Each starts on day 1 today, sent from their shepherd's WhatsApp."}</p>
      {isLoading ? <p className="muted">Loading.</p> : rows.length === 0 ? <p className="muted">{contacts ? 'Every current contact is already on a journey.' : 'Every current newcomer is already on a journey.'}</p> : (
        <>
          <label className="fu-start-row all"><input type="checkbox" checked={chosen.size === rows.length} onChange={(e) => setPicked(e.target.checked ? new Set(rows.map((r) => r.id)) : new Set())} /> Select all ({rows.length})</label>
          {rows.map((r) => (
            <label className="fu-start-row" key={r.id}>
              <input type="checkbox" checked={chosen.has(r.id)} onChange={() => toggle(r.id)} />
              <span><b>{r.name}</b><br /><span className="muted">{r.stage}, {r.shepherd ? `${contacts ? 'follow-up person' : 'shepherd'} ${r.shepherd}` : (contacts ? 'no follow-up person yet' : 'no shepherd yet')}</span></span>
              <span className="muted">{r.has_phone ? 'Phone on file' : 'No phone'}</span>
            </label>
          ))}
          <p className="fu-start-note">{contacts
            ? 'Start only those who are happy to hear from us. Give each a follow-up person first, so their messages reach the right person.'
            : 'They were not asked at registration about keeping in touch. Start only those you know are happy to hear from us.'}</p>
        </>
      )}
      {err && <p className="form-error" role="alert">{err}</p>}
      <div className="fu-acts">
        {rows.length > 0 && <button className="btn sm" disabled={chosen.size === 0 || start.isPending} onClick={() => start.mutate()}>Start messages for {chosen.size}</button>}
        <button className="btn sm ghost" onClick={onClose}>Cancel</button>
      </div>
    </div>
  );
}
