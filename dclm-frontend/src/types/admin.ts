export interface RolePermission {
  id: number;
  role: number;
  module: string;
  can_view: boolean;
  can_create: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export interface Role {
  id: number;
  name: string;
  permissions: RolePermission[];
}

export interface AdminUser {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: number | null;
  role_name: string | null;
  location: string | null;
  location_name: string | null;
  member: number | null;
  is_active: boolean;
  last_login: string | null;
}

export interface AuditLogEntry {
  id: number;
  user: number | null;
  user_name_snapshot: string;
  timestamp: string;
  action: string;
  entity_type: string;
  entity_name: string;
  details: string;
}

export interface LoginAttempt {
  id: number;
  email_attempted: string;
  ip_address: string;
  successful: boolean;
  reason: string;
  timestamp: string;
}

// 'outreach' governs campaign and spend data. Deliberately separate
// from 'admin': whoever runs the church's adverts should be able to see
// what a campaign cost per person reached without also being able to
// create accounts and change church settings.
export const MODULES = ['members', 'attendance', 'newcomers', 'finance', 'goals', 'reports', 'outreach', 'admin'] as const;
