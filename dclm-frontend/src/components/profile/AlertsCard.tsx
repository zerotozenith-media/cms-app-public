import { useEffect, useState } from 'react';
import { Card } from '../ui/Card';
import { useAlertSettings, useSaveAlertKind, useTestAlert } from '../../api/alerts';
import { currentSubscription, isIOS, pushState, turnOff, turnOn, type PushState } from '../../lib/push';

/**
 * Alerts on this device (Kay, October 2026). Turned on once per phone or
 * computer. The choices of which alerts to get belong to the person, so
 * they follow them to every device.
 */
export function AlertsCard() {
  const [state, setState] = useState<PushState | null>(null);
  const [endpoint, setEndpoint] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const { data, refetch } = useAlertSettings(endpoint);
  const save = useSaveAlertKind();
  const test = useTestAlert();

  async function refresh() {
    const s = await pushState();
    const sub = await currentSubscription().catch(() => null);
    setEndpoint(sub?.endpoint ?? null);
    setState(s);
  }
  useEffect(() => { refresh(); }, []);
  // On here but not known to the server (for example after signing in as
  // someone else on this device): treat as off, so one press fixes it.
  const on = state === 'on' && (data ? data.this_device : true);

  async function enable() {
    setBusy(true); setErr(''); setMsg('');
    try {
      const s = await turnOn();
      await refresh(); await refetch();
      if (s === 'on') setMsg('Alerts are on for this device.');
      else if (s === 'denied') setErr('Alerts are blocked for this site. Allow notifications for it in your browser settings, then press Turn on again.');
    } catch {
      setErr('Alerts could not be turned on. Check you are online and try again.');
    } finally { setBusy(false); }
  }
  async function disable() {
    setBusy(true); setErr(''); setMsg('');
    try { await turnOff(); await refresh(); await refetch(); setMsg('Alerts are off for this device.'); }
    catch { setErr('Alerts could not be turned off. Try again.'); }
    finally { setBusy(false); }
  }

  return (
    <Card style={{ marginTop: 16 }}>
      <h3>Alerts on this device</h3>
      <p className="muted alerts-intro">Alerts reach this phone or computer even when the system is closed. Turn them on once on each device you use.</p>

      {state === null ? null : state === 'unsupported' ? (
        <p className="gender-notice">This browser cannot show alerts. Use Chrome, Edge, Firefox or Safari, kept up to date.</p>
      ) : state === 'ios-needs-home-screen' ? (
        <div className="gender-notice">
          On an iPhone or iPad, alerts work once the system is on your Home Screen. In Safari, press <b>Share</b>, then <b>Add to Home Screen</b>. Open DCLM Bahrain from there and come back to this page.
        </div>
      ) : state === 'denied' ? (
        <div className="gender-notice">Alerts are blocked for this site. Allow notifications for it in your browser or phone settings, then reload this page.</div>
      ) : (
        <div className="form-actions-row alerts-actions">
          {on ? (
            <>
              <span className="alerts-on">On for this device</span>
              <button className="btn sm outline" disabled={test.isPending || busy}
                onClick={() => { setErr(''); setMsg(''); test.mutate(undefined, {
                  onSuccess: () => setMsg('Test alert sent. It should appear in a few seconds.'),
                  onError: (e: any) => setErr(e?.response?.data?.detail || 'The test alert could not be sent.'),
                }); }}>Send me a test alert</button>
              <button className="btn sm ghost" disabled={busy} onClick={disable}>Turn off here</button>
            </>
          ) : (
            <button className="btn sm" disabled={busy} onClick={enable}>Turn on alerts</button>
          )}
        </div>
      )}
      {msg && <p className="muted alerts-msg" role="status">{msg}</p>}
      {err && <p className="form-error" role="alert">{err}</p>}

      {data && (
        <>
          <div className="alerts-head">Send me alerts for</div>
          {data.kinds.map((k) => (
            <label className="alerts-kind" key={k.key}>
              <input type="checkbox" checked={k.on} disabled={save.isPending}
                onChange={(e) => save.mutate({ [k.key]: e.target.checked })} />
              <span><b>{k.label}</b><span className="muted">{k.help}</span></span>
            </label>
          ))}
          {save.isError && <p className="form-error" role="alert">That choice could not be saved. Try again.</p>}
          <p className="muted alerts-foot">
            {data.devices === 0 ? 'No device of yours has alerts on yet.' : `Alerts are on for ${data.devices} of your devices.`}
            {!isIOS() && ' On an iPhone, first add the system to your Home Screen: in Safari press Share, then Add to Home Screen, and open it from there.'}
          </p>
        </>
      )}
    </Card>
  );
}
