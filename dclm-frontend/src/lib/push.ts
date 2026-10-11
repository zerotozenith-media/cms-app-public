/**
 * Phone and computer alerts (Kay, October 2026): web push through the
 * service worker in /sw.js. Everything here is safe to call on a browser
 * that cannot do alerts; it simply reports that.
 */
import { apiClient } from '../api/client';

export type PushState = 'unsupported' | 'ios-needs-home-screen' | 'denied' | 'off' | 'on';

export function isIOS() {
  const ua = navigator.userAgent || '';
  return /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && (navigator.maxTouchPoints ?? 0) > 1);
}

export function isStandalone() {
  return window.matchMedia?.('(display-mode: standalone)').matches || (navigator as any).standalone === true;
}

/** For wording only: what to call this device. */
export function deviceKind(): 'phone' | 'iPhone' | 'iPad' | 'computer' | 'device' {
  const ua = navigator.userAgent || '';
  if (/iPhone|iPod/.test(ua)) return 'iPhone';
  if (/iPad/.test(ua) || (navigator.platform === 'MacIntel' && (navigator.maxTouchPoints ?? 0) > 1)) return 'iPad';
  if (/Android/.test(ua)) return 'phone';
  if (/Windows|Macintosh|Mac OS X|Linux|CrOS/.test(ua)) return 'computer';
  return 'device';
}

export function pushSupported() {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
}

/** Registered once when the app starts, so alerts can arrive. */
export function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => { /* alerts stay off; nothing else depends on it */ });
  });
}

async function registration() {
  if (!('serviceWorker' in navigator)) return null;
  return (await navigator.serviceWorker.getRegistration('/')) ?? (await navigator.serviceWorker.register('/sw.js'));
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const reg = await registration();
  return reg ? reg.pushManager.getSubscription() : null;
}

export async function pushState(): Promise<PushState> {
  if (!pushSupported()) return isIOS() && !isStandalone() ? 'ios-needs-home-screen' : 'unsupported';
  if (Notification.permission === 'denied') return 'denied';
  return (await currentSubscription()) ? 'on' : 'off';
}

function keyBytes(base64url: string) {
  const pad = '='.repeat((4 - (base64url.length % 4)) % 4);
  const raw = atob((base64url + pad).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

function deviceName() {
  const ua = navigator.userAgent;
  const os = /Android/.test(ua) ? 'Android' : isIOS() ? 'iPhone or iPad' : /Windows/.test(ua) ? 'Windows' : /Mac/.test(ua) ? 'Mac' : /Linux/.test(ua) ? 'Linux' : 'this device';
  const br = /Edg\//.test(ua) ? 'Edge' : /Firefox\//.test(ua) ? 'Firefox' : /Chrome\//.test(ua) ? 'Chrome' : /Safari\//.test(ua) ? 'Safari' : 'browser';
  return `${br} on ${os}`;
}

/** Ask permission, subscribe this device and tell the server. */
export async function turnOn(): Promise<PushState> {
  if (!pushSupported()) return pushState();
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') return permission === 'denied' ? 'denied' : 'off';
  const reg = await registration();
  if (!reg) return 'unsupported';
  const { data } = await apiClient.get<{ public_key: string }>('/alerts/key/');
  let sub = await reg.pushManager.getSubscription();
  // A device subscribed against another key cannot receive this server's alerts.
  if (sub && sub.options?.applicationServerKey) {
    const have = new Uint8Array(sub.options.applicationServerKey as ArrayBuffer);
    const want = keyBytes(data.public_key);
    if (have.length !== want.length || have.some((b, i) => b !== want[i])) { await sub.unsubscribe(); sub = null; }
  }
  if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(data.public_key) });
  const json = sub.toJSON();
  await apiClient.post('/alerts/subscribe/', { endpoint: json.endpoint, keys: json.keys, device: deviceName() });
  return 'on';
}

/** Turn alerts off for this device, on the server and in the browser. */
export async function turnOff() {
  const sub = await currentSubscription();
  if (!sub) return;
  try { await apiClient.post('/alerts/unsubscribe/', { endpoint: sub.endpoint }); } catch { /* signed out already */ }
  await sub.unsubscribe();
}
