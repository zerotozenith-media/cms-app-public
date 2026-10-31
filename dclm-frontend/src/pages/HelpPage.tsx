import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { HELP_SECTIONS, HELP_CONTENT, slug } from '../help/content';
import type { HelpEntry } from '../help/content';
import { downloadManual, openManual, useHelpContacts, useHelpImage } from '../api/help';
import type { HelpMsg } from '../api/help';

type Entry = HelpEntry & { from?: string };

function ManualLink({ page }: { page: number }) {
  // The message shows beside the link, where the person is looking.
  const [msg, setMsg] = useState<HelpMsg>(null);
  return (
    <>
      <button type="button" className="help-manual" onClick={async () => setMsg(await openManual(page))}
        title="Opens the user manual at this page, for the full detail">
        Full details: manual, page {page} <span aria-hidden="true">›</span>
      </button>
      {msg && <div className={msg.error ? 'form-error' : 'help-ok'} role={msg.error ? 'alert' : 'status'} style={{ marginTop: 8 }}>{msg.text}</div>}
    </>
  );
}

function HelpPicture({ name, alt }: { name: string; alt: string }) {
  const { data, isError } = useHelpImage(name);
  const [big, setBig] = useState(false);
  if (isError) return null;
  if (!data) return <div className="help-img loading" aria-hidden="true" />;
  return (
    <>
      <button type="button" className="help-img" onClick={() => setBig(true)} aria-label={`Enlarge the picture: ${alt}`}>
        <img src={data} alt={alt} />
        <span className="help-img-tap" aria-hidden="true">Tap to enlarge</span>
      </button>
      {big && (
        <div className="help-img-big" role="dialog" aria-label={alt} onClick={() => setBig(false)}>
          <img src={data} alt={alt} />
          <button type="button" className="btn" onClick={() => setBig(false)}>Close</button>
        </div>
      )}
    </>
  );
}

function EntryBlock({ it, onJump }: { it: Entry; onJump: (key: string, h?: string) => void }) {
  return (
    <div className="help-entry" id={`h-${slug(it.h)}`}>
      <div className="help-entry-h">
        {it.h}
        {it.from && <span className="badge gray" style={{ fontWeight: 700 }}>{it.from}</span>}
      </div>
      {it.roles && (
        <div className="help-roles">
          {it.roles.map((r) => <span key={r} className="help-role">{r}</span>)}
        </div>
      )}
      {it.say && <div className="help-say"><span className="help-say-l">The app says</span>{it.say}</div>}
      {it.why && <div className="help-entry-p"><b>Why:</b> {it.why}</div>}
      {it.fix && <div className="help-fix"><b>What to do:</b> {it.fix}</div>}
      {it.p && <div className="help-entry-p">{it.p}</div>}
      {it.steps && (
        <ol className="help-steps">
          {it.steps.map((s, i) => <li key={i}>{s}</li>)}
        </ol>
      )}
      {it.note && <div className="help-note">{it.note}</div>}
      {it.img && <HelpPicture name={it.img} alt={it.h} />}
      {it.links && (
        <div className="help-links">
          {it.links.map((l) => (
            <button key={l.to + l.t} className="help-link" onClick={() => onJump(l.to)}>
              {l.t} <span style={{ opacity: 0.6 }}>&rsaquo;</span>
            </button>
          ))}
        </div>
      )}
      {it.manual && <ManualLink page={it.manual} />}
    </div>
  );
}

function Contacts() {
  const { data, isLoading, isError } = useHelpContacts();
  if (isLoading) return <div className="muted">Finding who to ask…</div>;
  if (isError || !data) return <div className="muted">Who to ask could not be loaded. Ask your shepherd or an administrator.</div>;
  const row = (c: { name: string; email: string; covers: string }) => (
    <li key={c.email + c.name}><b>{c.name}</b> <span className="muted">({c.covers})</span>{c.email && <div><a href={`mailto:${c.email}`}>{c.email}</a></div>}</li>
  );
  return (
    <div className="help-entry">
      <div className="help-entry-h">Who to ask</div>
      <div className="help-entry-p">For follow-up questions, ask a Follow-up Coordinator. For your account, role or anything else, ask an administrator.</div>
      <div className="help-contacts">
        <div className="help-contacts-h">Follow-up Coordinators</div>
        {data.coordinators.length ? <ul>{data.coordinators.map(row)}</ul> : <div className="muted">None chosen yet. Ask an administrator.</div>}
        <div className="help-contacts-h">Administrators</div>
        {data.administrators.length ? <ul>{data.administrators.map(row)}</ul> : <div className="muted">None found for your location.</div>}
      </div>
    </div>
  );
}

/**
 * Written by job rather than by menu, because a new usher needs "here
 * is what you do on Friday", not a description of what a screen is.
 * Each guide links to its manual page, and "Why can't I...?" answers every
 * message where the app says no.
 */
export function HelpPage() {
  const [params, setParams] = useSearchParams();
  const section = HELP_SECTIONS.some((s) => s.key === params.get('s')) ? params.get('s')! : 'start';
  const [query, setQuery] = useState(params.get('q') ?? '');
  const [err, setErr] = useState<HelpMsg>(null);
  const target = params.get('h');

  const q = query.trim().toLowerCase();
  let items: Entry[];
  let heading: string;
  const sec = HELP_SECTIONS.find((s) => s.key === section)!;

  if (q) {
    items = [];
    Object.keys(HELP_CONTENT).forEach((k) => {
      HELP_CONTENT[k].forEach((it) => {
        // Search everything shown, including the app's own words, so
        // typing a word from a message finds its answer.
        const hay = [it.h, it.p ?? '', (it.steps ?? []).join(' '), it.note ?? '', it.say ?? '', it.why ?? '', it.fix ?? '', (it.roles ?? []).join(' ')]
          .join(' ').toLowerCase().replace(/[“”"']/g, '');
        if (q.split(/\s+/).every((w) => hay.includes(w.replace(/[“”"']/g, '')))) {
          items.push({ ...it, from: HELP_SECTIONS.find((s) => s.key === k)!.label });
        }
      });
    });
    heading = `${items.length} result${items.length === 1 ? '' : 's'} for "${query}"`;
  } else {
    items = HELP_CONTENT[section] ?? [];
    heading = sec.label;
  }

  const groups = [...new Set(HELP_SECTIONS.map((s) => s.group))];

  function jump(key: string, h?: string) {
    setQuery('');
    const next: Record<string, string> = { s: key };
    if (h) next.h = slug(h);
    setParams(next);
    if (!h) window.scrollTo(0, 0);
  }

  // Arriving from "Help for this page" scrolls to the answer asked for.
  useEffect(() => {
    if (!target || q) return;
    const el = document.getElementById(`h-${target}`);
    if (el) {
      el.scrollIntoView({ block: 'start' });
      el.classList.add('help-flash');
      // Pictures above it may still be loading and push it down, so it is
      // brought back into view as they arrive, unless the person scrolls.
      let moved = false;
      const stop = () => { moved = true; };
      window.addEventListener('wheel', stop, { once: true }); window.addEventListener('touchmove', stop, { once: true });
      const again = [400, 1000, 1800].map((ms) => setTimeout(() => { if (!moved) el.scrollIntoView({ block: 'start' }); }, ms));
      const t = setTimeout(() => el.classList.remove('help-flash'), 2400);
      return () => { clearTimeout(t); again.forEach(clearTimeout); window.removeEventListener('wheel', stop); window.removeEventListener('touchmove', stop); };
    }
  }, [target, section, q]);

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 4 }}>Help &amp; Guide</h3>
        <p className="muted" style={{ marginBottom: 12 }}>
          Step by step, by job. Search for a word from what you are doing, or from any message the app showed you.
        </p>
        <label htmlFor="help-search" className="sr-only">Search the guide</label>
        <input
          id="help-search"
          className="search"
          style={{ width: '100%', maxWidth: 420 }}
          placeholder="Search, for example: reason, check in, away"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="help-top-btns">
          <button type="button" className="btn outline" onClick={async () => setErr(await downloadManual())}
            title="The whole user manual, with pictures of every screen">Download the manual (PDF, about 7 MB)</button>
          <button type="button" className="btn outline" onClick={() => jump('new')}>What's new</button>
          <button type="button" className="btn outline" onClick={() => jump('why')}>Why can't I...?</button>
        </div>
        {err && <div className={err.error ? 'form-error' : 'help-ok'} role={err.error ? 'alert' : 'status'} style={{ marginTop: 10 }}>{err.text}</div>}
      </div>

      <div className="grid help-layout" style={{ gridTemplateColumns: '230px 1fr', gap: 16, alignItems: 'start' }}>
        <div className="card help-nav">
          <label htmlFor="help-section" className="sr-only">Section</label>
          <select
            id="help-section"
            className="selectbox help-nav-select"
            value={section}
            onChange={(e) => jump(e.target.value)}
          >
            {groups.map((g) => (
              <optgroup key={g} label={g}>
                {HELP_SECTIONS.filter((s) => s.group === g).map((s) => (
                  <option key={s.key} value={s.key}>{s.label}</option>
                ))}
              </optgroup>
            ))}
          </select>

          {groups.map((g) => (
            <div key={g}>
              <div className="help-nav-group">{g}</div>
              {HELP_SECTIONS.filter((s) => s.group === g).map((s) => (
                <button
                  key={s.key}
                  className={`help-nav-item${!q && section === s.key ? ' active' : ''}`}
                  onClick={() => jump(s.key)}
                >
                  {s.label}
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="card">
          <h3 style={{ marginBottom: q || !sec.intro ? 14 : 4 }}>{heading}</h3>
          {!q && sec.intro && <p className="muted" style={{ marginBottom: 14 }}>{sec.intro}</p>}
          {items.length
            ? items.map((it, i) => <EntryBlock key={`${it.h}-${i}`} it={it} onJump={jump} />)
            : <div className="empty">Nothing in the guide matches that. Try one word, such as "reason" or "shepherd", or see Still stuck? Ask.</div>}
          {!q && section === 'ask' && <Contacts />}
        </div>
      </div>
    </>
  );
}
