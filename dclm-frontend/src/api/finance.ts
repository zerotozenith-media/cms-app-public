import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { PaginatedResponse } from '../types/members';
import type { Fund, PaymentMethod, ExpenseCategory, Project, Giving, Expense, FinanceSummary } from '../types/finance';

function useSimpleList<T>(key: string, url: string) {
  return useQuery({
    queryKey: [key],
    queryFn: async () => {
      const resp = await apiClient.get<PaginatedResponse<T> | T[]>(url);
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
  });
}

export const useFunds = () => useSimpleList<Fund>('funds', '/funds/');
export const usePaymentMethods = () => useSimpleList<PaymentMethod>('payment-methods', '/payment-methods/');
export const useExpenseCategories = () => useSimpleList<ExpenseCategory>('expense-categories', '/expense-categories/');
export const useProjects = () => useSimpleList<Project>('projects', '/projects/');

export function useFinanceSummary() {
  return useQuery({
    queryKey: ['finance-summary'],
    queryFn: async () => (await apiClient.get<FinanceSummary>('/finance/summary/')).data,
  });
}

interface GivingListParams {
  fund?: string; method?: string; ordering?: string; page?: number; page_size?: number;
}
export function useGivingList(params: GivingListParams) {
  return useQuery({
    queryKey: ['giving-list', params],
    queryFn: async () => (await apiClient.get<PaginatedResponse<Giving>>('/giving/', { params })).data,
  });
}

interface ExpenseListParams {
  category?: string; ordering?: string; page?: number; page_size?: number;
}
export function useExpenseList(params: ExpenseListParams) {
  return useQuery({
    queryKey: ['expense-list', params],
    queryFn: async () => (await apiClient.get<PaginatedResponse<Expense>>('/expenses/', { params })).data,
  });
}

function invalidateFinance(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ['giving-list'] });
  queryClient.invalidateQueries({ queryKey: ['expense-list'] });
  queryClient.invalidateQueries({ queryKey: ['finance-summary'] });
  queryClient.invalidateQueries({ queryKey: ['projects'] });
  queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
}

export function useCreateGiving() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) => (await apiClient.post<Giving>('/giving/', payload)).data,
    onSuccess: () => invalidateFinance(queryClient),
  });
}
export function useUpdateGiving() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      (await apiClient.patch<Giving>(`/giving/${id}/`, payload)).data,
    onSuccess: () => invalidateFinance(queryClient),
  });
}
export function useDeleteGiving() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/giving/${id}/`); },
    onSuccess: () => invalidateFinance(queryClient),
  });
}

export function useCreateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: FormData) =>
      (await apiClient.post<Expense>('/expenses/', payload, { headers: { 'Content-Type': 'multipart/form-data' } })).data,
    onSuccess: () => invalidateFinance(queryClient),
  });
}
export function useUpdateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: FormData }) =>
      (await apiClient.patch<Expense>(`/expenses/${id}/`, payload, { headers: { 'Content-Type': 'multipart/form-data' } })).data,
    onSuccess: () => invalidateFinance(queryClient),
  });
}
export function useDeleteExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => { await apiClient.delete(`/expenses/${id}/`); },
    onSuccess: () => invalidateFinance(queryClient),
  });
}
