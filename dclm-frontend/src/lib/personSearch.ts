/**
 * Search a loaded list of people by name, phone, email or social handle
 * (Kay, 31 October 2026: Newcomers and Online Enquiries had no search).
 *
 * Phone numbers match on digits only, so "3312 4455", "+973 33124455" and
 * "33124455" all find the same person.
 */
export function matchesPerson(
  p: { name?: string | null; phone?: string | null; email?: string | null; social_handle?: string | null },
  query: string,
): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const text = [p.name, p.email, p.social_handle].filter(Boolean).join(' ').toLowerCase();
  if (text.includes(q)) return true;
  const digits = q.replace(/\D/g, '');
  return digits.length >= 3 && (p.phone ?? '').replace(/\D/g, '').includes(digits);
}
