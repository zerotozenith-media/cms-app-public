import { ServiceNote } from '../components/service/ServiceBadge';
/**
 * The dashboard.
 *
 * One period control drives every card, so they cannot disagree about
 * which month they describe. The banner names what needs doing rather
 * than restating that this is the dashboard. Each card appears only when
 * the viewer may see its module.
 */
import { Skeleton } from '../components/ui/Skeleton';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useOutstanding } from '../api/notifications';
import { useAuth } from '../context/AuthContext';
import { useDashboardSummary } from '../api/dashboard';
import { ByLocationCard } from '../components/dashboard/ByLocationCard';
import { RingChart } from '../components/charts/RingChart';
import { TestimonySlider } from '../components/dashboard/TestimonySlider';
import { ChartTipBox, useChartTip } from '../components/charts/ChartTip';
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
// Same rule as the Goals page: green from 90% of target, blue from 60%, red below.
const ringColour = (pct: number) => (pct >= 90 ? 'var(--green)' : pct >= 60 ? 'var(--blue)' : 'var(--red)');

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}


function ringLines(g: { current: number; target: number; pct: number; not_started?: boolean }) {
  return g.not_started ? ['Not started'] : [`${g.current} of ${g.target}`, `${g.pct}% of the target`];
}

function attLabel(t: { date: string }, grouping?: string) {
  const d = new Date(`${t.date}T00:00:00`);
  return grouping === 'month'
    ? d.toLocaleDateString('en-GB', { month: 'short' })
    : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

function dueText(t: { days_overdue: number; due_date: string }) {
  if (t.days_overdue) return `${t.days_overdue} day${t.days_overdue === 1 ? '' : 's'} overdue`;
  const d = new Date(`${t.due_date}T00:00:00`);
  const today = new Date(); today.setHours(0, 0, 0, 0);
  if (d.getTime() === today.getTime()) return 'Due today';
  return `Due ${d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })}`;
}

function todayLabel() {
  return new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
}

export function DashboardPage() {
  const { data: outstanding } = useOutstanding();
  const goalTip = useChartTip();
  const denied = (useLocation().state as { denied?: string } | null)?.denied;
  const { user, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [period, setPeriod] = useState<DashPeriod>('this-month');
  const [meeting, setMeeting] = useState('fri-worship');
  const [chartPeriod, setChartPeriod] = useState<DashPeriod>('this-year');
  const [attView, setAttView] = useState<'chart' | 'table'>('chart');
  const { data, isLoading, isError } = useDashboardSummary(period, meeting, chartPeriod);

  if (isLoading) return <Skeleton shape="dashboard" />;
  if (isError || !data) {
    return <div className="card">Could not load the dashboard. Please try again.</div>;
  }

  const firstName = (user?.name || '').split(' ')[0];
  // Only jobs this person can do. A button that leads to a refusal is worse
  // than no button. An odd last one spans the row.
  const actions = [
    { label: 'New session', to: '/attendance/new', ok: hasPermission('attendance', 'create') },
    { label: 'Add member', to: '/members/new', ok: hasPermission('members', 'create') },
    { label: 'Add newcomer', to: '/newcomers/manual', ok: hasPermission('newcomers', 'create') },
    { label: 'Add testimony', to: '/reports?tab=testimonies', ok: hasPermission('reports', 'create') },
    { label: 'Record giving', to: '/finance', ok: hasPermission('finance', 'create') },
  ].filter((a) => a.ok);
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
      {/* F5, option B: a plain greeting, what needs attention, and the
          buttons this person can use. The blue block repeated the menu's
          colour and left none to signal what matters. */}
      <div className="dash-greeting">
        <div className="muted dash-date">{todayLabel()}</div>
        <h2>{greeting()}{firstName ? `, ${firstName}` : ''}</h2>
      </div>
      <ServiceNote />
      <div className={`dash-top${actions.length ? '' : ' single'}`}>
        <div className="card dash-attention">
          <h3>Needs your attention</h3>
          {outstanding && outstanding.items.length > 0 ? (
            outstanding.items.map((it) => (
              <button key={it.key} className={`attn-row ${it.level}`} onClick={() => navigate(it.link)}>
                <span className="attn-dot" aria-hidden="true" />
                <span className="attn-label">{it.label}</span>
                <span className="attn-chev" aria-hidden="true">›</span>
              </button>
            ))
          ) : (
            <p className="attn-clear"><Icon name="check" size={16} /> Nothing needs your attention</p>
          )}
        </div>
        {actions.length > 0 && (
          <div className="card dash-actions">
            <h3>Quick actions</h3>
            <div className="qa-grid">
              {actions.map((a) => (
                <button key={a.label} className="qa-btn" onClick={() => navigate(a.to)}>
                  <Icon name="plus" size={14} /> {a.label}
                </button>
              ))}
            </div>
          </div>
        )}
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

      {data.by_location && <ByLocationCard rows={data.by_location} periodLabel={data.period.label} />}

      <div className="grid g2 section-gap">
        {data.finance_access && (
          <div className="card">
            <h3>Giving by fund</h3>
            <p className="card-sub">{data.period.label}.</p>
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
            <div className="toolbar" style={{ marginBottom: 8 }}>
              <h3 style={{ flex: 1 }}>Attendance</h3>
              <div className="viewtoggle" role="group" aria-label="Show as">
                <button className={attView === 'chart' ? 'on' : ''} onClick={() => setAttView('chart')}>Chart</button>
                <button className={attView === 'table' ? 'on' : ''} onClick={() => setAttView('table')}>Table</button>
              </div>
            </div>
            <div className="att-filters">
              <label>Service
                <select className="selectbox" value={meeting} onChange={(e) => setMeeting(e.target.value)}>
                  {(data.meetings ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </label>
              <label>Period
                <select className="selectbox" value={chartPeriod} onChange={(e) => setChartPeriod(e.target.value as DashPeriod)}>
                  {PERIODS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
                </select>
              </label>
            </div>
            <p className="card-sub">
              {att.period?.label ?? ''}. {att.grouping === 'month' ? 'Average per service each month. ' : ''}
              Average {att.average}{att.target ? `, target ${att.target}` : ''}.
            </p>
            {attView === 'chart' ? (
              <GroupedBars groups={att.trend.map((t) => ({ label: attLabel(t, att.grouping), values: t as any }))} series={SERIES} />
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="house-table">
                  <thead><tr><th>{att.grouping === 'month' ? 'Month' : 'Date'}</th><th>Adults</th><th>Youth</th><th>Children</th><th>Online</th><th>Total</th></tr></thead>
                  <tbody>
                    {att.trend.map((t) => (
                      <tr key={t.date}><td>{attLabel(t, att.grouping)}</td><td>{t.adults}</td><td>{t.youth}</td><td>{t.children}</td><td>{t.online}</td><td><b>{t.total}</b></td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <a className="card-link-hint" onClick={() => navigate('/attendance')}>
              Go to Attendance →
            </a>
          </div>
        )}
      </div>

      <div className="grid g2 section-gap">
        {data.newcomers_access && fu && (
          <div className="card">
            {/* F14: the people, most overdue first, members and newcomers
                together. The counts were already shown twice elsewhere. */}
            <h3 style={{ marginBottom: 8 }}>Follow-ups due</h3>
            {(data.follow_up_people ?? []).length ? (data.follow_up_people ?? []).map((t) => (
              <div className="fu-row" key={`${t.link}-${t.task}`} onClick={() => navigate(t.link)}>
                <span className={`av-sm ${t.days_overdue ? 'red' : 'amber'}`}>{t.name.charAt(0)}</span>
                <div className="fu-main">
                  <b>{t.name}</b>
                  <span className="muted">{t.task}</span>
                </div>
                <span className={`fu-when ${t.days_overdue ? 'late' : ''}`}>{dueText(t)}</span>
              </div>
            )) : <div className="empty">Nothing outstanding.</div>}
            <a className="card-link-hint" onClick={() => navigate('/newcomers/follow-up')}>
              See all follow-ups →
            </a>
          </div>
        )}

        {data.goals_access && (
          <div className="card">
            <h3>Short-term goals</h3>
            <p className="card-sub">Green from 90% of target, blue from 60%, red below.</p>
            {/* The tooltip wraps the grid, not its rows, so the rows keep the
                grid's spacing. Inside it they collapsed and the rings touched. */}
            <div className="chart-wrap" ref={goalTip.ref}
              onPointerLeave={(e) => { if (e.pointerType === 'mouse') goalTip.hide(); }}>
            <ChartTipBox tip={goalTip.tip} />
            <div className="goalgrid">
              {(data.short_term_goals ?? []).map((g) => (
                <div className="goalrow" key={g.id}>
                  <div className="ring-wrap" style={{ width: 54, height: 54, flex: 'none', cursor: 'pointer' }}
                    onPointerEnter={(e) => { if (e.pointerType === 'mouse') goalTip.show(e, String(g.id), g.name, ringLines(g)); }}
                    onClick={(e) => goalTip.show(e, String(g.id), g.name, ringLines(g))}>
                    <RingChart pct={g.pct} size={54} stroke={6} color={ringColour(g.pct)} />
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
            <TestimonySlider items={data.testimonies.recent} />
            {hasPermission('reports', 'create') && (
              <a className="card-link-hint" onClick={() => navigate('/reports?tab=testimonies')}>
                Add a testimony →
              </a>
            )}
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
