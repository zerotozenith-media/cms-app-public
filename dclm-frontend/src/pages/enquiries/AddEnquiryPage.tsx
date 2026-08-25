import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useCreateEnquiry, useEnquirySources } from '../../api/enquiries';
import { useCampaigns } from '../../api/campaigns';
import { useAdminUsers } from '../../api/admin';
import { Icon } from '../../components/ui/Icon';

function today() {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Only a name, a source, and one way to reach them are required.
 *
 * These people are easy to lose: a worker screenshotting a message late
 * at night will abandon a form that demands six fields, and the person
 * is gone. A thin record that can be improved later beats no record.
 */
export function AddEnquiryPage() {
  const navigate = useNavigate();
  // Campaign data is marketing, not pastoral: the tab only appears for
  // roles granted the outreach permission.
  const { hasPermission } = useAuth();
  const canSeeOutreach = hasPermission('outreach', 'view');
  const createEnquiry = useCreateEnquiry();
  const { data: sources } = useEnquirySources();
  const { data: users } = useAdminUsers();
  // Only fetched when the role may see it; a 403 otherwise is expected.
  const { data: campaigns } = useCampaigns();

  const [values, setValues] = useState({
    name: '', source: '', phone: '', email: '', social_handle: '',
    enquiry_text: '', area: '', received_at: today(), assigned_to: '', campaign: '',
  });
  const [error, setError] = useState<string | null>(null);

  function set(field: string, value: string) {
    setValues((v) => ({ ...v, [field]: value }));
  }

  async function handleSubmit() {
    if (!values.name.trim()) { setError('A name is needed, even "Joy from Instagram".'); return; }
    if (!values.source) { setError('Choose where they came through.'); return; }
    if (!values.phone && !values.email && !values.social_handle) {
      setError('Record at least one way to reach them: phone, email, or social handle.');
      return;
    }
    setError(null);
    const created = await createEnquiry.mutateAsync({
      name: values.name.trim(),
      source: Number(values.source),
      phone: values.phone,
      email: values.email,
      social_handle: values.social_handle,
      enquiry_text: values.enquiry_text,
      area: values.area,
      received_at: values.received_at,
      assigned_to: values.assigned_to ? Number(values.assigned_to) : null,
      ...(canSeeOutreach && values.campaign ? { campaign: Number(values.campaign) } : {}),
    } as any);
    navigate(`/enquiries/${created.id}`);
  }

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className="tab" onClick={() => navigate('/enquiries')}>Pipeline</button>
          <button className="tab active">Add enquiry</button>
          {canSeeOutreach && (
            <button className="tab" onClick={() => navigate('/enquiries/outreach')}>Outreach</button>
          )}
        </div>
      </div>

      <div className="card" style={{ maxWidth: 560, margin: '0 auto' }}>
        <h3>Someone contacted us online</h3>
        <p className="muted" style={{ marginBottom: 16 }}>
          For people who messaged the church but have not attended yet. Only a name,
          where they came from, and one way to reach them are required.
        </p>

        <div className="form-row">
          <div className="field">
            <label htmlFor="enq-name">Name <span className="req">*</span></label>
            <input id="enq-name" value={values.name} onChange={(e) => set('name', e.target.value)}
              placeholder="Even 'Joy from Instagram' is fine" />
          </div>
          <div className="field">
            <label htmlFor="enq-source">Came through <span className="req">*</span></label>
            <select id="enq-source" value={values.source} onChange={(e) => set('source', e.target.value)}>
              <option value="">Choose…</option>
              {(sources ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        </div>

        <div className="followup-guide">
          <div className="followup-guide-title">
            <Icon name="alert" size={14} /> At least one way to reach them
          </div>
          <div className="followup-guide-note">
            Any one of the three below is enough. A social handle alone is often all we
            have at first.
          </div>
        </div>

        <div className="form-row">
          <div className="field">
            <label htmlFor="enq-phone">Phone</label>
            <input id="enq-phone" value={values.phone} onChange={(e) => set('phone', e.target.value)}
              placeholder="+973 0000 0000" />
          </div>
          <div className="field">
            <label htmlFor="enq-email">Email</label>
            <input id="enq-email" type="email" value={values.email}
              onChange={(e) => set('email', e.target.value)} />
          </div>
        </div>

        <div className="field">
          <label htmlFor="enq-handle">Social handle</label>
          <input id="enq-handle" value={values.social_handle}
            onChange={(e) => set('social_handle', e.target.value)} placeholder="@username" />
        </div>

        <div className="field">
          <label htmlFor="enq-text">What they asked about</label>
          <textarea id="enq-text" rows={2} value={values.enquiry_text}
            onChange={(e) => set('enquiry_text', e.target.value)}
            placeholder="Their words where possible" />
        </div>

        <div className="form-row">
          <div className="field">
            <label htmlFor="enq-area">Where they are</label>
            <input id="enq-area" value={values.area} onChange={(e) => set('area', e.target.value)}
              placeholder="May be outside Bahrain" />
          </div>
          <div className="field">
            <label htmlFor="enq-received">Date received</label>
            <input id="enq-received" type="date" value={values.received_at}
              onChange={(e) => set('received_at', e.target.value)} />
          </div>
        </div>

        <div className="field">
          <label htmlFor="enq-assigned">Assign to</label>
          <select id="enq-assigned" value={values.assigned_to}
            onChange={(e) => set('assigned_to', e.target.value)}>
            <option value="">Unassigned</option>
            {(users ?? []).map((u) => (
              <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
            ))}
          </select>
        </div>

        {canSeeOutreach && (
          <div className="field">
            <label htmlFor="enq-campaign">Campaign</label>
            <select id="enq-campaign" value={values.campaign}
              onChange={(e) => set('campaign', e.target.value)}>
              <option value="">Not from a campaign</option>
              {(campaigns ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <div className="field-hint">
              Only visible to roles with outreach access. Follow-up workers never see this.
            </div>
          </div>
        )}

        {error && <div className="form-error">{error}</div>}

        <button className="btn" onClick={handleSubmit} disabled={createEnquiry.isPending}>
          Add enquiry
        </button>
      </div>
    </>
  );
}
