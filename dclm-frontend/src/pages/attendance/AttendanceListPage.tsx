import { useState } from 'react';
import { DATE_RANGES, rangeBounds, type DateRangeKey } from '../../lib/dateRanges';
import { useFellowships, useCreateFellowship, useDeleteFellowship } from '../../api/attendance';
import { AUDIENCES } from '../../types/attendance';
import { useNavigate } from 'react-router-dom';
import { useMeetingTypes, useAttendanceStats, useSessions, useRecentFilledSessions, useDeleteSession } from '../../api/attendance';
import { useDashboardSummary } from '../../api/dashboard';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { StackedBars } from '../../components/charts/StackedBars';
import { Pagination } from '../../components/ui/Pagination';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';

export function AttendanceListPage() {
  const navigate = useNavigate();
  const [meetingFilter, setMeetingFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [ordering, setOrdering] = useState('-date');
  const [audienceFilter, setAudienceFilter] = useState('all');
  const [rangeFilter, setRangeFilter] = useState<DateRangeKey>('all');
  const [checkedInFilter, setCheckedInFilter] = useState('all');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { data: fellowships } = useFellowships();
  const createFellowship = useCreateFellowship();
  const deleteFellowship = useDeleteFellowship();

  async function addFellowship() {
    const name = prompt('Name of the fellowship, for example HCF Youth');
    if (!name) return;
    const area = prompt('Which area does it meet in?') || '';
    await createFellowship.mutateAsync({ name, area });
  }

  async function removeFellowship(id: number, name: string, sessions: number) {
    if (sessions) {
      alert(`${name} has ${sessions} session(s) recorded. Those records would lose what they belong to, so it cannot be removed.`);
      return;
    }
    if (!confirm(`Remove ${name}?`)) return;
    await deleteFellowship.mutateAsync(id);
  }
  const [page, setPage] = useState(1);
  const pageSize = 8;

  const { data: meetingTypes } = useMeetingTypes();
  const { data: stats } = useAttendanceStats();
  const { data: dashboard } = useDashboardSummary();
  const { data: recentFW } = useRecentFilledSessions('fri-worship');
  const { data: sessions, isLoading } = useSessions({
    meeting_type: meetingFilter !== 'all' ? meetingFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    audience: audienceFilter !== 'all' ? audienceFilter : undefined,
    date_from: rangeBounds(rangeFilter)?.[0],
    date_to: rangeBounds(rangeFilter)?.[1],
    checked_in: checkedInFilter !== 'all' ? checkedInFilter : undefined,
    ordering,
    page,
    page_size: pageSize,
  });
  const deleteSession = useDeleteSession();

  const statItems: StatItem[] = [
    { icon: 'check', color: 'blue', label: 'Sessions this month', value: stats?.sessions_this_month ?? 0 },
    { icon: 'check', color: 'green', label: 'Filled', value: stats?.filled ?? 0 },
    { icon: 'alert', color: 'amber', label: 'Pending', value: stats?.pending ?? 0 },
    { icon: 'users', color: 'blue', label: 'Friday Worship (latest)', value: dashboard?.friday_worship?.total ?? 0 },
  ];

  const chartData = (recentFW ?? []).map((s) => ({
    label: s.date.slice(5),
    adults: s.men + s.women,
    youth: s.youth_boys + s.youth_girls,
    children: s.children_boys + s.children_girls,
  }));

  const totalPages = sessions ? Math.max(1, Math.ceil(sessions.count / pageSize)) : 1;

  async function handleDelete(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (!confirm('Delete this session?')) return;
    await deleteSession.mutateAsync(id);
  }

  return (
    <>
      <StatRow stats={statItems} />

      <div className="card section-gap">
        <h3>Friday Worship attendance by age group</h3>
        {chartData.length ? <StackedBars data={chartData} /> : <div className="empty">No filled Friday Worship sessions yet.</div>}
      </div>

      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>All sessions</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', flex: 1, justifyContent: 'flex-end' }}>
            {/* Collapsed on a phone: six stacked dropdowns pushed the table
                more than a screen down, so the data comes first. */}
            <button className="filter-toggle" onClick={() => setFiltersOpen(!filtersOpen)}>
              <span>Filters</span><span>{filtersOpen ? 'Hide' : 'Show'}</span>
            </button>
            <div className={`filter-panel${filtersOpen ? ' open' : ''}`}>
              <label className="sr-only" htmlFor="att-meeting">Meeting</label>
              <select id="att-meeting" className="selectbox" value={meetingFilter}
                onChange={(e) => { setMeetingFilter(e.target.value); setPage(1); }}>
                <option value="all">All meetings</option>
                {(meetingTypes ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <label className="sr-only" htmlFor="att-audience">Who it is for</label>
              <select id="att-audience" className="selectbox" value={audienceFilter}
                onChange={(e) => { setAudienceFilter(e.target.value); setPage(1); }}>
                <option value="all">All audiences</option>
                {AUDIENCES.map((a) => <option key={a.key} value={a.key}>{a.label}</option>)}
              </select>
              <label className="sr-only" htmlFor="att-range">Date range</label>
              <select id="att-range" className="selectbox" value={rangeFilter}
                onChange={(e) => { setRangeFilter(e.target.value as DateRangeKey); setPage(1); }}>
                {DATE_RANGES.map((r) => <option key={r.key} value={r.key}>{r.label}</option>)}
              </select>
              <label className="sr-only" htmlFor="att-checkedin">Headcount or check-in</label>
              <select id="att-checkedin" className="selectbox" value={checkedInFilter}
                onChange={(e) => { setCheckedInFilter(e.target.value); setPage(1); }}>
                <option value="all">Headcount or check-in</option>
                <option value="yes">Checked in by name</option>
                <option value="no">Headcount only</option>
              </select>
              <label className="sr-only" htmlFor="att-status">Status</label>
              <select id="att-status" className="selectbox" value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
                <option value="all">All statuses</option>
                <option value="filled">Filled</option>
                <option value="pending">Pending</option>
              </select>
              <label className="sr-only" htmlFor="att-sort">Sort</label>
              <select id="att-sort" className="selectbox" value={ordering}
                onChange={(e) => setOrdering(e.target.value)}>
                <option value="-date">Sort: Newest first</option>
                <option value="date">Sort: Oldest first</option>
                <option value="-total_computed">Sort: Highest total</option>
              </select>
            </div>
            <a className="btn sm" onClick={() => navigate('/attendance/new')}>
              <Icon name="plus" size={15} /> New session
            </a>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead>
              <tr><th>Date</th><th>Meeting</th><th>Location</th><th>Mode</th><th>Total</th><th>Status</th><th></th></tr>
            </thead>
            <tbody>
              {(sessions?.results ?? []).map((s) => (
                <tr key={s.id} className="clickable" onClick={() => navigate(`/attendance/${s.id}`)}>
                  <td data-label="Date">{s.date}</td>
                  <td data-label="Meeting">{s.meeting_type_name}</td>
                  <td data-label="Location">{s.location}</td>
                  <td data-label="Mode" style={{ textTransform: 'capitalize' }}>{s.mode.replace('-', ' ')}</td>
                  <td data-label="Total">{s.status === 'filled' ? s.total : '–'}</td>
                  <td data-label="Status">
                    {s.status === 'filled' ? <Badge color="green">Filled</Badge> : <Badge color="amber">Pending</Badge>}
                  </td>
                  <td className="td-actions" onClick={(e) => e.stopPropagation()}>
                    {s.status === 'pending' && (
                      <button className="btn sm" onClick={() => navigate(`/attendance/${s.id}/check-in`)}>
                        <Icon name="check" size={14} /> Check in
                      </button>
                    )}
                    <button className="icon-btn" title="Delete session" onClick={(e) => handleDelete(e, s.id)}>
                      <Icon name="trash" size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && sessions?.results.length === 0 && <div className="empty">No sessions match these filters.</div>}
        </div>

        {sessions && (
          <Pagination page={page} totalPages={totalPages} totalCount={sessions.count} pageSize={pageSize} onPageChange={setPage} />
        )}
      </div>

      <div className="card section-gap">
        <h3>Weekly meeting schedule</h3>
        <table className="cardtable">
          <thead><tr><th>Meeting</th><th>Day</th><th>Detail level</th><th>Monthly target</th></tr></thead>
          <tbody>
            {(meetingTypes ?? []).map((m) => (
              <tr key={m.id}>
                <td data-label="Meeting">{m.name}</td>
                <td data-label="Day">{m.day}</td>
                <td data-label="Detail level" style={{ textTransform: 'capitalize' }}>
                  {m.detail_level}{m.frequency === 'occasional' ? ' · occasional' : ''}
                </td>
                <td data-label="Monthly target">{m.monthly_target ?? '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="muted" style={{ fontSize: '.8rem', marginTop: 8 }}>
          Recurring sessions above are generated automatically each week from this schedule. Manage meeting types in Admin.
        </div>
      </div>

      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>House fellowships</h3>
          <button className="btn sm outline" onClick={addFellowship}>
            <Icon name="plus" size={15} /> Add a fellowship
          </button>
        </div>
        <div className="muted" style={{ fontSize: '.8rem', marginBottom: 10 }}>
          Several fellowships meet on the same evening, so a session belongs to a fellowship as
          well as a date. The list is configurable because the number changes.
        </div>
        <table className="cardtable">
          <thead>
            <tr><th>Fellowship</th><th>Area</th><th>Sessions recorded</th><th /></tr>
          </thead>
          <tbody>
            {(fellowships ?? []).map((f) => (
              <tr key={f.id}>
                <td data-label="Fellowship"><b>{f.name}</b></td>
                <td data-label="Area">{f.area || '–'}</td>
                <td data-label="Sessions recorded">{f.session_count}</td>
                <td className="td-actions">
                  <button className="icon-btn" title="Remove"
                    onClick={() => removeFellowship(f.id, f.name, f.session_count)}>
                    <Icon name="trash" size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {!(fellowships ?? []).length && (
              <tr><td colSpan={4} className="empty">No fellowships set up yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
