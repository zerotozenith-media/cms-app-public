import type { ReactNode } from 'react';
import { IconBadge } from './IconBadge';
import type { IconName } from './Icon';

export interface StatItem {
  icon: IconName;
  color: 'blue' | 'red' | 'amber' | 'green' | 'gray';
  label: string;
  value: ReactNode;
  onClick?: () => void;
  hint?: string;
  valueColor?: string;
  topRight?: ReactNode; // e.g. a RingChart or a trend-chip , the demo's dashboard stat-row pattern
}

interface StatRowProps {
  stats: StatItem[];
  columns?: 3 | 4;
}

/**
 * The combined stat-row card pattern established across the demo , one
 * card, divider-separated columns, icon per stat, 2×2 on mobile (CSS
 * handles the breakpoint, ported as-is in design-system.css).
 */
export function StatRow({ stats, columns = 4 }: StatRowProps) {
  return (
    <div className="statcard" style={{ marginBottom: 20 }}>
      <div className={`statrow${columns === 3 ? ' c3' : ''}`}>
        {stats.map((s, i) => (
          <div
            key={i}
            className={s.onClick ? 'stat stat-link' : 'stat'}
            onClick={s.onClick}
          >
            {s.topRight ? (
              <div className="stat-top-row">
                <IconBadge icon={s.icon} color={s.color} size="sm" />
                {s.topRight}
              </div>
            ) : (
              <IconBadge icon={s.icon} color={s.color} size="sm" />
            )}
            <div className="label">{s.label}</div>
            <div className="value" style={s.valueColor ? { color: s.valueColor } : undefined}>
              {s.value}
            </div>
            {s.hint && <span className="card-link-hint">{s.hint}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
