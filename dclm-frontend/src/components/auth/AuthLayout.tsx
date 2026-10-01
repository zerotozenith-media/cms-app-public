import logoBadge from '../../assets/logo-badge.png';

/**
 * The frame shared by sign-in, "reset your password" and "choose a new
 * password": the church's logo, name and Jude 3 on the left on a computer
 * (on top on a phone), the form on the right. Kay approved this design,
 * with the logo's own red for accents and blue for buttons.
 */
export function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth-screen">
      <div className="auth-brand">
        <img className="auth-logo" src={logoBadge} alt="Deeper Christian Life Ministry logo" />
        <div className="auth-church">Deeper Christian Life Ministry Bahrain</div>
        <div className="auth-verse">
          <div className="auth-verse-text">Earnestly contending for the faith once delivered to the saints.</div>
          <div className="auth-verse-ref">Jude 3</div>
        </div>
      </div>
      <div className="auth-form">
        <div className="auth-box">{children}</div>
      </div>
    </div>
  );
}

/** A round icon above a heading, in the logo's red. */
export function AuthIcon({ name }: { name: 'key' | 'lock' | 'mail' }) {
  const paths: Record<string, React.ReactNode> = {
    key: <><circle cx="8" cy="15" r="4" /><path d="M10.8 12.2 20 3M17 6l3 3M14 9l2 2" /></>,
    lock: <><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></>,
  };
  return (
    <div className="auth-icon" aria-hidden="true">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>
    </div>
  );
}
