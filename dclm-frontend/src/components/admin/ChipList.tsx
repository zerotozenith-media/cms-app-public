import { useState } from 'react';
import { useSimpleListCrud } from '../../api/simpleList';

import { useAuth } from '../../context/AuthContext';
interface ChipListProps {
  title: string;
  endpoint: string;
  badgeColor: 'blue' | 'green' | 'amber' | 'red' | 'gray';
  placeholder: string;
  /** The section whose permission governs this list. */
  module?: string;
}

/** One reusable component for every simple admin-configurable
 * name-only list , Funds, Payment Methods, Expense Categories,
 * Newcomer Sources, Milestone Types, Services, Departments all use
 * this same structure on the backend. */
export function ChipList({ title, endpoint, badgeColor, placeholder, module }: ChipListProps) {
  const { hasPermission } = useAuth();
  const canAdd = module ? hasPermission(module, 'create') : true;
  const canRemove = module ? hasPermission(module, 'delete') : true;
  const { list, create, remove } = useSimpleListCrud(endpoint);
  const [value, setValue] = useState('');
  // A refused add or removal is explained. Before, a fund still used by
  // giving could not be removed and nothing on screen said why.
  const [error, setError] = useState('');

  const reason = (err: any, fallback: string) => {
    const d = err?.response?.data;
    const text = String(d?.detail ?? d?.name?.[0] ?? fallback);
    return text.charAt(0).toUpperCase() + text.slice(1);
  };

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim()) return;
    setError('');
    try {
      await create.mutateAsync(value.trim());
      setValue('');
    } catch (err) {
      setError(reason(err, 'That could not be added.'));
    }
  }
  async function handleRemove(id: number | string, name: string) {
    // Anything still in use is refused by the server, so this only
    // removes items nothing refers to.
    if (!confirm(`Remove ${name}?`)) return;
    setError('');
    try {
      await remove.mutateAsync(id);
    } catch (err) {
      setError(reason(err, `${name} could not be removed.`));
    }
  }

  return (
    <div className="card">
      <h3>{title}</h3>
      <div>
        {(list.data ?? []).map((item) => (
          <span className={`chip badge ${badgeColor}`} key={item.id}>
            {item.name}
            {canRemove && <button type="button" onClick={() => handleRemove(item.id, item.name)} aria-label={`Remove ${item.name}`}>×</button>}
          </span>
        ))}
        {list.data?.length === 0 && <div className="muted" style={{ fontSize: '.85rem' }}>None yet.</div>}
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {canAdd && <form style={{ display: 'flex', gap: 6, marginTop: 10 }} onSubmit={handleAdd}>
        <input
          value={value} onChange={(e) => setValue(e.target.value)} placeholder={placeholder}
          style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 8, padding: '.4rem .6rem' }}
          aria-label={`New ${title.toLowerCase()} name`}
        />
        <button className="btn sm" type="submit" disabled={create.isPending}>Add</button>
      </form>}
    </div>
  );
}
