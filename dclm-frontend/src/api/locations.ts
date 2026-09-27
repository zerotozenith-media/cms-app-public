import { useAuth } from '../context/AuthContext';
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

/** The display name for a location code. Showing the code itself put
 *  "bahrain" in lower case on profiles and session forms. */
export function useLocationName() {
  const { data } = useLocations();
  return (code?: string | null) =>
    (data ?? []).find((l) => l.id === code)?.name ?? (code || '');
}

/**
 * The locations this person may record things for. Someone limited to one
 * location gets just that one, because the server refuses any other.
 * Offering the rest only led to a refusal after the form was filled in.
 */
export function useMyLocations() {
  const query = useLocations();
  const { user } = useAuth();
  const mine = user?.location;
  return {
    ...query,
    data: mine ? (query.data ?? []).filter((l) => l.id === mine) : query.data,
  };
}
