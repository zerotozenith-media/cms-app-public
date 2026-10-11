import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAlertSettings } from '../../api/alerts';
import { useAuth } from '../../context/AuthContext';
import { currentSubscription, deviceKind, pushState, turnOn, type PushState } from '../../lib/push';

const KEY = 'alert-banner-later';
const LATER_DAYS = 30;

function snoozed(uid?: number) {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || '{}');
    return uid != null && v[uid] && Date.now() - v[uid] < LATER_DAYS * 86400000;
  } catch { return false; }
}
function snooze(uid?: number) {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || '{}');
    if (uid != null) v[uid] = Date.now();
    localStorage.setItem(KEY, JSON.stringify(v));
  } catch { /* private window: the banner simply comes back next time */ }
}

/**
 * Invites people to turn alerts on for the device they are using (Kay,
 * October 2026). Shown on the dashboard until alerts are on here, or until
 * Not now, which hides it on this device for 30 days. Never shown where the
 * browser cannot do alerts, or where they were blocked.
 */
export function AlertBanner() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [state, setState] = useState<PushState | null>(null);
  const [endpoint, setEndpoint] = useState<string | null>(null);
  const [hidden, setHidden] = useState(() => snoozed(user?.id));
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const { data } = useAlertSettings(endpoint);

  useEffect(() => {
    let live = true;
    (async () => {
      const s = await pushState().catch(() => 'unsupported' as PushState);
      const sub = await currentSubscription().catch(() => null);
      if (live) { setEndpoint(sub?.endpoint ?? null); setState(s); }
    })();
    return () => { live = false; };
  }, []);

  if (hidden || state === null) return null;
  // On here and known to the server for this person: nothing to ask.
  const onHere = state === 'on' && (!data || data.this_device);
  if (!note && (state === 'unsupported' || state === 'denied' || onHere)) return null;
  if (state === 'on' && !data) return null;

  const kind = deviceKind();
  const ios = state === 'ios-needs-home-screen';
  const name = kind === 'device' ? 'device' : kind;

  async function enable() {
    setBusy(true);
    try {
      const s = await turnOn();
      if (s === 'on') { setNote('Alerts are on for this ' + name + '.'); setTimeout(() => setHidden(true), 4000); }
      else if (s === 'denied') setNote('Alerts are blocked for this site. Allow notifications for it in your settings, then turn them on in My profile.');
      else setNote('');
    } catch {
      setNote('Alerts could not be turned on. Try again from My profile.');
    } finally { setBusy(false); }
  }

  return (
    <div className="alert-banner" role="region" aria-label="Alerts">
      <span className="alert-banner-icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" /></svg>
      </span>
      <span className="alert-banner-text">
        {note ? <b role="status">{note}</b> : ios ? (
          <>
            <b>Get alerts on this {name}?</b>
            <span>First add DCLM Bahrain to your Home Screen: in Safari press Share, then Add to Home Screen, and open it from there.</span>
          </>
        ) : (
          <>
            <b>Get alerts on this {name}?</b>
            <span>Know straight away when someone is given to you, and get a 7 am summary of what is waiting.</span>
          </>
        )}
      </span>
      <span className="alert-banner-acts">
        {note ? (
          <button className="btn sm ghost" onClick={() => setHidden(true)}>Close</button>
        ) : (
          <>
            {ios
              ? <button className="btn sm" onClick={() => navigate('/profile')}>Show me how</button>
              : <button className="btn sm" disabled={busy} onClick={enable}>Turn on</button>}
            <button className="btn sm ghost" onClick={() => { snooze(user?.id); setHidden(true); }}>Not now</button>
          </>
        )}
      </span>
    </div>
  );
}
