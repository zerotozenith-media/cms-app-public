import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { Member, Household, PaginatedResponse, MemberListParams } from '../types/members';

const PAGE_SIZE = 8; // matches the demo's list page size

export interface MemberStats {
  total: number;
  workers: number;
  workers_in_training: number;
  general_members: number;
}

export function useMemberStats() {
  return useQuery({
    queryKey: ['members-stats'],
    queryFn: async () => {
      const resp = await apiClient.get<MemberStats>('/members/stats/');
      return resp.data;
    },
  });
}

export function useMembers(params: MemberListParams) {
  return useQuery({
    queryKey: ['members', params],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<Member>>('/members/', {
        params: { ...params, page_size: PAGE_SIZE },
      });
      return resp.data;
    },
  });
}

export function useMember(id: number | undefined) {
  return useQuery({
    queryKey: ['member', id],
    queryFn: async () => {
      const resp = await apiClient.get<Member>(`/members/${id}/`);
      return resp.data;
    },
    enabled: id !== undefined,
  });
}

export function useHouseholds(search?: string) {
  return useQuery({
    queryKey: ['households', search],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<Household>>('/households/', {
        params: search ? { search } : undefined,
      });
      return resp.data.results;
    },
  });
}

export function useCreateHousehold() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; address: string; phone: string }) =>
      (await apiClient.post<Household>('/households/', payload)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['households'] }),
  });
}

export function useDeleteHousehold() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/households/${id}/`); },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['households'] }),
  });
}

export function useCreateMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Member>) => {
      const resp = await apiClient.post<Member>('/members/', payload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members'] });
    },
  });
}

export function useUpdateMember(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Member>) => {
      const resp = await apiClient.patch<Member>(`/members/${id}/`, payload);
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['member', id] });
      queryClient.invalidateQueries({ queryKey: ['members'] });
    },
  });
}

export function useDeleteMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/members/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members'] });
    },
  });
}

export function useMoveCategory(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (to_category: string) => {
      const resp = await apiClient.post<Member>(`/members/${id}/move-category/`, { to_category });
      return resp.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['member', id] });
      queryClient.invalidateQueries({ queryKey: ['members'] });
    },
  });
}

/** Async replacement for the demo's synchronous local-array surname
 * check , queries the real API instead of a mock in-memory list. */
export async function findMembersBySurname(surname: string, exceptId?: number): Promise<Member[]> {
  if (!surname.trim()) return [];
  const resp = await apiClient.get<PaginatedResponse<Member>>('/members/', { params: { search: surname } });
  return resp.data.results.filter(
    (m) => m.surname.toLowerCase() === surname.trim().toLowerCase() && m.id !== exceptId,
  );
}

/**
 * Every member at a location, unpaginated, for the live check-in roster.
 * Separate from useMembers because that one is deliberately paginated
 * for the directory; an usher needs the whole list on one screen with no
 * paging while people are walking through the door.
 */
export function useMemberRoster(location?: string | null) {
  return useQuery({
    queryKey: ['member-roster', location ?? 'all'],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<Member>>('/members/', {
        params: {
          page_size: 500,
          ordering: 'surname,first_name',
          ...(location ? { location } : {}),
        },
      });
      return resp.data.results;
    },
  });
}
