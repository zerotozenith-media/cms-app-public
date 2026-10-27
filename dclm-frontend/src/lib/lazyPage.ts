import { lazy } from 'react';
import type { ComponentType } from 'react';

/**
 * Speed (Kay, 27 October 2026): each page is downloaded only when it is
 * first opened, so signing in loads less. After an update the old page
 * files are gone, so a page that cannot be fetched reloads the app once to
 * get the new version instead of showing a blank screen.
 */
const KEY = 'dclm-reloaded-for-update';

export function reloadOnceForUpdate(): boolean {
  try {
    if (sessionStorage.getItem(KEY)) return false;
    sessionStorage.setItem(KEY, String(Date.now()));
  } catch { /* storage blocked: still reload once per page view */ }
  window.location.reload();
  return true;
}

export function clearReloadMark() {
  try { sessionStorage.removeItem(KEY); } catch { /* nothing to clear */ }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function lazyPage<T extends Record<string, ComponentType<any>>, K extends keyof T>(load: () => Promise<T>, name: K) {
  return lazy(async () => {
    try {
      const m = await load();
      clearReloadMark();
      return { default: m[name] };
    } catch (e) {
      if (reloadOnceForUpdate()) return new Promise<never>(() => {});
      throw e;
    }
  });
}
