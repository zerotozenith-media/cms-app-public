/** Ported from the demo's fmt() , BHD amounts throughout. */
export function fmt(n: number): string {
  return `BHD ${n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}
