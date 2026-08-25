import type { IconName } from '../components/ui/Icon';

export interface NavItem {
  key: string;
  label: string;
  icon: IconName;
  path: string;
  module: string | null; // null = always visible to any authenticated user (Dashboard has no ViewSet/module of its own)
}

// Ported exactly from the demo's NAV_ITEMS, now with each item mapped to
// its real backend module (Batch 0.6's permission system) for genuine
// role-based filtering in Batch 3.2, replacing the demo's role.nav array.
export const NAV_ITEMS: NavItem[] = [
  { key: 'dashboard', label: 'Dashboard', icon: 'grid', path: '/', module: null },
  { key: 'attendance', label: 'Attendance', icon: 'check', path: '/attendance', module: 'attendance' },
  { key: 'members', label: 'Members', icon: 'users', path: '/members', module: 'members' },
  { key: 'newcomers', label: 'Newcomers & Follow-up', icon: 'userplus', path: '/newcomers', module: 'newcomers' },
  // Under the newcomers module: the same people do both jobs, and a
  // separate permission would mean one more thing to configure for no gain.
  { key: 'enquiries', label: 'Online Enquiries', icon: 'userplus', path: '/enquiries', module: 'newcomers' },
  { key: 'finance', label: 'Giving & Finance', icon: 'coin', path: '/finance', module: 'finance' },
  { key: 'goals', label: 'Goals', icon: 'target', path: '/goals', module: 'goals' },
  { key: 'reports', label: 'Reports', icon: 'doc', path: '/reports', module: 'reports' },
  { key: 'admin', label: 'Admin', icon: 'gear', path: '/admin', module: 'admin' },
  // module: null so the guide shows for every role. Someone with the
  // narrowest permissions is exactly who needs it most.
  { key: 'help', label: 'Help & Guide', icon: 'doc', path: '/help', module: null },
];
