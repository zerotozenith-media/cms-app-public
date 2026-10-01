import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { AuthIcon, AuthLayout } from '../components/auth/AuthLayout';

/** F18: choose a new password from the emailed link, then go straight in. */
export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const uid = params.get('uid') ?? '';
  const token = params.get('token') ?? '';
  const { startSession } = useAuth();
  const navigate = useNavigate();
  const [state, setState] = useState<'checking' | 'ready' | 'bad'>('checking');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [again, setAgain] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Check the link first, so an expired one says so before anything is typed.
    apiClient.post('/auth/password-reset/confirm/', { uid, token, check_only: true })
      .then((r) => { setEmail(r.data.email); setState('ready'); })
      .catch(() => setState('bad'));
  }, [uid, token]);

  const rules = [
    { label: 'At least 10 characters', met: password.length >= 10 },
    { label: 'Not only numbers', met: password.length > 0 && !/^\d+$/.test(password) },
    { label: 'Both passwords match', met: password.length > 0 && password === again },
  ];

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await apiClient.post('/auth/password-reset/confirm/', { uid, token, password, password_again: again });
      startSession(r.data);
      navigate('/', { replace: true });
    } catch (err: any) {
      const d = err?.response?.data ?? {};
      setError(d.password?.[0] ?? d.password_again?.[0] ?? d.detail ?? 'Could not save the new password.');
      if (err?.response?.status === 400 && d.detail) setState('bad');
    } finally {
      setBusy(false);
    }
  }

  if (state === 'checking') {
    return <AuthLayout><p className="auth-sub">Checking your link…</p></AuthLayout>;
  }
  if (state === 'bad') {
    return (
      <AuthLayout>
        <AuthIcon name="key" />
        <h1>This link has expired</h1>
        <p className="auth-sub">Reset links work once and for one hour. Ask for a new one and use it straight away.</p>
        <Link to="/forgot-password" className="btn" style={{ display: 'block', justifyContent: 'center' }}>Send a new link</Link>
        <div style={{ marginTop: 16 }}><Link className="auth-link" to="/login">← Back to sign in</Link></div>
      </AuthLayout>
    );
  }
  return (
    <AuthLayout>
      <AuthIcon name="lock" />
      <h1>Choose a new password</h1>
      <p className="auth-sub">For {email}</p>
      <form onSubmit={save}>
        <div className="field">
          <label htmlFor="new-password">New password</label>
          <input id="new-password" type="password" autoComplete="new-password" value={password}
            onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="new-password-again">New password again</label>
          <input id="new-password-again" type="password" autoComplete="new-password" value={again}
            onChange={(e) => setAgain(e.target.value)} required />
        </div>
        <div className="auth-rules">
          {rules.map((r) => (
            <div key={r.label} className={`auth-rule${r.met ? ' met' : ''}`}>{r.met ? '✓' : '○'} {r.label}</div>
          ))}
          <div className="auth-rule">Not a common password, and not too like your name or email</div>
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <Button type="submit" disabled={busy || !rules.every((r) => r.met)} style={{ width: '100%', justifyContent: 'center' }}>
          {busy ? 'Saving…' : 'Save and sign in'}
        </Button>
      </form>
    </AuthLayout>
  );
}
