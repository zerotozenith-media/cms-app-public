import { useState } from 'react';
import { useAuditLog, useLoginAttempts } from '../../api/admin';
import { Pagination } from '../../components/ui/Pagination';
import { Badge } from '../../components/ui/Badge';

export function AuditLogTab() {
  const [entityFilter, setEntityFilter] = useState('');
  const [sort, setSort] = useState('-timestamp');
  const [page, setPage] = useState(1);
  const pageSize = 8;
  const { data: auditLog } = useAuditLog({
    entity_type: entityFilter || undefined, ordering: sort, page, page_size: pageSize,
  });

  const [loginPage, setLoginPage] = useState(1);
  const { data: loginAttempts } = useLoginAttempts({ ordering: '-timestamp', page: loginPage, page_size: 8 });

  const auditTotalPages = auditLog ? Math.max(1, Math.ceil(auditLog.count / pageSize)) : 1;
  const loginTotalPages = loginAttempts ? Math.max(1, Math.ceil(loginAttempts.count / 8)) : 1;

  return (
    <>
      <div className="card">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>Audit log</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              className="search" placeholder="Filter by entity type..." value={entityFilter}
              onChange={(e) => { setEntityFilter(e.target.value); setPage(1); }}
            />
            <select className="selectbox" value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="-timestamp">Newest first</option>
              <option value="timestamp">Oldest first</option>
            </select>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Entity</th><th>Details</th></tr></thead>
            <tbody>
              {(auditLog?.results ?? []).map((a) => (
                <tr key={a.id}>
                  <td data-label="Time">{a.timestamp.slice(0, 19).replace('T', ' ')}</td>
                  <td data-label="User">{a.user_name_snapshot}</td>
                  <td data-label="Action">{a.action}</td>
                  <td data-label="Entity">{a.entity_type}: <b>{a.entity_name}</b></td>
                  <td data-label="Details">{a.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {auditLog?.results.length === 0 && <div className="empty">No audit entries match this filter.</div>}
        </div>
        {auditLog && (
          <Pagination page={page} totalPages={auditTotalPages} totalCount={auditLog.count} pageSize={pageSize} onPageChange={setPage} />
        )}
      </div>

      <div className="card section-gap">
        <h3>Login security</h3>
        <p className="muted" style={{ fontSize: '.84rem', marginBottom: 10 }}>
          Every login attempt, successful or not: honeypot triggers, rate-limited submissions, and account
          lockouts are all recorded here for review.
        </p>
        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead><tr><th>Time</th><th>Email attempted</th><th>IP</th><th>Result</th></tr></thead>
            <tbody>
              {(loginAttempts?.results ?? []).map((a) => (
                <tr key={a.id}>
                  <td data-label="Time">{a.timestamp.slice(0, 19).replace('T', ' ')}</td>
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
