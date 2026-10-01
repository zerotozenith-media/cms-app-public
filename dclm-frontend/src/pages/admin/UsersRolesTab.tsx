import { useState } from 'react';
import { useAdminUsers, useCreateUser, useDeleteUser, useUpdateUser, useRoles, useCreateRole, useDeleteRole } from '../../api/admin';
import { useMyLocations } from '../../api/locations';
import { RolePermissionMatrix } from '../../components/admin/RolePermissionMatrix';
import { Badge } from '../../components/ui/Badge';
import { Icon } from '../../components/ui/Icon';

import { useAuth } from '../../context/AuthContext';
export function UsersRolesTab() {
  // Roles and their permissions apply to every location, so only somebody
  // covering every location changes them. A coordinator adds accounts at
  // their own location, with roles no more powerful than their own.
  const { user: me, hasPermission } = useAuth();
  const churchWide = !me?.location && hasPermission('admin', 'edit');
  const canAddUser = hasPermission('admin', 'create');
  const canDeleteUser = hasPermission('admin', 'delete');
  const { data: users } = useAdminUsers();
  const { data: roles } = useRoles();
  const { data: locations } = useMyLocations();
  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const canEditUser = hasPermission('admin', 'edit');
  const [canShepherd, setCanShepherd] = useState(false);
  const deleteUser = useDeleteUser();
  const createRole = useCreateRole();
  const deleteRole = useDeleteRole();

  const [showUserForm, setShowUserForm] = useState(false);
  const [email, setEmail] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('');
  const [location, setLocation] = useState('');
  const [userError, setUserError] = useState<string | null>(null);

  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);
  const [newRoleName, setNewRoleName] = useState('');

  if (roles && !role && roles.length) setRole(String(roles[0].id));

  async function handleAddUser(e: React.FormEvent) {
    e.preventDefault();
    setUserError(null);
    try {
      await createUser.mutateAsync({
        email, first_name: firstName, last_name: lastName, password, can_shepherd: canShepherd,
        // Someone limited to one location adds accounts there. The box showed
        // their location but sent none, which the server refused.
        role: Number(role), location: location || me?.location || null,
      });
      setEmail(''); setFirstName(''); setLastName(''); setPassword('');
      setShowUserForm(false);
    } catch (err: any) {
      const data = err?.response?.data;
      if (data?.password) setUserError(`Password: ${data.password[0]}`);
      else if (data?.email) setUserError(`Email: ${data.email[0]}`);
      else setUserError('Could not create the user. Please check the form.');
    }
  }
  async function handleDeleteUser(id: number) {
    if (!confirm('Delete this user?')) return;
    try {
      await deleteUser.mutateAsync(id);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Could not delete this user.');
    }
  }
  async function handleAddRole(e: React.FormEvent) {
    e.preventDefault();
    if (!newRoleName.trim()) return;
    const created = await createRole.mutateAsync(newRoleName.trim());
    setNewRoleName('');
    setSelectedRoleId(created.id);
  }
  async function handleDeleteRole(id: number) {
    if (!confirm('Delete this role? Users assigned to it will need a new role.')) return;
    await deleteRole.mutateAsync(id);
    if (selectedRoleId === id) setSelectedRoleId(null);
  }

  const selectedRole = roles?.find((r) => r.id === selectedRoleId);

  return (
    <div className="grid g2 admin-users-grid">
      <div className="card">
        <div className="toolbar" style={{ marginBottom: 10 }}>
          <h3>Users</h3>
          {canAddUser && (
          <a className="btn sm" onClick={() => setShowUserForm(!showUserForm)}>
            <Icon name="plus" size={14} /> Add user
          </a>
          )}
        </div>
        {showUserForm && (
          <div className="form-card editing">
            <form onSubmit={handleAddUser}>
              <div className="form-row">
                <div className="field">
                  <label htmlFor="user-first">First name</label>
                  <input id="user-first" value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
                </div>
                <div className="field">
                  <label htmlFor="user-last">Last name</label>
                  <input id="user-last" value={lastName} onChange={(e) => setLastName(e.target.value)} />
                </div>
              </div>
              <div className="field">
                <label htmlFor="user-email">Email</label>
                <input id="user-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>
              <div className="field">
                <label htmlFor="user-password">Password</label>
                <input id="user-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </div>
              <div className="form-row">
                <div className="field">
                  <label htmlFor="user-role">Role</label>
                  <select id="user-role" value={role} onChange={(e) => setRole(e.target.value)}>
                    {(roles ?? []).filter((r: any) => r.assignable !== false).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="user-location">Location</label>
                  <select id="user-location" value={location || me?.location || ''} onChange={(e) => setLocation(e.target.value)}>
                    {!me?.location && <option value="">All locations</option>}
                    {(locations ?? []).map((l: any) => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </select>
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '4px 0 12px', fontSize: '.88rem' }}>
                <input type="checkbox" checked={canShepherd} onChange={(e) => setCanShepherd(e.target.checked)} style={{ width: 16, height: 16 }} />
                Can shepherd others
                <span className="muted" style={{ fontSize: '.8rem' }}>People can be assigned to them to follow up, whatever their member category.</span>
              </label>
              {userError && <p style={{ color: 'var(--red)', fontSize: '.85rem', marginBottom: 10 }}>{userError}</p>}
              <button className="btn sm" type="submit" disabled={createUser.isPending}>Add user</button>
              <button className="btn sm ghost" type="button" onClick={() => setShowUserForm(false)}>Cancel</button>
            </form>
          </div>
        )}
        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead><tr><th>Name</th><th>Role</th><th>Location</th><th></th></tr></thead>
            <tbody>
              {(users ?? []).map((u) => (
                <tr key={u.id}>
                  <td data-label="Name">{u.full_name}<div className="muted" style={{ fontSize: '.78rem' }}>{u.email}</div></td>
                  <td data-label="Role">
                    {u.role_name ? <Badge color="blue">{u.role_name}</Badge> : <span className="muted">–</span>}
                    <label className="shepherd-tick" title="Can shepherd others: people can be assigned to them to follow up">
                      <input type="checkbox" aria-label={`${u.full_name} can shepherd others`} checked={!!u.can_shepherd}
                        disabled={!canEditUser || updateUser.isPending}
                        onChange={(e) => updateUser.mutate({ id: u.id, can_shepherd: e.target.checked })} />
                      Shepherd
                    </label>
                  </td>
                  <td data-label="Location">{u.location_name ?? 'All locations'}</td>
                  <td className="td-actions">
                    {canDeleteUser && <button className="icon-btn" title="Delete user" aria-label="Delete user" onClick={() => handleDeleteUser(u.id)}><Icon name="trash" size={14} /></button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 10 }}>Roles &amp; Permissions</h3>
        {!churchWide && (
          <p className="muted" style={{ fontSize: '.84rem', marginTop: 0 }}>
            Roles apply to every location, so they are changed by an administrator who covers every location.
          </p>
        )}
        {churchWide && <form style={{ display: 'flex', gap: 6, marginBottom: 14 }} onSubmit={handleAddRole}>
          <input
            value={newRoleName} onChange={(e) => setNewRoleName(e.target.value)} placeholder="New role name"
            style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 8, padding: '.4rem .6rem' }}
            aria-label="New role name"
          />
          <button className="btn sm" type="submit" disabled={createRole.isPending}>Add role</button>
        </form>}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
          {(roles ?? []).map((r) => (
            <span key={r.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <button
                className={`tab${selectedRoleId === r.id ? ' active' : ''}`}
                onClick={() => setSelectedRoleId(r.id)}
              >
                {r.name}
              </button>
              {churchWide && (
                <button className="icon-btn" title="Delete role" onClick={() => handleDeleteRole(r.id)}>
                  <Icon name="trash" size={12} />
                </button>
              )}
            </span>
          ))}
        </div>
        {selectedRole ? (
          <RolePermissionMatrix role={selectedRole} readOnly={!churchWide} />
        ) : (
          <div className="empty">Select a role above to view or edit its permissions.</div>
        )}
      </div>
    </div>
  );
}
