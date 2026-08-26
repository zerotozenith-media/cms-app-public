import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'outline' | 'red' | 'ghost';
  size?: 'default' | 'sm';
  children: ReactNode;
}

export function Button({ variant = 'primary', size = 'default', className = '', children, ...rest }: ButtonProps) {
  const classes = ['btn'];
  if (variant === 'outline') classes.push('outline');
  if (variant === 'red') classes.push('red');
  if (variant === 'ghost') classes.push('ghost');
  if (size === 'sm') classes.push('sm');
  if (className) classes.push(className);
  return (
    <button className={classes.join(' ')} {...rest}>
      {children}
    </button>
  );
}
