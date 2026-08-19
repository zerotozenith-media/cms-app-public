import { useState, useRef, useEffect } from 'react';
import { findMembersBySurname, useHouseholds } from '../../api/members';

export interface MemberFormValues {
  surname: string;
  first_name: string;
  other_names: string;
  gender: string;
  date_of_birth: string;
  phone: string;
  email: string;
  category: string;
  location: string;
  household: string;
  joined_date: string;
}

interface MemberFormFieldsProps {
  values: MemberFormValues;
  onChange: (values: MemberFormValues) => void;
  locations: { id: string; name: string }[];
  excludeMemberId?: number;
  showCategoryAndJoined?: boolean;
}

/**
 * Shared between Add Member and the profile page's inline edit , the
 * demo's checkSurnameMatch() queried a local in-memory array
 * synchronously; this queries the real API, debounced, since every
 * keystroke triggering a request would be wasteful and the backend has
 * real network latency the demo never had to account for.
 *
 * Every field uses a real htmlFor/id pair , found this was missing
 * here (and in every form built since) while testing the Newcomers
 * intake form with Playwright's label-based locators in Batch 3.6,
 * which correctly refused to match an unassociated label. A real
 * accessibility gap, not just a testing inconvenience.
 */
export function MemberFormFields({ values, onChange, locations, excludeMemberId, showCategoryAndJoined = true }: MemberFormFieldsProps) {
  const [surnameHint, setSurnameHint] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { data: households } = useHouseholds();

  function set<K extends keyof MemberFormValues>(key: K, value: MemberFormValues[K]) {
    onChange({ ...values, [key]: value });
  }

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!values.surname.trim()) {
      setSurnameHint(null);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      const matches = await findMembersBySurname(values.surname, excludeMemberId);
      if (!matches.length) {
        setSurnameHint(null);
        return;
      }
      const names = matches
        .map((m) => `${m.full_name}${m.household_name ? ` (${m.household_name})` : ' (no household set)'}`)
        .join(', ');
      setSurnameHint(`${matches.length} existing member(s) share this surname: ${names}. Consider selecting the same household below.`);
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values.surname]);

  return (
    <>
      <div className="form-row">
        <div className="field">
          <label htmlFor="member-surname">Surname</label>
          <input id="member-surname" value={values.surname} onChange={(e) => set('surname', e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor="member-first-name">First name</label>
          <input id="member-first-name" value={values.first_name} onChange={(e) => set('first_name', e.target.value)} required />
        </div>
      </div>
      {surnameHint && (
        <div className="muted" style={{ fontSize: '.8rem', marginTop: -8, marginBottom: 14 }}>
          {surnameHint}
        </div>
      )}
      <div className="field">
        <label htmlFor="member-other-names">Other names (optional)</label>
        <input id="member-other-names" value={values.other_names} onChange={(e) => set('other_names', e.target.value)} />
      </div>
      <div className="form-row">
        <div className="field">
          <label htmlFor="member-gender">Gender</label>
          <select id="member-gender" value={values.gender} onChange={(e) => set('gender', e.target.value)}>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="member-dob">Date of birth</label>
          <input id="member-dob" type="date" value={values.date_of_birth} onChange={(e) => set('date_of_birth', e.target.value)} />
        </div>
      </div>
      <div className="form-row">
        <div className="field">
          <label htmlFor="member-phone">Phone</label>
          <input id="member-phone" value={values.phone} onChange={(e) => set('phone', e.target.value)} placeholder="+973 0000 0000" />
        </div>
        <div className="field">
          <label htmlFor="member-email">Email</label>
          <input id="member-email" type="email" value={values.email} onChange={(e) => set('email', e.target.value)} />
        </div>
      </div>
      <div className="form-row">
        {showCategoryAndJoined && (
          <div className="field">
            <label htmlFor="member-category">Category</label>
            <select id="member-category" value={values.category} onChange={(e) => set('category', e.target.value)}>
              <option>General Member</option>
              <option>Worker in Training</option>
              <option>Worker</option>
            </select>
          </div>
        )}
        <div className="field">
          <label htmlFor="member-location">Location</label>
          <select id="member-location" value={values.location} onChange={(e) => set('location', e.target.value)}>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="form-row">
        <div className="field">
          <label htmlFor="member-household">Household (optional)</label>
          <select id="member-household" value={values.household} onChange={(e) => set('household', e.target.value)}>
            <option value="">No household</option>
            {(households ?? []).map((h) => (
              <option key={h.id} value={h.id}>{h.name}</option>
            ))}
          </select>
        </div>
        {showCategoryAndJoined && (
          <div className="field">
            <label htmlFor="member-joined-date">Joined date</label>
            <input id="member-joined-date" type="date" value={values.joined_date} onChange={(e) => set('joined_date', e.target.value)} />
          </div>
        )}
      </div>
    </>
  );
}
