import { useState } from 'react';
import { ChipList } from '../../components/admin/ChipList';
import { useAdminLocations, useCreateLocation, useDeleteLocation } from '../../api/admin';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';

function LocationsCard() {
  const { data: locations } = useAdminLocations();
  const createLocation = useCreateLocation();
  const deleteLocation = useDeleteLocation();
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!id.trim() || !name.trim()) return;
    await createLocation.mutateAsync({ id: id.trim(), name: name.trim(), note });
    setId(''); setName(''); setNote('');
  }
  async function handleDelete(locId: string) {
    if (!confirm('Delete this location?')) return;
    setError(null);
    try {
      await deleteLocation.mutateAsync(locId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Could not delete this location.');
    }
  }

  return (
    <div className="card">
      <h3>Locations</h3>
      <div style={{ overflowX: 'auto' }}>
        <table className="cardtable">
          <thead><tr><th>Location</th><th>Note</th><th></th></tr></thead>
          <tbody>
            {(locations ?? []).map((l: any) => (
              <tr key={l.id}>
                <td data-label="Location">
                  {l.name} {l.is_core && <Badge color="blue">Protected</Badge>}
                </td>
                <td data-label="Note">{l.note || '–'}</td>
                <td className="td-actions">
                  {!l.is_core && (
                    <button className="icon-btn" onClick={() => handleDelete(l.id)}><Icon name="trash" size={14} /></button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && <p style={{ color: 'var(--red)', fontSize: '.85rem', margin: '8px 0' }}>{error}</p>}
      <form onSubmit={handleAdd} style={{ marginTop: 10 }}>
        <div className="form-row">
          <div className="field">
            <label htmlFor="loc-id">ID (short code)</label>
            <input id="loc-id" value={id} onChange={(e) => setId(e.target.value)} placeholder="e.g. dubai" />
          </div>
          <div className="field">
            <label htmlFor="loc-name">Name</label>
            <input id="loc-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Dubai" />
          </div>
        </div>
        <div className="field">
          <label htmlFor="loc-note">Note (optional)</label>
          <input id="loc-note" value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        <button className="btn sm" type="submit" disabled={createLocation.isPending}>Add location</button>
      </form>
    </div>
  );
}

/**
 * Every simple admin-configurable name-only list established across
 * Batch 0.1–0.7 , more than the demo showed (it only had 3), since the
 * real approved schema has more of these than the original mock data did.
 */
export function ConfigListsTab() {
  return (
    <>
      <LocationsCard />
      <div className="grid g3 section-gap">
        <ChipList title="Funds" endpoint="funds" badgeColor="blue" placeholder="New fund" />
        <ChipList title="Payment methods" endpoint="payment-methods" badgeColor="green" placeholder="New payment method" />
        <ChipList title="Expense categories" endpoint="expense-categories" badgeColor="amber" placeholder="New category" />
        <ChipList title="Newcomer sources" endpoint="newcomer-sources" badgeColor="gray" placeholder="New source" />
        <ChipList title="Milestone types" endpoint="milestone-types" badgeColor="blue" placeholder="New milestone" />
        <ChipList title="Services" endpoint="services" badgeColor="green" placeholder="New service" />
        <ChipList title="Departments" endpoint="departments" badgeColor="amber" placeholder="New department" />
      </div>
    </>
  );
}
