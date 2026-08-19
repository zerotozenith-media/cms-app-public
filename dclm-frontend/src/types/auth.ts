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

export interface AuthUser {
  id: number;
  email: string;
  name: string;
  role: string | null;
  location: string | null;
  location_name: string | null;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: AuthUser;
}
