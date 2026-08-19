import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type { Role, RolePermission, AdminUser, AuditLogEntry, LoginAttempt } from '../types/admin';

// --- Users ---
export function useAdminUsers() {
  return useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => (await apiClient.get<PaginatedResponse<AdminUser>>('/users/', { params: { page_size: 100 } })).data.results,
  });
}
export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await apiClient.post<AdminUser>('/users/', payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  });
}
export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/users/${id}/`); },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  });
}

// --- Roles & Permissions ---
export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: async () => (await apiClient.get<PaginatedResponse<Role> | Role[]>('/roles/', { params: { page_size: 100 } })).data,
    select: (data) => Array.isArray(data) ? data : data.results,
  });
}
export function useCreateRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => (await apiClient.post<Role>('/roles/', { name })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['roles'] }),
  });
}
export function useDeleteRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/roles/${id}/`); },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['roles'] }),
  });
}
export function useUpsertRolePermission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { existingId?: number; role: number; module: string } & Partial<RolePermission>) => {
      const { existingId, ...body } = payload;
      if (existingId) {
        return (await apiClient.patch<RolePermission>(`/role-permissions/${existingId}/`, body)).data;
      }
      return (await apiClient.post<RolePermission>('/role-permissions/', {
        can_view: false, can_create: false, can_edit: false, can_delete: false, ...body,
      })).data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['roles'] }),
  });
}

// --- Locations ---
export function useAdminLocations() {
  return useQuery({
    queryKey: ['locations'],
    queryFn: async () => {
      const resp = await apiClient.get('/locations/', { params: { page_size: 100 } });
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
  });
}
export function useCreateLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { id: string; name: string; note: string }) =>
      (await apiClient.post('/locations/', payload)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['locations'] }),
  });
}
export function useDeleteLocation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => apiClient.delete(`/locations/${id}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['locations'] }),
  });
}

// --- Audit Log & Login Attempts (read-only) ---
interface AuditParams { entity_type?: string; ordering?: string; page?: number; page_size?: number; search?: string; }
export function useAuditLog(params: AuditParams) {
  return useQuery({
    queryKey: ['audit-log', params],
    queryFn: async () => (await apiClient.get<PaginatedResponse<AuditLogEntry>>('/audit-log/', { params })).data,
  });
}

interface LoginAttemptParams { successful?: string; ordering?: string; page?: number; page_size?: number; }
export function useLoginAttempts(params: LoginAttemptParams) {
  return useQuery({
    queryKey: ['login-attempts', params],
    queryFn: async () => (await apiClient.get<PaginatedResponse<LoginAttempt>>('/login-attempts/', { params })).data,
  });
}
