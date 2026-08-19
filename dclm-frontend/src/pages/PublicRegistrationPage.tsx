import { useState, useRef } from 'react';
import { submitPublicRegistration } from '../api/newcomers';
import { IntakeFormFields, EMPTY_INTAKE_VALUES, intakeFullName, type IntakeFormValues } from './newcomers/IntakeFormFields';
import { Button } from '../components/ui/Button';
import logoBadge from '../assets/logo-badge.png';

/**
 * The real, working public self-registration form the QR code points
 * to , deliberately outside the authenticated app shell entirely (no
 * sidebar, no login required). Confirmed: Bahrain-only, no location
 * picker needed.
 */
export function PublicRegistrationPage() {
  const [values, setValues] = useState<IntakeFormValues>(EMPTY_INTAKE_VALUES);
  const [website, setWebsite] = useState(''); // honeypot
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const formLoadedAt = useRef(new Date().toISOString());

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      // first_name/last_name exist only in the form; the API takes a
      // single `name`, so they are joined and removed here.
      const { first_name: _f, last_name: _l, ...rest } = values;
      await submitPublicRegistration({
        ...rest, name: intakeFullName(values),
        meeting_attended: values.meeting_attended || null,
        website, form_loaded_at: formLoadedAt.current,
      });
      setSubmitted(true);
    } catch (err: any) {
      if (err?.response?.status === 429) {
        setError('Too many submissions from this connection. Please see a leader at the welcome desk.');
      } else if (err?.response?.data?.name) {
        setError('Please enter your name.');
      } else {
        setError("We couldn't process your submission. Please see a leader at the welcome desk.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="login-screen">
        <div className="login-card" style={{ textAlign: 'center' }}>
          <img className="login-logo" src={logoBadge} alt="DCLM Bahrain" />
          <h2>Thank you!</h2>
          <p className="login-sub">Someone from our team will be in touch soon. We're glad you're here.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-screen">
      <div className="login-card" style={{ maxWidth: 480 }}>
        <img className="login-logo" src={logoBadge} alt="DCLM Bahrain" />
        <h2>Welcome! We're so glad you're here.</h2>
        <p className="login-sub">
          Tell us a little about yourself so we can stay connected and support you.
        </p>

        <form onSubmit={handleSubmit}>
          <IntakeFormFields values={values} onChange={setValues} />

          {/* Honeypot , hidden from real visitors, a bot reading the DOM may still fill it */}
          <div style={{ position: 'absolute', left: '-9999px', width: 1, height: 1, overflow: 'hidden' }} aria-hidden="true">
            <label htmlFor="website">Website</label>
            <input id="website" name="website" type="text" tabIndex={-1} autoComplete="off"
              value={website} onChange={(e) => setWebsite(e.target.value)} />
          </div>

          {error && <p style={{ color: 'var(--red)', fontSize: '.85rem', margin: '4px 0 14px' }}>{error}</p>}

          <Button type="submit" disabled={submitting} style={{ width: '100%', justifyContent: 'center' }}>
            {submitting ? 'Submitting…' : 'Submit'}
          </Button>
        </form>
      </div>
    </div>
  );
}
