import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

/**
 * Help & Guide (Kay, 26 October 2026): the manual and Help pictures are
 * served to signed-in people only, so they are fetched with the person's
 * sign-in and shown from memory. The manual is fetched once per visit.
 */
let manualUrl: string | null = null;

async function manualBlobUrl(): Promise<string> {
  if (manualUrl) return manualUrl;
  const r = await apiClient.get('/help/manual/', { responseType: 'blob' });
  manualUrl = URL.createObjectURL(new Blob([r.data], { type: 'application/pdf' }));
  return manualUrl;
}

/** A message after opening or saving the manual. */
export type HelpMsg = { text: string; error: boolean } | null;

/** Phones and tablets: most cannot show a PDF inside the app, so the manual
 *  is saved to the device instead, and the message says which page to open. */
const isTouch = () => typeof window !== 'undefined' && !!window.matchMedia?.('(pointer: coarse)').matches;

/** Saves the manual as a file. */
export async function downloadManual(printed?: number): Promise<HelpMsg> {
  try {
    const url = await manualBlobUrl();
    const a = document.createElement('a');
    a.href = url;
    a.download = 'DCLM-user-manual-v11.14.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    return { text: printed ? `The manual is saved as DCLM-user-manual-v11.14.pdf. Open it and go to page ${printed}.`
      : 'The manual is saved as DCLM-user-manual-v11.14.pdf.', error: false };
  } catch {
    return { text: 'The manual could not be downloaded. Check your connection and try again.', error: true };
  }
}

/** Opens the manual at a printed page number (the PDF page is one later,
 *  because of the cover). On a phone it is saved instead. */
export async function openManual(printed?: number): Promise<HelpMsg> {
  if (isTouch()) return downloadManual(printed);
  // Open the window straight away, so the browser does not block it.
  const w = window.open('', '_blank');
  if (w) {
    try { w.document.title = 'User manual'; w.document.body.innerHTML = '<p style="font-family:sans-serif;padding:20px">Opening the manual…</p>'; } catch { /* another origin */ }
  }
  try {
    const url = await manualBlobUrl();
    const at = printed ? `${url}#page=${printed + 1}` : url;
    if (w) { w.location.href = at; return null; }
    return downloadManual(printed);
  } catch {
    w?.close();
    return { text: 'The manual could not be opened. Check your connection and try again.', error: true };
  }
}

export function useHelpImage(name?: string) {
  return useQuery({
    queryKey: ['help-img', name],
    enabled: !!name,
    staleTime: Infinity,
    gcTime: Infinity,
    retry: 1,
    queryFn: async () => {
      const r = await apiClient.get(`/help/img/${name}/`, { responseType: 'blob' });
      return URL.createObjectURL(r.data as Blob);
    },
  });
}

export interface HelpContact { name: string; email: string; covers: string }

export function useHelpContacts(enabled = true) {
  return useQuery({
    queryKey: ['help-contacts'],
    enabled,
    staleTime: 10 * 60 * 1000,
    queryFn: async () => (await apiClient.get('/help/contacts/')).data as { administrators: HelpContact[]; coordinators: HelpContact[] },
  });
}
