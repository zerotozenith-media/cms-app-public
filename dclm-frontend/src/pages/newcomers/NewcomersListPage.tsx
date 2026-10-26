import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAllNewcomers, useChangeStageForAnyNewcomer } from '../../api/newcomers';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { Skeleton } from '../../components/ui/Skeleton';
import { KanbanBoard } from '../../components/newcomers/KanbanBoard';
import { Pagination } from '../../components/ui/Pagination';
import { Badge } from '../../components/ui/Badge';
import type { Newcomer, NewcomerStage } from '../../types/newcomers';
import { useLocationName } from '../../api/locations';
import { useAuth } from '../../context/AuthContext';
import { useEligibleShepherds } from '../../api/followup';
import { canPair } from '../../lib/gender';
import { apiClient } from '../../api/client';
import { refusal } from '../../api/accountability';
import { useMutation, useQueryClient } from '@tanstack/react-query';

function stageBadgeColor(stage: NewcomerStage): 'blue' | 'green' | 'gray' {
  if (stage === 'member') return 'green';
  if (stage === 'not-interested') return 'gray';
  return 'blue';
}
function stageLabel(stage: NewcomerStage): string {
  const map: Record<NewcomerStage, string> = {
    new: 'New', contacted: 'Contacted', attending: 'Attending', member: 'Member', 'not-interested': 'Not Interested',
  };
  return map[stage];
}

export function NewcomersListPage() {
  const locationName = useLocationName();
  const { hasPermission } = useAuth();
  const canMove = hasPermission('newcomers', 'edit');
  const canMakeMember = canMove && hasPermission('members', 'create');
  const navigate = useNavigate();
  const { data: allNewcomers } = useAllNewcomers();
  const [stageFilter, setStageFilter] = useState('active');
  const [shepherdFilter, setShepherdFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [sort, setSort] = useState('days-desc');
  const [view, setView] = useState<'board' | 'table'>('board');
  const [page, setPage] = useState(1);
  const pageSize = 12;
  // Item 13 (Kay): tick several and give them one shepherd.
  const qc = useQueryClient();
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [bulkTo, setBulkTo] = useState('');
  const [bulkMsg, setBulkMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const { data: eligible } = useEligibleShepherds();
  const bulk = useMutation({
    mutationFn: async () => (await apiClient.post('/newcomers-bulk-assign/', { newcomer_ids: [...picked], shepherd_id: Number(bulkTo) })).data,
    onSuccess: (d: any) => {
      setBulkMsg({ ok: true, text: `${d.updated} given to ${d.shepherd}. Their open tasks moved too.` });
      setPicked(new Set()); setBulkTo('');
      qc.invalidateQueries({ queryKey: ['newcomers-all'] });
    },
    onError: (e) => setBulkMsg({ ok: false, text: refusal(e, 'Not saved. Try again.') }),
  });
  const toggle = (id: number) => { const s2 = new Set(picked); if (s2.has(id)) s2.delete(id); else s2.add(id); setPicked(s2); setBulkMsg(null); };

  const everyone = allNewcomers ?? [];
  const shepherds = [...new Set(everyone.map((n) => n.assigned_to_name).filter(Boolean))].sort() as string[];
  const sources = [...new Set(everyone.map((n) => n.source_name).filter(Boolean))].sort() as string[];

  const filtered = everyone.filter((n) => {
    if (stageFilter === 'active' && n.stage === 'not-interested') return false;
    if (stageFilter !== 'active' && stageFilter !== 'all' && n.stage !== stageFilter) return false;
    if (shepherdFilter === 'none' && n.assigned_to_name) return false;
    if (shepherdFilter !== 'all' && shepherdFilter !== 'none' && n.assigned_to_name !== shepherdFilter) return false;
    if (sourceFilter !== 'all' && n.source_name !== sourceFilter) return false;
    return true;
  });
  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'name-asc') return a.name.localeCompare(b.name);
    if (sort === 'created-desc') return b.created_at.localeCompare(a.created_at);
    return b.days_in_stage - a.days_in_stage;
  });
  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const pageRows = sorted.slice((page - 1) * pageSize, page * pageSize);

  // The heading names what is shown. "All newcomers" over a filtered list
  // is untrue, and somebody will read the number off it in a meeting.
  const headingBits: string[] = [];
  if (stageFilter !== 'active' && stageFilter !== 'all') headingBits.push(stageLabel(stageFilter as NewcomerStage));
  if (shepherdFilter === 'none') headingBits.push('with no shepherd');
  else if (shepherdFilter !== 'all') headingBits.push(`assigned to ${shepherdFilter}`);
  if (sourceFilter !== 'all') headingBits.push(`from ${sourceFilter}`);
  const heading = headingBits.length ? `Newcomers ${headingBits.join(', ')}` : 'Newcomer pipeline';
  const baseCount = everyone.filter((n) => n.stage !== 'not-interested').length;
  const subhead = !allNewcomers ? 'Loading' : headingBits.length || stageFilter === 'all'
    ? `${filtered.length} of ${everyone.length} shown`
    : `${filtered.length} in the pipeline`;
  void baseCount;

  const active = (allNewcomers ?? []).filter((n) => n.stage !== 'not-interested');
  const thisMonthPrefix = new Date().toISOString().slice(0, 7);
  const newThisMonth = (allNewcomers ?? []).filter((n) => n.created_at.slice(0, 7) === thisMonthPrefix).length;
  const overdueCount = active.filter((n) => n.open_tasks_count > 0 && n.urgency === 'red').length;
  const unassignedCount = active.filter((n) => !n.assigned_to_name && n.stage !== 'member').length;

  const stats: StatItem[] = [
    { icon: 'users', color: 'blue', label: 'In the pipeline', value: active.length },
    { icon: 'userplus', color: 'blue', label: 'New this month', value: newThisMonth },
    { icon: 'alert', color: overdueCount ? 'red' : 'gray', label: 'Overdue follow-ups', value: overdueCount, valueColor: overdueCount ? 'var(--red)' : undefined },
    { icon: 'user', color: unassignedCount ? 'amber' : 'gray', label: 'Unassigned', value: unassignedCount, valueColor: unassignedCount ? 'var(--amber)' : undefined },
  ];

  const changeStage = useChangeStageForAnyNewcomer();
  function handleDrop(id: number, stage: NewcomerStage) {
    // Becoming a member adds them to the member roll, which needs the
    // Members permission as well.
    if (stage === 'member' && !canMakeMember) {
      alert('Making someone a member needs permission to add members. Ask an administrator.');
      return;
    }
    // Becoming a member adds them to the member roll, so it is confirmed
    // rather than happening on a stray drop.
    if (stage === 'member') {
      const who = everyone.find((n) => n.id === id)?.name ?? 'this person';
      if (!confirm(`Make ${who} a member? They will be added to the member roll.`)) return;
    }
    changeStage.mutate({ id, to_stage: stage });
  }


  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab active">Pipeline</button>
          <button className="tab" onClick={() => navigate('/newcomers/follow-up')}>Follow-up</button>
          <button className="tab" onClick={() => navigate('/newcomers/messages')}>Messages</button>
          <button className="tab" onClick={() => navigate('/newcomers/qr')}>QR Registration</button>
          <button className="tab" onClick={() => navigate('/newcomers/manual')}>Manual Entry</button>
        </div>
      </div>

      <StatRow stats={stats} loading={!allNewcomers} />

      <div className="card section-gap">
        <div className="toolbar">
          <div style={{ flex: 'none' }}>
            <h3 style={{ margin: 0 }}>{heading}</h3>
            <div className="muted" style={{ fontSize: '.8rem' }}>{subhead}</div>
          </div>
          <div className="viewtoggle" role="group" aria-label="Choose a view">
            <button className={view === 'board' ? 'on' : ''} onClick={() => setView('board')}>Board</button>
            <button className={view === 'table' ? 'on' : ''} onClick={() => setView('table')}>Table</button>
          </div>
        </div>

        <div className="nc-filters">
          <select className="selectbox" value={stageFilter} aria-label="Stage"
            onChange={(e) => { setStageFilter(e.target.value); setPage(1); }}>
            <option value="active">Active stages</option>
            <option value="all">All stages</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="attending">Attending</option>
            <option value="member">Member</option>
            <option value="not-interested">Not Interested</option>
          </select>
          <select className="selectbox" value={shepherdFilter} aria-label="Shepherd"
            onChange={(e) => { setShepherdFilter(e.target.value); setPage(1); }}>
            <option value="all">All shepherds</option>
            <option value="none">No shepherd</option>
            {shepherds.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="selectbox" value={sourceFilter} aria-label="Source"
            onChange={(e) => { setSourceFilter(e.target.value); setPage(1); }}>
            <option value="all">All sources</option>
            {sources.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select className="selectbox" value={sort} aria-label="Sort"
            onChange={(e) => setSort(e.target.value)}>
            <option value="days-desc">Longest waiting</option>
            <option value="name-asc">Name A to Z</option>
            <option value="created-desc">Newest first</option>
          </select>
        </div>

        {!allNewcomers ? (
          <Skeleton shape={view === 'board' ? 'board' : 'rows'} />
        ) : view === 'board' ? (
          <KanbanBoard
            newcomers={filtered}
            onCardClick={(id) => navigate(`/newcomers/${id}`)}
            onDropToStage={handleDrop}
            canMove={canMove}
            onOpenMembers={() => navigate('/members?from=pipeline')}
          />
        ) : (
          <>
            {canMove && picked.size > 0 && (() => {
              const chosen = everyone.filter((n) => picked.has(n.id));
              const fits = (eligible ?? []).filter((s: any) => chosen.every((n) => canPair((n as any).gender ?? '', s.gender)));
              return (
                <div className="bulk-bar">
                  <span><b>{picked.size}</b> selected</span>
                  <select className="selectbox" aria-label="Shepherd for the selected newcomers" value={bulkTo} onChange={(e) => setBulkTo(e.target.value)}>
                    <option value="">Choose shepherd</option>
                    {fits.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                  <button className="btn sm" disabled={!bulkTo || bulk.isPending} onClick={() => bulk.mutate()}>Assign</button>
                  <button className="btn sm ghost" onClick={() => { setPicked(new Set()); setBulkMsg(null); }}>Clear</button>
                  <span className="muted" style={{ fontSize: '.8rem' }}>Only shepherds who may take all {picked.size} are offered: men for men, women for women.</span>
                </div>
              );
            })()}
            {bulkMsg && <p className={bulkMsg.ok ? 'fr-done' : 'form-error'} role={bulkMsg.ok ? 'status' : 'alert'}>{bulkMsg.text}</p>}
            <div style={{ overflowX: 'auto' }}>
              <table className="cardtable">
                <thead><tr>
                  {canMove && <th style={{ width: 34 }}><input type="checkbox" aria-label="Select all on this page"
                    checked={pageRows.length > 0 && pageRows.every((n: Newcomer) => picked.has(n.id))}
                    onChange={(e) => { const s2 = new Set(picked); pageRows.forEach((n: Newcomer) => e.target.checked ? s2.add(n.id) : s2.delete(n.id)); setPicked(s2); }} /></th>}
                  <th>Name</th><th>Stage</th><th>Shepherd</th><th>Waiting</th><th>Source</th><th>Location</th>
                </tr></thead>
                <tbody>
                  {pageRows.map((n: Newcomer) => (
                    <tr key={n.id} className="clickable" onClick={() => navigate(`/newcomers/${n.id}`)} style={picked.has(n.id) ? { background: '#F3F7FC' } : undefined}>
                      {canMove && <td data-label="Select" onClick={(e) => e.stopPropagation()}><input type="checkbox" aria-label={`Select ${n.name}`} checked={picked.has(n.id)} onChange={() => toggle(n.id)} /></td>}
                      <td data-label="Name"><b>{n.name}</b></td>
                      <td data-label="Stage"><Badge color={stageBadgeColor(n.stage)}>{stageLabel(n.stage)}</Badge></td>
                      <td data-label="Shepherd">
                        {n.assigned_to_name || <Badge color="amber">Unassigned</Badge>}
                      </td>
                      <td data-label="Waiting">{n.days_in_stage}d</td>
                      <td data-label="Source">{n.source_name}</td>
                      <td data-label="Location">{locationName(n.location)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {pageRows.length === 0 && <div className="empty">Nobody matches those filters.</div>}
            </div>
            {sorted.length > pageSize && (
              <Pagination page={page} totalPages={totalPages} totalCount={sorted.length}
                pageSize={pageSize} onPageChange={setPage} />
            )}
          </>
        )}
      </div>
    </>
  );
}
