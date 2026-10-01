import { enableKeyboardLinks } from './lib/keyboardLinks';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import './styles/design-system.css';
import './styles/app.css';

/**
 * F11. Lists keep showing while a filter or page changes, with a thin bar
 * across the top, instead of emptying to "Loading". Only lists: on a
 * profile the previous person must never flash up.
 */
const LISTS = new Set([
  'members', 'sessions', 'recent-sessions', 'newcomers', 'all-newcomer-tasks', 'newcomer-tasks',
  'member-followup-tasks', 'enquiries', 'enquiry-tasks', 'giving-list', 'expense-list',
  'remittances', 'audit-log', 'login-attempts', 'testimonies', 'weekly-notes', 'households',
  'dashboard-summary',
]);

const queryClient: QueryClient = new QueryClient({
  // After any change is saved, everything remembered is marked out of date,
  // so no page can show old figures for the minute it is remembered.
  mutationCache: new MutationCache({ onSuccess: () => { queryClient.invalidateQueries(); } }),
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      // Pages seen in the last minute open at once and refresh quietly.
      staleTime: 60_000,
      gcTime: 10 * 60_000,
      placeholderData: (previous: unknown, previousQuery?: { queryKey: readonly unknown[] }) =>
        previousQuery && LISTS.has(String(previousQuery.queryKey[0])) ? previous : undefined,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);

enableKeyboardLinks();
