import { useMeetingTypes } from '../../api/attendance';
import { usePublicMeetingTypes } from '../../api/newcomers';

export interface IntakeFormValues {
  /** Split in the form because people fill a paper slip that way, but
   *  joined into the API's single `name` field on submit. */
  first_name: string;
  last_name: string;
  address: string;
  city_governorate: string;
  phone: string;
  email: string;
  gender: string;
  age_group: string;
  prayer_request: string;
  meeting_attended: string;
  is_first_timer: boolean;
  is_new_resident: boolean;
  wants_visit: boolean;
  wants_to_know_more: boolean;
  wants_salvation_info: boolean;
  invited_by_name: string;
}

export const EMPTY_INTAKE_VALUES: IntakeFormValues = {
  first_name: '', last_name: '', address: '', city_governorate: '', phone: '', email: '',
  gender: '', age_group: '', prayer_request: '', meeting_attended: '',
  is_first_timer: false, is_new_resident: false,
  wants_visit: false, wants_to_know_more: false, wants_salvation_info: false,
  invited_by_name: '',
};

interface IntakeFormFieldsProps {
  values: IntakeFormValues;
  onChange: (values: IntakeFormValues) => void;
  /** A form-unique prefix for field ids, so two instances of this
   * component on the same page (unlikely, but possible) never collide. */
  idPrefix?: string;
  /** True on the public registration page, where the visitor is not
   *  signed in and the protected meeting-types endpoint returns nothing. */
  isPublic?: boolean;
}

/**
 * Matches the real DCLM Bahrain intake slip exactly , shared between
 * the authenticated Manual Entry form and the public QR self-
 * registration form, so both really do capture the same fields, per
 * the correction made ahead of this batch.
 *
 * Every field uses a real htmlFor/id pair, not just visually adjacent
 * label/input elements , found this was missing across every form
 * built since Batch 3.4 while testing this component with Playwright's
 * label-based locators, which correctly refused to match an
 * unassociated label. A real accessibility gap, not just a testing
 * inconvenience , a screen reader would have had the same problem.
 */
export function IntakeFormFields({ values, onChange, idPrefix = 'intake', isPublic = false }: IntakeFormFieldsProps) {
  // The same fields serve the staff form and the public one. A visitor is
  // not signed in, so the protected endpoint returns nothing for them.
  const staffMeetingTypes = useMeetingTypes({ enabled: !isPublic });
  const publicMeetingTypes = usePublicMeetingTypes({ enabled: isPublic });
  const meetingTypes = isPublic ? publicMeetingTypes.data : staffMeetingTypes.data;
  const fid = (name: string) => `${idPrefix}-${name}`;

  function set<K extends keyof IntakeFormValues>(key: K, value: IntakeFormValues[K]) {
    onChange({ ...values, [key]: value });
  }

  return (
    <>
      <div className="form-row">
        <div className="field">
          <label htmlFor={fid('date')}>Date</label>
          <input id={fid('date')} value={new Date().toISOString().slice(0, 10)} disabled />
        </div>
        <div className="field">
          <label htmlFor={fid('meeting')}>Meeting</label>
          <select id={fid('meeting')} value={values.meeting_attended} onChange={(e) => set('meeting_attended', e.target.value)}>
            <option value="">Select…</option>
            {(meetingTypes ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        </div>
      </div>
      <div className="form-row">
        <div className="field">
          <label htmlFor={fid('first-name')}>First name</label>
          <input id={fid('first-name')} value={values.first_name} onChange={(e) => set('first_name', e.target.value)} required />
        </div>
        <div className="field">
          <label htmlFor={fid('last-name')}>Last name</label>
          <input id={fid('last-name')} value={values.last_name} onChange={(e) => set('last_name', e.target.value)} required />
        </div>
      </div>
      <div className="field">
        <label htmlFor={fid('address')}>Address</label>
        <input id={fid('address')} value={values.address} onChange={(e) => set('address', e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor={fid('city')}>City/Governorate</label>
        <input id={fid('city')} value={values.city_governorate} onChange={(e) => set('city_governorate', e.target.value)} />
      </div>
      <div className="form-row">
        <div className="field">
          <label htmlFor={fid('phone')}>Phone</label>
          <input id={fid('phone')} value={values.phone} onChange={(e) => set('phone', e.target.value)} placeholder="+973 0000 0000" />
        </div>
        <div className="field">
          <label htmlFor={fid('email')}>Email</label>
          <input id={fid('email')} type="email" value={values.email} onChange={(e) => set('email', e.target.value)} />
        </div>
      </div>
      <div className="form-row">
        <div className="field">
          <label htmlFor={fid('gender')}>Gender</label>
          <select id={fid('gender')} value={values.gender} onChange={(e) => set('gender', e.target.value)}>
            <option value="">–</option>
            <option value="Male">Male</option>
            <option value="Female">Female</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor={fid('age')}>Age group</label>
          <select id={fid('age')} value={values.age_group} onChange={(e) => set('age_group', e.target.value)}>
            <option value="">–</option>
            <option value="under_20">Under 20</option>
            <option value="20_and_above">20 and above</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gap: 8, margin: '14px 0' }}>
        <label htmlFor={fid('first-timer')} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.85rem' }}>
          <input id={fid('first-timer')} type="checkbox" checked={values.is_first_timer} onChange={(e) => set('is_first_timer', e.target.checked)} style={{ width: 16, height: 16 }} />
          First Timer
        </label>
        <label htmlFor={fid('new-resident')} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.85rem' }}>
          <input id={fid('new-resident')} type="checkbox" checked={values.is_new_resident} onChange={(e) => set('is_new_resident', e.target.checked)} style={{ width: 16, height: 16 }} />
          New Resident
        </label>
        <label htmlFor={fid('wants-visit')} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.85rem' }}>
          <input id={fid('wants-visit')} type="checkbox" checked={values.wants_visit} onChange={(e) => set('wants_visit', e.target.checked)} style={{ width: 16, height: 16 }} />
          Would like a visit
        </label>
        <label htmlFor={fid('wants-more')} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.85rem' }}>
          <input id={fid('wants-more')} type="checkbox" checked={values.wants_to_know_more} onChange={(e) => set('wants_to_know_more', e.target.checked)} style={{ width: 16, height: 16 }} />
          Would like to know more about the church
        </label>
        <label htmlFor={fid('wants-salvation')} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '.85rem' }}>
          <input id={fid('wants-salvation')} type="checkbox" checked={values.wants_salvation_info} onChange={(e) => set('wants_salvation_info', e.target.checked)} style={{ width: 16, height: 16 }} />
          Want to know about being a Christian
        </label>
      </div>

      <div className="field">
        <label htmlFor={fid('invited-by')}>Invited by</label>
        <input id={fid('invited-by')} value={values.invited_by_name} onChange={(e) => set('invited_by_name', e.target.value)} placeholder="Name of the person who invited you" />
      </div>
      <div className="field">
        <label htmlFor={fid('prayer')}>Prayer request</label>
        <textarea id={fid('prayer')} value={values.prayer_request} onChange={(e) => set('prayer_request', e.target.value)} />
      </div>
    </>
  );
}

/** The API stores a single name. Join here so every caller does it the
 *  same way rather than each form inventing its own. */
export function intakeFullName(values: IntakeFormValues): string {
  return `${values.first_name} ${values.last_name}`.trim().replace(/\s+/g, ' ');
}
