import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMember, useUpdateMember, useDeleteMember, useMoveCategory } from '../../api/members';
import { useLocations } from '../../api/locations';
import { apiClient } from '../../api/client';
import { useQuery } from '@tanstack/react-query';
import { MemberFormFields, type MemberFormValues } from './MemberFormFields';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';
import { fmt } from '../../lib/format';
import type { Household, Member } from '../../types/members';

const CATEGORIES = ['General Member', 'Worker in Training', 'Worker'];

function categoryBadgeColor(cat: string): 'green' | 'amber' | 'gray' {
  if (cat === 'Worker') return 'green';
  if (cat === 'Worker in Training') return 'amber';
  return 'gray';
}

function toFormValues(m: Member): MemberFormValues {
  return {
    surname: m.surname, first_name: m.first_name, other_names: m.other_names,
    gender: m.gender || 'Male', date_of_birth: m.date_of_birth || '',
    phone: m.phone, email: m.email, category: m.category,
    location: m.location, household: m.household ? String(m.household) : '', joined_date: m.joined_date,
  };
}

export function MemberProfilePage() {
  const { id } = useParams();
  const memberId = Number(id);
  const navigate = useNavigate();
  const { data: member, isLoading } = useMember(memberId);
  const { data: locations } = useLocations();
  const updateMember = useUpdateMember(memberId);
  const deleteMember = useDeleteMember();
  const moveCategory = useMoveCategory(memberId);

  const [editing, setEditing] = useState(false);
  const [formValues, setFormValues] = useState<MemberFormValues | null>(null);
  const [moveTarget, setMoveTarget] = useState('');

  const { data: household } = useQuery({
    queryKey: ['household', member?.household],
    queryFn: async () => (await apiClient.get<Household>(`/households/${member!.household}/`)).data,
    enabled: !!member?.household,
  });
  const { data: householdMembers } = useQuery({
    queryKey: ['household-members', member?.household, memberId],
    queryFn: async () => {
      const resp = await apiClient.get<{ results: Member[] }>('/members/', { params: { household: member!.household } });
      return resp.data.results.filter((m) => m.id !== memberId);
    },
    enabled: !!member?.household,
  });

  if (isLoading || !member) return <div className="card">Loading…</div>;

  function startEdit() {
    setFormValues(toFormValues(member!));
    setEditing(true);
  }

  async function saveEdit() {
    if (!formValues) return;
    await updateMember.mutateAsync({
      surname: formValues.surname,
      first_name: formValues.first_name,
      phone: formValues.phone,
      email: formValues.email,
      location: formValues.location,
      household: formValues.household ? Number(formValues.household) : null,
    });
    setEditing(false);
  }

  async function handleDelete() {
    if (!confirm('Delete this member?')) return;
    await deleteMember.mutateAsync(memberId);
    navigate('/members');
  }

  async function handleMove() {
    if (!moveTarget) return;
    await moveCategory.mutateAsync(moveTarget);
    setMoveTarget('');
  }

  const availableCategories = CATEGORIES.filter((c) => c !== member.category);

  return (
    <>
      <a className="backlink" onClick={() => navigate('/members')}>← Back to members</a>
      <div className="grid g2">
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <h3 style={{ fontSize: '1.15rem' }}>
              {member.full_name}
              {member.other_names && (
                <span className="muted" style={{ fontSize: '.85rem', fontWeight: 600 }}> {member.other_names}</span>
              )}
            </h3>
            <div className="row-actions">
              <button className="icon-btn edit" title="Edit" onClick={startEdit}>
                <Icon name="edit" size={15} />
              </button>
              <button className="icon-btn" title="Delete member" onClick={handleDelete}>
                <Icon name="trash" size={15} />
              </button>
            </div>
          </div>
          <div className="muted" style={{ margin: '4px 0 14px' }}>
            {member.location} · Joined {member.joined_date}
          </div>

          {editing && formValues && locations && (
            <div className="form-card editing">
              <MemberFormFields
                values={formValues}
                onChange={setFormValues}
                locations={locations}
                excludeMemberId={memberId}
                showCategoryAndJoined={false}
              />
              <button className="btn sm" onClick={saveEdit} disabled={updateMember.isPending}>
                Save changes
              </button>
              <button className="btn sm ghost" onClick={() => setEditing(false)}>Cancel</button>
            </div>
          )}

          <div><Badge color={categoryBadgeColor(member.category)}>{member.category}</Badge></div>

          <div className="section-gap" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, fontSize: '.9rem' }}>
            <div><span className="muted">Gender</span><div>{member.gender || '–'}</div></div>
            <div><span className="muted">Date of birth</span><div>{member.date_of_birth || '–'}</div></div>
            <div><span className="muted">Phone</span><div>{member.phone || '–'}</div></div>
            <div><span className="muted">Email</span><div>{member.email || '–'}</div></div>
          </div>

          <div className="field section-gap">
            <label htmlFor="move-category">Move to category</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <select id="move-category" className="selectbox" value={moveTarget || availableCategories[0]} onChange={(e) => setMoveTarget(e.target.value)}>
                {availableCategories.map((c) => <option key={c}>{c}</option>)}
              </select>
              <button className="btn sm" onClick={handleMove} disabled={moveCategory.isPending}>Move</button>
            </div>
          </div>
        </div>

        <div>
          <div className="card">
            <h3>Household</h3>
            {household ? (
              <>
                <div style={{ fontWeight: 700, color: 'var(--blue-deep)' }}>{household.name}</div>
                <div className="muted" style={{ fontSize: '.86rem', marginTop: 2 }}>{household.address}</div>
                <div className="muted" style={{ fontSize: '.86rem' }}>{household.phone}</div>
                {householdMembers && householdMembers.length > 0 ? (
                  <div className="section-gap">
                    <div className="muted" style={{ fontSize: '.78rem', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 6 }}>
                      Other household members
                    </div>
                    {householdMembers.map((hm) => (
                      <div key={hm.id} style={{ padding: '6px 0', borderBottom: '1px solid var(--line)', fontSize: '.9rem' }}>
                        <a onClick={() => navigate(`/members/${hm.id}`)} style={{ color: 'var(--blue)', cursor: 'pointer', fontWeight: 600 }}>
                          {hm.full_name}
                        </a>{' '}
                        <span className="muted">· {hm.category}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="muted section-gap" style={{ fontSize: '.85rem' }}>No other members linked to this household yet.</div>
                )}
              </>
            ) : (
              <div className="empty">Not linked to a household. Use Edit to add one.</div>
            )}
          </div>

          <div className="card section-gap">
            <h3>Movement history</h3>
            {member.category_history.length ? (
              member.category_history.map((h) => (
                <div key={h.id} style={{ padding: '8px 0', borderBottom: '1px solid var(--line)', fontSize: '.86rem' }}>
                  <b>{h.from_category}</b> → <b>{h.to_category}</b>
                  <div className="muted">{h.changed_date}</div>
                </div>
              ))
            ) : (
              <div className="empty">No movement recorded yet.</div>
            )}
          </div>

          <div className="card section-gap">
            <h3>Giving</h3>
            <div className="kpi2-value" style={{ fontSize: '1.3rem' }}>{fmt(member.total_given)}</div>
            <div className="muted" style={{ fontSize: '.82rem' }}>Total given, linked to this member</div>
          </div>
        </div>
      </div>
    </>
  );
}
