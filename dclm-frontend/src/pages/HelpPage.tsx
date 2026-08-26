import { useState } from 'react';
import { HELP_SECTIONS, HELP_CONTENT } from '../help/content';
import type { HelpEntry } from '../help/content';

type Entry = HelpEntry & { from?: string };

function EntryBlock({ it, onJump }: { it: Entry; onJump: (key: string) => void }) {
  return (
    <div className="help-entry">
      <div className="help-entry-h">
        {it.h}
        {it.from && <span className="badge gray" style={{ fontWeight: 700 }}>{it.from}</span>}
      </div>
      {it.p && <div className="help-entry-p">{it.p}</div>}
      {it.steps && (
        <ol className="help-steps">
          {it.steps.map((s, i) => <li key={i}>{s}</li>)}
        </ol>
      )}
      {it.note && <div className="help-note">{it.note}</div>}
      {it.links && (
        <div className="help-links">
          {it.links.map((l) => (
            <button key={l.to} className="help-link" onClick={() => onJump(l.to)}>
              {l.t} <span style={{ opacity: 0.6 }}>&rsaquo;</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Written by job rather than by menu, because a new usher needs "here
 * is what you do on Friday", not a description of what a screen is.
 * The reference sections are kept for looking things up afterwards.
 */
export function HelpPage() {
  const [section, setSection] = useState('start');
  const [query, setQuery] = useState('');

  const q = query.trim().toLowerCase();
  let items: Entry[];
  let heading: string;

  if (q) {
    items = [];
    Object.keys(HELP_CONTENT).forEach((k) => {
      HELP_CONTENT[k].forEach((it) => {
        // Search the steps and notes too, not just the heading: most of
        // the useful detail lives in the steps.
        const hay = [it.h, it.p ?? '', (it.steps ?? []).join(' '), it.note ?? ''].join(' ').toLowerCase();
        if (hay.includes(q)) {
          items.push({ ...it, from: HELP_SECTIONS.find((s) => s.key === k)!.label });
        }
      });
    });
    heading = `${items.length} result${items.length === 1 ? '' : 's'} for "${query}"`;
  } else {
    items = HELP_CONTENT[section] ?? [];
    heading = HELP_SECTIONS.find((s) => s.key === section)!.label;
  }

  const groups = [...new Set(HELP_SECTIONS.map((s) => s.group))];

  function jump(key: string) {
    setQuery('');
    setSection(key);
    window.scrollTo(0, 0);
  }

  return (
    <>
      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 4 }}>Help &amp; Guide</h3>
        <p className="muted" style={{ marginBottom: 12 }}>
          Step by step, by job. Search below, or pick a topic.
        </p>
        <label htmlFor="help-search" className="sr-only">Search the guide</label>
        <input
          id="help-search"
          className="search"
          style={{ width: '100%', maxWidth: 420 }}
          placeholder="Search the guide..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
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
          <h3 style={{ marginBottom: 14 }}>{heading}</h3>
          {items.length
            ? items.map((it, i) => <EntryBlock key={`${it.h}-${i}`} it={it} onJump={jump} />)
            : <div className="empty">Nothing in the guide matches that. Try a different word.</div>}
        </div>
      </div>
    </>
  );
}
