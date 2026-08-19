import { useUpsertRolePermission } from '../../api/admin';
import { MODULES } from '../../types/admin';
import type { Role } from '../../types/admin';

const ACTIONS: ['can_view', 'can_create', 'can_edit', 'can_delete'] = ['can_view', 'can_create', 'can_edit', 'can_delete'];
const ACTION_LABELS: Record<string, string> = { can_view: 'View', can_create: 'Create', can_edit: 'Edit', can_delete: 'Delete' };

/**
 * Per-module view/create/edit/delete matrix for one Role. A RolePermission
 * row may not exist yet for a given module (e.g. a newly created Role
 * has none at all) , checking a box for the first time creates it,
 * matching how ModulePermission on the backend fails closed for any
 * module without a row at all.
 */
export function RolePermissionMatrix({ role }: { role: Role }) {
  const upsert = useUpsertRolePermission();

  function toggle(moduleName: string, action: string, checked: boolean) {
    const existing = role.permissions.find((p) => p.module === moduleName);
    upsert.mutate({
      existingId: existing?.id,
      role: role.id,
      module: moduleName,
      can_view: existing?.can_view ?? false,
      can_create: existing?.can_create ?? false,
      can_edit: existing?.can_edit ?? false,
      can_delete: existing?.can_delete ?? false,
      [action]: checked,
    });
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="cardtable">
        <thead>
          <tr><th>Module</th>{ACTIONS.map((a) => <th key={a}>{ACTION_LABELS[a]}</th>)}</tr>
        </thead>
        <tbody>
          {MODULES.map((moduleName) => {
            const existing = role.permissions.find((p) => p.module === moduleName);
            return (
              <tr key={moduleName}>
                <td data-label="Module" style={{ textTransform: 'capitalize' }}>{moduleName}</td>
                {ACTIONS.map((action) => (
                  <td data-label={ACTION_LABELS[action]} key={action}>
                    <input
                      type="checkbox"
                      checked={existing ? Boolean(existing[action as keyof typeof existing]) : false}
                      onChange={(e) => toggle(moduleName, action, e.target.checked)}
                      style={{ width: 16, height: 16 }}
                    />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
