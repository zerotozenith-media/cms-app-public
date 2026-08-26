import { useState, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import logoBadge from '../assets/logo-badge.png';

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
  const [submitting, setSubmitting] = useState(false);
  const formLoadedAt = useRef(new Date().toISOString());

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password, { website, form_loaded_at: formLoadedAt.current });
      const from = (location.state as { from?: string })?.from || '/';
      navigate(from, { replace: true });
    } catch (err: any) {
      if (err?.response?.status === 429) {
        setError('Too many attempts. Please wait a few minutes and try again.');
      } else {
        setError('Invalid email or password.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="login-card">
        <img className="login-logo" src={logoBadge} alt="DCLM Bahrain" />
        <h2>Sign in to DCLM Bahrain CMS</h2>
        <p className="login-sub">Enter your email and password to continue.</p>

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

          {error && (
            <p style={{ color: 'var(--red)', fontSize: '.85rem', margin: '4px 0 14px' }}>{error}</p>
          )}

          <Button type="submit" disabled={submitting} style={{ width: '100%', justifyContent: 'center' }}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>

        <p className="login-note">
          Trouble signing in? Contact your Administrator to confirm your account is active.
        </p>
      </div>
    </div>
  );
}
