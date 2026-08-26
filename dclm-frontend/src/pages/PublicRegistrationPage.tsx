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
      // A visitor who mistyped their email needs to be told that, not sent
      // to find a leader. Only the anti-spam guards stay deliberately
      // vague, since naming which one tripped would help a bot tune
      // around it. Everything else names the field so they can fix it.
      const status = err?.response?.status;
      const data = err?.response?.data;

      if (status === 429) {
        setError('Too many submissions from this connection. Please see a leader at the welcome desk.');
      } else if (data && typeof data === 'object' && !data.detail) {
        const FIELD_LABELS: Record<string, string> = {
          name: 'name', first_name: 'first name', last_name: 'last name',
          phone: 'phone number', email: 'email address',
          meeting_attended: 'meeting attended', address: 'address',
          city_governorate: 'city or governorate', gender: 'gender',
          age_group: 'age group', invited_by_name: 'who invited you',
          prayer_request: 'prayer request',
        };
        const [field, messages] = Object.entries(data)[0] ?? [];
        const label = FIELD_LABELS[field as string] ?? (field as string);
        const detail = Array.isArray(messages) ? messages[0] : String(messages ?? '');
        // "Please enter your name" is only right when it is missing. If
        // the name was entered but rejected, say why, or the visitor has
        // no idea what to change.
        const isMissing = /required|may not be blank|cannot be blank/i.test(detail);
        setError(
          field === 'name' && isMissing
            ? 'Please enter your name.'
            : `Please check your ${label}. ${detail}`.trim(),
        );
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
          <IntakeFormFields values={values} onChange={setValues} isPublic />

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
