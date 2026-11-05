import { useNotOfferedShepherds, type EligibleShepherd } from '../../api/followup';
import { HelpMark } from '../ui/HelpMark';

/**
 * Under a shepherd list: everyone not offered, and why (5 November 2026).
 * A Qatar leader covering All locations was missing from a Bahrain HQ
 * newcomer's list and nothing said why.
 *
 * genders: the gender of each person being given a shepherd (one on a
 * profile, several when assigning many at once). Empty when not known.
 */
export function NotOffered({ location, member, genders, eligible }: {
  location?: string; member?: number; genders: string[]; eligible: EligibleShepherd[] | undefined;
}) {
  const { data } = useNotOfferedShepherds(location, member);
  const known = [...new Set(genders.filter(Boolean))];
  const byGender = (eligible ?? []).flatMap((s) => {
    if (!known.length || known.every((g) => g === s.gender)) return [];
    if (!s.gender) return [{ id: s.id, name: s.name, reason: 'their gender is not set in Admin, Users & Roles, so they can only take people whose gender is not known.' }];
    return [{ id: s.id, name: s.name, reason: known.length > 1
      ? 'men follow up men, women follow up women, and the people chosen include both.'
      : 'men follow up men, women follow up women.' }];
  });
  const rows = [...(data ?? []), ...byGender];
  if (!rows.length) return null;
  // People with the same reason share a line, so the list stays short.
  const groups = new Map<string, string[]>();
  rows.forEach((r) => groups.set(r.reason, [...(groups.get(r.reason) ?? []), r.name]));
  const people = new Set(rows.map((r) => r.id)).size;
  return (
    <details className="not-offered" open>
      <summary>Not offered ({people})<HelpMark topic="notOffered" /></summary>
      <ul>
        {[...groups].map(([reason, names]) => <li key={reason}><b>{names.join(', ')}:</b> {reason}</li>)}
      </ul>
    </details>
  );
}
