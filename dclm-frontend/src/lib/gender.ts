/**
 * Men follow up men, women follow up women (Kay, 10 October 2026). Someone
 * whose gender is not known may go to anyone, with a warning. The server
 * applies the same rule, so these only decide what the lists offer.
 */
export type Gender = '' | 'Male' | 'Female';

export function canPair(personGender: string | undefined | null, shepherdGender: string | undefined | null) {
  return !personGender || personGender === shepherdGender;
}

export const GROUP: Record<string, string> = { Male: 'Men', Female: 'Women' };
export const ONLY: Record<string, string> = { Male: 'Men only, to match this', Female: 'Women only, to match this' };
