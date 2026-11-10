import { useEffect, useState } from 'react';
import { useAppSettings, useUpdateAppSetting, type AppSettings, type AppSettingsPatch } from '../../api/settings';
import { HelpMark } from '../../components/ui/HelpMark';
import { Skeleton } from '../../components/ui/Skeleton';
import { useAuth } from '../../context/AuthContext';

/**
 * Admin, Settings (dashboard redesign, approved 10 November 2026): the
 * financial year, the month the records start, the receipt amount flagged
 * on the dashboard, the period the dashboard opens on, and two-step
 * sign-in by role. Rules live here rather than in the code, and every
 * change is written to the Audit Log.
 */
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const OPENS = [['this_month', 'This month'], ['this_quarter', 'Quarter'], ['this_year', 'Year to date'], ['last_year', 'Last year']];
const TWO = [['required', 'Required'], ['choose', 'Person chooses'], ['off', 'Off']];

export function SettingsTab() {
  const { data } = useAppSettings();
  const save = useUpdateAppSetting();
  const { user } = useAuth();
  const [draft, setDraft] = useState<AppSettings | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [done, setDone] = useState('');
  useEffect(() => { if (data) setDraft(data); }, [data]);
  if (!data || !draft) return <div className="card"><Skeleton shape="rows" rows={8} /></div>;
  const locked = !!user?.location;
  const set = <K extends keyof AppSettings>(k: K, v: AppSettings[K]) => { setDraft({ ...draft, [k]: v }); setDone(''); };
  const keys: (keyof AppSettings)[] = ['finance_year_end_month', 'records_start', 'receipt_flag_over', 'dashboard_opens_on', 'two_step_remember_days'];
  const changed = keys.filter((k) => String(draft[k]) !== String(data[k]));
  const roleChanges = Object.fromEntries(draft.two_step_roles
    .filter((r) => r.two_step !== data.two_step_roles.find((x) => x.id === r.id)?.two_step).map((r) => [String(r.id), r.two_step]));
  const any = changed.length > 0 || Object.keys(roleChanges).length > 0;

  async function onSave() {
    setErrors({}); setDone('');
    const patch: AppSettingsPatch = {};
    changed.forEach((k) => { (patch as any)[k] = draft![k]; });
    if (Object.keys(roleChanges).length) patch.two_step_roles = roleChanges;
    try {
      await save.mutateAsync(patch);
      setDone('Saved. The change applies from now on, and it is in the Audit Log.');
    } catch (e: any) {
      const d = e?.response?.data ?? {};
      const out: Record<string, string> = {};
      Object.entries(d).forEach(([k, v]) => { out[k] = String(([] as unknown[]).concat(v as any)[0]); });
      setErrors(Object.keys(out).length ? out : { detail: 'The settings could not be saved. Try again.' });
    }
  }
  const row = (label: string, topic: string, ctrl: React.ReactNode, field: string, note?: string) => (
    <div className="fr-row">
      <div className="fr-label">
        <div className="fr-name">{label}<HelpMark topic={topic} /></div>
        {note && <div className="muted fr-note">{note}</div>}
        {errors[field] && <div className="fr-err" role="alert">{errors[field]}</div>}
      </div>
      <div className="fr-ctrl">{ctrl}</div>
    </div>
  );
  const ym = draft.records_start;
  const example = `With ${MONTHS[draft.finance_year_end_month - 1]}, Year to date runs from 1 ${MONTHS[draft.finance_year_end_month % 12]}.`;

  return (
    <div className="fr-page">
      <div className="gender-notice">
        <b>These settings apply at every location.</b> {locked
          ? 'Only an administrator covering All locations can change them, so they are shown here to read.'
          : 'Only an administrator covering All locations can change them, and every change is written to the Audit Log.'}
      </div>

      <div className="card fr-card">
        <h3>Financial year and records</h3>
        <p className="muted fr-sub">Year to date, Quarter and Last year on the dashboard follow these.</p>
        {row('Financial year ends in', 'setFinYear', <select className="selectbox" aria-label="Financial year ends in" disabled={locked}
          value={draft.finance_year_end_month} onChange={(e) => set('finance_year_end_month', Number(e.target.value))}>
          {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
        </select>, 'finance_year_end_month', example)}
        {row('Records start', 'setRecordsStart', <input type="month" className="fr-num" aria-label="Records start" disabled={locked} style={{ width: 170 }}
          value={ym} onChange={(e) => set('records_start', e.target.value)} />, 'records_start',
        'The first month with real records. A card compares with the same days a year earlier only when they are on or after this month. Before that, it compares with the period just before: 1 to 10 November with 1 to 10 October.')}
      </div>

      <div className="card fr-card">
        <h3>Dashboard</h3>
        {row('Flag expenses with no receipt over', 'setReceipt', <span className="fr-inline">BHD <input type="number" min="0" step="0.5" className="fr-num" aria-label="Amount in BHD" disabled={locked} style={{ width: 90 }}
          value={draft.receipt_flag_over} onChange={(e) => set('receipt_flag_over', e.target.value)} /></span>, 'receipt_flag_over',
        `Listed under Needs your attention for those who can edit Giving and Finance. Example: with ${Number(draft.receipt_flag_over) || 0}, an expense of BHD ${(Number(draft.receipt_flag_over) + 15).toFixed(2)} with no receipt is listed.`)}
        {row('The dashboard opens on', 'setOpensOn', <select className="selectbox" aria-label="The dashboard opens on" disabled={locked}
          value={draft.dashboard_opens_on} onChange={(e) => set('dashboard_opens_on', e.target.value as AppSettings['dashboard_opens_on'])}>
          {OPENS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>, 'dashboard_opens_on', 'The period shown first. Anyone can then choose another on the dashboard.')}
      </div>

      <div className="card fr-card">
        <h3>Two-step sign-in</h3>
        <p className="muted fr-sub">A 6-digit number from an authenticator app after the password. Required: set up at the next sign-in. Person chooses: each person can turn it on in My profile. Off: not offered.</p>
        {draft.two_step_roles.map((r) => row(r.name, 'setTwoStep', <select className="selectbox" aria-label={`Two-step sign-in for ${r.name}`} disabled={locked}
          value={r.two_step} onChange={(e) => set('two_step_roles', draft.two_step_roles.map((x) => x.id === r.id ? { ...x, two_step: e.target.value as 'required' | 'choose' | 'off' } : x))}>
          {TWO.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>, `role-${r.id}`))}
        {errors.two_step_roles && <div className="fr-err" role="alert">{errors.two_step_roles}</div>}
        {row('Remember a device for', 'setRemember', <span className="fr-inline"><input type="number" min="0" max="90" className="fr-num" aria-label="Days" disabled={locked} style={{ width: 80 }}
          value={draft.two_step_remember_days} onChange={(e) => set('two_step_remember_days', e.target.value === '' ? ('' as any) : Number(e.target.value))} /> days</span>,
        'two_step_remember_days', 'After the number is typed with the box ticked, that browser is not asked again for this many days. Set 0 to ask every time.')}
      </div>

      {errors.detail && <p className="form-error" role="alert">{errors.detail}</p>}
      {done && <p className="fr-done" role="status">{done}</p>}
      {!locked && (
        <div className="form-actions-row">
          <button type="button" className="btn" disabled={!any || save.isPending} onClick={onSave}>{save.isPending ? 'Saving…' : 'Save settings'}</button>
          {any && <button type="button" className="btn ghost" onClick={() => { setDraft(data); setErrors({}); }}>Undo changes</button>}
        </div>
      )}
    </div>
  );
}
