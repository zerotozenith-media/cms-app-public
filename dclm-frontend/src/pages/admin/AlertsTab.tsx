import { useState } from 'react';
import { useSendAlert, useSentAlerts } from '../../api/alerts';
import { useRoles } from '../../api/admin';
import { useMyLocations } from '../../api/locations';
import { useAuth } from '../../context/AuthContext';
import { Skeleton } from '../../components/ui/Skeleton';

/** Admin, Alerts (Kay, October 2026): send a church announcement to phones
 *  and computers, and see what was sent. */
export function AlertsTab() {
  const { user: me, hasPermission } = useAuth();
  const canSend = hasPermission('admin', 'edit');
  const { data: sent } = useSentAlerts(true);
  const { data: roles } = useRoles();
  const { data: locations } = useMyLocations();
  const send = useSendAlert();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [audience, setAudience] = useState('everyone');
  const [location, setLocation] = useState('');
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(''); setErr('');
    if (!title.trim() || !body.trim()) { setErr('Give the alert a title and a message.'); return; }
    if (!confirm(`Send "${title.trim()}" now? It cannot be called back.`)) return;
    send.mutate({ title: title.trim(), body: body.trim(), audience, location: me?.location ? '' : location }, {
      onSuccess: (r) => {
        setMsg(r.people ? `Sent to ${r.people} ${r.people === 1 ? 'person' : 'people'} on ${r.devices} ${r.devices === 1 ? 'device' : 'devices'}.`
          : 'Saved, but nobody chosen has alerts on yet, so it reached nobody.');
        setTitle(''); setBody('');
      },
      onError: (x: any) => setErr(x?.response?.data?.detail || Object.values(x?.response?.data ?? {}).flat().join(' ') || 'The alert could not be sent. Try again.'),
    });
  }

  return (
    <div>
      {canSend && (
        <div className="card">
          <h3>Send an alert</h3>
          <p className="muted alerts-intro">
            Goes straight to the phones and computers of everyone chosen who has alerts turned on.
            {sent ? ` ${sent.people_with_alerts} ${sent.people_with_alerts === 1 ? 'person has' : 'people have'} alerts on.` : ''}
          </p>
          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="al-title">Title</label>
              <input id="al-title" value={title} maxLength={80} onChange={(e) => setTitle(e.target.value)} placeholder="For example: Ebenezer Night tonight" />
            </div>
            <div className="field">
              <label htmlFor="al-body">Message</label>
              <textarea id="al-body" rows={3} value={body} maxLength={300} onChange={(e) => setBody(e.target.value)} />
              <span className="muted field-note">{300 - body.length} characters left. Your name is added at the end.</span>
            </div>
            <div className="form-row">
              <div className="field">
                <label htmlFor="al-to">Send to</label>
                <select id="al-to" value={audience} onChange={(e) => setAudience(e.target.value)}>
                  <option value="everyone">Everyone</option>
                  <option value="shepherds">Shepherds and follow-up people</option>
                  {(roles ?? []).map((r) => <option key={r.id} value={`role-${r.id}`}>Everyone with the {r.name} role</option>)}
                </select>
              </div>
              {!me?.location && (
                <div className="field">
                  <label htmlFor="al-loc">Location</label>
                  <select id="al-loc" value={location} onChange={(e) => setLocation(e.target.value)}>
                    <option value="">All locations</option>
                    {(locations ?? []).map((l: any) => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                </div>
              )}
            </div>
            <div className="form-actions-row">
              <button className="btn sm" type="submit" disabled={send.isPending}>{send.isPending ? 'Sending…' : 'Send alert'}</button>
              <span className="muted alerts-msg">It is kept below and in the audit log.</span>
            </div>
            {msg && <p className="alerts-msg" role="status"><b>{msg}</b></p>}
            {err && <p className="form-error" role="alert">{err}</p>}
          </form>
        </div>
      )}

      <div className="card section-gap">
        <h3>Sent alerts</h3>
        {!sent ? <Skeleton shape="rows" rows={3} /> : sent.results.length === 0 ? (
          <div className="empty">No alerts sent yet.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="cardtable">
              <thead><tr><th>When</th><th>Alert</th><th>To</th><th>Reached</th></tr></thead>
              <tbody>
                {sent.results.map((a) => (
                  <tr key={a.id}>
                    <td data-label="When">{new Date(a.created_at).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}</td>
                    <td data-label="Alert"><b>{a.title}</b><div className="muted" style={{ fontSize: '.8rem' }}>{a.body}</div><div className="muted" style={{ fontSize: '.75rem' }}>By {a.sent_by}</div></td>
                    <td data-label="To">{a.audience}{a.location !== 'All locations' ? `, ${a.location}` : ''}</td>
                    <td data-label="Reached">{a.people} {a.people === 1 ? 'person' : 'people'}, {a.devices} {a.devices === 1 ? 'device' : 'devices'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
