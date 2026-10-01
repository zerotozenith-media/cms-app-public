import { getViewingLocation } from './viewing';
import axios, { type InternalAxiosRequestConfig } from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const ACCESS_TOKEN_KEY = 'dclm_access_token';
const REFRESH_TOKEN_KEY = 'dclm_refresh_token';

export const tokenStorage = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach the access token to every request.
apiClient.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // F2: narrows what the server returns to the location picked in the top bar.
  const viewing = getViewingLocation();
  if (viewing) config.headers['X-Viewing-Location'] = viewing;
  return config;
});

// On a 401, try refreshing the access token once, then retry the
// original request. If refresh also fails, clear tokens and let the
// caller's own error handling / route protection take over , no forced
// redirect here, so this stays a plain API client, not tied to routing.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) return null;
  try {
    const resp = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, { refresh });
    const newAccess = resp.data.access as string;
    localStorage.setItem(ACCESS_TOKEN_KEY, newAccess);
    return newAccess;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean };
    if (error.response?.status === 401 && !original._retried && tokenStorage.getRefresh()) {
      original._retried = true;
      // Coalesce concurrent 401s into a single refresh call, not one per request.
      if (!refreshPromise) refreshPromise = refreshAccessToken().finally(() => { refreshPromise = null; });
      const newAccess = await refreshPromise;
      if (newAccess) {
        original.headers.Authorization = `Bearer ${newAccess}`;
        return apiClient(original);
      }
    }
    return Promise.reject(error);
  },
);


/** A stored file's address. The server may give a path such as
 *  /media/..., which lives on the API's host, not the app's. */
export function mediaUrl(url?: string | null): string | null {
  if (!url) return null;
  if (/^https?:\/\//.test(url)) return url;
  try { return new URL(url, API_BASE_URL).toString(); } catch { return url; }
}
