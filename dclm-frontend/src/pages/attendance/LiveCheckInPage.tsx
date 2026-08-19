import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSession, useCheckIn, useCheckOut, useSetCheckInMode } from '../../api/attendance';
import { useMemberRoster } from '../../api/members';
import { Icon } from '../../components/ui/Icon';
import type { Member } from '../../types/members';
import type { AttendanceSessionMember } from '../../types/attendance';
import { HelpMark } from '../../components/ui/HelpMark';

const CATEGORY_ORDER = ['Worker', 'Worker in Training', 'General Member'] as const;

export function LiveCheckInPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const navigate = useNavigate();

  const { data: session, isLoading: loadingSession } = useSession(sessionId);
  const { data: roster, isLoading: loadingRoster } = useMemberRoster(session?.location);
  const checkIn = useCheckIn(sessionId);
  const checkOut = useCheckOut(sessionId);
  const setMode = useSetCheckInMode(sessionId);

  const [query, setQuery] = useState('');

  // Who is already checked in, by member id, so a row can render its
  // state without scanning the attendee array on every keystroke.
  const attendeeByMember = useMemo(() => {
    const map = new Map<number, AttendanceSessionMember>();
    (session?.attendees ?? []).forEach((a) => map.set(a.member, a));
    return map;
  }, [session?.attendees]);

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const out: Record<string, Member[]> = {};
    CATEGORY_ORDER.forEach((c) => { out[c] = []; });
    (roster ?? []).forEach((m) => {
      if (q && !m.full_name.toLowerCase().includes(q)) return;
      if (out[m.category]) out[m.category].push(m);
    });
    return out;
  }, [roster, query]);

  if (loadingSession || loadingRoster) return <div className="card">Loading…</div>;
  if (!session) return <div className="card">Session not found.</div>;

  const checkedCount = session.attendees.length;
  const total = roster?.length ?? 0;
  const anyVisible = CATEGORY_ORDER.some((c) => grouped[c].length > 0);

  function toggle(member: Member) {
    // Each tap is its own request. Several ushers on different doors work
    // the same session at once, so nothing is batched into a form that
    // could overwrite someone else's taps on submit.
    if (attendeeByMember.has(member.id)) checkOut.mutate(member.id);
    else checkIn.mutate({ memberId: member.id });
  }

  return (
    <>
      <a className="backlink" onClick={() => navigate(`/attendance/${sessionId}`)}>
        ← Back to session details
      </a>

      <div className="card checkin-header">
        <div className="checkin-header-row">
          <div style={{ minWidth: 0 }}>
            <h3 style={{ fontSize: '1.1rem' }}>{session.meeting_type_name}</h3>
            <div className="muted">{session.date} · Live check-in<HelpMark topic="liveCheckIn" /></div>
          </div>
          <div style={{ textAlign: 'right', flex: 'none' }}>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--blue-deep)' }}>
              {checkedCount}
              <span className="muted" style={{ fontSize: '1rem', fontWeight: 600 }}> / {total}</span>
            </div>
            <div className="muted" style={{ fontSize: '.78rem' }}>checked in</div>
          </div>
        </div>
        <label htmlFor="checkin-search" className="sr-only">Search members</label>
        <input
          id="checkin-search"
          className="search"
          style={{ width: '100%', marginTop: 10 }}
          placeholder="Search members..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="card section-gap">
        {anyVisible ? CATEGORY_ORDER.map((cat) => {
          const rows = grouped[cat];
          if (!rows.length) return null;
          return (
            <div key={cat}>
              <div className="checkin-group">{cat}</div>
              {rows.map((m) => {
                const att = attendeeByMember.get(m.id);
                const online = att?.mode === 'online';
                return (
                  <div
                    key={m.id}
                    className={`checkin-row${att ? ' checked' : ''}`}
                    onClick={() => toggle(m)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(m); } }}
                  >
                    <span className="avatar" style={att ? { background: 'var(--green-bg)', color: 'var(--green)' } : undefined}>
                      {att ? <Icon name="check" size={18} /> : m.full_name.charAt(0)}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <b>{m.full_name}</b>
                      <div className="muted" style={{ fontSize: '.78rem' }}>
                        {att ? `Checked in · ${online ? 'Online' : 'In person'}` : 'Not checked in'}
                      </div>
                    </div>
                    {att && (
                      <button
                        className="btn sm outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          setMode.mutate({ memberId: m.id, mode: online ? 'in-person' : 'online' });
                        }}
                      >
                        {online ? 'Mark in person' : 'Mark online'}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          );
        }) : (
          <div className="empty">
            {query ? 'No members match this search.' : 'No members at this location yet.'}
          </div>
        )}
      </div>

      <div className="card section-gap checkin-note">
        Nobody needs to press a finish button. A few hours after this meeting's start time,
        anyone still not checked in is treated as absent and a follow-up task is created for
        their shepherd. This only happens for meetings marked
        <b> Counts toward absence follow-up</b> in Admin.
      </div>
    </>
  );
}
