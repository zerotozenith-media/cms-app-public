import { useState, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ServiceNote } from '../components/service/ServiceBadge';
import { AlertBanner } from '../components/dashboard/AlertBanner';
import { Skeleton } from '../components/ui/Skeleton';
import { HelpMark } from '../components/ui/HelpMark';
import { useOutstanding } from '../api/notifications';
import { useViewingLocation } from '../api/viewing';
import { exportTable, useDashboard, type Dashboard, type PeriodChoice, type PeriodKey } from '../api/dashboard2';
import { AttendanceLine, BarRows, C, CountBars, Donut, Legend, MoneyBars, bhd, monLong, whole } from '../components/charts/DashCharts';

/**
 * The dashboard (redesign approved 10 November 2026, the same design as
 * DCLM Canada): greeting with the period and small quick-action buttons, a
 * one-line "Needs your attention", the cards, the charts, the lists, then
 * the summary table for the person: by location, by meeting, or by month
 * for Accounts. A Follow-up shepherd sees their own follow-ups and no
 * money or table. Every part shows only when the role can see its area.
 */
const CHIPS: { key: PeriodKey; label: string }[] = [
  { key: 'this_month', label: 'This month' },
  { key: 'this_quarter', label: 'Quarter' },
  { key: 'this_year', label: 'Year to date' },
  { key: 'last_year', label: 'Last year' },
];
const MORE: { key: PeriodKey; label: string }[] = [
  { key: 'last_month', label: 'Last month' },
  { key: 'year', label: 'Choose a year' },
  { key: 'range', label: 'Choose a range of months' },
];
const thisMonthKey = () => new Date().toLocaleDateString('en-CA').slice(0, 7);

/** Short names for the tags on the attention line on a tablet or phone. A computer shows the full words. */
const TAGS: Record<string, [string, string]> = {
  reasons: ['', 'reasons'],
  'newcomer-follow-ups': ['', 'overdue'],
  'member-follow-ups': ['', 'overdue'],
  review: ['', 'review'],
  enquiries: ['', 'enquiries'],
  sessions: ['', 'sessions'],
  'followup-messages': ['', 'messages'],
  'no-receipt': ['', 'no receipt'],
};

const ACTIONS: Record<string, [string, string]> = {
  new_session: ['New session', '/attendance/new'],
  add_member: ['Add member', '/members/new'],
  add_newcomer: ['Add newcomer', '/newcomers/manual'],
  add_testimony: ['Add testimony', '/reports?tab=testimonies'],
  record_giving: ['Record giving', '/finance'],
  add_expense: ['Add expense', '/finance'],
  month_end: ['Month-end', '/finance?tab=monthend'],
};

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
}
function longDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
}
function shortDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

function Card({ title, sub, children, action, className }: { title: ReactNode; sub?: ReactNode; children: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <section className={`card dv-card${className ? ` ${className}` : ''}`}>
      <div className="dv-card-head"><div><h3>{title}</h3>{sub && <div className="dv-sub">{sub}</div>}</div>{action}</div>
      {children}
    </section>
  );
}

/** "▲ 12% vs 1 to 10 October 2026". A rise in expenses is shown in red. */
/** "1 to 10 October" rather than "1 to 10 October 2026" when it is this year. */
function cmpLabel(c: { label: string } | null | undefined) {
  if (!c) return '';
  const y = ` ${new Date().getFullYear()}`;
  return c.label.endsWith(y) && !c.label.slice(0, -y.length).match(/\d{4}/) ? c.label.slice(0, -y.length) : c.label;
}

function Change({ now, before, compare, rising = 'good' }: { now: number | null | undefined; before: number | null | undefined; compare: Dashboard['compare']; rising?: 'good' | 'bad' }) {
  if (!compare) return <span className="muted">No earlier figure to compare</span>;
  if (now == null || before == null || Number(before) === 0) return <span className="muted">Nothing recorded {/^\d/.test(compare.label) ? 'from' : 'in'} {cmpLabel(compare)}</span>;
  const d = ((Number(now) - Number(before)) / Math.abs(Number(before))) * 100;
  const up = d >= 0;
  const good = rising === 'good' ? up : !up;
  return <><span className={good ? 'dv-up' : 'dv-down'}>{up ? '▲' : '▼'} {Math.abs(d).toFixed(0)}%</span> vs {cmpLabel(compare)}</>;
}

function Pct({ v }: { v: number | null | undefined }) {
  if (v == null) return <span className="muted">No earlier figure</span>;
  return <span className={v >= 0 ? 'dv-up' : 'dv-down'}>{v >= 0 ? '▲' : '▼'} {Math.abs(v)}%</span>;
}

interface Kpi { label: string; value: string; sub: ReactNode; sub2?: ReactNode; tip?: string; to?: string }

function cardsFor(d: Dashboard): Kpi[] {
  const c = d.cards;
  const out: Kpi[] = [];
  const att = c.attendance && {
    label: 'Average Friday Worship', value: c.attendance.value === null ? 'Not recorded' : whole(c.attendance.value),
    sub: <Change now={c.attendance.value} before={c.attendance.before} compare={d.compare} />,
    sub2: c.attendance.latest ? `Latest Friday: ${whole(c.attendance.latest.total)} on ${shortDate(c.attendance.latest.date)}` : undefined,
    tip: 'dashAttendance', to: '/attendance',
  };
  const membership = c.membership && {
    label: 'On track for membership', value: `${c.membership.on_track} on track`,
    sub: `${c.membership.ready === 0 ? 'None' : c.membership.ready} ready to propose`,
    sub2: `Of ${c.membership.pipeline} ${d.kind === 'worker' ? 'of your newcomers' : 'newcomers being followed up'}`,
    tip: 'dashMembership', to: '/newcomers',
  };
  const giving = c.giving && { label: 'Giving', value: `BHD ${bhd(c.giving.value)}`, sub: <Change now={Number(c.giving.value)} before={c.giving.before === null ? null : Number(c.giving.before)} compare={d.compare} />, to: '/finance' };
  const expenses = c.expenses && { label: 'Expenses', value: `BHD ${bhd(c.expenses.value)}`, sub: <Change now={Number(c.expenses.value)} before={c.expenses.before === null ? null : Number(c.expenses.before)} compare={d.compare} rising="bad" />, to: '/finance' };
  const net = c.net && { label: 'Net', value: `${Number(c.net.value) < 0 ? '-' : ''}BHD ${bhd(Math.abs(Number(c.net.value)))}`, sub: 'Giving less expenses', tip: 'dashNet' };
  if (d.kind === 'worker') {
    if (c.my_tasks) out.push({ label: 'My follow-ups due', value: whole(c.my_tasks.due), to: '/follow-up',
      sub: <>{c.my_tasks.overdue > 0 ? <span className="dv-down">{c.my_tasks.overdue} overdue</span> : 'None overdue'} · {c.my_tasks.today} due today</> });
    if (c.my_newcomers !== undefined) out.push({ label: 'My newcomers', value: whole(c.my_newcomers), sub: 'Being followed up by you', to: '/follow-up' });
    if (membership) out.push({ ...membership, sub2: `Of your ${c.membership!.pipeline} newcomers` });
    if (att) out.push(att);
    return out;
  }
  if (d.kind === 'accounts') {
    if (c.cash) out.push({ label: 'Cash in hand', value: `BHD ${bhd(c.cash.value)}`, tip: 'dashCash', to: '/finance?tab=monthend',
      sub: c.cash.by_location.length > 1 ? c.cash.by_location.map((l) => `${l.name} ${l.value === null ? 'not set up' : `BHD ${bhd(l.value)}`}`).join(' · ') : 'Today, from Month-end balance' });
    if (giving) out.push(giving);
    if (expenses) out.push(expenses);
    if (net) out.push(net);
    if (c.month_end) {
      const w = c.month_end.waiting, o = c.month_end.open;
      const oldest = [...o].sort((a, b) => a.month.localeCompare(b.month))[0];
      out.push({ label: 'Month-end', tip: 'dashMonthEnd', to: '/finance?tab=monthend',
        value: w.length ? `${w.length} waiting` : o.length ? `${o.length} to balance` : 'Up to date',
        sub: w.length ? `${w[0].location}, ${monLong(w[0].month)}: waiting for approval${w.length > 1 ? ` and ${w.length - 1} more` : ''}`
          : oldest ? `Oldest: ${oldest.location}, ${monLong(oldest.month)}` : 'Every past month is closed',
        sub2: w.length && o.length ? `${o.length} more to balance` : undefined });
    }
    return out;
  }
  for (const k of [att, giving, expenses, net, membership]) if (k) out.push(k);
  return out;
}

function AttentionLine() {
  const { data } = useOutstanding();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const items = data?.items ?? [];
  if (!data) return null;
  if (!items.length) return <section className="dv-att dv-att-none"><span className="dv-ok" aria-hidden="true">✓</span>Nothing needs your attention.</section>;
  const sorted = [...items].sort((a, b) => Number(b.level === 'overdue') - Number(a.level === 'overdue'));
  const total = items.reduce((s, a) => s + a.count, 0);
  return (
    <section className="dv-att">
      <h3><span className="dv-long">Needs your attention</span><span className="dv-short">Attention</span><em>{whole(total)}</em></h3>
      {sorted.slice(0, 2).map((a, i) => (
        <button key={a.key} type="button" className={`dv-pill ${a.level === 'overdue' ? 'red' : 'amber'}${i > 0 ? ' second' : ''}`} onClick={() => navigate(a.link)} title={a.label}>
          <b>{whole(a.count)}</b>
          <span className="dv-long">{a.label.replace(/^\d+\s/, '')}</span>
          <span className="dv-short">{TAGS[a.key]?.[1] ?? 'to check'}</span>
        </button>
      ))}
      <button type="button" className="dv-more" aria-expanded={open} onClick={() => setOpen(!open)}>
        {open ? 'Hide ▴' : <>{items.length > 2 && <span className="dv-long">+{items.length - 2} more · </span>}View all ▾</>}
      </button>
      {open && (
        <div className="dv-att-list">
          {sorted.map((a) => (
            <button key={a.key} type="button" className="dv-att-row" onClick={() => navigate(a.link)}>
              <span className={`att-dot ${a.level === 'overdue' ? 'red' : 'amber'}`} aria-hidden="true" />
              <span>{a.label}</span><span className="dv-go">Open ›</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function MoneyCard({ d }: { d: Dashboard }) {
  const [table, setTable] = useState(false);
  const rows = d.charts.money_by_month!;
  const any = rows.some((r) => Number(r.giving) || Number(r.expenses));
  const ly = rows.some((r) => r.giving_last_year !== null);
  const first = rows[0]?.month, last = rows[rows.length - 1]?.month;
  const span = first === last ? monLong(first) : `${monLong(first).split(' ')[0]}${first.slice(0, 4) !== last.slice(0, 4) ? ` ${first.slice(0, 4)}` : ''} to ${monLong(last)}`;
  return (
    <Card title="Giving and expenses, by month" className="dv-hero"
      sub={`${span}, in BHD.${rows[rows.length - 1]?.so_far ? ` ${monLong(last).split(' ')[0]} so far.` : ''}${first <= d.records_start ? ` Records start in ${monLong(d.records_start)}.` : ''}`}
      action={any && <button type="button" className="btn sm ghost" onClick={() => setTable(!table)}>{table ? 'Chart view' : 'Table view'}</button>}>
      {!any ? <div className="empty">Nothing recorded for these months yet.</div> : table ? (
        <div className="table-wrap">
          <table className="dv-table">
            <thead><tr><th>Month</th><th className="num">Giving (BHD)</th><th className="num">Expenses (BHD)</th><th className="num">Net (BHD)</th>{ly && <th className="num">Giving a year earlier (BHD)</th>}</tr></thead>
            <tbody>{[...rows].reverse().map((r) => (
              <tr key={r.month}><td>{monLong(r.month)}{r.so_far ? ' (so far)' : ''}</td><td className="num">{bhd(r.giving)}</td><td className="num">{bhd(r.expenses)}</td>
                <td className="num"><b>{bhd(Number(r.giving) - Number(r.expenses))}</b></td>{ly && <td className="num">{r.giving_last_year === null ? <span className="muted">No records</span> : bhd(r.giving_last_year)}</td>}</tr>
            ))}</tbody>
          </table>
        </div>
      ) : <>
        <MoneyBars rows={rows} />
        <Legend items={[{ label: 'Giving', color: C.blue }, { label: 'Expenses', color: C.orange }, ...(ly ? [{ label: 'Giving a year earlier', kind: 'tick' as const }] : [])]} />
      </>}
    </Card>
  );
}

/**
 * Giving by fund (13 November 2026, Option A): each fund's amount beside
 * its share, with a total. With giving in one fund only, a full ring says
 * nothing, so the fund and its amount are shown instead. Beside the money
 * chart on a wide screen ("alone") it fills the card's height.
 */
function FundsCard({ d, alone }: { d: Dashboard; alone?: boolean }) {
  const parts = (d.charts.funds ?? []).map((f) => ({ label: f.fund, amount: f.amount }));
  const total = parts.reduce((a, p) => a + p.amount, 0);
  const given = parts.filter((p) => p.amount > 0);
  const one = given.length === 1 ? given[0] : null;
  return (
    <Card title="Giving by fund" sub={`In BHD, ${d.period.span}`}
      className={`dv-mix dv-funds${alone ? ' alone' : ''}`}>
      <div className="dv-mix-body">
        {total <= 0 ? <div className="empty">No giving recorded for this period yet.</div>
          : one ? (
            <div className="dv-one">
              <div className="dv-one-name"><i style={{ background: C.blue }} />{one.label}</div>
              <div className="dv-one-fig">BHD {bhd(one.amount)}</div>
              <div className="dv-one-note">All giving in this period went to one fund, so there is no split to show.</div>
            </div>
          ) : <Donut parts={parts} centre={total >= 10000 ? `${(total / 1000).toFixed(1)}k` : whole(total)} sub="BHD" amounts />}
      </div>
    </Card>
  );
}

function CategoriesCard({ d }: { d: Dashboard }) {
  const c = d.charts.expense_categories!;
  const max = Math.max(1, ...c.top.map((r) => r.amount));
  return (
    <Card title="Top expense categories" sub={`In BHD, ${d.period.span}`}>
      {!c.top.length ? <div className="empty">No expenses recorded for this period yet.</div> : <>
        <BarRows rows={c.top.map((r) => ({ label: r.category, value: r.amount, max, figure: bhd(r.amount), color: C.orange }))} />
        {c.more > 0 && <div className="dv-foot">and {c.more} more {c.more === 1 ? 'category' : 'categories'} in Giving & Finance</div>}
      </>}
    </Card>
  );
}

function AttendanceCard({ d, meeting, setMeeting }: { d: Dashboard; meeting: string; setMeeting: (m: string) => void }) {
  const a = d.charts.attendance_by_month!;
  const any = a.months.some((m) => m.attendance !== null);
  return (
    <Card title="Average attendance, by month" className="dv-attendance"
      sub="Average per service each month. A shaded gap means nothing was recorded that month."
      action={<select className="dv-select2" aria-label="Meeting" value={meeting || a.meeting} onChange={(e) => setMeeting(e.target.value)}>
        {a.meetings.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
      </select>}>
      {!any ? <div className="empty">No attendance recorded for these months yet.</div> : <AttendanceLine months={a.months} today={d.today} />}
    </Card>
  );
}

function NewcomersCard({ d }: { d: Dashboard }) {
  const rows = (d.charts.newcomers_by_month ?? []).map((r) => ({ month: r.month, n: r.newcomers }));
  const mine = d.kind === 'worker';
  const stats: [ReactNode, string][] = [[whole(rows.reduce((a, r) => a + r.n, 0)), `newcomers in these months${d.scope ? ` at ${d.scope.name}` : ''}`]];
  if (mine && d.cards.my_tasks) {
    stats.push([whole(d.cards.my_newcomers), 'being followed up by you'], [whole(d.cards.my_tasks.due), 'your follow-ups due']);
  } else if (d.newcomer_stats) {
    stats.push([whole(d.newcomer_stats.pipeline), 'being followed up'], [whole(d.newcomer_stats.follow_ups_due), 'follow-ups due']);
  }
  return (
    <Card title="Newcomers and follow-ups" sub="First-time visitors, by the month they first came">
      {rows.some((r) => r.n > 0) ? <CountBars rows={rows} label="Newcomers by month" /> : <div className="empty">No newcomers recorded in these months.</div>}
      <div className="dv-stats">{stats.map(([v, k]) => <span key={k}><b>{v}</b>{k}</span>)}</div>
    </Card>
  );
}

function GoalsCard({ d }: { d: Dashboard }) {
  const navigate = useNavigate();
  const goals = d.goals ?? [];
  const label = { achieved: 'Achieved', on_track: 'On track', behind: 'Behind', not_started: 'Not started' };
  return (
    <Card title="Goals" sub="Short-term goals. Blue from 60% of the target, yellow below.">
      {!goals.length ? <div className="empty">No short-term goals yet.</div> : (
        <div className="dv-goals">{goals.map((g) => (
          <button type="button" key={g.id} className="dv-goal" onClick={() => navigate('/goals')}>
            <div className="dv-goal-top"><span>{g.name}</span><b>{g.pct}%</b></div>
            <div className="dv-track"><i style={{ width: `${Math.max(2, Math.min(100, g.pct))}%`, background: g.status === 'achieved' ? C.green : g.pct >= 60 ? C.blue : C.yellow }} /></div>
            <div className="dv-goal-state">{whole(g.current)} of {whole(g.target)} · {label[g.status]}</div>
          </button>
        ))}</div>
      )}
    </Card>
  );
}

function FollowUpsCard({ d }: { d: Dashboard }) {
  const navigate = useNavigate();
  const rows = d.follow_up_people ?? [];
  const due = (t: { days_overdue: number; due_date: string }) => {
    if (t.days_overdue) return [`${t.days_overdue} day${t.days_overdue === 1 ? '' : 's'} overdue`, 'red'];
    return t.due_date === d.today ? ['Due today', 'amber'] : [`Due ${shortDate(t.due_date)}`, 'blue'];
  };
  return (
    <Card title={d.kind === 'worker' ? 'My follow-ups due' : 'Follow-ups due'}>
      {!rows.length ? <div className="empty">Nothing outstanding.</div> : (
        <div className="kv-list">{rows.map((t) => {
          const [w, c] = due(t);
          return (
            <button type="button" className="kv-row" key={`${t.link}-${t.task}`} onClick={() => navigate(t.link)}>
              <span><b>{t.name}</b><br /><span className="muted">{t.task}</span></span><span className={`badge ${c}`}>{w}</span>
            </button>
          );
        })}</div>
      )}
      <button type="button" className="dv-link" onClick={() => navigate(d.kind === 'worker' ? '/follow-up' : '/newcomers/follow-up')}>See all follow-ups ›</button>
    </Card>
  );
}

function FellowshipsCard({ d }: { d: Dashboard }) {
  const f = d.fellowships!;
  const max = Math.max(1, ...f.groups.map((g) => g.attendance));
  return (
    <Card title="House fellowships" sub={`${d.period.span}, ${f.meetings_held} meeting${f.meetings_held === 1 ? '' : 's'} held`}>
      {f.groups.some((g) => g.attendance) ? <BarRows rows={f.groups.map((g) => ({ label: g.name, value: g.attendance, max, figure: whole(g.attendance) }))} />
        : <div className="empty">No fellowship meetings in this period.</div>}
      <div className="dv-also"><div><span>Offering collected</span><b>BHD {bhd(f.offering)}</b></div></div>
    </Card>
  );
}

function TestimoniesCard({ d, canAdd }: { d: Dashboard; canAdd: boolean }) {
  const navigate = useNavigate();
  const t = d.testimonies!;
  return (
    <Card title="Recent testimonies" sub={`${t.count} recorded`}>
      {t.latest ? <div className="dv-quote">"{t.latest.text}"<small>{[t.latest.by, t.latest.service, shortDate(t.latest.date)].filter(Boolean).join(' · ')}</small></div>
        : <div className="empty">No testimonies recorded yet.</div>}
      <button type="button" className="dv-link" onClick={() => navigate('/reports?tab=testimonies')}>{canAdd ? 'Add a testimony ›' : 'See testimonies ›'}</button>
    </Card>
  );
}

function PeopleCard({ d }: { d: Dashboard }) {
  const navigate = useNavigate();
  const m = d.new_members?.recent ?? [];
  const e = d.kind === 'worker' ? [] : d.enquiries?.oldest ?? [];
  return (
    <Card title={e.length || (d.enquiries && d.kind !== 'worker') ? 'New members and enquiries' : 'New members'}>
      {!m.length && !e.length ? <div className="empty">No new members or waiting enquiries in this period.</div> : (
        <div className="kv-list">
          {m.map((x) => <button type="button" className="kv-row" key={`m${x.id}`} onClick={() => navigate(`/members/${x.id}`)}><span>{x.name} · New member</span><span className="badge blue">Joined {shortDate(x.joined)}</span></button>)}
          {e.map((x) => <button type="button" className="kv-row" key={`e${x.id}`} onClick={() => navigate(`/enquiries/${x.id}`)}><span>{x.name}{x.source ? ` · Enquiry from ${x.source}` : ' · Enquiry'}</span><span className="badge red">Waiting {x.days} day{x.days === 1 ? '' : 's'}</span></button>)}
        </div>
      )}
    </Card>
  );
}

interface Col { head: ReactNode; cell: ReactNode; text?: string; num?: boolean; phone?: boolean; tablet?: boolean }

function SummaryTable({ d, choice }: { d: Dashboard; choice: PeriodChoice }) {
  const navigate = useNavigate();
  const [, setViewing] = useViewingLocation();
  const [menu, setMenu] = useState(false);
  const [openRow, setOpenRow] = useState<string | null>(null);
  const [locTab, setLocTab] = useState<string | null>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const t = d.table!;
  const changeHead = d.compare ? <>Change from {cmpLabel(d.compare)}<HelpMark topic="dashChange" /></> : 'Change';
  let title = '', sub = '', rows: { key: string; cols: Col[]; foot?: boolean }[] = [];
  let tabs: ReactNode = null;
  const meBadge = (s: string) => <span className={`badge ${s === 'Closed' ? 'green' : s === 'Waiting for approval' ? 'amber' : 'gray'}`}>{s}</span>;

  if (t.by === 'location') {
    title = 'By location'; sub = `${d.period.span}, all locations. Tap a location to see its dashboard.`;
    const make = (r: typeof t.rows[number], foot = false): Col[] => {
      const cols: Col[] = [{ head: 'Location', cell: foot ? <b>{r.name}</b> : <button type="button" className="linkish dv-name" onClick={() => setViewing(r.id!)}>{r.name} ›</button>, text: r.name }];
      if (t.columns.attendance) cols.push({ head: 'Average Friday Worship', cell: r.attendance == null ? <span className="muted">Not recorded</span> : whole(r.attendance), num: true, phone: true },
        { head: changeHead, cell: <Pct v={r.attendance_change} />, text: d.compare ? `Change from ${cmpLabel(d.compare)}` : 'Change', phone: true, tablet: true });
      if (t.columns.newcomers) cols.push({ head: 'Newcomers', cell: whole(r.newcomers), num: true, phone: true, tablet: true });
      if (t.columns.money) cols.push({ head: 'Giving (BHD)', cell: bhd(r.giving), num: true, phone: true }, { head: 'Expenses (BHD)', cell: bhd(r.expenses), num: true, phone: true },
        { head: 'Net (BHD)', cell: <b>{bhd(r.net)}</b>, num: true }, { head: `Month-end, ${monLong(t.month_end_month)}`, cell: foot ? '' : meBadge(r.month_end!) });
      return cols;
    };
    rows = [...t.rows.map((r) => ({ key: r.id!, cols: make(r) })), { key: 'total', cols: make(t.total, true), foot: true }];
  } else if (t.by === 'meeting') {
    title = `By meeting, ${t.location}`; sub = `${d.period.span}. Tap a meeting to open Attendance.`;
    rows = t.rows.map((r) => {
      const cols: Col[] = [
        { head: 'Meeting', cell: <button type="button" className="linkish dv-name" onClick={() => navigate('/attendance')}>{r.name}</button>, text: r.name },
        { head: 'Held', cell: whole(r.held), num: true, phone: true, tablet: true },
        { head: 'Not filled in', cell: r.not_filled ? <span className="badge red">{r.not_filled} not filled in</span> : <span className="badge green">All filled in</span> },
        { head: 'Average attendance', cell: r.attendance == null ? <span className="muted">Not recorded</span> : whole(r.attendance), num: true, phone: true },
        { head: changeHead, cell: <Pct v={r.attendance_change} />, text: d.compare ? `Change from ${cmpLabel(d.compare)}` : 'Change', phone: true, tablet: true },
      ];
      if (t.columns.money) cols.push({ head: 'Offering (BHD)', cell: r.offering == null ? <span className="muted">Not collected</span> : bhd(r.offering), num: true, phone: true });
      return { key: r.id, cols };
    });
  } else {
    const loc = t.locations.find((l) => l.id === locTab) ?? t.locations[0];
    if (loc) {
      title = `By month, ${loc.name}`; sub = 'From the month balancing starts. Latest first. A closed month\'s counted cash is the next month\'s start.';
      if (t.locations.length > 1) tabs = (
        <div className="dv-tabs" role="tablist" aria-label="Location">
          {t.locations.map((l) => <button key={l.id} type="button" role="tab" aria-selected={l.id === loc.id} className={l.id === loc.id ? 'on' : ''} onClick={() => { setLocTab(l.id); setOpenRow(null); }}>{l.name}</button>)}
        </div>);
      rows = loc.rows.map((r) => ({ key: r.month, cols: [
        { head: 'Month', cell: <b className="dv-name">{monLong(r.month)}{r.so_far ? ' (so far)' : ''}</b>, text: monLong(r.month) },
        { head: 'Cash at start (BHD)', cell: bhd(r.start), num: true, phone: true, tablet: true },
        { head: 'Giving (BHD)', cell: bhd(r.giving), num: true, phone: true },
        { head: 'Expenses (BHD)', cell: bhd(r.expenses), num: true, phone: true },
        { head: 'Remitted (BHD)', cell: bhd(r.remitted), num: true, phone: true, tablet: true },
        { head: 'Net (BHD)', cell: <b>{bhd(r.net)}</b>, num: true },
        { head: <>Cash in hand (BHD)<HelpMark topic="dashCashInHand" /></>, text: 'Cash in hand (BHD)', cell: bhd(r.cash), num: true, phone: true },
        { head: 'Month-end', cell: meBadge(r.status_label) },
      ] }));
    }
  }

  async function doExport(output: 'excel' | 'pdf') {
    setMenu(false); setErr(''); setBusy(true);
    try {
      await exportTable(choice, output, t.by === 'month' ? (locTab ?? t.locations[0]?.id) : undefined);
    } catch (e: any) {
      let msg = 'The file could not be made. Check your connection and try again.';
      try { const blob = e?.response?.data as Blob | undefined; const j = blob ? JSON.parse(await blob.text()) : {}; msg = [j.detail, j.why, j.fix].filter(Boolean).join(' '); } catch { /* not JSON */ }
      setErr(msg);
    } finally { setBusy(false); }
  }

  const head = rows[0]?.cols ?? [];
  const cls = (c: Col) => `${c.num ? 'num' : ''}${c.phone ? ' dv-ph-hide' : ''}${c.tablet ? ' dv-tab-hide' : ''}`;
  return (
    <Card title={title} sub={sub} className="dv-table-card" action={
      <div className="dv-table-actions">
        <div className="tb-pop">
          <button type="button" className="btn sm ghost" aria-expanded={menu} disabled={busy} onClick={() => setMenu(!menu)}>{busy ? 'Preparing…' : 'Export ▾'}</button>
          {menu && (
            <div className="tb-menu" role="menu">
              <button type="button" role="menuitem" className="tb-menu-item" onClick={() => doExport('excel')}>Excel</button>
              <button type="button" role="menuitem" className="tb-menu-item" onClick={() => doExport('pdf')}>PDF</button>
            </div>
          )}
        </div>
      </div>}>
      {tabs}
      {err && <p className="form-error" role="alert">{err}</p>}
      {!rows.length ? <div className="empty">Nothing to show for this period yet.</div> : (
        <div className="table-wrap dv-table-wrap">
          <table className="dv-table">
            <thead><tr>{head.map((c, i) => <th key={i} className={cls(c)}>{c.head}</th>)}</tr></thead>
            <tbody>{rows.map((r) => {
              const isOpen = openRow === r.key;
              return [
                <tr key={r.key} className={`dv-tr${r.foot ? ' dv-foot-row' : ''}`} aria-expanded={isOpen}
                  onClick={(e) => { if (window.innerWidth <= 600 && !(e.target as HTMLElement).closest('a,button')) setOpenRow(isOpen ? null : r.key); }}>
                  {r.cols.map((c, j) => <td key={j} className={cls(c)}>{c.cell}</td>)}
                </tr>,
                isOpen && (
                  <tr key={`${r.key}-more`} className="dv-tr-more"><td colSpan={r.cols.length}>
                    <div className="dv-more-grid">{r.cols.filter((c) => c.phone).map((c, j) => <div key={j}><span>{c.text ?? c.head}</span><b>{c.cell}</b></div>)}</div>
                  </td></tr>
                ),
              ];
            })}</tbody>
          </table>
          <div className="dv-ph-note">Tap a row to see all its columns.</div>
        </div>
      )}
    </Card>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const denied = (useLocation().state as { denied?: string } | null)?.denied;
  const [period, setPeriod] = useState<PeriodKey | undefined>(undefined);
  const [moreOpen, setMoreOpen] = useState(false);
  const [year, setYear] = useState(new Date().getFullYear());
  const [from, setFrom] = useState(thisMonthKey());
  const [to, setTo] = useState(thisMonthKey());
  const [meeting, setMeeting] = useState('');
  const rangeOk = /^\d{4}-\d{2}$/.test(from) && /^\d{4}-\d{2}$/.test(to) && from <= to;
  const choice: PeriodChoice = period === 'year' ? { period, year } : period === 'range' ? (rangeOk ? { period, from, to } : { period: 'this_month' }) : { period };
  const { data: d, isLoading, isError, error } = useDashboard(choice, meeting || undefined);

  if (isLoading && !d) return <Skeleton shape="dashboard" />;
  if (isError && !d) {
    const r = (error as any)?.response?.data ?? {};
    const msg = Object.values(r)[0];
    return (
      <div className="card" role="alert" style={{ maxWidth: 640 }}>
        <h3 style={{ marginBottom: 8 }}>The dashboard could not be shown.</h3>
        <p className="muted">{msg ? String(([] as unknown[]).concat(msg)[0]) : 'Check your connection and try again.'}</p>
        <button type="button" className="btn sm" onClick={() => { setPeriod('this_month'); }}>Show this month</button>
      </div>
    );
  }
  if (!d) return null;
  const current = period ?? d.period.key;
  const inMore = MORE.some((m) => m.key === current);
  const cards = cardsFor(d);
  const c = d.charts;
  const firstYear = Number(d.records_start.slice(0, 4));
  const years = Array.from({ length: new Date().getFullYear() - firstYear + 1 }, (_, i) => new Date().getFullYear() - i);
  const actions = d.actions.filter((a) => ACTIONS[a]);
  const worker = d.kind === 'worker';
  const people = [c.attendance_by_month, c.newcomers_by_month, d.goals].filter(Boolean).length;

  return (
    <div className="dash dv">
      <AlertBanner />
      {denied && (
        <p className="form-note" role="status">
          Your role does not include the page you tried to open, so you are back on the dashboard.
          If you need it, ask an administrator to check your role.
        </p>
      )}
      <div className="dv-head">
        <div className="dv-hello">
          <div className="muted">{longDate(d.today)} · {d.scope?.name ?? 'All locations'}{worker ? ' · My follow-ups' : ''}</div>
          <h2>{greeting()}{d.name ? `, ${d.name}` : ''}</h2>
        </div>
        <div className="dv-periods">
          <div className="dv-chips" role="group" aria-label="Period shown">
            {CHIPS.map((p) => [
              <button key={p.key} type="button" className={current === p.key ? 'on' : ''} aria-pressed={current === p.key} onClick={() => { setPeriod(p.key); setMoreOpen(false); }}>
                {p.label}
              </button>,
              p.key === 'this_year' && <span key="help" className="dv-chip-help"><HelpMark topic="dashPeriods" /></span>,
            ])}
            <div className="tb-pop">
              <button type="button" className={inMore ? 'on' : ''} aria-expanded={moreOpen} onClick={() => setMoreOpen(!moreOpen)}>
                {inMore ? MORE.find((m) => m.key === current)!.label : 'More'} ▾
              </button>
              {moreOpen && (
                <div className="tb-menu" role="menu">
                  {MORE.map((m) => <button key={m.key} type="button" role="menuitem" className="tb-menu-item" onClick={() => { setPeriod(m.key); setMoreOpen(false); }}>{m.label}</button>)}
                </div>
              )}
            </div>
          </div>
          {current === 'year' && <select className="selectbox dv-select" aria-label="Year" value={year} onChange={(e) => setYear(Number(e.target.value))}>{years.map((y) => <option key={y} value={y}>{y}</option>)}</select>}
          {current === 'range' && <div className="dv-range">
            <input type="month" aria-label="First month" min={d.records_start} max={thisMonthKey()} value={from} onChange={(e) => setFrom(e.target.value)} />
            <span>to</span>
            <input type="month" aria-label="Last month" min={d.records_start} max={thisMonthKey()} value={to} onChange={(e) => setTo(e.target.value)} />
            <HelpMark topic="dashRange" />
            {!rangeOk && <span className="form-error">Choose the first month, then a last month that is not before it.</span>}
          </div>}
        </div>
        {actions.length > 0 && (
          <div className="dv-actions" aria-label="Quick actions">
            {actions.map((a) => <button key={a} type="button" className="dv-action" onClick={() => navigate(ACTIONS[a][1])}>{ACTIONS[a][0]}</button>)}
          </div>
        )}
      </div>
      <ServiceNote />

      <AttentionLine />

      {cards.length > 0 && (
        <div className={`dv-cards n${cards.length}`}>
          {cards.map((k) => (
            <div key={k.label} className={`card dv-kpi${k.to ? ' dv-kpi-link' : ''}`} onClick={(e) => { if (k.to && !(e.target as HTMLElement).closest('button')) navigate(k.to); }}>
              <div className="dv-kpi-label">{k.label}{k.tip && <HelpMark topic={k.tip} />}</div>
              <div className="dv-kpi-value">{k.value}</div>
              <div className="dv-kpi-sub">{k.sub}</div>
              {k.sub2 && <div className="dv-kpi-sub muted">{k.sub2}</div>}
            </div>
          ))}
        </div>
      )}

      {c.money_by_month && (
        <div className="dv-grid dv-g-hero">
          <MoneyCard d={d} />
          {c.expense_categories ? (
            <div className="dv-stack"><FundsCard d={d} /><CategoriesCard d={d} /></div>
          ) : <FundsCard d={d} alone />}
        </div>
      )}

      {worker ? (
        <div className={`dv-grid dv-g3 n${1 + (c.attendance_by_month ? 1 : 0) + (c.newcomers_by_month ? 1 : 0)}`}>
          <FollowUpsCard d={d} />
          {c.attendance_by_month && <AttendanceCard d={d} meeting={meeting} setMeeting={setMeeting} />}
          {c.newcomers_by_month && <NewcomersCard d={d} />}
        </div>
      ) : people > 0 && (
        <div className={`dv-grid dv-g3 n${people}`}>
          {c.attendance_by_month && <AttendanceCard d={d} meeting={meeting} setMeeting={setMeeting} />}
          {c.newcomers_by_month && <NewcomersCard d={d} />}
          {d.goals && <GoalsCard d={d} />}
        </div>
      )}

      {!worker && (d.follow_up_people || d.fellowships) && (
        <div className="dv-grid dv-g2">
          {d.follow_up_people && <FollowUpsCard d={d} />}
          {d.fellowships && <FellowshipsCard d={d} />}
        </div>
      )}
      {(d.testimonies || d.new_members) && (
        <div className="dv-grid dv-g2">
          {d.testimonies && <TestimoniesCard d={d} canAdd={d.actions.includes('add_testimony')} />}
          {d.new_members && <PeopleCard d={d} />}
        </div>
      )}

      {d.table && <SummaryTable d={d} choice={choice} />}
    </div>
  );
}
