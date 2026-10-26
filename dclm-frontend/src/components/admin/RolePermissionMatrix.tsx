import { useState } from 'react';
import { useUpsertRolePermission } from '../../api/admin';
import { MODULES, MODULE_LABELS } from '../../types/admin';
import { HelpMark } from '../ui/HelpMark';
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
export function RolePermissionMatrix({ role, readOnly = false }: { role: Role; readOnly?: boolean }) {
  const upsert = useUpsertRolePermission();
  const [err, setErr] = useState('');

  function toggle(moduleName: string, action: string, checked: boolean) {
    const existing = role.permissions.find((p) => p.module === moduleName);
    // A2: the Administrator role holds the right to change roles at all, so
    // a change to it is confirmed first. The server also refuses any change
    // that would leave nobody with full Admin rights.
    if (role.name === 'Administrator' && !confirm(`Change the Administrator role? Every administrator gets this change at once.`)) return;
    setErr('');
    upsert.mutate({
      existingId: existing?.id,
      role: role.id,
      module: moduleName,
      can_view: existing?.can_view ?? false,
      can_create: existing?.can_create ?? false,
      can_edit: existing?.can_edit ?? false,
      can_delete: existing?.can_delete ?? false,
      [action]: checked,
    }, {
      onError: (e: any) => {
        const d = e?.response?.data;
        setErr(d?.detail ?? (d && Object.values(d)[0] ? String(([] as unknown[]).concat(Object.values(d)[0] as any)[0]) : 'That change could not be saved.'));
      },
    });
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      {err && <p className="form-error" role="alert">{err}</p>}
      <table className="cardtable">
        <thead>
          <tr><th>Module</th>{ACTIONS.map((a) => <th key={a}>{ACTION_LABELS[a]}</th>)}</tr>
        </thead>
        <tbody>
          {MODULES.map((moduleName) => {
            const existing = role.permissions.find((p) => p.module === moduleName);
            return (
              <tr key={moduleName}>
                <td data-label="Module" style={{ textTransform: MODULE_LABELS[moduleName] ? 'none' : 'capitalize' }}>
                  {MODULE_LABELS[moduleName] ?? moduleName}
                  {moduleName === 'followup-review' && <HelpMark topic="fuReviewModule" />}
                </td>
                {ACTIONS.map((action) => (
                  <td data-label={ACTION_LABELS[action]} key={action}>
                    <input
                      type="checkbox"
                      aria-label={`${ACTION_LABELS[action]} ${MODULE_LABELS[moduleName] ?? moduleName.charAt(0).toUpperCase() + moduleName.slice(1)}`}
                      checked={existing ? Boolean(existing[action as keyof typeof existing]) : false}
                      disabled={readOnly}
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
      <p className="muted" style={{ fontSize: '.78rem', margin: '10px 0 0' }}>
        An account with the Follow-up Coordinator tick gets Follow-up review for its chosen locations, whatever its role.
      </p>
    </div>
  );
}
