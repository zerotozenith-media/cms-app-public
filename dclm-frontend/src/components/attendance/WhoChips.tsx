/**
 * Everyone / Members / Newcomers / Not ticked (Kay, 31 October 2026), so a
 * long check-in list can be narrowed with one tap instead of scrolling.
 * Used on Live check-in and on the session page's named attendance.
 */
export type Who = 'everyone' | 'members' | 'newcomers' | 'unticked';

export const NEWCOMER_STAGE: Record<string, string> = {
  new: 'New', contacted: 'Contacted', attending: 'Attending', member: 'Member', 'not-interested': 'Not interested',
};

export function WhoChips({ value, onChange, counts }: {
  value: Who; onChange: (w: Who) => void;
  counts: { everyone: number; members: number; newcomers: number; unticked: number | null };
}) {
  const chips: [Who, string, number | null][] = [
    ['everyone', 'Everyone', counts.everyone],
    ['members', 'Members', counts.members],
    ['newcomers', 'Newcomers', counts.newcomers],
    ['unticked', 'Not ticked', counts.unticked],
  ];
  return (
    <div className="who-chips" role="group" aria-label="Show">
      {chips.map(([k, label, n]) => (
        <button key={k} type="button" className={`who-chip${value === k ? ' on' : ''}`} aria-pressed={value === k}
          onClick={() => onChange(k)}>
          {label}{n !== null ? ` ${n}` : ''}
        </button>
      ))}
    </div>
  );
}

/** Rows shown at a time, so a phone is not handed hundreds of names. */
export const PAGE = 50;
