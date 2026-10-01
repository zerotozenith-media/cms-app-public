/**
 * Keyboard and screen-reader access for clickable links without an address
 * (found in the manual check). Around 25 controls, such as Add member, Add
 * household, the dashboard's "Go to" links and every Back link, are links
 * with a click handler but no href, so Tab skipped them and screen readers
 * did not announce them as buttons. This makes every such control, now and
 * in future, focusable, announced as a button, and pressed by Enter or Space.
 */
export function enableKeyboardLinks() {
  const fix = () => {
    document.querySelectorAll<HTMLAnchorElement>('a:not([href]):not([tabindex])').forEach((a) => {
      a.setAttribute('tabindex', '0');
      if (!a.getAttribute('role')) a.setAttribute('role', 'button');
    });
  };
  fix();
  new MutationObserver(fix).observe(document.body, { childList: true, subtree: true });
  document.addEventListener('keydown', (e) => {
    const t = e.target as HTMLElement | null;
    if (t && t.tagName === 'A' && !t.hasAttribute('href') && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      t.click();
    }
  });
}
