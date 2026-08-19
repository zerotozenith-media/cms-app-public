import { useState } from 'react';
import { useSimpleListCrud } from '../../api/simpleList';

interface ChipListProps {
  title: string;
  endpoint: string;
  badgeColor: 'blue' | 'green' | 'amber' | 'red' | 'gray';
  placeholder: string;
}

/** One reusable component for every simple admin-configurable
 * name-only list , Funds, Payment Methods, Expense Categories,
 * Newcomer Sources, Milestone Types, Services, Departments all use
 * this same structure on the backend. */
export function ChipList({ title, endpoint, badgeColor, placeholder }: ChipListProps) {
  const { list, create, remove } = useSimpleListCrud(endpoint);
  const [value, setValue] = useState('');

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim()) return;
    await create.mutateAsync(value.trim());
    setValue('');
  }
  async function handleRemove(id: number | string) {
    if (!confirm(`Remove this ${title.toLowerCase()} item? Existing records that reference it are unaffected.`)) return;
    await remove.mutateAsync(id);
  }

  return (
    <div className="card">
      <h3>{title}</h3>
      <div>
        {(list.data ?? []).map((item) => (
          <span className={`chip badge ${badgeColor}`} key={item.id}>
            {item.name}
            <button type="button" onClick={() => handleRemove(item.id)} aria-label={`Remove ${item.name}`}>×</button>
          </span>
        ))}
        {list.data?.length === 0 && <div className="muted" style={{ fontSize: '.85rem' }}>None yet.</div>}
      </div>
      <form style={{ display: 'flex', gap: 6, marginTop: 10 }} onSubmit={handleAdd}>
        <input
          value={value} onChange={(e) => setValue(e.target.value)} placeholder={placeholder}
          style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 8, padding: '.4rem .6rem' }}
          aria-label={`New ${title.toLowerCase()} name`}
        />
        <button className="btn sm" type="submit" disabled={create.isPending}>Add</button>
      </form>
    </div>
  );
}
