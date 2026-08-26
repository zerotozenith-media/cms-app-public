import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnquiries, useEnquiryStats, useChangeEnquiryStage } from '../../api/enquiries';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { Badge } from '../../components/ui/Badge';
import { EnquiryKanbanBoard } from '../../components/enquiries/EnquiryKanbanBoard';
import { Icon } from '../../components/ui/Icon';
import type { Enquiry, EnquiryStage } from '../../types/enquiries';

/**
 * Same pipeline pattern as Newcomers, on purpose: a worker who has
 * learned one should not have to learn a second.
 *
 * Every card carries a stage dropdown as well as being draggable.
 * HTML5 drag and drop does not work on touch screens at all, so without
 * the dropdown nobody could move anyone along from a phone.
 */
export function EnquiriesPage() {
  const navigate = useNavigate();
  // Campaign data is marketing, not pastoral: the tab only appears for
  // roles granted the outreach permission.
  const { hasPermission } = useAuth();
  const canSeeOutreach = hasPermission('outreach', 'view');
  const { data: enquiries, isLoading } = useEnquiries();
  const { data: stats } = useEnquiryStats();
  const changeStage = useChangeEnquiryStage();

  async function move(enquiry: Enquiry, stage: EnquiryStage) {
    if (enquiry.stage === stage) return;
    let note = '';
    if (stage === 'not-pursuing') {
      // A record saying someone was dropped, with no reason, helps
      // nobody reading it later.
      const entered = window.prompt('Why are we not pursuing this enquiry?');
      if (!entered) return;
      note = entered;
    }
    await changeStage.mutateAsync({ id: enquiry.id, stage, note });
  }

  const all = enquiries ?? [];
  const notPursuing = all.filter((e) => e.stage === 'not-pursuing');

  const statItems: StatItem[] = [
    { icon: 'userplus', color: 'blue', label: 'Active enquiries', value: stats?.active ?? 0 },
    {
      icon: 'alert', color: stats?.awaiting_first_contact ? 'amber' : 'gray',
      label: 'Awaiting first contact', value: stats?.awaiting_first_contact ?? 0,
      valueColor: stats?.awaiting_first_contact ? 'var(--amber)' : undefined,
    },
    {
      icon: 'alert', color: stats?.overdue_tasks ? 'red' : 'gray',
      label: 'Overdue follow-ups', value: stats?.overdue_tasks ?? 0,
      valueColor: stats?.overdue_tasks ? 'var(--red)' : undefined,
    },
    { icon: 'check', color: 'green', label: 'Became newcomers', value: stats?.converted ?? 0 },
  ];

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab active">Pipeline</button>
          <button className="tab" onClick={() => navigate('/enquiries/new')}>Add enquiry</button>
          {canSeeOutreach && (
            <button className="tab" onClick={() => navigate('/enquiries/outreach')}>Outreach</button>
          )}
        </div>
      </div>

      <StatRow stats={statItems} />

      {isLoading && <div className="card section-gap">Loading…</div>}

      <EnquiryKanbanBoard
        enquiries={all}
        onCardClick={(id) => navigate(`/enquiries/${id}`)}
        onDropToStage={(id: number, stage) => {
          const enquiry = all.find((x) => x.id === id);
          if (enquiry) move(enquiry, stage);
        }}
        onSelectStage={move}
      />

      <div className="muted" style={{ fontSize: '.8rem', marginTop: 10 }}>
        Drag a card between columns, or use the dropdown on each card. The dropdown is
        there because dragging does not work on phones and tablets.
      </div>

      {notPursuing.length > 0 && (
        <div className="card section-gap">
          <h3>Not pursuing</h3>
          {notPursuing.map((e) => (
            <div key={e.id} className="followup-row">
              <span className="avatar">{e.name.charAt(0)}</span>
              <div className="followup-row-info">
                <b style={{ cursor: 'pointer', color: 'var(--blue-deep)' }}
                  onClick={() => navigate(`/enquiries/${e.id}`)}>{e.name}</b>
                {' '}<Badge color="gray">{e.source_name}</Badge>
                <div className="muted" style={{ fontSize: '.8rem' }}>{e.not_pursuing_note}</div>
              </div>
              <div className="followup-row-actions">
                <button className="btn sm outline" onClick={() => move(e, 'contacted')}>
                  <Icon name="check" size={14} /> Reactivate
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
