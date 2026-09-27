import { useState } from 'react';
import { ChipList } from '../../components/admin/ChipList';
import { useAdminLocations, useCreateLocation, useDeleteLocation, useUpdateLocation } from '../../api/admin';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { useCampaigns, useCreateCampaign, useDeleteCampaign } from '../../api/campaigns';
import { useEnquirySources } from '../../api/enquiries';
import { useProjects, useCreateProject, useDeleteProject } from '../../api/finance';
import { useLocations } from '../../api/locations';
import { useAuth } from '../../context/AuthContext';

function LocationsCard() {
  // Locations apply to the whole church.
  const { user: me, hasPermission } = useAuth();
  const churchWide = !me?.location && hasPermission('admin', 'edit');
  const { data: locations } = useAdminLocations();
  const createLocation = useCreateLocation();
  const updateLocation = useUpdateLocation();
  const [renaming, setRenaming] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newNote, setNewNote] = useState('');
  async function saveRename(locId: string) {
    setError(null);
    try {
      await updateLocation.mutateAsync({ id: locId, name: newName.trim(), note: newNote.trim() });
      setRenaming(null);
    } catch (err: any) {
      const d = err?.response?.data;
      setError(d?.name?.[0] || d?.detail || 'That name could not be saved.');
    }
  }
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
                  {renaming === l.id ? (
                    <input className="cell-input" aria-label="New name" value={newName}
                      onChange={(e) => setNewName(e.target.value)} />
                  ) : <>{l.name} {l.is_core && <Badge color="blue">Main location</Badge>}</>}
                </td>
                <td data-label="Note">
                  {renaming === l.id ? (
                    <input className="cell-input" aria-label="Note" value={newNote}
                      onChange={(e) => setNewNote(e.target.value)} />
                  ) : (l.note || '–')}
                </td>
                <td className="td-actions">
                  {churchWide && renaming === l.id && (
                    <>
                      <button className="btn sm" disabled={!newName.trim() || updateLocation.isPending}
                        onClick={() => saveRename(l.id)}>Save</button>
                      <button className="btn sm ghost" onClick={() => setRenaming(null)}>Cancel</button>
                    </>
                  )}
                  {churchWide && renaming !== l.id && (
                    <button className="icon-btn edit" title="Rename location" aria-label="Rename location"
                      onClick={() => { setRenaming(l.id); setNewName(l.name); setNewNote(l.note || ''); }}>
                      <Icon name="edit" size={14} />
                    </button>
                  )}
                  {churchWide && !l.is_core && (
                    <button className="icon-btn" title="Remove location" aria-label="Remove location" onClick={() => handleDelete(l.id)}><Icon name="trash" size={14} /></button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && <p style={{ color: 'var(--red)', fontSize: '.85rem', margin: '8px 0' }}>{error}</p>}
      {churchWide && <form onSubmit={handleAdd} style={{ marginTop: 10 }}>
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
      </form>}
    </div>
  );
}

/**
 * Every simple admin-configurable name-only list established across
 * Batch 0.1–0.7 , more than the demo showed (it only had 3), since the
 * real approved schema has more of these than the original mock data did.
 */
/**
 * Campaigns carry a platform and a spend, so a chip list will not do.
 * The spend matters because the outreach screen reports cost per
 * enquiry from it.
 */
function CampaignsCard() {
  const { hasPermission } = useAuth();
  const canAdd = hasPermission('outreach', 'create');
  const canRemove = hasPermission('outreach', 'delete');
  const { data: campaigns } = useCampaigns();
  const { data: sources } = useEnquirySources();
  const create = useCreateCampaign();
  const remove = useDeleteCampaign();
  const [name, setName] = useState('');
  const [source, setSource] = useState('');
  const [spend, setSpend] = useState('0');
  const [error, setError] = useState('');

  return (
    <div className="card section-gap">
      <h3>Campaigns</h3>
      <p className="muted" style={{ fontSize: '.8rem', marginBottom: 12 }}>
        What was spent reaching people, and on which platform. The outreach screen
        reports cost per enquiry from this.
      </p>
      <table className="cardtable">
        <thead><tr><th>Campaign</th><th>Platform</th><th>Spend</th><th /></tr></thead>
        <tbody>
          {(campaigns ?? []).map((c) => (
            <tr key={c.id}>
              <td data-label="Campaign"><b>{c.name}</b></td>
              <td data-label="Platform">{c.source_name || '-'}</td>
              <td data-label="Spend">{c.spend ? Number(c.spend).toFixed(3) : '-'}</td>
              <td className="td-actions">
                {canRemove && (<button className="icon-btn" title="Remove"
                  onClick={async () => {
                    setError('');
                    try { await remove.mutateAsync(c.id); }
                    catch (err: any) {
                      setError(err?.response?.data?.detail
                        ?? 'That campaign could not be removed.');
                    }
                  }}>
                  <Icon name="trash" size={14} />
                </button>)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <p className="form-error">{error}</p>}
      {canAdd && <>
      <div className="form-row" style={{ marginTop: 12 }}>
        <div className="field">
          <label htmlFor="cmp-name">Name</label>
          <input id="cmp-name" value={name} onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Easter Service 2027" />
        </div>
        <div className="field">
          <label htmlFor="cmp-source">Platform</label>
          <select id="cmp-source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">None, organic</option>
            {(sources ?? []).map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="cmp-spend">Spend</label>
          <input id="cmp-spend" type="number" step="0.001" min={0} value={spend}
            onChange={(e) => setSpend(e.target.value)} />
        </div>
      </div>
      <button className="btn sm" disabled={!name.trim() || create.isPending}
        onClick={async () => {
          await create.mutateAsync({ name: name.trim(),
            source: source ? Number(source) : null, spend });
          setName(''); setSpend('0');
        }}>
        <Icon name="plus" size={14} /> Add campaign
      </button>
      </>}
    </div>
  );
}

/** Fundraising targets giving can be counted towards. */
function ProjectsCard() {
  const { hasPermission } = useAuth();
  const canAdd = hasPermission('finance', 'create');
  const canRemove = hasPermission('finance', 'delete');
  const { user } = useAuth();
  const { data: projects } = useProjects();
  const { data: locations } = useLocations();
  const create = useCreateProject();
  const remove = useDeleteProject();
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [error, setError] = useState('');

  return (
    <div className="card section-gap">
      <h3>Projects</h3>
      <p className="muted" style={{ fontSize: '.8rem', marginBottom: 12 }}>
        Fundraising targets giving can be counted towards.
      </p>
      <table className="cardtable">
        <thead><tr><th>Project</th><th>Location</th><th>Target</th><th /></tr></thead>
        <tbody>
          {(projects ?? []).map((pr: any) => (
            <tr key={pr.id}>
              <td data-label="Project"><b>{pr.name}</b></td>
              <td data-label="Location">{pr.location_name || '-'}</td>
              <td data-label="Target">{Number(pr.target_amount).toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 })}</td>
              <td className="td-actions">
                {canRemove && (<button className="icon-btn" title="Remove"
                  onClick={async () => {
                    setError('');
                    try { await remove.mutateAsync(pr.id); }
                    catch (err: any) {
                      setError(err?.response?.data?.detail
                        ?? 'That project could not be removed.');
                    }
                  }}>
                  <Icon name="trash" size={14} />
                </button>)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <p className="form-error">{error}</p>}
      {canAdd && <>
      <div className="form-row" style={{ marginTop: 12 }}>
        <div className="field">
          <label htmlFor="prj-name">Name</label>
          <input id="prj-name" value={name} onChange={(e) => setName(e.target.value)}
            placeholder="e.g. New Hall Fund" />
        </div>
        <div className="field">
          <label htmlFor="prj-target">Target</label>
          <input id="prj-target" type="number" min={0} value={target}
            onChange={(e) => setTarget(e.target.value)} />
        </div>
      </div>
      <button className="btn sm" disabled={!name.trim() || !target || create.isPending}
        onClick={async () => {
          await create.mutateAsync({ name: name.trim(), target_amount: target,
            location: user?.location ?? locations?.find((l) => l.is_core)?.id ?? locations?.[0]?.id });
          setName(''); setTarget('');
        }}>
        <Icon name="plus" size={14} /> Add project
      </button>
      </>}
    </div>
  );
}

export function ConfigListsTab() {
  return (
    <>
      <LocationsCard />
      <div className="grid g3 section-gap">
        <ChipList title="Funds" endpoint="funds" module="finance" badgeColor="blue" placeholder="New fund" />
        <ChipList title="Payment methods" endpoint="payment-methods" module="finance" badgeColor="green" placeholder="New payment method" />
        <ChipList title="Expense categories" endpoint="expense-categories" module="finance" badgeColor="amber" placeholder="New category" />
        <ChipList title="Newcomer sources" endpoint="newcomer-sources" module="newcomers" badgeColor="gray" placeholder="New source" />
        <ChipList title="Enquiry sources" endpoint="enquiry-sources" module="newcomers" badgeColor="blue" placeholder="e.g. Threads" />
        <ChipList title="Milestone types" endpoint="milestone-types" module="newcomers" badgeColor="blue" placeholder="New milestone" />
        <ChipList title="Services" endpoint="services" module="reports" badgeColor="green" placeholder="New service" />
        <ChipList title="Departments" endpoint="departments" module="reports" badgeColor="amber" placeholder="New department" />
      </div>
      <CampaignsCard />
      <ProjectsCard />
    </>
  );
}
