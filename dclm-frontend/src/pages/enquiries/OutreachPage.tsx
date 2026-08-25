import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCampaigns, useCampaignSummary, useCreateCampaign, useDeleteCampaign } from '../../api/campaigns';
import { useEnquirySources } from '../../api/enquiries';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';

function money(v: number | null) {
  return v === null ? '–' : `BHD ${v.toFixed(2)}`;
}

/**
 * Which outreach streams actually work.
 *
 * The figure worth watching is cost per newcomer: what the church paid
 * for each person who walked through the door, not each click. Cost per
 * enquiry flatters a campaign that generates messages from people who
 * never turn up.
 */
export function OutreachPage() {
  const navigate = useNavigate();
  const { data: campaigns, isLoading } = useCampaigns();
  const { data: summary } = useCampaignSummary();
  const { data: sources } = useEnquirySources();
  const createCampaign = useCreateCampaign();
  const deleteCampaign = useDeleteCampaign();

  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [source, setSource] = useState('');
  const [spend, setSpend] = useState('');
  const [startedOn, setStartedOn] = useState('');
  const [error, setError] = useState<string | null>(null);

  const stats: StatItem[] = [
    { icon: 'coin', color: 'blue', label: 'Spend, all campaigns', value: money(summary?.total_spend ?? 0) },
    { icon: 'userplus', color: 'blue', label: 'Enquiries received', value: summary?.total_enquiries ?? 0 },
    { icon: 'check', color: 'green', label: 'Became newcomers', value: summary?.total_converted ?? 0 },
    { icon: 'target', color: 'gray', label: 'Cost per newcomer', value: money(summary?.cost_per_newcomer ?? null) },
  ];

  async function handleCreate() {
    if (!name.trim()) { setError('Give the campaign a name.'); return; }
    setError(null);
    await createCampaign.mutateAsync({
      name: name.trim(),
      source: source ? Number(source) : null,
      spend: spend || '0',
      started_on: startedOn || null,
    } as any);
    setName(''); setSource(''); setSpend(''); setStartedOn(''); setShowForm(false);
  }

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab" onClick={() => navigate('/enquiries')}>Pipeline</button>
          <button className="tab" onClick={() => navigate('/enquiries/new')}>Add enquiry</button>
          <button className="tab active">Outreach</button>
        </div>
      </div>

      <StatRow stats={stats} />

      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>Which streams actually work</h3>
          <button className="btn sm" onClick={() => setShowForm(!showForm)}>
            <Icon name="plus" size={14} /> Add campaign
          </button>
        </div>

        {showForm && (
          <div className="form-card" style={{ marginBottom: 14 }}>
            <div className="form-row">
              <div className="field">
                <label htmlFor="camp-name">Campaign name</label>
                <input id="camp-name" value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Christmas Service 2026" />
              </div>
              <div className="field">
                <label htmlFor="camp-source">Platform</label>
                <select id="camp-source" value={source} onChange={(e) => setSource(e.target.value)}>
                  <option value="">Not one platform</option>
                  {(sources ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label htmlFor="camp-spend">Spend (BHD)</label>
                <input id="camp-spend" type="number" step="0.001" value={spend}
                  onChange={(e) => setSpend(e.target.value)} placeholder="0 for organic" />
              </div>
              <div className="field">
                <label htmlFor="camp-start">Started on</label>
                <input id="camp-start" type="date" value={startedOn}
                  onChange={(e) => setStartedOn(e.target.value)} />
              </div>
            </div>
            {error && <div className="form-error">{error}</div>}
            <button className="btn sm" onClick={handleCreate} disabled={createCampaign.isPending}>Save campaign</button>
            <button className="btn sm ghost" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        )}

        {isLoading && <div className="empty">Loading…</div>}

        {!isLoading && (campaigns ?? []).length === 0 && (
          <div className="empty">
            No campaigns yet. Add one to see what each advert costs per person reached.
          </div>
        )}

        {!isLoading && (campaigns ?? []).length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table className="cardtable">
              <thead>
                <tr>
                  <th>Campaign</th><th>Platform</th><th>Spend</th>
                  <th>Enquiries</th><th>Attended</th><th>Conversion</th>
                  <th>Cost per enquiry</th><th>Cost per newcomer</th><th></th>
                </tr>
              </thead>
              <tbody>
                {(campaigns ?? []).map((c) => (
                  <tr key={c.id}>
                    <td data-label="Campaign"><b>{c.name}</b></td>
                    <td data-label="Platform">{c.source_name || '–'}</td>
                    <td data-label="Spend">{Number(c.spend) ? `BHD ${Number(c.spend).toFixed(2)}` : '–'}</td>
                    <td data-label="Enquiries">{c.enquiries_received}</td>
                    <td data-label="Attended">{c.converted}</td>
                    <td data-label="Conversion">
                      <Badge color={c.conversion_rate >= 50 ? 'green' : c.conversion_rate > 0 ? 'amber' : 'gray'}>
                        {c.conversion_rate}%
                      </Badge>
                    </td>
                    <td data-label="Cost per enquiry">{money(c.cost_per_enquiry)}</td>
                    <td data-label="Cost per newcomer">{money(c.cost_per_newcomer)}</td>
                    <td className="td-actions">
                      <button className="icon-btn" title="Delete campaign"
                        onClick={() => { if (confirm(`Delete "${c.name}"? Enquiries keep their records but lose the link.`)) deleteCampaign.mutate(c.id); }}>
                        <Icon name="trash" size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="muted" style={{ fontSize: '.8rem', marginTop: 10 }}>
          Cost per newcomer is the figure worth watching: it says what the church actually
          paid for each person who walked through the door, not each click.
        </div>
      </div>
    </>
  );
}
