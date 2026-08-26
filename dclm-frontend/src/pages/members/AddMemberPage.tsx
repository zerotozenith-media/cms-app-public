import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateMember } from '../../api/members';
import { useLocations } from '../../api/locations';
import { MemberFormFields, type MemberFormValues } from './MemberFormFields';
import { Button } from '../../components/ui/Button';

const today = new Date().toISOString().slice(0, 10);

const EMPTY: MemberFormValues = {
  surname: '', first_name: '', other_names: '', gender: 'Male', date_of_birth: '',
  phone: '', email: '', category: 'General Member', location: '', household: '', joined_date: today,
};

export function AddMemberPage() {
  const navigate = useNavigate();
  const { data: locations } = useLocations();
  const createMember = useCreateMember();
  const [values, setValues] = useState<MemberFormValues>(EMPTY);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const created = await createMember.mutateAsync({
        surname: values.surname,
        first_name: values.first_name,
        other_names: values.other_names,
        gender: values.gender,
        date_of_birth: values.date_of_birth || null,
        phone: values.phone,
        email: values.email,
        category: values.category as any,
        location: values.location,
        household: values.household ? Number(values.household) : null,
        joined_date: values.joined_date,
      });
      navigate(`/members/${created.id}`);
    } catch (err: any) {
      const data = err?.response?.data;
      if (data?.phone) setError(`Phone: ${data.phone[0]}`);
      else setError('Could not create the member. Please check the form and try again.');
    }
  }

  if (!locations) return null;

  // Default the location select to the first available once loaded.
  if (!values.location && locations.length) {
    setValues((v) => ({ ...v, location: v.location || locations[0].id }));
  }

  return (
    <>
      <a className="backlink" onClick={() => navigate('/members')}>← Back to members</a>
      <div className="card" style={{ maxWidth: 520, margin: '0 auto' }}>
        <h3>Add member</h3>
        <form onSubmit={handleSubmit}>
          <MemberFormFields values={values} onChange={setValues} locations={locations} />
          {error && <p style={{ color: 'var(--red)', fontSize: '.85rem', marginBottom: 12 }}>{error}</p>}
          <Button type="submit" disabled={createMember.isPending}>
            {createMember.isPending ? 'Adding…' : 'Add member'}
          </Button>
        </form>
      </div>
    </>
  );
}
