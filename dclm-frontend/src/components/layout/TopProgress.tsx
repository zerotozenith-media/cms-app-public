import { useEffect, useState } from 'react';
import { useIsFetching } from '@tanstack/react-query';

/**
 * A thin bar across the top while data is on its way (F11), instead of a
 * page emptying to "Loading". Shown only after a moment, so quick loads do
 * not flicker.
 */
export function TopProgress() {
  const busy = useIsFetching() > 0;
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (!busy) { setShow(false); return; }
    const t = setTimeout(() => setShow(true), 250);
    return () => clearTimeout(t);
  }, [busy]);
  return <div className={`top-progress${show ? ' on' : ''}`} role="progressbar" aria-hidden={!show} aria-label="Loading" />;
}
