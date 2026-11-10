import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { QRCodeSVG } from 'qrcode.react';
import { apiClient } from '../../api/client';
import { Card } from '../ui/Card';
import { HelpMark } from '../ui/HelpMark';

/**
 * Two-step sign-in on My profile (10 November 2026): turn it on when the
 * role lets the person choose, make new backup codes, or turn it off. Not
 * shown when the role has it Off.
 */
interface Status { mode: 'required' | 'choose' | 'off'; on: boolean; on_since: string | null; backup_left: number }

function msg(e: any) {
  const d = e?.response?.data ?? {};
  return [d.detail, d.why, d.fix].filter(Boolean).join(' ') || 'That did not work. Check your connection and try again.';
}

export function TwoStepCard() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ['my-two-step'], queryFn: async () => (await apiClient.get<Status>('/auth/me/two-step/')).data });
  const [setup, setSetup] = useState<{ ticket: string; secret: string; otpauth: string } | null>(null);
  const [asking, setAsking] = useState<'off' | 'new_codes' | null>(null);
  const [code, setCode] = useState('');
  const [codes, setCodes] = useState<string[] | null>(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  if (!data || data.mode === 'off') return null;

  async function post(body: object) {
    setErr(''); setBusy(true);
    try { return (await apiClient.post('/auth/me/two-step/', body)).data; }
    catch (e) { setErr(msg(e)); return null; }
    finally { setBusy(false); }
  }
  async function start() { const r = await post({ action: 'start' }); if (r) { setSetup(r); setCode(''); } }
  async function confirm(e: React.FormEvent) {
    e.preventDefault();
    const r = await post({ action: 'confirm', ticket: setup!.ticket, code });
    if (r) { setSetup(null); setCodes(r.backup_codes); setCode(''); qc.invalidateQueries({ queryKey: ['my-two-step'] }); }
  }
  async function act(e: React.FormEvent) {
    e.preventDefault();
    const r = await post({ action: asking, code });
    if (r) {
      if (r.backup_codes) setCodes(r.backup_codes);
      setAsking(null); setCode('');
      qc.invalidateQueries({ queryKey: ['my-two-step'] });
    }
  }
  const since = data.on_since ? new Date(data.on_since).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) : '';

  return (
    <Card style={{ marginTop: 16 }}>
      <h3>Two-step sign-in<HelpMark topic="twoStep" /></h3>
      {codes ? (
        <>
          <p className="muted">Keep these backup codes somewhere safe, not on the same phone. Each works once instead of the number. They are shown only now.</p>
          <div className="ts-codes">{codes.map((c) => <span key={c}>{c}</span>)}</div>
          <button type="button" className="btn sm" onClick={() => setCodes(null)}>I have kept them</button>
        </>
      ) : setup ? (
        <form onSubmit={confirm}>
          <ol className="ts-steps">
            <li>Install a free authenticator app on your phone, for example Microsoft Authenticator or Google Authenticator.</li>
            <li>In the app, add an account and scan this code.</li>
            <li>Type the 6-digit number the app shows, then press Turn on.</li>
          </ol>
          <div className="ts-qr" style={{ justifyContent: 'flex-start' }}><QRCodeSVG value={setup.otpauth} size={150} /></div>
          <p className="muted" style={{ fontSize: '.85rem' }}>Can't scan? In the app, choose to enter a key and type <span className="ts-key">{setup.secret}</span></p>
          <div className="field" style={{ maxWidth: 260 }}><label htmlFor="ts-new">6-digit number from the app</label>
            <input id="ts-new" inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} required /></div>
          {err && <p className="form-error" role="alert">{err}</p>}
          <div className="form-actions-row">
            <button type="submit" className="btn sm" disabled={busy}>Turn on</button>
            <button type="button" className="btn sm ghost" onClick={() => { setSetup(null); setErr(''); }}>Cancel</button>
          </div>
        </form>
      ) : data.on ? (
        <>
          <p className="muted">On since {since}. {data.backup_left} backup code{data.backup_left === 1 ? '' : 's'} left.
            {data.mode === 'required' && ' Your role requires it, so it stays on.'}</p>
          {data.backup_left <= 2 && <p className="gender-warn" role="note">You have {data.backup_left === 0 ? 'no' : 'only ' + data.backup_left} backup codes left. Make new ones in case you lose your phone.</p>}
          {asking ? (
            <form onSubmit={act}>
              <div className="field" style={{ maxWidth: 260 }}><label htmlFor="ts-confirm">Type the number from the app, or a backup code</label>
                <input id="ts-confirm" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} required /></div>
              {err && <p className="form-error" role="alert">{err}</p>}
              <div className="form-actions-row">
                <button type="submit" className="btn sm" disabled={busy}>{asking === 'off' ? 'Turn off' : 'Make new backup codes'}</button>
                <button type="button" className="btn sm ghost" onClick={() => { setAsking(null); setErr(''); setCode(''); }}>Cancel</button>
              </div>
            </form>
          ) : (
            <div className="form-actions-row">
              <button type="button" className="btn sm outline" onClick={() => setAsking('new_codes')}>Make new backup codes</button>
              {data.mode === 'choose' && <button type="button" className="btn sm ghost" onClick={() => setAsking('off')}>Turn off</button>}
            </div>
          )}
          <p className="muted" style={{ fontSize: '.8rem' }}>New phone? Type a backup code at sign-in, then ask an Administrator to reset your two-step sign-in and set it up on the new phone.</p>
        </>
      ) : (
        <>
          <p className="muted">{data.mode === 'required' ? 'Your role requires it. You will set it up at your next sign-in, or now.' : 'Off. Turn it on so a stolen password alone cannot open your account.'}</p>
          {err && <p className="form-error" role="alert">{err}</p>}
          <button type="button" className="btn sm" onClick={start} disabled={busy}>Turn on</button>
        </>
      )}
    </Card>
  );
}
