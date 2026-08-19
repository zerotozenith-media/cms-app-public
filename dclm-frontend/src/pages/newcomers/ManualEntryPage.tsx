import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateNewcomer, useNewcomerSources } from '../../api/newcomers';
import { useLocations } from '../../api/locations';
import { IntakeFormFields, EMPTY_INTAKE_VALUES, intakeFullName, type IntakeFormValues } from './IntakeFormFields';
import { Button } from '../../components/ui/Button';

export function ManualEntryPage() {
  const navigate = useNavigate();
  const { data: sources } = useNewcomerSources();
  const { data: locations } = useLocations();
  const createNewcomer = useCreateNewcomer();

  const [values, setValues] = useState<IntakeFormValues>(EMPTY_INTAKE_VALUES);
  const [location, setLocation] = useState('');
  const [source, setSource] = useState<number | ''>('');
  const [error, setError] = useState<string | null>(null);

  if (locations && !location && locations.length) setLocation(locations[0].id);
  if (sources && !source && sources.length) setSource(sources[0].id);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await createNewcomer.mutateAsync({
        name: intakeFullName(values), location, source,
        address: values.address, city_governorate: values.city_governorate,
        phone: values.phone, email: values.email, gender: values.gender, age_group: values.age_group,
        prayer_request: values.prayer_request, meeting_attended: values.meeting_attended || null,
        is_first_timer: values.is_first_timer, is_new_resident: values.is_new_resident,
        wants_visit: values.wants_visit, wants_to_know_more: values.wants_to_know_more,
        wants_salvation_info: values.wants_salvation_info, invited_by_name: values.invited_by_name,
      });
      navigate(`/newcomers/${created.id}`);
    } catch {
      setError('Could not add this newcomer. Please check the form and try again.');
    }
  }

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab" onClick={() => navigate('/newcomers')}>Pipeline</button>
          <button className="tab" onClick={() => navigate('/newcomers/follow-up')}>Follow-up</button>
          <button className="tab" onClick={() => navigate('/newcomers/qr')}>QR Registration</button>
          <button className="tab active">Manual Entry</button>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 520, margin: '0 auto' }}>
        <h3>Enter details from a paper form</h3>
        <p className="muted" style={{ marginBottom: 16 }}>
          Use this for newcomers who filled a paper card instead of scanning the QR code.
        </p>
        <form onSubmit={handleSubmit}>
          <IntakeFormFields values={values} onChange={setValues} />
          <div className="form-row">
            <div className="field">
              <label htmlFor="manual-location">Location</label>
              <select id="manual-location" value={location} onChange={(e) => setLocation(e.target.value)}>
                {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="manual-source">Learnt about the church from</label>
              <select id="manual-source" value={source} onChange={(e) => setSource(Number(e.target.value))}>
                {(sources ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          </div>
          {error && <p style={{ color: 'var(--red)', fontSize: '.85rem', marginBottom: 12 }}>{error}</p>}
          <Button type="submit" disabled={createNewcomer.isPending}>
            {createNewcomer.isPending ? 'Adding…' : 'Add newcomer'}
          </Button>
        </form>
      </div>
    </>
  );
}
