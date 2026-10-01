import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { apiClient, tokenStorage } from '../api/client';
import type { AuthUser, LoginResponse, RolePermission } from '../types/auth';

const USER_STORAGE_KEY = 'dclm_user';

interface AuthContextValue {
  user: AuthUser | null;
  permissions: RolePermission[];
  isLoading: boolean;
  login: (email: string, password: string, extra?: { website?: string; form_loaded_at?: string }) => Promise<void>;
  startSession: (data: LoginResponse & { user: AuthUser & { role_permissions: RolePermission[] } }) => void;
  updateUser: (changes: Partial<AuthUser>) => void;
  logout: () => Promise<void>;
  hasPermission: (module: string, action: 'view' | 'create' | 'edit' | 'delete') => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [permissions, setPermissions] = useState<RolePermission[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from storage on load, so a page refresh doesn't
  // silently log the user out even though their tokens are still valid.
  useEffect(() => {
    const storedUser = localStorage.getItem(USER_STORAGE_KEY);
    if (storedUser && tokenStorage.getAccess()) {
      try {
        const parsed = JSON.parse(storedUser);
        setUser(parsed.user);
        setPermissions(parsed.permissions);
      } catch {
        localStorage.removeItem(USER_STORAGE_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  async function login(email: string, password: string, extra?: { website?: string; form_loaded_at?: string }) {
    const resp = await apiClient.post<LoginResponse & { user: AuthUser & { role_permissions: RolePermission[] } }>(
      '/auth/login/',
      { email, password, ...extra },
    );
    startSession(resp.data);
  }

  // One way to start a session, used by sign-in and by the password reset,
  // which signs the person straight in once their new password is saved.
  function startSession(data: LoginResponse & { user: AuthUser & { role_permissions: RolePermission[] } }) {
    const { access, refresh, user: loggedInUser } = data;
    const { role_permissions, ...userWithoutPerms } = loggedInUser;
    tokenStorage.set(access, refresh);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ user: userWithoutPerms, permissions: role_permissions }));
    setUser(userWithoutPerms);
    setPermissions(role_permissions);
  }

  // After My profile changes a name, email or photo, the top bar follows.
  function updateUser(changes: Partial<AuthUser>) {
    setUser((current) => {
      if (!current) return current;
      const next = { ...current, ...changes };
      try {
        const stored = JSON.parse(localStorage.getItem(USER_STORAGE_KEY) || '{}');
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify({ ...stored, user: next }));
      } catch { /* storage unavailable, the session still works */ }
      return next;
    });
  }

  async function logout() {
    const refresh = tokenStorage.getRefresh();
    try {
      await apiClient.post('/auth/logout/', { refresh });
    } catch {
      // Best-effort , the tokens are cleared locally regardless, so the
      // user is logged out client-side even if the request itself fails
      // (e.g. connectivity), matching the backend's own graceful handling
      // of an already-invalid token in Batch 1.4's LogoutView.
    }
    tokenStorage.clear();
    localStorage.removeItem(USER_STORAGE_KEY);
    setUser(null);
    setPermissions([]);
  }

  function hasPermission(module: string, action: 'view' | 'create' | 'edit' | 'delete') {
    const perm = permissions.find((p) => p.module === module);
    if (!perm) return false;
    return perm[`can_${action}` as const];
  }

  return (
    <AuthContext.Provider value={{ user, permissions, isLoading, login, logout, hasPermission, startSession, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
