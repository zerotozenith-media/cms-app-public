/** Male, Female, or Gender not known. The not-known tag stays until
 *  someone sets the gender, so it is never forgotten after assignment. */
export function GenderTag({ gender, long }: { gender?: string | null; long?: boolean }) {
  if (gender === 'Male') return <span className="gender-tag g-male">Male</span>;
  if (gender === 'Female') return <span className="gender-tag g-female">Female</span>;
  return <span className="gender-tag g-unknown">{long ? 'Gender not known' : 'Not known'}</span>;
}
