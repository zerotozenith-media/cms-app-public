import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAllNewcomers, useNewcomers, useChangeStageForAnyNewcomer } from '../../api/newcomers';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { KanbanBoard } from '../../components/newcomers/KanbanBoard';
import { Pagination } from '../../components/ui/Pagination';
import { Badge } from '../../components/ui/Badge';
import type { Newcomer, NewcomerStage } from '../../types/newcomers';

function stageBadgeColor(stage: NewcomerStage): 'blue' | 'green' | 'gray' {
  if (stage === 'integrated') return 'green';
  if (stage === 'not-interested') return 'gray';
  return 'blue';
}
function stageLabel(stage: NewcomerStage): string {
  const map: Record<NewcomerStage, string> = {
    new: 'New', contacted: 'Contacted', visiting: 'Visiting', integrated: 'Integrated', 'not-interested': 'Not Interested',
  };
  return map[stage];
}

export function NewcomersListPage() {
  const navigate = useNavigate();
  const { data: allNewcomers } = useAllNewcomers();
  const [stageFilter, setStageFilter] = useState('active');
  const [sort, setSort] = useState('name-asc');
  const [page, setPage] = useState(1);
  const pageSize = 8;

  const orderingMap: Record<string, string> = {
    'name-asc': 'name', 'created-desc': '-created_at', 'created-asc': 'created_at', 'days-desc': '-stage_since',
  };
  const { data: pagedList, isLoading } = useNewcomers({
    ordering: orderingMap[sort] ?? 'name',
    page, page_size: pageSize,
  });

  // Stage filtering happens client-side against the paged results , the
  // "active stages" default and specific-stage filters are cheap boolean
  // checks on an already-small page, unlike the counts on the stat-row,
  // which need the full unfiltered set.
  const filteredResults = (pagedList?.results ?? []).filter((n) => {
    if (stageFilter === 'active') return n.stage !== 'not-interested';
    if (stageFilter === 'all') return true;
    return n.stage === stageFilter;
  });

  const active = (allNewcomers ?? []).filter((n) => n.stage !== 'not-interested');
  const thisMonthPrefix = new Date().toISOString().slice(0, 7);
  const newThisMonth = (allNewcomers ?? []).filter((n) => n.created_at.slice(0, 7) === thisMonthPrefix).length;
  const overdueCount = active.filter((n) => n.open_tasks_count > 0 && n.urgency === 'red').length;
  const unassignedCount = active.filter((n) => !n.assigned_to_name && n.stage !== 'integrated').length;

  const stats: StatItem[] = [
    { icon: 'users', color: 'blue', label: 'In the pipeline', value: active.length },
    { icon: 'userplus', color: 'blue', label: 'New this month', value: newThisMonth },
    { icon: 'alert', color: overdueCount ? 'red' : 'gray', label: 'Overdue follow-ups', value: overdueCount, valueColor: overdueCount ? 'var(--red)' : undefined },
    { icon: 'user', color: unassignedCount ? 'amber' : 'gray', label: 'Unassigned', value: unassignedCount, valueColor: unassignedCount ? 'var(--amber)' : undefined },
  ];

  const changeStage = useChangeStageForAnyNewcomer();
  function handleDrop(id: number, stage: NewcomerStage) {
    changeStage.mutate({ id, to_stage: stage });
  }

  const totalPages = pagedList ? Math.max(1, Math.ceil(pagedList.count / pageSize)) : 1;

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab active">Pipeline</button>
          <button className="tab" onClick={() => navigate('/newcomers/follow-up')}>Follow-up</button>
          <button className="tab" onClick={() => navigate('/newcomers/qr')}>QR Registration</button>
          <button className="tab" onClick={() => navigate('/newcomers/manual')}>Manual Entry</button>
        </div>
      </div>

      <StatRow stats={stats} />

      <KanbanBoard
        newcomers={active}
        onCardClick={(id) => navigate(`/newcomers/${id}`)}
        onDropToStage={handleDrop}
      />

      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>All newcomers</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select className="selectbox" value={stageFilter} onChange={(e) => { setStageFilter(e.target.value); setPage(1); }}>
              <option value="active">Active stages</option>
              <option value="all">All stages</option>
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="visiting">Visiting</option>
              <option value="integrated">Integrated</option>
              <option value="not-interested">Not Interested</option>
            </select>
            <select className="selectbox" value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="name-asc">Sort: Name A-Z</option>
              <option value="created-desc">Sort: Newest first</option>
              <option value="created-asc">Sort: Oldest first</option>
            </select>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead><tr><th>Name</th><th>Stage</th><th>Assigned</th><th>Days in stage</th><th>Source</th><th>Location</th></tr></thead>
            <tbody>
              {filteredResults.map((n: Newcomer) => (
                <tr key={n.id} className="clickable" onClick={() => navigate(`/newcomers/${n.id}`)}>
                  <td data-label="Name"><b>{n.name}</b></td>
                  <td data-label="Stage"><Badge color={stageBadgeColor(n.stage)}>{stageLabel(n.stage)}</Badge></td>
                  <td data-label="Assigned">{n.assigned_to_name || 'Unassigned'}</td>
                  <td data-label="Days in stage">{n.days_in_stage}d</td>
                  <td data-label="Source">{n.source_name}</td>
                  <td data-label="Location">{n.location}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && filteredResults.length === 0 && <div className="empty">No newcomers match these filters.</div>}
        </div>
        {pagedList && (
          <Pagination page={page} totalPages={totalPages} totalCount={pagedList.count} pageSize={pageSize} onPageChange={setPage} />
        )}
      </div>
    </>
  );
}
