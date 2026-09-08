import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSession, useDeleteSession, useRecordSession, useMeetingTypes } from '../../api/attendance';
import { apiClient } from '../../api/client';
import type { Member, PaginatedResponse } from '../../types/members';
import { Badge } from '../../components/ui/Badge';
import { useMembers } from '../../api/members';
import { Icon } from '../../components/ui/Icon';

const DETAILED_FIELDS: [keyof typeof EMPTY_COUNTS, string][] = [
  ['men', 'Men'], ['women', 'Women'], ['youth_boys', 'Youth Boys'], ['youth_girls', 'Youth Girls'],
  ['children_boys', 'Children Boys'], ['children_girls', 'Children Girls'],
];
const SIMPLE_FIELDS: [keyof typeof EMPTY_COUNTS, string][] = [['men', 'Men'], ['women', 'Women']];

const EMPTY_COUNTS = { men: 0, women: 0, youth_boys: 0, youth_girls: 0, children_boys: 0, children_girls: 0 };

function categoryBadgeColor(cat: string): 'green' | 'amber' | 'gray' {
  if (cat === 'Worker') return 'green';
  if (cat === 'Worker in Training') return 'amber';
  return 'gray';
}

export function SessionRecordPage() {
  const { id } = useParams();
  const sessionId = Number(id);
  const navigate = useNavigate();
  const { data: session, isLoading } = useSession(sessionId);
  const { data: meetingTypes } = useMeetingTypes();
  const deleteSession = useDeleteSession();
  const recordSession = useRecordSession(sessionId);

  // Only Workers lead a fellowship, so the list is scoped to them.
  const { data: workerPage } = useMembers({ category: 'Worker' });
  const workers = workerPage?.results;
  const [counts, setCounts] = useState(EMPTY_COUNTS);
  // Online attendance, kept separate. Any meeting can be hybrid and a
  // total showing only the room understates the month.
  const [online, setOnline] = useState(EMPTY_COUNTS);
  const [onlineOpen, setOnlineOpen] = useState(false);
  const [newComers, setNewComers] = useState(0);
  const [newConverts, setNewConverts] = useState(0);
  const [ledBy, setLedBy] = useState<number | ''>('');
  const [lesson, setLesson] = useState('');
  const [trackNamed, setTrackNamed] = useState(false);
  const [attendeeIds, setAttendeeIds] = useState<Set<number>>(new Set());
  const [selectedNames, setSelectedNames] = useState<Map<number, string>>(new Map());
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<Member[]>([]);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!session) return;
    setCounts({
      men: session.men, women: session.women, youth_boys: session.youth_boys,
      youth_girls: session.youth_girls, children_boys: session.children_boys, children_girls: session.children_girls,
    });
    setTrackNamed(session.track_named);
    const ids = new Set(session.attendees.map((a) => a.member));
    setAttendeeIds(ids);
    const names = new Map(session.attendees.map((a) => [a.member, a.member_name] as const));
    setSelectedNames(names);
  }, [session]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      // No location restriction , any member, from any location, can be
      // checked into any session (Batch 0.2 approved decision).
      const resp = await apiClient.get<PaginatedResponse<Member>>('/members/', {
        params: { search: search || undefined, page_size: 50 },
      });
      setSearchResults(resp.data.results);
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search]);

  if (isLoading || !session || !meetingTypes) return <div className="card">Loading…</div>;

  const meetingType = meetingTypes.find((m) => m.id === session.meeting_type);
  const fields = meetingType?.detail_level === 'simple' ? SIMPLE_FIELDS : DETAILED_FIELDS;

  const inPerson = Object.values(counts).reduce((a, b) => a + b, 0);
  const onlineCount = Object.values(online).reduce((a, b) => a + b, 0);
  const total = inPerson + onlineCount;
  const isFellowship = !!session?.fellowship;

  function toggleAttendee(member: Member) {
    const next = new Set(attendeeIds);
    const names = new Map(selectedNames);
    if (next.has(member.id)) {
      next.delete(member.id);
      names.delete(member.id);
    } else {
      next.add(member.id);
      names.set(member.id, member.full_name);
    }
    setAttendeeIds(next);
    setSelectedNames(names);
  }

  async function handleDelete() {
    if (!confirm('Delete this session?')) return;
    await deleteSession.mutateAsync(sessionId);
    navigate('/attendance');
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await recordSession.mutateAsync({
      ...counts,
      online_men: online.men, online_women: online.women,
      online_youth_boys: online.youth_boys, online_youth_girls: online.youth_girls,
      online_children_boys: online.children_boys, online_children_girls: online.children_girls,
      new_comers: newComers, new_converts: newConverts,
      ...(isFellowship ? { led_by: ledBy === '' ? null : ledBy, lesson } : {}),
      track_named: trackNamed,
      attendee_ids: Array.from(attendeeIds),
    });
    navigate('/attendance');
  }

  return (
    <>
      <a className="backlink" onClick={() => navigate('/attendance')}>← Back to sessions</a>
      <div className="card" style={{ maxWidth: 560, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem' }}>
              {session.meeting_type_name}
              {session.fellowship_name ? ` · ${session.fellowship_name}` : ''} · {session.date}
            </h3>
            <div className="muted" style={{ marginBottom: 16 }}>{session.location} · {session.mode.replace('-', ' ')}</div>
          </div>
          <button className="icon-btn" title="Delete session" onClick={handleDelete}>
            <Icon name="trash" size={15} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="followup-guide">
            <div className="followup-guide-title"><Icon name="users" size={14} /> In person</div>
            <div className="followup-guide-note">Everyone physically in the room.</div>
          </div>
          {fields.map(([key, label]) => (
            <div className="field" key={key}>
              <label htmlFor={`session-count-${key}`}>{label}</label>
              <input
                id={`session-count-${key}`}
                type="number" min={0} value={counts[key]}
                onChange={(e) => setCounts({ ...counts, [key]: Number(e.target.value) || 0 })}
              />
            </div>
          ))}

          <button type="button" className="followup-guide"
            style={{ width: '100%', textAlign: 'left', cursor: 'pointer', border: 0 }}
            onClick={() => setOnlineOpen(!onlineOpen)}>
            <div className="followup-guide-title">
              <Icon name="grid" size={14} /> Joining online
              <span className="muted" style={{ fontWeight: 400, fontSize: '.78rem', marginLeft: 6 }}>
                {onlineOpen || onlineCount ? '' : '(tap to add)'}
              </span>
            </div>
            <div className="followup-guide-note">Leave blank when nobody joined remotely.</div>
          </button>
          {(onlineOpen || onlineCount > 0) && fields.map(([key, label]) => (
            <div className="field" key={`online-${key}`}>
              <label htmlFor={`session-online-${key}`}>{label} online</label>
              <input
                id={`session-online-${key}`}
                type="number" min={0} value={online[key]}
                onChange={(e) => setOnline({ ...online, [key]: Number(e.target.value) || 0 })}
              />
            </div>
          ))}

          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderTop: '1px solid var(--line)', marginTop: 6, fontWeight: 800 }}>
            <span>Total{onlineCount > 0 && (
              <span className="muted" style={{ fontWeight: 400, fontSize: '.8rem', marginLeft: 8 }}>
                {inPerson} in person, {onlineCount} online
              </span>
            )}</span>
            <span>{total}</span>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="session-new-comers">New comers</label>
              <input id="session-new-comers" type="number" min={0} value={newComers}
                onChange={(e) => setNewComers(Number(e.target.value) || 0)} />
              <div className="field-hint">Present for the first time.</div>
            </div>
            <div className="field">
              <label htmlFor="session-new-converts">New converts</label>
              <input id="session-new-converts" type="number" min={0} value={newConverts}
                onChange={(e) => setNewConverts(Number(e.target.value) || 0)} />
              <div className="field-hint">Gave their life to Christ here.</div>
            </div>
          </div>

          {isFellowship && (
            <>
              <div className="followup-guide">
                <div className="followup-guide-title"><Icon name="users" size={14} /> This fellowship meeting</div>
                <div className="followup-guide-note">
                  Recorded per meeting, since who leads changes week to week.
                </div>
              </div>
              <div className="form-row">
                <div className="field">
                  <label htmlFor="session-led-by">Led by</label>
                  <select id="session-led-by" value={ledBy}
                    onChange={(e) => setLedBy(e.target.value === '' ? '' : Number(e.target.value))}>
                    <option value="">Not recorded</option>
                    {(workers ?? []).map((m) => (
                      <option key={m.id} value={m.id}>{m.first_name} {m.surname}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="session-lesson">Lesson studied</label>
                  <input id="session-lesson" value={lesson}
                    onChange={(e) => setLesson(e.target.value)} placeholder="e.g. BTB 15" />
                </div>
              </div>
            </>
          )}

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '14px 0', fontSize: '.85rem' }}>
            <input type="checkbox" checked={trackNamed} onChange={(e) => setTrackNamed(e.target.checked)} style={{ width: 16, height: 16 }} />
            Track named attendance for this session
          </label>

          {trackNamed && (
            <div className="form-card">
              <div className="muted" style={{ fontSize: '.8rem', marginBottom: 10 }}>
                Any member, from any location, can be checked in here. Headcounts above remain the source of
                truth for attendance totals; this list is supplementary.
                {selectedNames.size > 0 && ` ${selectedNames.size} selected.`}
              </div>
              <input
                className="search" style={{ width: '100%', marginBottom: 10 }}
                placeholder="Search members..." value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <div style={{ maxHeight: 280, overflowY: 'auto', display: 'grid', gap: 2 }}>
                {searchResults.length ? searchResults.map((m) => (
                  <label
                    key={m.id}
                    style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 4px', borderBottom: '1px solid var(--line)', fontSize: '.88rem', cursor: 'pointer' }}
                  >
                    <input type="checkbox" checked={attendeeIds.has(m.id)} onChange={() => toggleAttendee(m)} style={{ width: 16, height: 16 }} />
                    <span style={{ flex: 1 }}>{m.full_name}</span>
                    <Badge color={categoryBadgeColor(m.category)}>{m.category}</Badge>
                  </label>
                )) : <div className="empty">No members match this search.</div>}
              </div>
            </div>
          )}

          <button className="btn" type="submit" disabled={recordSession.isPending}>
            {recordSession.isPending ? 'Saving…' : 'Save session'}
          </button>
        </form>
      </div>
    </>
  );
}
