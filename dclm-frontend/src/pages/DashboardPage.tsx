import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useDashboardSummary } from '../api/dashboard';
import { StatRow, type StatItem } from '../components/ui/StatRow';
import { RingChart } from '../components/charts/RingChart';
import { DonutChart } from '../components/charts/DonutChart';
import { MiniBars } from '../components/charts/MiniBars';
import { Icon } from '../components/ui/Icon';
import { fmt } from '../lib/format';

const PALETTE = ['#0B3C91', '#1F6FE5', '#D6202C', '#F2A93B', '#1E9E64'];

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data, isLoading, isError } = useDashboardSummary();

  if (isLoading) return <div className="card">Loading…</div>;
  if (isError || !data) return <div className="card">Could not load the dashboard. Please try again.</div>;

  // Phase 4.3: each section is gated by the viewer's real per-module
  // permission and entirely absent from the response when they lack
  // it , restricted stat cards and panels are simply omitted below,
  // rather than shown empty or with a misleading "go to X" link to a
  // page the route guard (Batch 3.10) would just redirect them away from.
  const fwPct = data.attendance_access && data.friday_worship?.target
    ? Math.min(100, Math.round((data.friday_worship.total / data.friday_worship.target) * 100))
    : 0;

  const stats: StatItem[] = [];
  if (data.attendance_access && data.friday_worship) {
    stats.push({
      icon: 'check',
      color: 'blue',
      label: `Friday Worship (latest)${data.friday_worship.target ? ` · target ${data.friday_worship.target}` : ''}`,
      value: data.friday_worship.total,
      onClick: () => navigate('/attendance'),
      hint: 'Go to Attendance →',
      topRight: <RingChart pct={fwPct} size={38} stroke={5} color="var(--blue)" valueFontSize=".62rem" />,
    });
  }
  if (data.finance_access) {
    stats.push({
      icon: 'coin',
      color: 'red',
      label: 'Giving, all time (filtered)',
      value: fmt(data.giving_total ?? 0),
      onClick: () => navigate('/finance'),
      hint: 'Go to Giving & Finance →',
      topRight: <span className="trend-chip up">{data.fund_count ?? 0} funds</span>,
    });
  }
  if (data.newcomers_access) {
    stats.push({
      icon: 'userplus',
      color: 'amber',
      label: 'Newcomers in the pipeline',
      value: data.newcomers_in_pipeline ?? 0,
      onClick: () => navigate('/newcomers'),
      hint: 'Go to Newcomers →',
      topRight: (data.pending_followups_count ?? 0) > 0
        ? <span className="trend-chip warn">{data.pending_followups_count} due</span>
        : undefined,
    });
  }
  if (data.finance_access) {
    stats.push({
      icon: 'gear',
      color: 'blue',
      label: `Net (expenses ${fmt(data.expense_total ?? 0)})`,
      value: fmt(data.net_total ?? 0),
      onClick: () => navigate('/finance'),
      hint: 'Go to Giving & Finance →',
    });
  }

  const donutData = (data.giving_by_fund ?? []).map((f, i) => ({
    label: f.fund,
    value: f.value,
    color: PALETTE[i % PALETTE.length],
  }));
  const trendData = (data.friday_worship?.trend ?? []).map((t) => ({
    label: t.date.slice(5),
    value: t.total,
  }));

  return (
    <>
      <div className="dash-hero">
        <div className="dash-hero-text">
          <div className="eyebrow light" style={{ color: '#BFD5FF' }}>Welcome back</div>
          <h2 style={{ color: '#fff' }}>Here's how DCLM Bahrain is doing</h2>
          <p>
            A snapshot of attendance, giving, and follow-up across{' '}
            {user?.location_name ?? 'all locations'}.
          </p>
        </div>
        <div className="hero-actions">
          <a className="btn-light-hero" onClick={() => navigate('/attendance')}>
            <Icon name="plus" size={15} /> New session
          </a>
          <a className="btn-light-hero" onClick={() => navigate('/members')}>
            <Icon name="plus" size={15} /> Add member
          </a>
          <a className="btn-light-hero" onClick={() => navigate('/reports')}>
            <Icon name="plus" size={15} /> Add testimony
          </a>
        </div>
      </div>

      {stats.length > 0 && <StatRow stats={stats} />}

      {(data.finance_access || data.attendance_access) && (
        <div className="grid g2 section-gap">
          {data.finance_access && (
            <div className="card card-link" onClick={() => navigate('/finance')}>
              <h3>Giving by fund</h3>
              <div style={{ marginTop: 12 }}>
                {donutData.length ? <DonutChart data={donutData} /> : <div className="empty">No giving recorded yet.</div>}
              </div>
              <span className="card-link-hint">Go to Giving &amp; Finance →</span>
            </div>
          )}
          {data.attendance_access && (
            <div className="card card-link" onClick={() => navigate('/attendance')}>
              <h3>Friday Worship attendance trend</h3>
              <div style={{ marginTop: 6 }}>
                {trendData.length ? <MiniBars data={trendData} /> : <div className="empty">No filled sessions yet.</div>}
              </div>
              <span className="card-link-hint">Go to Attendance →</span>
            </div>
          )}
        </div>
      )}

      {(data.newcomers_access || data.goals_access) && (
        <div className="grid g2 section-gap">
          {data.newcomers_access && (
            <div className="card card-link" onClick={() => navigate('/newcomers')}>
              <h3>Follow-ups due</h3>
              {(data.follow_ups_due ?? []).length ? (
                data.follow_ups_due!.map((f, i) => (
                  <div className="followup-row" key={i}>
                    <span className="avatar">{f.newcomer_name.charAt(0)}</span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <b
                        style={{ cursor: 'pointer', color: 'var(--blue-deep)' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate('/newcomers');
                        }}
                      >
                        {f.newcomer_name}
                      </b>
                      <div className="muted" style={{ fontSize: '.8rem' }}>{f.text}</div>
                    </div>
                    <span className="badge amber">Due {f.due_date}</span>
                  </div>
                ))
              ) : (
                <div className="empty">No pending follow-up tasks. Everyone has been reached.</div>
              )}
              <span className="card-link-hint">Go to Newcomers &amp; Follow-up →</span>
            </div>
          )}
          {data.goals_access && (
            <div className="card">
              <h3>Short-term goals</h3>
              <div className="ring-grid section-gap" style={{ marginTop: 14 }}>
                {(data.short_term_goals ?? []).map((g) => {
                  const color = g.pct >= 90 ? 'var(--green)' : g.pct < 60 ? 'var(--red)' : 'var(--blue)';
                  const dest = g.link_route || 'newcomers';
                  return (
                    <div
                      className="ring-item ring-item-link"
                      key={g.id}
                      onClick={() => navigate(`/${dest}`)}
                    >
                      <RingChart pct={g.pct} size={72} stroke={7} color={color} />
                      <div className="ring-item-label">{g.name}</div>
                    </div>
                  );
                })}
              </div>
              <div style={{ marginTop: 14, textAlign: 'center' }}>
                <a className="btn sm outline" onClick={() => navigate('/goals')}>View all goals →</a>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
