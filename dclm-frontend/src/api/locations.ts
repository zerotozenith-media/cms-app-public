import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export interface Location {
  id: string;
  name: string;
  note: string;
  is_core: boolean;
}

export function useLocations() {
  return useQuery({
    queryKey: ['locations'],
    queryFn: async () => {
      const resp = await apiClient.get<Location[] | { results: Location[] }>('/locations/');
      return Array.isArray(resp.data) ? resp.data : resp.data.results;
    },
  });
}
