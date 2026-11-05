import { useEffect, useState } from 'react';
import { useAuditChoices, useAuditLog, useLoginAttempts } from '../../api/admin';
import { Pagination } from '../../components/ui/Pagination';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { HelpMark } from '../../components/ui/HelpMark';

/** Bahrain time, readable: "Wed 14 Oct 2026, 9:12 pm". */
export function bahrainTime(iso: string) {
  const d = new Date(iso);
  const date = d.toLocaleDateString('en-GB', { timeZone: 'Asia/Bahrain', weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  const time = d.toLocaleTimeString('en-US', { timeZone: 'Asia/Bahrain', hour: 'numeric', minute: '2-digit', hour12: true }).toLowerCase();
  return `${date}, ${time}`;
}

/**
 * The Audit Log, with search and filters (5 November 2026). It could
 * only be paged through, eight entries at a time, with one box that
 * needed the exact type name.
 */
export function AuditLogTab() {
  const [text, setText] = useState('');
  const [search, setSearch] = useState('');
  const [entityType, setEntityType] = useState('');
  const [who, setWho] = useState('');
  const [action, setAction] = useState('');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [sort, setSort] = useState('-timestamp');
  const [page, setPage] = useState(1);
  const pageSize = 25;
  // Search once typing pauses, not on every key.
  useEffect(() => { const t = setTimeout(() => { setSearch(text.trim()); setPage(1); }, 350); return () => clearTimeout(t); }, [text]);
  const { data: choices } = useAuditChoices();
  const { data: auditLog, isFetching } = useAuditLog({
    search: search || undefined, entity_type: entityType || undefined, who: who || undefined, action: action || undefined,
    date_from: from || undefined, date_to: to || undefined, ordering: sort, page, page_size: pageSize,
  });
  const any = !!(text || entityType || who || action || from || to);
  const set = (f: (v: string) => void) => (e: { target: { value: string } }) => { f(e.target.value); setPage(1); };
  const clear = () => { setText(''); setSearch(''); setEntityType(''); setWho(''); setAction(''); setFrom(''); setTo(''); setPage(1); };
  const badDates = !!(from && to && from > to);

  const [loginPage, setLoginPage] = useState(1);
  const { data: loginAttempts } = useLoginAttempts({ ordering: '-timestamp', page: loginPage, page_size: 8 });

  const auditTotalPages = auditLog ? Math.max(1, Math.ceil(auditLog.count / pageSize)) : 1;
  const loginTotalPages = loginAttempts ? Math.max(1, Math.ceil(loginAttempts.count / 8)) : 1;

  return (
    <>
      <div className="card">
        <div className="toolbar">
          <div style={{ flex: 'none' }}>
            <h3 style={{ margin: 0 }}>Audit log<HelpMark topic="auditFilters" /></h3>
            <div className="muted" style={{ fontSize: '.8rem' }} role="status">
              {auditLog ? `${auditLog.count.toLocaleString()} ${auditLog.count === 1 ? 'entry' : 'entries'}${any ? ' match' : ''}` : 'Loading'}
            </div>
          </div>
          <select className="selectbox" aria-label="Order" value={sort} onChange={set(setSort)}>
            <option value="-timestamp">Newest first</option>
            <option value="timestamp">Oldest first</option>
          </select>
        </div>
        <label htmlFor="audit-search" className="sr-only">Search the audit log</label>
        <input id="audit-search" type="search" className="search audit-search" placeholder="Search, e.g. Monday Bible Study 14"
          value={text} onChange={(e) => setText(e.target.value)} />
        <div className="audit-filters">
          <div className="field"><label htmlFor="audit-type">Type</label>
            <select id="audit-type" value={entityType} onChange={set(setEntityType)}>
              <option value="">Any type</option>
              {(choices?.entity_types ?? []).map((t) => <option key={t}>{t}</option>)}
            </select></div>
          <div className="field"><label htmlFor="audit-who">Person</label>
            <select id="audit-who" value={who} onChange={set(setWho)}>
              <option value="">Anyone</option>
              {(choices?.people ?? []).map((t) => <option key={t}>{t}</option>)}
            </select></div>
          <div className="field"><label htmlFor="audit-action">Action</label>
            <select id="audit-action" value={action} onChange={set(setAction)}>
              <option value="">Any action</option>
              {(choices?.actions ?? []).map((t) => <option key={t}>{t}</option>)}
            </select></div>
          <div className="field"><label htmlFor="audit-from">From</label><input id="audit-from" type="date" value={from} onChange={set(setFrom)} /></div>
          <div className="field"><label htmlFor="audit-to">To</label><input id="audit-to" type="date" value={to} onChange={set(setTo)} /></div>
        </div>
        {badDates && <p className="form-error" role="alert">From is after To, so nothing can match. Swap the dates.</p>}
        {any && <button type="button" className="linkish" onClick={clear}>Clear filters</button>}
        <div style={{ overflowX: 'auto', opacity: isFetching ? 0.6 : 1 }}>
          <table className="cardtable">
            <thead><tr><th>When (Bahrain time)</th><th>Who</th><th>Action</th><th>What</th><th>Details</th></tr></thead>
            <tbody>
              {(auditLog?.results ?? []).map((a) => (
                <tr key={a.id}>
                  <td data-label="When">{bahrainTime(a.timestamp)}</td>
                  <td data-label="Who">{a.user_name_snapshot}</td>
                  <td data-label="Action">{a.action}</td>
                  <td data-label="What">{a.entity_type}: <b>{a.entity_name}</b></td>
                  <td data-label="Details">{a.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!auditLog && <Skeleton shape="rows" rows={5} />}
          {auditLog?.results.length === 0 && (
            <div className="empty">{any ? 'Nothing matches these filters. Remove one, or press Clear filters.' : 'Nothing has been recorded yet.'}</div>
          )}
        </div>
        {auditLog && auditLog.count > pageSize && (
          <Pagination page={page} totalPages={auditTotalPages} totalCount={auditLog.count} pageSize={pageSize} onPageChange={setPage} />
        )}
      </div>

      <div className="card section-gap">
        <h3>Sign-in attempts</h3>
        <p className="muted" style={{ fontSize: '.84rem', marginBottom: 10 }}>
          Every login attempt, successful or not: honeypot triggers, rate-limited submissions, and account
          lockouts are all recorded here for review.
        </p>
        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead><tr><th>When (Bahrain time)</th><th>Email attempted</th><th>IP</th><th>Result</th></tr></thead>
            <tbody>
              {(loginAttempts?.results ?? []).map((a) => (
                <tr key={a.id}>
                  <td data-label="Time">{bahrainTime(a.timestamp)}</td>
                  <td data-label="Email attempted">{a.email_attempted}</td>
                  <td data-label="IP">{a.ip_address}</td>
                  <td data-label="Result">
                    {a.successful ? <Badge color="green">Success</Badge> : <Badge color="red">{a.reason}</Badge>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {loginAttempts && (
          <Pagination page={loginPage} totalPages={loginTotalPages} totalCount={loginAttempts.count} pageSize={8} onPageChange={setLoginPage} />
        )}
      </div>
    </>
  );
}
