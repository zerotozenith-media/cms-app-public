import type { ReactNode, CSSProperties } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
  onClick?: () => void;
}

export function Card({ children, className = '', style, onClick }: CardProps) {
  const classes = ['card'];
  if (onClick) classes.push('card-link');
  if (className) classes.push(className);
  return (
    <div className={classes.join(' ')} style={style} onClick={onClick}>
      {children}
    </div>
  );
}
