import type { ReactNode } from 'react';

type BadgeColor = 'blue' | 'green' | 'amber' | 'red' | 'gray';

interface BadgeProps {
  color: BadgeColor;
  children: ReactNode;
}

export function Badge({ color, children }: BadgeProps) {
  return <span className={`badge ${color}`}>{children}</span>;
}
