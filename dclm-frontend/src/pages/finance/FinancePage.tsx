import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  useFunds, usePaymentMethods, useExpenseCategories, useProjects, useFinanceSummary,
  useGivingList, useExpenseList, useCreateGiving, useUpdateGiving, useDeleteGiving,
  useCreateExpense, useUpdateExpense, useDeleteExpense,
} from '../../api/finance';
import { useLocations } from '../../api/locations';
import { apiClient } from '../../api/client';
import { useQuery } from '@tanstack/react-query';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { Pagination } from '../../components/ui/Pagination';
import { Icon } from '../../components/ui/Icon';
import { fmt } from '../../lib/format';
import type { Giving, Expense } from '../../types/finance';

const today = new Date().toISOString().slice(0, 10);

export function FinancePage() {
  const navigate = useNavigate();
  const { data: funds } = useFunds();
  const { data: methods } = usePaymentMethods();
  const { data: categories } = useExpenseCategories();
  const { data: projects } = useProjects();
  const { data: locations } = useLocations();
  const { data: summary } = useFinanceSummary();
  const { data: members } = useQuery({
    queryKey: ['members-for-giving'],
    queryFn: async () => (await apiClient.get('/members/', { params: { ordering: 'surname,first_name', page_size: 100 } })).data.results,
  });

  // --- Giving list state ---
  const [givingFund, setGivingFund] = useState('all');
  const [givingMethod, setGivingMethod] = useState('all');
  const [givingSort, setGivingSort] = useState('-date');
  const [givingPage, setGivingPage] = useState(1);
  const givingPageSize = 6;
  const { data: givingList } = useGivingList({
    fund: givingFund !== 'all' ? givingFund : undefined,
    method: givingMethod !== 'all' ? givingMethod : undefined,
    ordering: givingSort, page: givingPage, page_size: givingPageSize,
  });

  // --- Expense list state ---
  const [expenseCategory, setExpenseCategory] = useState('all');
  const [expenseSort, setExpenseSort] = useState('-date');
  const [expensePage, setExpensePage] = useState(1);
  const expensePageSize = 6;
  const { data: expenseList } = useExpenseList({
    category: expenseCategory !== 'all' ? expenseCategory : undefined,
    ordering: expenseSort, page: expensePage, page_size: expensePageSize,
  });

  // --- Giving form ---
  const [givingEditId, setGivingEditId] = useState<number | null>(null);
  const [gFund, setGFund] = useState('');
  const [gMethod, setGMethod] = useState('');
  const [gAmount, setGAmount] = useState('');
  const [gLocation, setGLocation] = useState('');
  const [gMember, setGMember] = useState('');
  const createGiving = useCreateGiving();
  const updateGiving = useUpdateGiving();
  const deleteGiving = useDeleteGiving();

  if (funds && !gFund && funds.length) setGFund(String(funds[0].id));
  if (methods && !gMethod && methods.length) setGMethod(String(methods[0].id));
  if (locations && !gLocation && locations.length) setGLocation(locations[0].id);

  function startGivingEdit(g: Giving) {
    setGivingEditId(g.id);
    setGFund(String(g.fund));
    setGMethod(String(g.method));
    setGAmount(String(g.amount));
    setGLocation(g.location);
    setGMember(g.member ? String(g.member) : '');
  }
  function cancelGivingEdit() {
    setGivingEditId(null);
    setGAmount('');
    setGMember('');
  }
  async function handleGivingSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = {
      fund: Number(gFund), method: Number(gMethod), amount: gAmount,
      location: gLocation, member: gMember ? Number(gMember) : null,
      date: today,
    };
    if (givingEditId) {
      await updateGiving.mutateAsync({ id: givingEditId, ...payload });
      cancelGivingEdit();
    } else {
      await createGiving.mutateAsync(payload);
      setGAmount('');
      setGMember('');
    }
  }
  async function handleDeleteGiving(id: number) {
    if (!confirm('Delete this giving entry?')) return;
    await deleteGiving.mutateAsync(id);
  }

  // --- Expense form ---
  const [expenseEditId, setExpenseEditId] = useState<number | null>(null);
  const [eCategory, setECategory] = useState('');
  const [eAmount, setEAmount] = useState('');
  const [eDescription, setEDescription] = useState('');
  const [eReceiptFile, setEReceiptFile] = useState<File | null>(null);
  const [eLocation, setELocation] = useState('');
  const createExpense = useCreateExpense();
  const updateExpense = useUpdateExpense();
  const deleteExpense = useDeleteExpense();

  if (categories && !eCategory && categories.length) setECategory(String(categories[0].id));
  if (locations && !eLocation && locations.length) setELocation(locations[0].id);

  function startExpenseEdit(x: Expense) {
    setExpenseEditId(x.id);
    setECategory(String(x.category));
    setEAmount(String(x.amount));
    setEDescription(x.description);
    setELocation(x.location);
    setEReceiptFile(null);
  }
  function cancelExpenseEdit() {
    setExpenseEditId(null);
    setEAmount('');
    setEDescription('');
    setEReceiptFile(null);
  }
  async function handleExpenseSubmit(e: React.FormEvent) {
    e.preventDefault();
    const formData = new FormData();
    formData.append('category', eCategory);
    formData.append('amount', eAmount);
    formData.append('location', eLocation);
    formData.append('description', eDescription);
    formData.append('date', today);
    if (eReceiptFile) formData.append('receipt_file', eReceiptFile);
    if (expenseEditId) {
      await updateExpense.mutateAsync({ id: expenseEditId, payload: formData });
      cancelExpenseEdit();
    } else {
      await createExpense.mutateAsync(formData);
      setEAmount('');
      setEDescription('');
      setEReceiptFile(null);
    }
  }
  async function handleDeleteExpense(id: number) {
    if (!confirm('Delete this expense entry?')) return;
    await deleteExpense.mutateAsync(id);
  }

  const stats: StatItem[] = [
    { icon: 'coin', color: 'green', label: 'Income (all time)', value: fmt(summary?.income_total ?? 0) },
    { icon: 'coin', color: 'blue', label: 'Income this month', value: fmt(summary?.income_this_month ?? 0) },
    { icon: 'coin', color: 'red', label: 'Expenses (all time)', value: fmt(summary?.expense_total ?? 0) },
    { icon: 'gear', color: 'blue', label: 'Net', value: fmt(summary?.net_total ?? 0) },
  ];

  const givingTotalPages = givingList ? Math.max(1, Math.ceil(givingList.count / givingPageSize)) : 1;
  const expenseTotalPages = expenseList ? Math.max(1, Math.ceil(expenseList.count / expensePageSize)) : 1;

  return (
    <>
      <StatRow stats={stats} />

      <div className="grid g2 section-gap">
        <div className="card">
          <h3>Income by fund</h3>
          {(summary?.income_by_fund ?? []).map((f) => (
            <div key={f.fund} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--line)' }}>
              <span>{f.fund}</span><b>{fmt(f.total)}</b>
            </div>
          ))}
        </div>
        <div className="card">
          <h3>Expenses by category</h3>
          {(summary?.expenses_by_category ?? []).length ? summary!.expenses_by_category.map((c) => (
            <div key={c.category} style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--line)' }}>
              <span>{c.category}</span><b>{fmt(c.total)}</b>
            </div>
          )) : <div className="empty">No expenses recorded.</div>}
        </div>
      </div>

      {projects && projects.length > 0 && (
        <div className="card section-gap">
          <h3>Projects</h3>
          {projects.map((p) => {
            const pct = p.target_amount ? Math.min(100, Math.round((p.amount_raised / p.target_amount) * 100)) : 0;
            return (
              <div key={p.id} style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <b>{p.name}</b><span>{fmt(p.amount_raised)} / {fmt(p.target_amount)}</span>
                </div>
                <div className="bar-track"><div className="bar-fill red" style={{ width: `${pct}%` }} /></div>
              </div>
            );
          })}
        </div>
      )}

      <div className="grid g2 section-gap">
        <div className="card">
          <h3>{givingEditId ? 'Edit giving entry' : 'Record giving'}</h3>
          <form onSubmit={handleGivingSubmit}>
            <div className="form-row">
              <div className="field">
                <label htmlFor="g-fund">Fund</label>
                <select id="g-fund" value={gFund} onChange={(e) => setGFund(e.target.value)}>
                  {(funds ?? []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="g-method">Method</label>
                <select id="g-method" value={gMethod} onChange={(e) => setGMethod(e.target.value)}>
                  {(methods ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="field">
                <label htmlFor="g-amount">Amount (BHD)</label>
                <input id="g-amount" type="number" step="0.001" min="0" value={gAmount} onChange={(e) => setGAmount(e.target.value)} required />
              </div>
              <div className="field">
                <label htmlFor="g-location">Location</label>
                <select id="g-location" value={gLocation} onChange={(e) => setGLocation(e.target.value)}>
                  {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                </select>
              </div>
            </div>
            <div className="field">
              <label htmlFor="g-member">Member (optional)</label>
              <select id="g-member" value={gMember} onChange={(e) => setGMember(e.target.value)}>
                <option value="">Anonymous / not linked</option>
                {(members ?? []).map((m: any) => <option key={m.id} value={m.id}>{m.full_name}</option>)}
              </select>
            </div>
            <button className="btn" type="submit" disabled={createGiving.isPending || updateGiving.isPending}>
              {givingEditId ? 'Save changes' : 'Add entry'}
            </button>
            {givingEditId && <button className="btn ghost" type="button" onClick={cancelGivingEdit}>Cancel</button>}
          </form>
        </div>

        <div className="card">
          <h3>{expenseEditId ? 'Edit expense entry' : 'Record expense'}</h3>
          <form onSubmit={handleExpenseSubmit}>
            <div className="form-row">
              <div className="field">
                <label htmlFor="e-category">Category</label>
                <select id="e-category" value={eCategory} onChange={(e) => setECategory(e.target.value)}>
                  {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="e-amount">Amount (BHD)</label>
                <input id="e-amount" type="number" step="0.001" min="0" value={eAmount} onChange={(e) => setEAmount(e.target.value)} required />
              </div>
            </div>
            <div className="field">
              <label htmlFor="e-description">Description</label>
              <input id="e-description" value={eDescription} onChange={(e) => setEDescription(e.target.value)} placeholder="Brief note" />
            </div>
            <div className="field">
              <label htmlFor="e-location">Location</label>
              <select id="e-location" value={eLocation} onChange={(e) => setELocation(e.target.value)}>
                {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="e-receipt">Receipt (optional)</label>
              <input id="e-receipt" type="file" accept="image/*,.pdf" onChange={(e) => setEReceiptFile(e.target.files?.[0] ?? null)} />
            </div>
            <button className="btn" type="submit" disabled={createExpense.isPending || updateExpense.isPending}>
              {expenseEditId ? 'Save changes' : 'Add entry'}
            </button>
            {expenseEditId && <button className="btn ghost" type="button" onClick={cancelExpenseEdit}>Cancel</button>}
          </form>
        </div>
      </div>

      {/* Giving list */}
      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>Giving entries</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select className="selectbox" value={givingFund} onChange={(e) => { setGivingFund(e.target.value); setGivingPage(1); }}>
              <option value="all">All funds</option>
              {(funds ?? []).map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
            </select>
            <select className="selectbox" value={givingMethod} onChange={(e) => { setGivingMethod(e.target.value); setGivingPage(1); }}>
              <option value="all">All methods</option>
              {(methods ?? []).map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <select className="selectbox" value={givingSort} onChange={(e) => setGivingSort(e.target.value)}>
              <option value="-date">Sort: Newest first</option>
              <option value="date">Sort: Oldest first</option>
              <option value="-amount">Sort: Highest amount</option>
              <option value="amount">Sort: Lowest amount</option>
            </select>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead><tr><th>Date</th><th>Fund</th><th>Method</th><th>Member</th><th>Amount</th><th></th></tr></thead>
            <tbody>
              {(givingList?.results ?? []).map((g) => (
                <tr key={g.id}>
                  <td data-label="Date">{g.date}</td>
                  <td data-label="Fund">{g.fund_name}</td>
                  <td data-label="Method">{g.method_name}</td>
                  <td data-label="Member">
                    {g.member ? (
                      <a onClick={() => navigate(`/members/${g.member}`)} style={{ color: 'var(--blue)', cursor: 'pointer', fontWeight: 600 }}>
                        {g.member_name}
                      </a>
                    ) : <span className="muted">Anonymous</span>}
                  </td>
                  <td data-label="Amount"><b>{fmt(g.amount)}</b></td>
                  <td className="td-actions" style={{ border: 0 }}>
                    <button className="icon-btn edit" onClick={() => startGivingEdit(g)}><Icon name="edit" size={14} /></button>
                    <button className="icon-btn" onClick={() => handleDeleteGiving(g.id)}><Icon name="trash" size={14} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {givingList?.results.length === 0 && <div className="empty">No giving matches these filters.</div>}
        </div>
        {givingList && (
          <Pagination page={givingPage} totalPages={givingTotalPages} totalCount={givingList.count} pageSize={givingPageSize} onPageChange={setGivingPage} />
        )}
      </div>

      {/* Expense list */}
      <div className="card section-gap">
        <div className="toolbar">
          <h3 style={{ flex: 'none' }}>Expense entries</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <select className="selectbox" value={expenseCategory} onChange={(e) => { setExpenseCategory(e.target.value); setExpensePage(1); }}>
              <option value="all">All categories</option>
              {(categories ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select className="selectbox" value={expenseSort} onChange={(e) => setExpenseSort(e.target.value)}>
              <option value="-date">Sort: Newest first</option>
              <option value="date">Sort: Oldest first</option>
              <option value="-amount">Sort: Highest amount</option>
              <option value="amount">Sort: Lowest amount</option>
            </select>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table className="cardtable">
            <thead><tr><th>Date</th><th>Category</th><th>Amount</th><th>Receipt</th><th></th></tr></thead>
            <tbody>
              {(expenseList?.results ?? []).map((x) => (
                <tr key={x.id}>
                  <td data-label="Date">{x.date}</td>
                  <td data-label="Category">{x.category_name}</td>
                  <td data-label="Amount"><b>{fmt(x.amount)}</b></td>
                  <td data-label="Receipt">
                    {x.receipt_file ? (
                      <a href={x.receipt_file} target="_blank" rel="noreferrer" style={{ color: 'var(--blue)', fontWeight: 600, cursor: 'pointer' }}>
                        📎 View
                      </a>
                    ) : <span className="muted">–</span>}
                  </td>
                  <td className="td-actions" style={{ border: 0 }}>
                    <button className="icon-btn edit" onClick={() => startExpenseEdit(x)}><Icon name="edit" size={14} /></button>
                    <button className="icon-btn" onClick={() => handleDeleteExpense(x.id)}><Icon name="trash" size={14} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {expenseList?.results.length === 0 && <div className="empty">No expenses match these filters.</div>}
        </div>
        {expenseList && (
          <Pagination page={expensePage} totalPages={expenseTotalPages} totalCount={expenseList.count} pageSize={expensePageSize} onPageChange={setExpensePage} />
        )}
      </div>
    </>
  );
}
