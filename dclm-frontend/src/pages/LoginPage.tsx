import { useState, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { AuthLayout } from '../components/auth/AuthLayout';

/**
 * A real login form , deliberately NOT the demo's "click your account"
 * list. The demo's login was an explicit, stated mock ("no password
 * required for this prototype"); Batch 1.4 built genuine email/password
 * authentication with hashing, honeypot detection, and rate limiting,
 * so this needs to be a real form that actually exercises those
 * server-side checks, not carry the mock pattern forward.
 */
export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [website, setWebsite] = useState(''); // honeypot , real users never see or fill this
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const formLoadedAt = useRef(new Date().toISOString());

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setWarning(false);
    setSubmitting(true);
    try {
      await login(email, password, { website, form_loaded_at: formLoadedAt.current });
      const from = (location.state as { from?: string })?.from || '/';
      navigate(from, { replace: true });
    } catch (err: any) {
      const data = err?.response?.data;
      setWarning(Boolean(data?.warning));
      if (err?.response?.status === 429) {
        // The server says how long to wait.
        setError(data?.detail ?? 'Too many attempts. Please wait a few minutes and try again.');
      } else {
        // On the attempt before a lock the server adds a warning.
        setError(data?.detail ?? 'Invalid email or password.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout>
        <h1>Welcome back</h1>
        <p className="auth-sub">Sign in with the email your account was created with.</p>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {/* Honeypot: hidden from real users via CSS, not just visually
              tucked away , a bot reading the DOM still sees a normal-
              looking field and may fill it, which the backend rejects on. */}
          <div style={{ position: 'absolute', left: '-9999px', width: 1, height: 1, overflow: 'hidden' }} aria-hidden="true">
            <label htmlFor="website">Website</label>
            <input
              id="website"
              name="website"
              type="text"
              tabIndex={-1}
              autoComplete="off"
              value={website}
              onChange={(e) => setWebsite(e.target.value)}
            />
          </div>

          {error && (warning
            ? <div className="auth-warning" role="alert">{error}</div>
            : <p className="auth-error" role="alert">{error}</p>)}

          <Button type="submit" disabled={submitting} style={{ width: '100%', justifyContent: 'center' }}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        <div style={{ marginTop: 16 }}><Link className="auth-link" to="/forgot-password">Forgotten your password?</Link></div>
        <p className="auth-note">No account yet? Ask an administrator.</p>
    </AuthLayout>
  );
}
