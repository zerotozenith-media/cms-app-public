import { useState } from 'react';
import { CONTACT_METHODS } from '../../types/members';
import type { ContactMethod, CompleteFollowUpPayload } from '../../types/members';
import { Icon } from '../ui/Icon';
import { HelpMark } from '../ui/HelpMark';

interface ExistingLog {
  contact_date: string | null;
  contact_method: string;
  contact_goal: string;
  contact_scripture: string;
  contact_root_cause: string;
  contact_next_step: string;
}

interface Props {
  /** Pass the existing record to edit a completed follow-up. The form
   *  pre-fills and saving corrects the record; it does not reopen it. */
  existing?: ExistingLog | null;
  idPrefix: string;
  onSave: (payload: CompleteFollowUpPayload) => void;
  onCancel: () => void;
  saving?: boolean;
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

export function FollowUpCompletionForm({ existing, idPrefix, onSave, onCancel, saving }: Props) {
  const editing = Boolean(existing);
  const [date, setDate] = useState(existing?.contact_date || today());
  const [method, setMethod] = useState<ContactMethod>(
    (existing?.contact_method as ContactMethod) || 'Home visit',
  );
  const [goal, setGoal] = useState(existing?.contact_goal ?? '');
  const [scripture, setScripture] = useState(existing?.contact_scripture ?? '');
  const [rootCause, setRootCause] = useState(existing?.contact_root_cause ?? '');
  const [nextStep, setNextStep] = useState(existing?.contact_next_step ?? '');
  const [error, setError] = useState<string | null>(null);

  function handleSave() {
    // The API rejects a missing field anyway, but naming them here is far
    // more useful than a generic server error after the fact.
    const missing: string[] = [];
    if (!goal.trim()) missing.push('Goal of the visit');
    if (!scripture.trim()) missing.push('Scripture shared');
    if (!rootCause.trim()) missing.push('Root cause');
    if (!nextStep.trim()) missing.push('Next step agreed');
    if (missing.length) {
      setError(`Please complete: ${missing.join(', ')}.`);
      return;
    }
    setError(null);
    onSave({
      contact_date: date,
      contact_method: method,
      contact_goal: goal.trim(),
      contact_scripture: scripture.trim(),
      contact_root_cause: rootCause.trim(),
      contact_next_step: nextStep.trim(),
    });
  }

  return (
    <div className="form-card" style={{ marginTop: 8 }}>
      {editing && (
        <div className="muted" style={{ fontSize: '.78rem', marginBottom: 8 }}>
          Editing a completed follow-up. This corrects the record, it does not reopen the task.
        </div>
      )}

      <div className="form-row">
        <div className="field">
          <label htmlFor={`${idPrefix}-date`}>Date</label>
          <input id={`${idPrefix}-date`} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor={`${idPrefix}-method`}>Method</label>
          <select
            id={`${idPrefix}-method`}
            value={method}
            onChange={(e) => setMethod(e.target.value as ContactMethod)}
          >
            {CONTACT_METHODS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
      </div>

      <div className="followup-guide">
        <div className="followup-guide-title">
          <Icon name="alert" size={14} /> A follow-up should be purposeful, not just a chat
          <HelpMark topic="followUpFields" />
        </div>
        <div className="followup-guide-note">
          All four are required. They are what make this record useful to whoever reads it next.
        </div>
      </div>

      <div className="field">
        <label htmlFor={`${idPrefix}-goal`}>Goal of the visit <span className="req">*</span></label>
        <input
          id={`${idPrefix}-goal`} value={goal} onChange={(e) => setGoal(e.target.value)}
          placeholder="What did you set out to achieve?"
        />
      </div>

      <div className="field">
        <label htmlFor={`${idPrefix}-scripture`}>Scripture shared <span className="req">*</span></label>
        <input
          id={`${idPrefix}-scripture`} value={scripture} onChange={(e) => setScripture(e.target.value)}
          placeholder="Reference and why it fit, or 'None this time'"
        />
        <div className="field-hint">
          If there genuinely was no opening, write "None this time" rather than inventing one.
        </div>
      </div>

      <div className="field">
        <label htmlFor={`${idPrefix}-root`}>Root cause <span className="req">*</span></label>
        <textarea
          id={`${idPrefix}-root`} rows={2} value={rootCause} onChange={(e) => setRootCause(e.target.value)}
          placeholder="What is really behind the absence: work, health, family, discouragement, something unresolved at church?"
        />
      </div>

      <div className="field">
        <label htmlFor={`${idPrefix}-next`}>Next step agreed <span className="req">*</span></label>
        <textarea
          id={`${idPrefix}-next`} rows={2} value={nextStep} onChange={(e) => setNextStep(e.target.value)}
          placeholder="Something concrete: what was committed, by whom, by when?"
        />
      </div>

      {error && <div className="form-error">{error}</div>}

      <button className="btn sm" onClick={handleSave} disabled={saving}>
        {editing ? 'Save changes' : 'Save & mark done'}
      </button>
      <button className="btn sm ghost" onClick={onCancel} disabled={saving}>Cancel</button>
    </div>
  );
}
