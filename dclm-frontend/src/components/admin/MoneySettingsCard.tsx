import { useEffect, useState } from 'react';
import { refusal } from '../../api/accountability';
import { useMyLocations } from '../../api/locations';
import { useMoneySettings, useSaveMoneySettings } from '../../api/monthEnd';
import { useAuth } from '../../context/AuthContext';
import { HelpMark } from '../ui/HelpMark';

/**
 * Money (Kay, 30 October 2026): how each location keeps its money and where
 * its month-end balancing starts. The start month and opening balance can
 * change until the first month is sent for approval.
 */
export function MoneySettingsCard() {
  const { hasPermission } = useAuth();
  const canEdit = hasPermission('admin', 'edit');
  const { data: locations } = useMyLocations();
  const [loc, setLoc] = useState('');
  const chosen = loc || locations?.find((l) => l.is_core)?.id || locations?.[0]?.id || '';
  const { data: s } = useMoneySettings(chosen);
  const save = useSaveMoneySettings();
  const [kept, setKept] = useState('cash'); const [start, setStart] = useState(''); const [opening, setOpening] = useState('');
  const [msg, setMsg] = useState<{ t: string; ok: boolean } | null>(null);

  useEffect(() => {
    if (!s) return;
    setKept(s.kept_as); setStart(s.start_month); setOpening(Number(s.opening_balance).toFixed(2)); setMsg(null);
  }, [s]);

  async function onSave() {
    setMsg(null);
    try {
      await save.mutateAsync({ location: chosen, kept_as: kept, ...(s?.locked ? {} : { start_month: start, opening_balance: opening }) });
      setMsg({ t: 'Saved.', ok: true });
    } catch (e) { setMsg({ t: refusal(e, 'It could not be saved.'), ok: false }); }
  }

  return (
    <div className="card section-gap">
      <div className="toolbar" style={{ flexWrap: 'wrap', gap: 8 }}>
        <div>
          <h3 style={{ flex: 'none' }}>Money</h3>
          <p className="muted" style={{ fontSize: '.82rem', margin: 0 }}>How the money is kept, for the Month-end balance in Giving &amp; Finance.</p>
        </div>
        {(locations ?? []).length > 1 && (
          <select className="selectbox" aria-label="Location" value={chosen} onChange={(e) => setLoc(e.target.value)}>
            {(locations ?? []).map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </select>
        )}
      </div>
      {s && (
        <div className="me-form" style={{ marginTop: 6 }}>
          <div className="field">
            <label htmlFor="ms-kept">Money kept as<HelpMark topic="meKeptAs" /></label>
            <select id="ms-kept" className="selectbox" value={kept} disabled={!canEdit} onChange={(e) => setKept(e.target.value)}>
              <option value="cash">Cash</option><option value="bank">Bank account</option>
            </select>
          </div>
          <div className="me-two">
            <div className="field">
              <label htmlFor="ms-start">Start month<HelpMark topic="meStart" /></label>
              <input id="ms-start" type="month" value={start} disabled={!canEdit || s.locked} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="ms-open">Opening balance (BHD)<HelpMark topic="meStartOpening" /></label>
              <input id="ms-open" inputMode="decimal" value={opening} disabled={!canEdit || s.locked} onChange={(e) => setOpening(e.target.value)} />
            </div>
          </div>
          {s.locked && <p className="muted" style={{ fontSize: '.8rem' }}>The start month and opening balance are fixed, because the first month has been sent for approval. To change them, reopen every month from the start month first.</p>}
          {!canEdit && <p className="muted" style={{ fontSize: '.8rem' }}>Only an administrator can change these.</p>}
          {canEdit && <button className="btn" type="button" disabled={save.isPending} onClick={onSave}>Save</button>}
          {msg && <p className={msg.ok ? 'help-ok' : 'form-error'} role={msg.ok ? 'status' : 'alert'} style={{ marginTop: 10 }}>{msg.t}</p>}
          {s.updated_by && <p className="muted" style={{ fontSize: '.78rem', marginTop: 8 }}>Last changed by {s.updated_by}.</p>}
        </div>
      )}
    </div>
  );
}
