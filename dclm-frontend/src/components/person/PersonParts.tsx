import { useState } from 'react';
import type { PersonSummary } from '../../api/person';

const day = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

export function initialsOf(name: string) {
  const p = (name || '').trim().split(/\s+/).filter(Boolean);
  return ((p[0]?.[0] ?? '') + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase() || '?';
}

/** How long since they first came, or joined: "2 yr 3 mo", "4 mo", "12 days". */
export function timeSince(from?: string | null) {
  if (!from) return '–';
  const a = new Date(`${from}T00:00:00`), b = new Date();
  const months = (b.getFullYear() - a.getFullYear()) * 12 + (b.getMonth() - a.getMonth()) - (b.getDate() < a.getDate() ? 1 : 0);
  if (months < 1) return `${Math.max(0, Math.round((b.getTime() - a.getTime()) / 86400000))} days`;
  const y = Math.floor(months / 12), m = months % 12;
  return [y ? `${y} yr` : '', m ? `${m} mo` : ''].filter(Boolean).join(' ');
}

/** The tab bar and its panels. Tabs scroll sideways on a phone. */
export function PersonTabs({ tabs }: { tabs: { key: string; label: string; body: React.ReactNode }[] }) {
  const [active, setActive] = useState(tabs[0]?.key);
  const current = tabs.find((t) => t.key === active) ?? tabs[0];
  return (
    <div className="card person-main">
      <div className="person-tabs" role="tablist">
        {tabs.map((t) => (
          <button key={t.key} role="tab" aria-selected={t.key === current?.key}
            className={t.key === current?.key ? 'on' : ''} onClick={() => setActive(t.key)}>{t.label}</button>
        ))}
      </div>
      <div role="tabpanel">{current?.body}</div>
    </div>
  );
}

export function PersonStats({ p, since }: { p: PersonSummary; since?: string | null }) {
  return (
    <div className="person-stats">
      <div><span>Time with us</span><b>{timeSince(since ?? p.first_came)}</b></div>
      <div><span>Milestones</span><b>{p.milestones.filter((m) => m.date).length}</b></div>
      <div><span>Open follow-ups</span><b>{p.open_follow_ups.length}</b></div>
    </div>
  );
}

export function MilestoneChips({ p }: { p: PersonSummary }) {
  return (
    <div className="ms-chips">
      {p.milestones.map((m) => (
        <span key={m.name} className={`ms-chip${m.date ? ' done' : ''}`}>
          {m.date ? `✓ ${m.name}, ${day(m.date)}` : m.name}
        </span>
      ))}
    </div>
  );
}

const KIND_CLASS: Record<string, string> = { registered: 'big', member: 'big', milestone: 'ms', category: 'big' };

export function JourneyTimeline({ p }: { p: PersonSummary }) {
  if (!p.journey.length) return <div className="empty">Nothing recorded yet.</div>;
  return (
    <ol className="timeline">
      {p.journey.map((e, i) => (
        <li key={i} className={KIND_CLASS[e.kind] ?? ''}>
          <span className="tl-dot" aria-hidden="true" />
          <div className="tl-date">{e.date ? day(e.date) : ''}</div>
          <div className="tl-title">{e.title}</div>
          {(e.detail || e.method || e.by) && (
            <div className="tl-detail">{[e.method, e.detail, e.by ? `by ${e.by}` : ''].filter(Boolean).join(' · ')}</div>
          )}
        </li>
      ))}
    </ol>
  );
}

export function AttendanceList({ p }: { p: PersonSummary }) {
  if (!p.attendance.count) return <div className="empty">No check-ins recorded yet.</div>;
  return (
    <>
      <p className="muted" style={{ marginTop: 0 }}>{p.attendance.count} check-in{p.attendance.count === 1 ? '' : 's'} in all, the latest below.</p>
      {p.attendance.recent.map((a, i) => (
        <div className="person-row" key={i}>
          <span>{a.meeting}</span>
          <span className="muted">{day(a.date)}{a.as === 'newcomer' ? ' · as a newcomer' : ''}</span>
        </div>
      ))}
    </>
  );
}

export function OpenFollowUps({ p, onOpen }: { p: PersonSummary; onOpen: (t: PersonSummary['open_follow_ups'][number]) => void }) {
  if (!p.open_follow_ups.length) return <div className="empty">No open follow-ups.</div>;
  return (
    <>
      {p.open_follow_ups.map((t) => (
        <div className="person-row clickable" key={`${t.kind}-${t.id}`} onClick={() => onOpen(t)}>
          <span><b>{t.text}</b><br /><span className="muted">{t.kind === 'newcomer' ? 'From when they were a newcomer' : 'Member follow-up'}{t.by ? ` · ${t.by}` : ''}</span></span>
          <span className="muted">Due {day(t.due_date)}</span>
        </div>
      ))}
    </>
  );
}
