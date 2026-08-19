import { useState } from 'react';
import { useServices, useTestimonies, useCreateTestimony, useUpdateTestimony, useDeleteTestimony } from '../../api/reports';
import { Icon } from '../../components/ui/Icon';
import type { Testimony } from '../../types/reports';

const today = new Date().toISOString().slice(0, 10);

export function TestimoniesTab() {
  const { data: services } = useServices();
  const [serviceFilter, setServiceFilter] = useState('all');
  const [sort, setSort] = useState('-date');
  const [page, setPage] = useState(1);
  const { data: testimonies } = useTestimonies({
    service: serviceFilter !== 'all' ? serviceFilter : undefined, ordering: sort, page, page_size: 5,
  });

  const [editId, setEditId] = useState<number | null>(null);
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [memberName, setMemberName] = useState('');
  const [service, setService] = useState('');
  const [text, setText] = useState('');
  const createTestimony = useCreateTestimony();
  const updateTestimony = useUpdateTestimony();
  const deleteTestimony = useDeleteTestimony();

  if (services && !service && services.length) setService(String(services[0].id));

  function startEdit(t: Testimony) {
    setEditId(t.id);
    setIsAnonymous(t.is_anonymous);
    setMemberName(t.member_name);
    setService(String(t.service));
    setText(t.text);
  }
  function cancelEdit() {
    setEditId(null);
    setIsAnonymous(false); setMemberName(''); setText('');
  }
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = { is_anonymous: isAnonymous, member_name: memberName, service: Number(service), text, date: today };
    if (editId) {
      await updateTestimony.mutateAsync({ id: editId, ...payload });
      cancelEdit();
    } else {
      await createTestimony.mutateAsync(payload);
      cancelEdit();
    }
  }
  async function handleDelete(id: number) {
    if (!confirm('Delete this testimony?')) return;
    await deleteTestimony.mutateAsync(id);
  }

  return (
    <div className="grid g2">
      <div className="card">
        <h3>{editId ? 'Edit testimony' : 'Submit a testimony'}</h3>
        <form onSubmit={handleSubmit}>
          <label htmlFor="testi-anon" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <input id="testi-anon" type="checkbox" checked={isAnonymous} onChange={(e) => setIsAnonymous(e.target.checked)} style={{ width: 16, height: 16 }} />
            Submit anonymously
          </label>
          <div className="field">
            <label htmlFor="testi-name">Name (if not anonymous)</label>
            <input id="testi-name" value={memberName} onChange={(e) => setMemberName(e.target.value)} disabled={isAnonymous} />
          </div>
          <div className="field">
            <label htmlFor="testi-service">Service</label>
            <select id="testi-service" value={service} onChange={(e) => setService(e.target.value)}>
              {(services ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="testi-text">Testimony</label>
            <textarea id="testi-text" value={text} onChange={(e) => setText(e.target.value)} required />
          </div>
          <button className="btn" type="submit" disabled={createTestimony.isPending || updateTestimony.isPending}>
            {editId ? 'Save changes' : 'Submit'}
          </button>
          {editId && <button className="btn ghost" type="button" onClick={cancelEdit}>Cancel</button>}
        </form>
      </div>

      <div className="card">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>Recent testimonies</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select className="selectbox" value={serviceFilter} onChange={(e) => { setServiceFilter(e.target.value); setPage(1); }}>
              <option value="all">All services</option>
              {(services ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <select className="selectbox" value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="-date">Newest first</option>
              <option value="date">Oldest first</option>
            </select>
          </div>
        </div>
        {(testimonies?.results ?? []).length ? testimonies!.results.map((t) => (
          <div key={t.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--line)', fontSize: '.88rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
              <div>
                "{t.text}"
                <div className="muted" style={{ fontSize: '.78rem' }}>
                  – {t.is_anonymous ? 'Anonymous' : t.member_name}, {t.service_name}, {t.date}
                </div>
              </div>
              <div className="row-actions">
                <button className="icon-btn edit" onClick={() => startEdit(t)}><Icon name="edit" size={14} /></button>
                <button className="icon-btn" onClick={() => handleDelete(t.id)}><Icon name="trash" size={14} /></button>
              </div>
            </div>
          </div>
        )) : <div className="empty">No testimonies match these filters.</div>}
      </div>
    </div>
  );
}
