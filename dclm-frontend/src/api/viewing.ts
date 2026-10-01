import { useCallback, useSyncExternalStore } from 'react';
import { useQueryClient } from '@tanstack/react-query';

/**
 * F2: the location an administrator covering every location has picked in
 * the top bar. Sent with every request as X-Viewing-Location; the server
 * only ever narrows what it shows by it, and ignores it for anyone limited
 * to one location.
 */
const KEY = 'dclm.viewingLocation';
const listeners = new Set<() => void>();

function read(): string | null {
  try { return localStorage.getItem(KEY) || null; } catch { return null; }
}
export function getViewingLocation(): string | null {
  return read();
}
function write(code: string | null) {
  try { code ? localStorage.setItem(KEY, code) : localStorage.removeItem(KEY); } catch { /* private mode */ }
  listeners.forEach((l) => l());
}
export function clearViewingLocation() {
  write(null);
}

export function useViewingLocation(): [string | null, (code: string | null) => void] {
  const qc = useQueryClient();
  const value = useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
    read, () => null,
  );
  const set = useCallback((code: string | null) => {
    write(code);
    // Every figure and list on screen belongs to the old choice.
    qc.invalidateQueries();
  }, [qc]);
  return [value, set];
}
