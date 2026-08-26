import { useState } from 'react';
import {
  useDepartments, useWeeklyNotes, useCreateWeeklyNote, useUpdateWeeklyNote, useDeleteWeeklyNote,
} from '../../api/reports';
import { Icon } from '../../components/ui/Icon';
import type { WeeklyNote } from '../../types/reports';

const today = new Date().toISOString().slice(0, 10);

export function WeeklyNotesTab() {
  const { data: departments } = useDepartments();
  const [deptFilter, setDeptFilter] = useState('all');
  const [sort, setSort] = useState('-week_start');
  const [page, setPage] = useState(1);
  const { data: notes } = useWeeklyNotes({
    department: deptFilter !== 'all' ? deptFilter : undefined, ordering: sort, page, page_size: 5,
  });

  const [editId, setEditId] = useState<number | null>(null);
  const [department, setDepartment] = useState('');
  const [weekLabel, setWeekLabel] = useState('');
  const [weekStart, setWeekStart] = useState(today);
  const [highlights, setHighlights] = useState('');
  const [challenges, setChallenges] = useState('');
  const [prayerPoints, setPrayerPoints] = useState('');
  const createNote = useCreateWeeklyNote();
  const updateNote = useUpdateWeeklyNote();
  const deleteNote = useDeleteWeeklyNote();

  if (departments && !department && departments.length) setDepartment(String(departments[0].id));

  function startEdit(n: WeeklyNote) {
    setEditId(n.id);
    setDepartment(String(n.department));
    setWeekLabel(n.week_label);
    setWeekStart(n.week_start);
    setHighlights(n.highlights);
    setChallenges(n.challenges);
    setPrayerPoints(n.prayer_points);
  }
  function cancelEdit() {
    setEditId(null);
    setWeekLabel(''); setHighlights(''); setChallenges(''); setPrayerPoints('');
    setWeekStart(today);
  }
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = {
      department: Number(department), week_label: weekLabel, week_start: weekStart,
      highlights, challenges, prayer_points: prayerPoints,
    };
    if (editId) {
      await updateNote.mutateAsync({ id: editId, ...payload });
      cancelEdit();
    } else {
      await createNote.mutateAsync(payload);
      cancelEdit();
    }
  }
  async function handleDelete(id: number) {
    if (!confirm('Delete this weekly note?')) return;
    await deleteNote.mutateAsync(id);
  }

  return (
    <div className="grid g2">
      <div className="card">
        <h3>{editId ? 'Edit note' : 'Submit a weekly note'}</h3>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="note-dept">Department</label>
            <select id="note-dept" value={department} onChange={(e) => setDepartment(e.target.value)}>
              {(departments ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="note-week-label">Week</label>
              <input id="note-week-label" value={weekLabel} onChange={(e) => setWeekLabel(e.target.value)} placeholder="e.g. 11–17 Aug 2026" required />
            </div>
            <div className="field">
              <label htmlFor="note-week-start">Week starting</label>
              <input id="note-week-start" type="date" value={weekStart} onChange={(e) => setWeekStart(e.target.value)} required />
            </div>
          </div>
          <div className="field">
            <label htmlFor="note-highlights">Highlights</label>
            <textarea id="note-highlights" value={highlights} onChange={(e) => setHighlights(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="note-challenges">Challenges</label>
            <textarea id="note-challenges" value={challenges} onChange={(e) => setChallenges(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="note-prayer">Prayer points / needs</label>
            <textarea id="note-prayer" value={prayerPoints} onChange={(e) => setPrayerPoints(e.target.value)} />
          </div>
          <button className="btn" type="submit" disabled={createNote.isPending || updateNote.isPending}>
            {editId ? 'Save changes' : 'Submit note'}
          </button>
          {editId && <button className="btn ghost" type="button" onClick={cancelEdit}>Cancel</button>}
        </form>
      </div>

      <div className="card">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>Recent notes</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select className="selectbox" value={deptFilter} onChange={(e) => { setDeptFilter(e.target.value); setPage(1); }}>
              <option value="all">All departments</option>
              {(departments ?? []).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
            <select className="selectbox" value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="-week_start">Newest first</option>
              <option value="week_start">Oldest first</option>
            </select>
          </div>
        </div>
        {(notes?.results ?? []).length ? notes!.results.map((n) => (
          <div key={n.id} style={{ padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div><b>{n.department_name}</b> <span className="muted">· {n.week_label}</span></div>
              <div className="row-actions">
                <button className="icon-btn edit" onClick={() => startEdit(n)}><Icon name="edit" size={14} /></button>
                <button className="icon-btn" onClick={() => handleDelete(n.id)}><Icon name="trash" size={14} /></button>
              </div>
            </div>
            <div style={{ fontSize: '.85rem', marginTop: 4 }}><b>Highlights:</b> {n.highlights}</div>
            <div style={{ fontSize: '.85rem' }}><b>Challenges:</b> {n.challenges}</div>
          </div>
        )) : <div className="empty">No notes match these filters.</div>}
      </div>
    </div>
  );
}
