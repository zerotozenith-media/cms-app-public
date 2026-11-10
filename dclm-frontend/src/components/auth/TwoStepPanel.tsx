import { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { apiClient } from '../../api/client';
import { Button } from '../ui/Button';

/**
 * The second step of signing in (two-step sign-in, approved 10 November
 * 2026, the same screens as DCLM Canada): type the 6-digit number from the
 * authenticator app, or set the app up when the role requires it, then keep
 * the backup codes. Used after the password and after a password reset.
 */
export interface TwoStepChallenge {
  two_step: 'code' | 'setup'; ticket: string; remember_days: number; secret?: string; otpauth?: string;
}
const DEVICE_KEY = 'dclm.twoStepDevice';
export function rememberedDevice(): string | undefined {
  try { return localStorage.getItem(DEVICE_KEY) || undefined; } catch { return undefined; }
}

function Shield() {
  return (
    <div className="auth-icon auth-icon-blue" aria-hidden="true">
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M9 12l2 2 4-4" />
      </svg>
    </div>
  );
}

export function BackupCodes({ codes, onDone, doneLabel = 'I have kept them, continue' }: { codes: string[]; onDone: () => void; doneLabel?: string }) {
  function print() {
    const w = window.open('', '_blank', 'width=480,height=640');
    if (!w) return;
    w.document.write(`<html><head><title>DCLM Bahrain backup codes</title></head><body style="font-family:Arial,Helvetica,sans-serif;padding:24px">
      <h2>DCLM Bahrain, two-step sign-in backup codes</h2><p>Each code works once. Keep them safe, not on the same phone.</p>
      <pre style="font-size:18px;line-height:1.8">${codes.join('\n')}</pre></body></html>`);
    w.document.close(); w.focus(); w.print();
  }
  return (
    <>
      <Shield />
      <h1>Keep your backup codes</h1>
      <p className="auth-sub">If you lose your phone, type one of these instead of the number. Each code works once. Print them or keep them somewhere safe, not on the same phone.</p>
      <div className="ts-codes">{codes.map((c) => <span key={c}>{c}</span>)}</div>
      <button type="button" className="btn ghost ts-wide" onClick={print}>Print or save the codes</button>
      <Button type="button" style={{ width: '100%', justifyContent: 'center', marginTop: 8 }} onClick={onDone}>{doneLabel}</Button>
    </>
  );
}

export function TwoStepPanel({ challenge, onSignedIn, onBack }: {
  challenge: TwoStepChallenge;
  onSignedIn: (data: any) => void;
  onBack: () => void;
}) {
  const [code, setCode] = useState('');
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState('');
  const [expired, setExpired] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<any>(null);
  const setup = challenge.two_step === 'setup';

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(''); setBusy(true);
    try {
      const r = await apiClient.post('/auth/two-step/', { ticket: challenge.ticket, code, remember });
      if (r.data.device) { try { localStorage.setItem(DEVICE_KEY, r.data.device); } catch { /* private mode */ } }
      if (r.data.backup_codes) setDone(r.data); else onSignedIn(r.data);
    } catch (err: any) {
      const d = err?.response?.data;
      setExpired(Boolean(d?.expired));
      setError(!err?.response ? 'Cannot reach the server. Check your internet connection and try again.' : d?.detail ?? 'The number is not right. Try again.');
    } finally { setBusy(false); }
  }

  if (done) return <BackupCodes codes={done.backup_codes} onDone={() => onSignedIn(done)} />;
  return (
    <>
      <Shield />
      <h1>{setup ? 'Set up two-step sign-in' : 'Enter your code'}</h1>
      {setup ? (
        <>
          <p className="auth-sub">Your role needs a second step when you sign in, to keep church records safe. You set it up once.</p>
          <ol className="ts-steps">
            <li>Install a free authenticator app on your phone, for example Microsoft Authenticator or Google Authenticator.</li>
            <li>In the app, add an account and scan this code.</li>
            <li>Type the 6-digit number the app shows, then press Turn on.</li>
          </ol>
          <div className="ts-qr"><QRCodeSVG value={challenge.otpauth!} size={150} /></div>
          <p className="auth-note">Can't scan? In the app, choose to enter a key and type <span className="ts-key">{challenge.secret}</span></p>
        </>
      ) : (
        <p className="auth-sub">Type the 6-digit number your authenticator app shows for DCLM Bahrain. It changes every 30 seconds.</p>
      )}
      <form onSubmit={submit}>
        <div className="field">
          <label htmlFor="ts-code">{setup ? '6-digit number from the app' : '6-digit number, or a backup code'}</label>
          <input id="ts-code" inputMode={setup ? 'numeric' : 'text'} autoComplete="one-time-code" autoFocus value={code} onChange={(e) => setCode(e.target.value)} required />
        </div>
        {challenge.remember_days > 0 && (
          <label className="ts-check"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            <span>On this device, ask again after {challenge.remember_days} days. Leave this unticked on a shared computer.</span></label>
        )}
        {error && <p className="auth-error" role="alert">{error}</p>}
        {expired ? (
          <Button type="button" style={{ width: '100%', justifyContent: 'center' }} onClick={onBack}>Sign in again</Button>
        ) : (
          <Button type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
            {busy ? 'Checking…' : setup ? 'Turn on' : 'Sign in'}
          </Button>
        )}
      </form>
      {!setup && <p className="auth-note">Can't use your phone? Type one of your backup codes. Each works once. No codes left? Ask an Administrator to reset your two-step sign-in.</p>}
      <div style={{ marginTop: 14 }}><button type="button" className="auth-link" onClick={onBack}>← Back to sign in</button></div>
    </>
  );
}
