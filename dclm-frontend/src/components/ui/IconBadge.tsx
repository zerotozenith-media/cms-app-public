import { Icon, type IconName } from './Icon';

type IconBadgeColor = 'blue' | 'red' | 'amber' | 'green' | 'gray';

interface IconBadgeProps {
  icon: IconName;
  color: IconBadgeColor;
  size?: 'default' | 'sm';
  iconSize?: number;
}

export function IconBadge({ icon, color, size = 'default', iconSize }: IconBadgeProps) {
  const classes = ['ic-badge', color];
  if (size === 'sm') classes.push('sm');
  return (
    <span className={classes.join(' ')}>
      <Icon name={icon} size={iconSize ?? (size === 'sm' ? 17 : 20)} />
    </span>
  );
}
