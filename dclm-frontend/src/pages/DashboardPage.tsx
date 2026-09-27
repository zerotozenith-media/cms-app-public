/**
 * The dashboard.
 *
 * One period control drives every card, so they cannot disagree about
 * which month they describe. The banner names what needs doing rather
 * than restating that this is the dashboard. Each card appears only when
 * the viewer may see its module.
 */
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useDashboardSummary } from '../api/dashboard';
import { RingChart } from '../components/charts/RingChart';
import { DonutChart } from '../components/charts/DonutChart';
import { GroupedBars } from '../components/charts/GroupedBars';
import { Icon } from '../components/ui/Icon';
import { fmt } from '../lib/format';
import type { DashPeriod } from '../types/dashboard';

const PERIODS: { value: DashPeriod; label: string }[] = [
  { value: 'this-month', label: 'This month' },
  { value: 'last-month', label: 'Last month' },
  { value: 'this-year', label: 'This year so far' },
  { value: 'last-year', label: 'Last year' },
];

const FUND_PALETTE = ['#0B3C91', '#1F6FE5', '#85B7EB', '#B5D4F4'];

const SERIES = [
  { key: 'adults', name: 'Adults', color: '#0B3C91' },
  { key: 'youth', name: 'Youth', color: '#BA7517' },
  { key: 'children', name: 'Children', color: '#1E9E64' },
  { key: 'online', name: 'Online', color: '#7F77DD' },
];

/** Stated in words beside the colour, because colour alone had no key. */
const GOAL_COLOUR = { 'on-track': 'var(--green)', behind: 'var(--amber)', attention: 'var(--red)' };

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}

function relative(days: number) {
  if (days > 0) return { text: `${days} day${days === 1 ? '' : 's'} over`, late: true };
  if (days === 0) return { text: 'Due today', late: false };
  const n = Math.abs(days);
  return { text: `Due in ${n} day${n === 1 ? '' : 's'}`, late: false };
}

export function DashboardPage() {
  const denied = (useLocation().state as { denied?: string } | null)?.denied;
  const { user, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [period, setPeriod] = useState<DashPeriod>('this-month');
  const [meeting, setMeeting] = useState('fri-worship');
  const { data, isLoading, isError } = useDashboardSummary(period, meeting);

  if (isLoading) return <div className="card">Loading…</div>;
  if (isError || !data) {
    return <div className="card">Could not load the dashboard. Please try again.</div>;
  }

  const firstName = (user?.name || '').split(' ')[0];
  const funds = (data.giving_by_fund ?? []).map((f, i) => ({
    label: f.fund, value: f.value, color: FUND_PALETTE[i % FUND_PALETTE.length],
  }));
  const att = data.attendance;
  const fu = data.follow_ups;

  return (
    <>
      {denied && (
        <p className="form-note" role="status">
          Your role does not include the page you tried to open, so you are back on the dashboard.
          If you need it, ask an administrator to check your role.
        </p>
      )}
      <div className="dash-hero">
        <div className="dash-hero-text">
          <h2>{greeting()}{firstName ? `, ${firstName}` : ''}</h2>
          <p>{data.banner.message}</p>
        </div>
        <div className="hero-actions">
          {/* Only jobs this person can do. A button that leads to a refusal
              is worse than no button. */}
          {hasPermission('attendance', 'create') && (
            <button className="btn-light-hero" onClick={() => navigate('/attendance/new')}>
              <Icon name="plus" size={15} /> New session
            </button>
          )}
          {hasPermission('members', 'create') && (
            <button className="btn-light-hero" onClick={() => navigate('/members/new')}>
              <Icon name="plus" size={15} /> Add member
            </button>
          )}
          {hasPermission('reports', 'create') && (
            <button className="btn-light-hero" onClick={() => navigate('/reports?tab=testimonies')}>
              <Icon name="plus" size={15} /> Add testimony
            </button>
          )}
        </div>
      </div>

      <div className="toolbar dash-period">
        <span className="muted">Showing {data.period.label}</span>
        <select className="selectbox" value={period} aria-label="Period"
          onChange={(e) => setPeriod(e.target.value as DashPeriod)}>
          {PERIODS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
      </div>

      <div className="statcard section-gap">
        <div className="statrow">
          {data.attendance_access && att && (
            <div className="stat stat-link" onClick={() => navigate('/attendance')}>
              <div className="stat-top-row">
                <span className="ic-badge sm blue"><Icon name="check" size={17} /></span>
                {att.target ? (
                  <span className={`badge ${att.latest / att.target >= 0.8 ? 'green' : 'amber'}`}>
                    {Math.round((att.latest / att.target) * 100)}% of target
                  </span>
                ) : null}
              </div>
              <div className="label">{att.meeting_name}, latest</div>
              <div className="value">{att.latest}</div>
              <div className="stat-hint">{att.target ? `Target ${att.target}` : 'No target set'}</div>
            </div>
          )}
          {data.finance_access && (
            <div className="stat stat-link" onClick={() => navigate('/finance')}>
              <div className="stat-top-row">
                <span className="ic-badge sm green"><Icon name="coin" size={17} /></span>
                {data.giving_change_pct != null && (
                  data.giving_change_pct === 0
                    ? <span className="badge gray">No change</span>
                    : <span className={`badge ${data.giving_change_pct > 0 ? 'green' : 'red'}`}>
                        {data.giving_change_pct > 0 ? 'Up' : 'Down'} {Math.abs(data.giving_change_pct)}%
                      </span>
                )}
              </div>
              <div className="label">Giving, {data.period.label}</div>
              <div className="value">{fmt(data.giving_total ?? 0)}</div>
              <div className="stat-hint">
                {data.giving_previous ? `Previously ${fmt(data.giving_previous)}` : 'No earlier figure'}
              </div>
            </div>
          )}
          {data.newcomers_access && (
            <div className="stat stat-link" onClick={() => navigate('/newcomers')}>
              <div className="stat-top-row">
                <span className="ic-badge sm amber"><Icon name="userplus" size={17} /></span>
                {fu && fu.overdue + fu.this_week > 0 && (
                  <span className={`badge ${fu.overdue ? 'red' : 'amber'}`}>
                    {fu.overdue + fu.this_week} due
                  </span>
                )}
              </div>
              <div className="label">Newcomers in the pipeline</div>
              <div className="value">{data.newcomers_in_pipeline ?? 0}</div>
              <div className="stat-hint">{data.newcomers_registered ?? 0} new in this period</div>
            </div>
          )}
          {data.finance_access && (
            <div className="stat stat-link" onClick={() => navigate('/finance')}>
              <div className="stat-top-row">
                <span className="ic-badge sm blue"><Icon name="coin" size={17} /></span>
              </div>
              <div className="label">Net, {data.period.label}</div>
              <div className="value"
                style={{ color: (data.net_total ?? 0) >= 0 ? 'var(--green)' : 'var(--red)' }}>
                {fmt(data.net_total ?? 0)}
              </div>
              <div className="stat-hint">After {fmt(data.expense_total ?? 0)} expenses</div>
            </div>
          )}
        </div>
      </div>

      <div className="grid g2 section-gap">
        {data.finance_access && (
          <div className="card">
            <h3>Giving by fund</h3>
            <p className="card-sub">{data.period.label}. Total {fmt(data.giving_total ?? 0)}.</p>
            {funds.length
              ? <DonutChart data={funds} size={128} showCentreTotal={false} />
              : <div className="empty">No giving recorded for this period.</div>}
            <a className="card-link-hint" onClick={() => navigate('/finance')}>
              Go to Giving and Finance →
            </a>
          </div>
        )}

        {data.attendance_access && att && (
          <div className="card">
            <div className="toolbar" style={{ marginBottom: 4 }}>
              <h3 style={{ flex: 'none' }}>Attendance</h3>
              <select className="selectbox" value={meeting} aria-label="Which meeting"
                style={{ width: 'auto', minWidth: 210 }}
                onChange={(e) => setMeeting(e.target.value)}>
                {(data.meetings ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
            </div>
            <p className="card-sub">
              {data.period.label}. Average {att.average}{att.target ? `, target ${att.target}` : ''}.
            </p>
            <GroupedBars
              groups={att.trend.map((t) => ({ label: t.date.slice(5), values: t as any }))}
              series={SERIES} />
            <a className="card-link-hint" onClick={() => navigate('/attendance')}>
              Go to Attendance →
            </a>
          </div>
        )}
      </div>

      <div className="grid g2 section-gap">
        {data.newcomers_access && fu && (
          <div className="card">
            <div className="toolbar" style={{ marginBottom: 12 }}>
              <h3 style={{ flex: 'none' }}>Follow-ups due</h3>
              {fu.overdue
                ? <span className="badge red">{fu.overdue} overdue</span>
                : <span className="badge green">None overdue</span>}
            </div>
            <div className="fu-counts">
              <div className="fu-count red"><b>{fu.overdue}</b><span>Overdue</span></div>
              <div className="fu-count amber"><b>{fu.this_week}</b><span>This week</span></div>
              <div className="fu-count plain"><b>{fu.later}</b><span>Later</span></div>
            </div>
            {fu.urgent.length ? fu.urgent.map((t) => {
              const r = relative(t.days);
              return (
                <div className="fu-row" key={`${t.newcomer_id}-${t.text}`}
                  onClick={() => navigate(`/newcomers/${t.newcomer_id}`)}>
                  <span className={`av-sm ${r.late ? 'red' : 'amber'}`}>{t.newcomer_name.charAt(0)}</span>
                  <div className="fu-main">
                    <b>{t.newcomer_name}</b>
                    <span className="muted">{t.text}</span>
                  </div>
                  <span className={`fu-when ${r.late ? 'late' : ''}`}>{r.text}</span>
                </div>
              );
            }) : <div className="empty">Nothing outstanding.</div>}
            <a className="card-link-hint" onClick={() => navigate('/newcomers?tab=followup')}>
              See all {fu.overdue + fu.this_week + fu.later} →
            </a>
          </div>
        )}

        {data.goals_access && (
          <div className="card">
            <h3>Short-term goals</h3>
            <p className="card-sub">Green on track, amber behind, red needs attention.</p>
            <div className="goalgrid">
              {(data.short_term_goals ?? []).map((g) => (
                <div className="goalrow" key={g.id}>
                  <div className="ring-wrap" style={{ width: 54, height: 54, flex: 'none' }}>
                    <RingChart pct={g.pct} size={54} stroke={6} color={GOAL_COLOUR[g.status]} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div className="goal-name">{g.name}</div>
                    <div className="muted" style={{
                      fontSize: '.78rem', color: g.not_started ? 'var(--red)' : undefined }}>
                      {g.not_started ? 'Not started' : `${g.current} of ${g.target}`}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <a className="card-link-hint" onClick={() => navigate('/goals')}>See all goals →</a>
          </div>
        )}
      </div>

      <div className="grid g2 section-gap">
        {data.testimonies_access && data.testimonies && (
          <div className="card">
            <div className="toolbar" style={{ marginBottom: 12 }}>
              <h3 style={{ flex: 'none' }}>Recent testimonies</h3>
              <span className="muted" style={{ fontSize: '.78rem' }}>{data.testimonies.count} recorded</span>
            </div>
            {data.testimonies.recent.length ? data.testimonies.recent.map((t, i) => (
              <div className={`quote${i === 0 ? ' accent' : ''}`} key={i}>
                <p>{t.text}</p>
                <span className="muted">{t.by || 'Unnamed'} · {t.date}</span>
              </div>
            )) : <div className="empty">None recorded yet.</div>}
            <a className="card-link-hint" onClick={() => navigate('/reports?tab=testimonies')}>
              Add a testimony →
            </a>
          </div>
        )}

        {data.newcomers_access && data.new_members && (
          <div className="card">
            <div className="toolbar" style={{ marginBottom: 12 }}>
              <h3 style={{ flex: 'none' }}>New members</h3>
              <span className="badge green">{data.new_members.count} added</span>
            </div>
            {data.new_members.recent.length ? data.new_members.recent.map((m) => (
              <div className="fu-row" key={m.id} onClick={() => navigate(`/members/${m.id}`)}>
                <span className="av-sm blue">
                  {m.name.split(' ').map((w) => w[0]).join('').slice(0, 2)}
                </span>
                <div className="fu-main">
                  <b>{m.name}</b>
                  <span className="muted">{m.how || 'Arrival not recorded'}</span>
                </div>
              </div>
            )) : <div className="empty">Nobody added in this period.</div>}
            <a className="card-link-hint" onClick={() => navigate('/members')}>Go to Members →</a>
          </div>
        )}
      </div>

      <div className="grid g2 section-gap">
        {data.newcomers_access && data.enquiries_waiting && (
          <div className="card">
            <div className="toolbar" style={{ marginBottom: 12 }}>
              <h3 style={{ flex: 'none' }}>Enquiries awaiting a reply</h3>
              {data.enquiries_waiting.count
                ? <span className="badge amber">{data.enquiries_waiting.count} waiting</span>
                : <span className="badge green">All answered</span>}
            </div>
            {data.enquiries_waiting.oldest.length ? data.enquiries_waiting.oldest.map((e) => (
              <div className="fu-row" key={e.id} onClick={() => navigate(`/enquiries/${e.id}`)}>
                <span className="av-sm amber">{e.name.charAt(0)}</span>
                <div className="fu-main">
                  <b>{e.name}</b>
                  <span className="muted">{e.source || 'Source not recorded'}</span>
                </div>
                <span className="fu-when">{e.days}d</span>
              </div>
            )) : <div className="empty">Nothing waiting.</div>}
            <a className="card-link-hint" onClick={() => navigate('/enquiries')}>
              Open the enquiries board →
            </a>
          </div>
        )}

        {data.attendance_access && data.fellowships && (
          <div className="card">
            <h3>House fellowships</h3>
            <p className="card-sub">
              {data.period.label}, {data.fellowships.meetings_held} meeting
              {data.fellowships.meetings_held === 1 ? '' : 's'} held
            </p>
            {data.fellowships.groups.some((g) => g.attendance) ? data.fellowships.groups.map((g) => {
              const max = Math.max(1, ...data.fellowships!.groups.map((x) => x.attendance));
              return (
                <div className="hbar-row" key={g.name}>
                  <span className="hbar-label">{g.name}</span>
                  <span className="hbar-track">
                    <span className="hbar-fill" style={{ width: `${(g.attendance / max) * 100}%` }} />
                  </span>
                  <span className="hbar-val">{g.attendance}</span>
                </div>
              );
            }) : <div className="empty">No fellowship meetings in this period.</div>}
            <div className="hcf-foot">
              <span className="muted">Offering collected</span>
              <b>{fmt(data.fellowships.offering)}</b>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
