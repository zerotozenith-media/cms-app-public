import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useServiceMe, useServiceTeam, useDismissServiceNote } from '../../api/service';
import { LevelBadge } from './LevelBadge';

// One badge drawing for the whole app, with the corrected, centred icons.
export { LevelBadge } from './LevelBadge';

/** What the badge note says about someone. */
export function badgeNote(name: string, levelName: string, points: number, nextName: string | null, needed: number) {
  const art = (w: string) => (/^[AEIOU]/.test(w) ? 'an ' : 'a ') + w;
  return { name, levelName, line: `${points} points in the last 90 days. ${nextName ? `${needed} more to become ${art(nextName)}.` : 'The highest level.'}` };
}

/**
 * F21: the signed-in person's own badge in the top bar, beside the bell.
 * Hovering, or a tap on a phone, shows the note. Pressing it again, or the
 * link in the note, opens My service. Nothing shows for someone who follows
 * nobody up.
 */
export function ServiceTopBadge() {
  const { data } = useServiceMe();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent | TouchEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', away); document.addEventListener('touchstart', away); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', away); document.removeEventListener('touchstart', away); document.removeEventListener('keydown', esc); };
  }, [open]);
  if (!data?.eligible) return null;
  const n = badgeNote('', data.level_name, data.points, data.keeping ? data.level_name : data.next_level_name, data.points_needed);
  const line = data.keeping ? `${data.points} points in the last 90 days. ${data.points_needed} more to keep ${data.level_name}.` : n.line;
  return (
    // Hovering opens the note only with a mouse. On a phone a tap opens it,
    // and a second tap goes to My service (the two used to collide).
    <div className="tb-pop tb-service" ref={ref}
      onPointerEnter={(e) => { if (e.pointerType === 'mouse') setOpen(true); }}
      onPointerLeave={(e) => { if (e.pointerType === 'mouse') setOpen(false); }}>
      <button className="tb-service-btn" aria-label={`Your service level: ${data.level_name}, ${data.points} points`} aria-expanded={open}
        onClick={() => (open ? navigate('/profile#my-service') : setOpen(true))}>
        <LevelBadge level={data.level} size={34} />
      </button>
      {open && (
        <div className="tb-menu tb-service-note" role="dialog" aria-label="Your service level">
          <b>{data.level_name}</b>
          <span className="muted">{line}</span>
          <a onClick={() => navigate('/profile#my-service')}>My service</a>
        </div>
      )}
    </div>
  );
}

/** F21: My service, at the foot of My profile. */
export function MyServiceCard() {
  const { data } = useServiceMe();
  const navigate = useNavigate();
  useEffect(() => {
    if (window.location.hash === '#my-service') document.getElementById('my-service')?.scrollIntoView({ block: 'start' });
  }, [data]);
  if (!data?.eligible) return null;
  const target = data.keeping ? `To keep ${data.level_name}` : data.next_level_name ? `To become ${/^[AEIOU]/.test(data.next_level_name) ? 'an' : 'a'} ${data.next_level_name}` : '';
  return (
    <div className="card section-gap" id="my-service">
      <h3 style={{ marginBottom: 10 }}>My service</h3>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <LevelBadge level={data.level} size={40} />
        <div><b>{data.level_name}</b><div className="muted" style={{ fontSize: '.86rem' }}>{data.points} points in the last 90 days. {data.scripture}</div></div>
      </div>
      <div className="ms-row" aria-label="The six levels">
        {data.levels.map((l, i) => (
          <span key={l.name} title={`${l.name}, from ${l.from} points`}><LevelBadge level={i} size={i === data.level ? 30 : 26} dim={i > data.level} /></span>
        ))}
      </div>
      {target && data.steps.length > 0 && (
        <p style={{ margin: 0, fontSize: '.9rem' }}>{target}: {data.steps.map((s) => `${s.count} ${s.text}`).join(' and ')}.</p>
      )}
      <a className="ms-team" onClick={() => navigate('/profile/team')}>See the team</a>
    </div>
  );
}

/** F21: the team at the viewer's location, by level then by name, never ranked by points. */
export function TeamListPage() {
  const navigate = useNavigate();
  const { data, isLoading } = useServiceTeam();
  const [tip, setTip] = useState<number | null>(null);
  const levels = useServiceMe().data?.levels ?? [];
  return (
    <div style={{ maxWidth: 640 }}>
      <a className="backlink" onClick={() => navigate('/profile')}>&#8592; Back to My profile</a>
      <div className="card">
        <h3 style={{ marginBottom: 2 }}>The team</h3>
        <p className="muted" style={{ marginTop: 0, fontSize: '.86rem' }}>Everyone who follows people up at your location, by level, then by name.</p>
        {isLoading ? <p className="muted">Loading the team.</p> : (data?.results ?? []).map((r) => {
          const next = levels[r.level + 1];
          const line = `${r.points} points in the last 90 days.${next ? ` ${next.from - r.points > 0 ? next.from - r.points : 0} more to become ${/^[AEIOU]/.test(next.name) ? 'an' : 'a'} ${next.name}.` : ''}`;
          return (
            <div className={`team-row${r.is_me ? ' me' : ''}`} key={r.id}>
              <span className="avatar">{r.initials}</span>
              <span className="team-name">{r.name}
                <span className="team-badge-wrap">
                  <button className="team-badge" aria-label={`${r.name}: ${r.level_name}, ${r.points} points`} aria-expanded={tip === r.id}
                    onClick={() => setTip(tip === r.id ? null : r.id)}
                    onPointerEnter={(e) => { if (e.pointerType === 'mouse') setTip(r.id); }}
                    onPointerLeave={(e) => { if (e.pointerType === 'mouse') setTip(null); }}>
                    <LevelBadge level={r.level} size={22} />
                  </button>
                  {/* Beside the badge, so it covers nobody's name. */}
                  {tip === r.id && <span className="team-tip" role="tooltip"><b>{r.name}</b><b>{r.level_name}</b><span className="muted">{line}</span></span>}
                </span>
                <span className="muted team-level">{r.level_name}</span>
              </span>
              <span className="muted team-points">{r.points} points</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** F21: a small note under the dashboard greeting, only when moving up or during a notice. */
export function ServiceNote() {
  const { data } = useServiceMe();
  const dismiss = useDismissServiceNote();
  const navigate = useNavigate();
  if (!data?.eligible || !data.note) return null;
  return (
    <div className="service-note" role="status">
      <span>{data.note.text}</span>
      <a onClick={() => navigate('/profile#my-service')}>My service</a>
      <button aria-label="Dismiss" onClick={() => dismiss.mutate()}>&#215;</button>
    </div>
  );
}
