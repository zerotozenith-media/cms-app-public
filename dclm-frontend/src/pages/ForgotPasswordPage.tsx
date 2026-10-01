import { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Button } from '../components/ui/Button';
import { AuthIcon, AuthLayout } from '../components/auth/AuthLayout';

/** F18: ask for a reset link. The answer never reveals whether an account exists. */
export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send(e?: React.FormEvent) {
    e?.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await apiClient.post('/auth/password-reset/', { email });
      setSent(true);
    } catch (err: any) {
      setError(err?.response?.data?.email?.[0] ?? 'Could not send the link. Try again in a moment.');
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <AuthLayout>
        <AuthIcon name="mail" />
        <h1>Check your email</h1>
        <p className="auth-sub">
          If an account exists for <b>{email}</b>, a link to reset your password is on its way.
          It works once and expires in one hour.
        </p>
        <p className="auth-note">
          Nothing arrived? Check your junk folder, or{' '}
          <button type="button" className="auth-link" onClick={() => send()} disabled={busy}>send it again</button>.
        </p>
        <div style={{ marginTop: 14 }}><Link className="auth-link" to="/login">← Back to sign in</Link></div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <AuthIcon name="key" />
      <h1>Reset your password</h1>
      <p className="auth-sub">Enter the email you sign in with and we'll send you a link to choose a new password.</p>
      <form onSubmit={send}>
        <div className="field">
          <label htmlFor="reset-email">Email</label>
          <input id="reset-email" type="email" autoComplete="email" value={email}
            onChange={(e) => setEmail(e.target.value)} required />
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <Button type="submit" disabled={busy} style={{ width: '100%', justifyContent: 'center' }}>
          {busy ? 'Sending…' : 'Send reset link'}
        </Button>
      </form>
      <div style={{ marginTop: 16 }}><Link className="auth-link" to="/login">← Back to sign in</Link></div>
    </AuthLayout>
  );
}
