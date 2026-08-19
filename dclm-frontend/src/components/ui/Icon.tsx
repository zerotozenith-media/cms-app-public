/**
 * Ported directly from the approved demo's ICONS object (cms-demo-v2.html),
 * extracted from the file rather than reconstructed from memory, so every
 * path is exactly what was already reviewed and approved.
 */
const ICON_PATHS: Record<string, string> = {
  grid: '<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
  check: '<path d="M4 11l5 5L20 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="1.4"/>',
  users: '<circle cx="9" cy="8" r="3" stroke="currentColor" stroke-width="1.6"/><path d="M3 20a6 6 0 0112 0M15 9a3 3 0 110-6M14 14a6 6 0 016 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
  user: '<circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.6"/><path d="M4 20a8 8 0 0116 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
  userplus: '<circle cx="9" cy="8" r="3" stroke="currentColor" stroke-width="1.6"/><path d="M3 20a6 6 0 0112 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M18 8v6M15 11h6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  coin: '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M12 7v10M9 9.5c0-1.5 1.3-2.5 3-2.5s3 1 3 2.2c0 3-6 1.3-6 4.3 0 1.4 1.3 2.5 3 2.5s3-1 3-2.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
  target: '<circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
  doc: '<path d="M6 3h9l3 3v15H6z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M15 3v3h3M9 12h6M9 15.5h6M9 8.5h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>',
  gear: '<circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.6"/><path d="M12 3v2M12 19v2M4.2 7.5l1.7 1M18 15.5l1.8 1M3 12h2M19 12h2M4.2 16.5l1.7-1M18 8.5l1.8-1M7.5 4.2l1 1.7M15.5 18l1 1.7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
  plus: '<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>',
  edit: '<path d="M4 20h4L18 10l-4-4L4 16v4z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>',
  alert: '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M12 7v6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="16" r="1" fill="currentColor"/>',
};

export type IconName = keyof typeof ICON_PATHS;

interface IconProps {
  name: IconName;
  size?: number;
}

export function Icon({ name, size = 18 }: IconProps) {
  const path = ICON_PATHS[name];
  if (!path) return null;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      dangerouslySetInnerHTML={{ __html: path }}
    />
  );
}
