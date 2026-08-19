import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';

export interface NamedItem { id: number | string; name: string; }

/**
 * Generic CRUD for the ~8 simple admin-configurable name-only lists
 * (Funds, Payment Methods, Expense Categories, Newcomer Sources,
 * Milestone Types, Services, Departments) , all structurally identical
 * on the backend, so one factory avoids writing nearly the same hooks
 * eight times over.
 */
export function useSimpleListCrud<T extends NamedItem = NamedItem>(endpoint: string) {
  const queryClient = useQueryClient();
  const queryKey = [`simple-list-${endpoint}`];

  const list = useQuery({
    queryKey,
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<T> | T[]>(`/${endpoint}/`, { params: { page_size: 100 } });
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
  });

  const create = useMutation({
    mutationFn: async (name: string) => (await apiClient.post<T>(`/${endpoint}/`, { name })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  const remove = useMutation({
    mutationFn: async (id: number | string) => { await apiClient.delete(`/${endpoint}/${id}/`); },
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  return { list, create, remove };
}
