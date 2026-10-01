/**
 * The six service ladder badges (F21): Sower, Reaper, Labourer, Soul Winner,
 * Faithful Steward, Good and Faithful Servant. Gold on a navy disc, each
 * icon centred on the disc, in the spirit of the hymn "Will there be any
 * stars in my crown" and Daniel 12:3.
 */
const GOLD = '#F5C451';

function star(x: number, y: number, s = 2.7) {
  const pts: string[] = [];
  for (let k = 0; k < 10; k++) {
    const r = k % 2 === 0 ? s : s * 0.45;
    const a = -Math.PI / 2 + (k * Math.PI) / 5;
    pts.push(`${(x + r * Math.cos(a)).toFixed(2)},${(y + r * Math.sin(a)).toFixed(2)}`);
  }
  return <polygon key={`${x}-${y}`} points={pts.join(' ')} fill={GOLD} />;
}

const crownBody = (
  <>
    <path d="M4 18 L5.2 10 L9.2 13 L12 8 L14.8 13 L18.8 10 L20 18 Z" fill={GOLD} />
    <rect x="4" y="18.7" width="16" height="2" rx="1" fill={GOLD} />
  </>
);

function Icon({ level }: { level: number }) {
  if (level === 0) {
    return (
      <g transform="translate(0,-0.5)">
        <path d="M12 21 V12" stroke={GOLD} strokeWidth="2" strokeLinecap="round" />
        <path d="M12 13.5 C7.2 13.5 5 10.5 5 6.5 C9.2 6.5 12 9 12 13.5Z" fill={GOLD} />
        <path d="M12 11.5 C12 7.5 14.6 4.5 19 4.5 C19 8.5 16.4 11.5 12 11.5Z" fill={GOLD} />
      </g>
    );
  }
  if (level === 1) {
    const grains: [number, number, number][] = [[12, 4.6, 0], [12, 8.6, 0], [7.4, 6.8, -18], [8.2, 10.4, -18], [16.6, 6.8, 18], [15.8, 10.4, 18]];
    return (
      <g>
        {[[12, 12], [11, 7.5], [13, 16.5]].map(([a, b]) => <path key={a} d={`M${a} 21 L${b} 7.5`} stroke={GOLD} strokeWidth="1.7" strokeLinecap="round" />)}
        {grains.map(([x, y, r]) => <ellipse key={`${x}${y}`} cx={x} cy={y} rx="1.7" ry="2.7" fill={GOLD} transform={`rotate(${r} ${x} ${y})`} />)}
        <rect x="8.6" y="14.3" width="6.8" height="2" rx="1" fill="#0B1F44" />
      </g>
    );
  }
  const stars = level - 2;
  if (stars === 0) return <g transform="translate(0,-2.3)">{crownBody}</g>;
  const pos: Record<number, [number, number][]> = { 1: [[12, 4.3]], 2: [[9, 4.6], [15, 4.6]], 3: [[6.6, 5.1], [12, 3.9], [17.4, 5.1]] };
  return (
    <g transform="translate(0,0.6)">
      <g transform="translate(12,13.2) scale(0.86) translate(-12,-14.3)">{crownBody}</g>
      {pos[stars].map(([x, y]) => star(x, y))}
    </g>
  );
}

export const LEVEL_NAMES = ['Sower', 'Reaper', 'Labourer', 'Soul Winner', 'Faithful Steward', 'Good and Faithful Servant'];

export function LevelBadge({ level, size = 24, dim = false, title }: { level: number; size?: number; dim?: boolean; title?: string }) {
  const name = LEVEL_NAMES[level] ?? '';
  return (
    <span className="level-badge" role="img" aria-label={title ?? name} title={title ?? name}
      style={{ width: size, height: size, padding: Math.max(3, Math.round(size * 0.17)), opacity: dim ? 0.3 : 1 }}>
      <svg viewBox="0 0 24 24" width="100%" height="100%" aria-hidden="true"><Icon level={level} /></svg>
    </span>
  );
}
