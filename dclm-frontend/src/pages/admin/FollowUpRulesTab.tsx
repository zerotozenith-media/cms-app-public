import { useEffect, useState } from 'react';
import { useFollowUpRules, useResetFollowUpRules, useSaveFollowUpRules, type FollowUpRules } from '../../api/followupRules';
import { HelpMark } from '../../components/ui/HelpMark';
import { Skeleton } from '../../components/ui/Skeleton';

/**
 * Admin, Follow-up Rules (Kay, 26 October 2026, plan demos 1 and 2). Every
 * follow-up time and number in one place, one set for every location.
 * Only an administrator covering All locations changes them, and each
 * change is written to the Audit Log.
 */
type Draft = Partial<FollowUpRules>;

const DAY = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MONTH = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function when(d: Date) {
  const h = d.getHours() % 12 || 12;
  const m = String(d.getMinutes()).padStart(2, '0');
  return `${DAY[d.getDay()]} ${d.getDate()} ${MONTH[d.getMonth()]} ${h}:${m} ${d.getHours() < 12 ? 'am' : 'pm'}`;
}

/** The worked example under Time limits: the next Friday service. */
function example(r: Draft) {
  const t = (r.clock_start ?? '18:00').split(':').map(Number);
  const d = new Date();
  d.setDate(d.getDate() + ((5 - d.getDay() + 7) % 7));
  d.setHours(t[0] || 0, t[1] || 0, 0, 0);
  const add = (h: number) => new Date(d.getTime() + h * 3600 * 1000);
  return {
    day: `Friday ${d.getDate()} ${MONTH[d.getMonth()]}`,
    due: when(add(r.due_hours ?? 24)),
    reason: when(add(r.reason_hours ?? 48)),
    review: when(add((r.review_days ?? 3) * 24)),
    decide: when(add((r.decide_days ?? 5) * 24)),
  };
}

export function FollowUpRulesTab() {
  const { data } = useFollowUpRules();
  const save = useSaveFollowUpRules();
  const reset = useResetFollowUpRules();
  const [draft, setDraft] = useState<Draft>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [done, setDone] = useState('');

  useEffect(() => { if (data) setDraft(data); }, [data]);

  if (!data) return <div className="card"><Skeleton shape="rows" rows={8} /></div>;
  const locked = !data.can_change;
  const set = (k: keyof FollowUpRules, v: unknown) => { setDraft((d) => ({ ...d, [k]: v })); setDone(''); };
  const changed = (Object.keys(draft) as (keyof FollowUpRules)[]).filter(
    (k) => !['updated_at', 'updated_by_name', 'can_change'].includes(k) && JSON.stringify(draft[k]) !== JSON.stringify(data[k]));

  async function onSave() {
    setErrors({}); setDone('');
    const patch: Draft = {};
    changed.forEach((k) => { (patch as any)[k] = draft[k]; });
    try {
      await save.mutateAsync(patch);
      setDone('Saved. The new rules apply from now on, and the change is in the Audit Log.');
    } catch (e: any) {
      const d = e?.response?.data ?? {};
      const out: Record<string, string> = {};
      Object.entries(d).forEach(([k, v]) => { out[k] = String(([] as unknown[]).concat(v as any)[0]); });
      setErrors(Object.keys(out).length ? out : { detail: 'The rules could not be saved. Try again.' });
    }
  }
  async function onReset() {
    if (!confirm('Put back the values decided on 26 October 2026? Every rule on this page goes back to them.')) return;
    setErrors({});
    await reset.mutateAsync();
    setDone('The decided values are back.');
  }

  const num = (k: keyof FollowUpRules, w = 64) => (
    <input type="number" className="fr-num" style={{ width: w }} aria-label={k.replace(/_/g, ' ')} disabled={locked}
      value={(draft[k] as number | undefined) ?? ''} onChange={(e) => set(k, e.target.value === '' ? '' : Number(e.target.value))} />
  );
  const time = (k: 'clock_start' | 'morning_alert_time') => (
    <input type="time" className="fr-num" aria-label={k.replace(/_/g, ' ')} disabled={locked}
      value={String(draft[k] ?? '').slice(0, 5)} onChange={(e) => set(k, e.target.value)} />
  );
  const tick = (label: string, on: boolean, onChange: (v: boolean) => void) => (
    <label className="fr-tick"><input type="checkbox" checked={on} disabled={locked} onChange={(e) => onChange(e.target.checked)} />{label}</label>
  );
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
  const stages = draft.newcomer_stages ?? [];
  const toggleStage = (s: string, on: boolean) =>
    set('newcomer_stages', on ? [...stages.filter((x) => x !== s), s] : stages.filter((x) => x !== s));
  const ex = example(draft);
  const last = data.updated_at
    ? ` Last changed by ${data.updated_by_name || 'the system'} on ${new Date(data.updated_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}.`
    : '';

  return (
    <div className="fr-page">
      <div className="gender-notice">
        <b>These rules apply at every location.</b> {locked
          ? 'Only an administrator covering All locations can change them, so they are shown here to read.'
          : 'Only an administrator covering All locations can change them, and every change is written to the Audit Log.'}{last}
      </div>

      <div className="card fr-card">
        <h3>Time limits</h3>
        <p className="muted fr-sub">The clock starts on the service day. When names are ticked after the absence check has run, it starts when the task is made instead.</p>
        {row('Clock starts at', 'frClock', <>{time('clock_start')} on the service day</>, 'clock_start')}
        {row('Follow-up due after', 'frDue', <>{num('due_hours')} hours</>, 'due_hours', 'Absence tasks and newcomer first-visit tasks')}
        {row('Reason required after', 'frReason', <>{num('reason_hours')} hours</>, 'reason_hours', 'The shepherd gives a reason and a new date for each late task')}
        {row("On the Follow-up Coordinator's Review list after", 'frReview', <>{num('review_days')} days</>, 'review_days')}
        {row('Follow-up Coordinator decides within', 'frDecide', <>{num('decide_days')} days</>, 'decide_days', 'Not decided by then: it goes to the administrators with an alert')}
        {row('Furthest new date a shepherd can give', 'frMaxDate', <>{num('max_new_date_days')} days ahead</>, 'max_new_date_days')}
        <div className="fr-example">
          <b>With these settings, for a {ex.day} service:</b><br />
          due {ex.due}, reason by {ex.reason}, on the Review list {ex.review}, decided by {ex.decide}.
        </div>
      </div>

      <div className="card fr-card">
        <h3>Repeated absences</h3>
        <p className="muted fr-sub">Counted for the same meeting each time, for example Friday Worship.</p>
        {row('Alert the Follow-up Coordinator from the', 'frAlertFrom', <>{num('alert_from_miss', 56)} miss in a row, then
          <select className="selectbox" aria-label="How often after that" disabled={locked} value={draft.alert_repeat ?? 'every'}
            onChange={(e) => set('alert_repeat', e.target.value)}>
            <option value="every">every further miss</option>
            <option value="every-second">every 2nd miss</option>
          </select></>, 'alert_from_miss')}
        {row('Follow-up Coordinator visit task at the', 'frVisit', <>{num('visit_task_at_miss', 56)} miss in a row</>, 'visit_task_at_miss', 'One visit task for the whole run, while the alerts continue')}
        {row('Failed attempts before it goes to the Follow-up Coordinator', 'frAttempts', num('attempts_before_coordinator'), 'attempts_before_coordinator')}
        {row('Attendance falling task', 'frFalling', <>fewer than {num('falling_percent', 56)}% of the last {num('falling_window', 56)} services</>, 'falling_percent')}
        {errors.falling_window && <div className="fr-err" role="alert">{errors.falling_window}</div>}
      </div>

      <div className="card fr-card">
        <h3>Shepherds and newcomers</h3>
        {row('People per shepherd before a warning', 'frLimit', num('shepherd_limit'), 'shepherd_limit', 'Auto-assign shows "7 of 6" and still lets you go ahead')}
        {row('Newcomer stages followed up', 'frStages', <>
          {tick('New', stages.includes('new'), (v) => toggleStage('new', v))}
          {tick('Contacted', stages.includes('contacted'), (v) => toggleStage('contacted', v))}
          {tick('Attending', stages.includes('attending'), (v) => toggleStage('attending', v))}
        </>, 'newcomer_stages', 'Member and Not Interested are not offered. Members are followed up as members, and Not Interested stops follow-up.')}
      </div>

      <div className="card fr-card">
        <h3>Reminders and alerts</h3>
        {row('Absence check and attendance reminder run', 'frCheck', <>{num('check_hours_after_start')} hours after a tracked service starts</>, 'check_hours_after_start', 'Start times are set in Meeting Types, under Settings on each meeting.')}
        {row('Attendance reminder goes to', 'frRemind', <>
          {tick('Administrators', !!draft.remind_administrators, (v) => set('remind_administrators', v))}
          {tick('Location Coordinators', !!draft.remind_location_coordinators, (v) => set('remind_location_coordinators', v))}
        </>, 'remind_administrators', 'Not sent when names are already ticked')}
        {row('Morning alert to shepherds at', 'frMorning', time('morning_alert_time'), 'morning_alert_time')}
        <p className="muted fr-note" style={{ marginTop: 8 }}>The app checks the clock twice an hour, so an alert can arrive up to 30 minutes after its time. Due times are always exact.</p>
      </div>

      <div className="card fr-card">
        <h3>Targets</h3>
        <p className="muted fr-sub">Shown on the Follow-up Review page.</p>
        {row('On time', 'frOnTime', <>{num('target_on_time')}% or more</>, 'target_on_time')}
        {row('First contact within', 'frFirst', <>{num('target_first_contact_hours')} hours</>, 'target_first_contact_hours')}
        {row('Reached', 'frReached', <>{num('target_reached')}% or more</>, 'target_reached')}
      </div>

      {errors.detail && <p className="form-error" role="alert">{errors.detail}</p>}
      {Object.keys(errors).length > 0 && !errors.detail && <p className="form-error" role="alert">Nothing was saved. Correct the rule shown in red, then save again.</p>}
      {done && <p className="fr-done" role="status">{done}</p>}
      {!locked && (
        <div className="fr-actions">
          <button className="btn" onClick={onSave} disabled={!changed.length || save.isPending}>Save changes</button>
          <button className="btn outline" onClick={onReset} disabled={reset.isPending}>Put back the decided values</button>
        </div>
      )}
    </div>
  );
}
