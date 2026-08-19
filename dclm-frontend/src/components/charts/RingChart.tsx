interface RingChartProps {
  pct: number;
  size?: number;
  stroke?: number;
  color?: string;
  track?: string;
  valueFontSize?: string;
}

/** Ported exactly from the demo's ringSVG() function. */
export function RingChart({ pct, size = 64, stroke = 7, color = 'var(--blue)', track = 'var(--sky)', valueFontSize }: RingChartProps) {
  const clamped = Math.min(100, Math.max(0, pct));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - clamped / 100);
  return (
    <span className="ring-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="ring-val" style={valueFontSize ? { fontSize: valueFontSize } : undefined}>
        {clamped}%
      </span>
    </span>
  );
}
