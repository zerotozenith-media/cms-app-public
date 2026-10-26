import { useEffect, useState } from 'react';

/**
 * P12, P13 and O8 (review, 25 October 2026): an action the server refuses
 * always says why. Every failed save comes here. Where the screen already
 * shows its own message beside the form, this stays quiet, so the person
 * never reads the same thing twice.
 */
type Listener = (msg: string) => void;
const listeners = new Set<Listener>();

function messageOf(e: any): string {
  const d = e?.response?.data;
  const status = e?.response?.status;
  if (!e?.response) return 'The app could not reach the server. Check the connection and try again.';
  if (status === 403 && !d?.detail) return 'Your role does not allow this.';
  if (status >= 500) return 'Something went wrong on the server. Try again, and tell an administrator if it keeps happening.';
  if (d && typeof d === 'object') {
    if (d.detail) return String(d.detail);
    const first = Object.entries(d)[0];
    if (first) {
      const v = String(([] as unknown[]).concat(first[1] as any)[0]);
      return v;
    }
  }
  return 'That could not be saved. Try again.';
}

function inlineShown(before: Set<Element>) {
  return [...document.querySelectorAll('.form-error, [role="alert"]')].some(
    (el) => !before.has(el) && !el.closest('.refusal-toast') && (el as HTMLElement).offsetParent !== null);
}

/** Called by the app's MutationCache for every failed save. */
export function reportRefusal(e: unknown) {
  // 401 is handled by signing in again, not by a message here.
  if ((e as any)?.response?.status === 401) return;
  const before = new Set(document.querySelectorAll('.form-error, [role="alert"]'));
  const msg = messageOf(e);
  window.setTimeout(() => {
    if (inlineShown(before)) return;
    listeners.forEach((l) => l(msg));
  }, 250);
}

export function RefusalToast() {
  const [msg, setMsg] = useState('');
  useEffect(() => {
    const l: Listener = (m) => setMsg(m);
    listeners.add(l);
    return () => { listeners.delete(l); };
  }, []);
  useEffect(() => {
    if (!msg) return;
    const t = window.setTimeout(() => setMsg(''), 12000);
    return () => window.clearTimeout(t);
  }, [msg]);
  if (!msg) return null;
  return (
    <div className="refusal-toast" role="alert">
      <div><b>Not saved.</b> {msg}</div>
      <button className="btn sm ghost" onClick={() => setMsg('')}>Close</button>
    </div>
  );
}
