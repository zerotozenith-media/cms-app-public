import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMembers, useMemberStats, useDeleteMember } from '../../api/members';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import {
  useFollowUpStats, useEligibleShepherds,
  useAssignmentPreview, useApplyAssignment, useBulkAssignShepherd,
} from '../../api/followup';
import { AssignmentPreviewPanel } from '../../components/members/AssignmentPreviewPanel';
import { Pagination } from '../../components/ui/Pagination';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { HelpMark } from '../../components/ui/HelpMark';

function categoryBadgeColor(cat: string): 'green' | 'amber' | 'gray' {
  if (cat === 'Worker') return 'green';
  if (cat === 'Worker in Training') return 'amber';
  return 'gray';
}

export function MembersListPage() {
  const navigate = useNavigate();
  // Shown on the tab so a leader sees what is waiting without opening it.
  const { data: followUpStats } = useFollowUpStats();
  const openFollowUps = followUpStats?.open_followups ?? 0;
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');

  // Assignment state. previewMode is null when no preview is open, so a
  // preview is only ever fetched after the admin asks for one.
  const [previewMode, setPreviewMode] = useState<null | 'unassigned' | 'everyone'>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [bulkShepherd, setBulkShepherd] = useState('');

  const { data: shepherds } = useEligibleShepherds();
  const preview = useAssignmentPreview(previewMode === 'everyone', previewMode !== null);
  const applyAssignment = useApplyAssignment();
  const bulkAssign = useBulkAssignShepherd();

  const [ordering, setOrdering] = useState('surname,first_name');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useMembers({
    search: query || undefined,
    category: category !== 'all' ? category : undefined,
    ordering,
    page,
  });
  const deleteMember = useDeleteMember();
  // Only the rows currently on screen, so "select all" means this page
  // rather than silently selecting members the admin cannot see.
  const pageIds = (data?.results ?? []).map((m) => m.id);

  const { data: memberStats } = useMemberStats();
  const stats: StatItem[] = [
    { icon: 'users', color: 'blue', label: 'Total members', value: memberStats?.total ?? 0 },
    { icon: 'check', color: 'green', label: 'Workers', value: memberStats?.workers ?? 0 },
    { icon: 'target', color: 'amber', label: 'Workers in Training', value: memberStats?.workers_in_training ?? 0 },
    { icon: 'user', color: 'gray', label: 'General Members', value: memberStats?.general_members ?? 0 },
  ];

  const pageSize = 8;
  const totalPages = data ? Math.max(1, Math.ceil(data.count / pageSize)) : 1;

  async function handleDelete(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (!confirm('Delete this member?')) return;
    await deleteMember.mutateAsync(id);
  }

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab active">Directory</button>
          <button className="tab" onClick={() => navigate('/members/follow-up')}>
            Follow-up{openFollowUps ? ` (${openFollowUps})` : ''}
          </button>
        </div>
      </div>

      <StatRow stats={stats} />

      <div className="card">
        <div className="toolbar">
          <input
            className="search"
            placeholder="Search members..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
          />
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select
              className="selectbox"
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
            >
              <option value="all">All categories</option>
              <option value="General Member">General Member</option>
              <option value="Worker in Training">Worker in Training</option>
              <option value="Worker">Worker</option>
            </select>
            <select className="selectbox" value={ordering} onChange={(e) => setOrdering(e.target.value)}>
              <option value="surname,first_name">Sort: Name A-Z</option>
              <option value="-joined_date">Sort: Newest joined</option>
              <option value="joined_date">Sort: Oldest joined</option>
              <option value="category">Sort: Category</option>
            </select>
            <a className="btn sm outline" onClick={() => setPreviewMode('unassigned')}>
              <Icon name="users" size={15} /> Auto-assign
            </a>
            <HelpMark topic="autoAssign" />
            <a className="btn sm" onClick={() => navigate('/members/new')}>
              <Icon name="plus" size={15} /> Add member
            </a>
          </div>
        </div>

        {previewMode && preview.data && preview.data.changes.length > 0 && (
          <AssignmentPreviewPanel
            changes={preview.data.changes}
            reassignEveryone={previewMode === 'everyone'}
            applying={applyAssignment.isPending}
            onCancel={() => setPreviewMode(null)}
            onSwitchToReassignEveryone={() => setPreviewMode('everyone')}
            onApply={async () => {
              await applyAssignment.mutateAsync(preview.data!.changes);
              setPreviewMode(null);
            }}
          />
        )}
        {previewMode && preview.data && preview.data.changes.length === 0 && (
          <div className="assign-preview">
            Nothing to assign. Everyone in scope already has a shepherd.
            <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn sm ghost" onClick={() => setPreviewMode(null)}>Close</button>
              {previewMode === 'unassigned' && (
                <button className="btn sm outline" onClick={() => setPreviewMode('everyone')}>
                  Reassign everyone instead
                </button>
              )}
            </div>
          </div>
        )}
        {previewMode && preview.isError && (
          <div className="form-error">
            {(preview.error as any)?.response?.data?.detail
              ?? 'Could not work out an assignment. Check that at least one member is in the Worker category.'}
            <button className="btn sm ghost" style={{ marginLeft: 8 }} onClick={() => setPreviewMode(null)}>Close</button>
          </div>
        )}

        {selected.length > 0 && (
          <div className="bulk-bar">
            <span><b>{selected.length}</b> selected</span>
            <label htmlFor="bulk-shepherd" className="sr-only">Shepherd</label>
            <select id="bulk-shepherd" className="selectbox" value={bulkShepherd}
              onChange={(e) => setBulkShepherd(e.target.value)}>
              <option value="">Choose shepherd…</option>
              {(shepherds ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <button className="btn sm" disabled={!bulkShepherd || bulkAssign.isPending}
              onClick={async () => {
                await bulkAssign.mutateAsync({ memberIds: selected, shepherdId: Number(bulkShepherd) });
                setSelected([]); setBulkShepherd('');
              }}>Assign</button>
            <button className="btn sm ghost" onClick={() => setSelected([])}>Clear</button>
          </div>
        )}

        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead>
              <tr>
                <th style={{ width: 34 }}>
                  <input
                    type="checkbox"
                    aria-label="Select all on this page"
                    checked={pageIds.length > 0 && pageIds.every((id) => selected.includes(id))}
                    onChange={(e) => {
                      setSelected(e.target.checked
                        ? [...new Set([...selected, ...pageIds])]
                        : selected.filter((id) => !pageIds.includes(id)));
                    }}
                  />
                </th>
                <th>Name</th>
                <th>Category</th>
                <th>Shepherd<HelpMark topic="shepherd" /></th>
                <th>Household</th>
                <th>Location</th>
                <th>Joined</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((m) => (
                <tr key={m.id} className="clickable" onClick={() => navigate(`/members/${m.id}`)}>
                  <td data-label="Select" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      aria-label={`Select ${m.full_name}`}
                      checked={selected.includes(m.id)}
                      onChange={() => setSelected(selected.includes(m.id)
                        ? selected.filter((id) => id !== m.id)
                        : [...selected, m.id])}
                    />
                  </td>
                  <td data-label="Name"><b>{m.full_name}</b></td>
                  <td data-label="Category">
                    <Badge color={categoryBadgeColor(m.category)}>{m.category}</Badge>
                  </td>
                  <td data-label="Shepherd">{m.assigned_to_name || <span className="muted">Unassigned</span>}</td>
                  <td data-label="Household">{m.household_name || <span className="muted">–</span>}</td>
                  <td data-label="Location">{m.location}</td>
                  <td data-label="Joined">{m.joined_date}</td>
                  <td className="td-actions" onClick={(e) => e.stopPropagation()}>
                    <button className="icon-btn" title="Delete member" onClick={(e) => handleDelete(e, m.id)}>
                      <Icon name="trash" size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && data?.results.length === 0 && <div className="empty">No members match these filters.</div>}
        </div>

        {data && (
          <Pagination page={page} totalPages={totalPages} totalCount={data.count} pageSize={pageSize} onPageChange={setPage} />
        )}
      </div>
    </>
  );
}
