import { Skeleton } from '../../components/ui/Skeleton';
import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSession, useCheckIn, useCheckOut, useSetCheckInMode, useNewcomerRoster, useAbsentPreview, useFollowUpAbsent, type RosterNewcomer } from '../../api/attendance';
import { useMemberRoster } from '../../api/members';
import { Icon } from '../../components/ui/Icon';
import type { Member } from '../../types/members';
import type { AttendanceSessionMember } from '../../types/attendance';
import { HelpMark } from '../../components/ui/HelpMark';
import { useAuth } from '../../context/AuthContext';

const CATEGORY_ORDER = ['Worker', 'Worker in Training', 'General Member'] as const;
const longDay = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).replace(',', '');

export function LiveCheckInPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const navigate = useNavigate();

  const { data: session, isLoading: loadingSession } = useSession(sessionId);
  const { data: roster, isLoading: loadingRoster } = useMemberRoster(session?.location);
  // Newcomers too, so their Friday attendance builds up towards membership.
  // Only for those who can check people in, as the server allows.
  const { hasPermission } = useAuth();
  const { data: ncRoster } = useNewcomerRoster(sessionId, !!session && hasPermission('attendance', 'edit'));
  const checkIn = useCheckIn(sessionId);
  const checkOut = useCheckOut(sessionId);
  const setMode = useSetCheckInMode(sessionId);

  const [query, setQuery] = useState('');
  // A tap that fails says so, rather than leaving the row silently unchanged.
  const [tapError, setTapError] = useState('');
  const [presentNote, setPresentNote] = useState<string[]>([]);
  const failed = (e: any) => setTapError(e?.response?.data?.detail || 'That tap was not saved. Check your connection and tap again.');

  // Who is already checked in, by member id, so a row can render its
  // state without scanning the attendee array on every keystroke.
  const attendeeByMember = useMemo(() => {
    const map = new Map<number, AttendanceSessionMember>();
    (session?.attendees ?? []).forEach((a) => { if (a.member) map.set(a.member, a); });
    return map;
  }, [session?.attendees]);
  const attendeeByNewcomer = useMemo(() => {
    const map = new Map<number, AttendanceSessionMember>();
    (session?.attendees ?? []).forEach((a) => { if (a.newcomer) map.set(a.newcomer, a); });
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
  const newcomers = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (ncRoster?.results ?? []).filter((n) => !q || n.name.toLowerCase().includes(q));
  }, [ncRoster, query]);

  if (loadingSession || loadingRoster) return <Skeleton shape="list" />;
  if (!session) return <div className="card">Session not found.</div>;

  const checkedCount = session.attendees.length;
  // A service from an earlier day, being ticked off afterwards.
  const todayIso = new Date().toLocaleDateString('en-CA');
  const past = session.date < todayIso;
  const daysAgo = Math.round((new Date(`${todayIso}T00:00:00`).getTime() - new Date(`${session.date}T00:00:00`).getTime()) / 86400000);
  // The absence check looks at services up to 7 days old.
  const recentAbsence = past && !!session.counts_for_absence && daysAgo <= 7;
  const total = (roster?.length ?? 0) + (ncRoster?.results.length ?? 0);
  const anyVisible = CATEGORY_ORDER.some((c) => grouped[c].length > 0) || newcomers.length > 0;

  function toggle(member: Member) {
    // Each tap is its own request. Several ushers on different doors work
    // the same session at once, so nothing is batched into a form that
    // could overwrite someone else's taps on submit.
    setTapError('');
    if (attendeeByMember.has(member.id)) checkOut.mutate({ memberId: member.id }, { onError: failed });
    else checkIn.mutate({ memberId: member.id }, { onError: failed, onSuccess: present });
  }
  // Ticked after their task was made: the task closes as Was present.
  function present(r: { was_present?: string[] }) {
    if (r?.was_present?.length) setPresentNote(r.was_present);
  }
  function toggleNewcomer(n: RosterNewcomer) {
    setTapError('');
    if (attendeeByNewcomer.has(n.id)) checkOut.mutate({ newcomerId: n.id }, { onError: failed });
    else checkIn.mutate({ newcomerId: n.id }, { onError: failed, onSuccess: present });
  }
  // Fridays so far, counting today once they are checked in.
  function fridays(n: RosterNewcomer, checked: boolean) {
    if (!ncRoster?.fridays || n.fridays_held === undefined) return '';
    const attended = n.fridays_attended ?? 0;
    if (!attended && !checked) return ' · No Fridays recorded yet';
    // The roster is refreshed after every tap, so its figures already
    // include today once they are checked in.
    return ` · Fridays ${attended} of ${n.fridays_held}`;
  }

  return (
    <>
      {tapError && <p className="form-error" role="alert">{tapError}</p>}
      {presentNote.length > 0 && (
        <div className="fr-done" role="status" style={{ marginBottom: 10 }}>
          <b>{presentNote.join(', ')} {presentNote.length === 1 ? 'was' : 'were'} ticked present.</b><HelpMark topic="faWasPresent" />{' '}
          {presentNote.length === 1 ? 'The follow-up task for this service is' : 'Their follow-up tasks for this service are'} closed as Was present, and the shepherd has been told.
        </div>
      )}
      {session.late_entry && session.attendees.some((a) => a.member != null) && (
        <div className="gender-notice" role="note">
          <b>Names ticked late</b><HelpMark topic="faNamesLate" /><br />
          The absence check already ran at {new Date(session.late_entry.check_ran).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true, timeZone: 'Asia/Bahrain' }).toLowerCase()} on {longDay(session.date)}.
          Tasks for anyone not ticked are made at the next check, within 30 minutes, and are due {session.late_entry.due_hours} hours from then, so shepherds are not late because of a late entry.
        </div>
      )}
      <a className="backlink" onClick={() => navigate(`/attendance/${sessionId}`)}>
        ← Back to session details
      </a>

      {past && (
        <div className="card checkin-past" role="note">
          <b>This service was on {longDay(session.date)}.</b>
          <div>
            Tick everyone who came that day. Newcomers ticked here count towards their Fridays for membership.
            {session.status === 'filled' ? ' The headcount already saved is not changed.' : ' The headcount is not changed.'}
            {recentAbsence && ' Members not ticked get an absence follow-up task, as this service follows up absence.'}
          </div>
        </div>
      )}
      <div className="card checkin-header">
        <div className="checkin-header-row">
          <div style={{ minWidth: 0 }}>
            <h3 style={{ fontSize: '1.1rem' }}>{session.meeting_type_name}</h3>
            <div className="muted">{session.date} · {past ? 'Checking in after the service' : 'Live check-in'}<HelpMark topic="liveCheckIn" /></div>
          </div>
          <div style={{ textAlign: 'right', flex: 'none' }}>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--blue-deep)' }}>
              {checkedCount}
              <span className="muted" style={{ fontSize: '1rem', fontWeight: 600 }}> / {total}</span>
            </div>
            <div className="muted" style={{ fontSize: '.78rem' }}>checked in</div>
          </div>
        </div>
        <label htmlFor="checkin-search" className="sr-only">Search members and newcomers</label>
        <input
          id="checkin-search"
          className="search"
          style={{ width: '100%', marginTop: 10 }}
          placeholder="Search members and newcomers..."
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
                    aria-pressed={!!att}
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
                          setMode.mutate({ memberId: m.id, mode: online ? 'in-person' : 'online' }, { onError: failed });
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
        }).concat(newcomers.length ? [
          <div key="newcomers" className="checkin-newcomers">
            <div className="checkin-group">Newcomers</div>
            <p className="muted checkin-newcomers-note">
              Tap a newcomer as you would a member. Their Friday attendance builds up on their profile, towards membership.
            </p>
            {newcomers.map((n) => {
              const att = attendeeByNewcomer.get(n.id);
              const online = att?.mode === 'online';
              return (
                <div
                  key={`n${n.id}`}
                  className={`checkin-row${att ? ' checked' : ''}`}
                  aria-pressed={!!att}
                  onClick={() => toggleNewcomer(n)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleNewcomer(n); } }}
                >
                  <span className="avatar" style={att ? { background: 'var(--green-bg)', color: 'var(--green)' } : undefined}>
                    {att ? <Icon name="check" size={18} /> : n.name.charAt(0)}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <b>{n.name}</b>
                    <div className="muted" style={{ fontSize: '.78rem' }}>
                      {att ? `Checked in · ${online ? 'Online' : 'In person'}` : 'Not checked in'}{fridays(n, !!att)}
                    </div>
                  </div>
                  {att && (
                    <button
                      className="btn sm outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMode.mutate({ newcomerId: n.id, mode: online ? 'in-person' : 'online' }, { onError: failed });
                      }}
                    >
                      {online ? 'Mark in person' : 'Mark online'}
                    </button>
                  )}
                </div>
              );
            })}
          </div>,
        ] : []) : (
          <div className="empty">
            {query ? 'Nobody matches this search.' : 'No members or newcomers at this location yet.'}
          </div>
        )}
      </div>

      {past && !recentAbsence && (
        <FollowUpNotTicked sessionId={sessionId} tracked={!!session.counts_for_absence}
          ticks={session.attendees.filter((a) => a.member != null).length} />
      )}

      {!past && (
        <div className="card section-gap checkin-note">
          Nobody needs to press a finish button. A few hours after this meeting's start time,
          anyone still not checked in is treated as absent and a follow-up task is created for
          their shepherd. This only happens for meetings marked
          <b> Counts toward absence follow-up</b> in Admin.
          <br /><br />
          Someone registered as a newcomer today, by QR code or Manual entry, is checked in to this
          service automatically.
        </div>
      )}
    </>
  );
}

/** "Follow up those not ticked" on a service ticked off afterwards: the
 *  automatic check does not cover it, so somebody asks for it here. */
function FollowUpNotTicked({ sessionId, tracked, ticks }: { sessionId: number; tracked: boolean; ticks: number }) {
  const { data, error, isLoading } = useAbsentPreview(sessionId, ticks, true);
  const make = useFollowUpAbsent(sessionId);
  const [confirming, setConfirming] = useState(false);
  const [done, setDone] = useState<number | null>(null);
  const [failed, setFailed] = useState('');
  const why = tracked
    ? 'This service is more than 7 days old, so nobody was followed up automatically.'
    : 'This meeting is not followed up automatically.';
  const refused = data?.blocked || ((error as any)?.response?.data?.detail as string | undefined);
  const n = data?.to_follow_up ?? 0;
  const people = (k: number) => `${k} member${k === 1 ? '' : 's'}`;

  async function create() {
    setFailed('');
    try {
      const r = await make.mutateAsync();
      setDone(r.created);
      setConfirming(false);
    } catch (e: any) {
      setFailed(e?.response?.data?.detail || 'The tasks could not be made. Please try again.');
    }
  }

  return (
    <div className="card section-gap followup-absent">
      <h3>Follow up those not ticked</h3>
      {isLoading ? <p className="muted">Working out who was not ticked…</p> : refused ? (
        <p className="muted">{refused}</p>
      ) : data && (
        <>
          <p className="muted">
            {why}{' '}
            {n ? <><b>{people(n)}</b> {n === 1 ? 'was' : 'were'} not ticked. Each gets a follow-up task for their shepherd, due in 2 days.</>
               : 'Everyone not ticked already has a follow-up.'}
            {data.open_elsewhere ? ` ${people(data.open_elsewhere)} with an open follow-up already ${data.open_elsewhere === 1 ? 'is' : 'are'} skipped.` : ''}
          </p>
          {done !== null && <p className="report-done" role="status">{done} follow-up task{done === 1 ? '' : 's'} made. They are in Members, on the Follow-up tab.</p>}
          {failed && <p className="form-error" role="alert">{failed}</p>}
          {n > 0 && !confirming && (
            <button className="btn sm" onClick={() => { setConfirming(true); setDone(null); }}>Follow up {people(n)}</button>
          )}
          {n > 0 && confirming && (
            <div className="followup-confirm">
              <b>Create {n} follow-up task{n === 1 ? '' : 's'}?</b>
              <div className="muted">
                For {data.names.join(', ')}.{data.ticked.length ? ` ${data.ticked.join(', ')} ${data.ticked.length === 1 ? 'was' : 'were'} ticked, so ${data.ticked.length === 1 ? 'is' : 'are'} left out.` : ''}
              </div>
              <div className="form-actions-row">
                <button className="btn sm" onClick={create} disabled={make.isPending}>{make.isPending ? 'Creating…' : 'Create tasks'}</button>
                <button className="btn sm ghost" onClick={() => setConfirming(false)}>Cancel</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
