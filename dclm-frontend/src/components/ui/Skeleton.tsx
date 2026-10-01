import { useEffect, useState } from 'react';

/**
 * Page-shaped placeholders while data is on its way (F11), instead of a
 * plain "Loading". Drawn only after a moment, so a quick load never
 * flickers, and shaped like the page about to appear.
 */
function useDelay(ms = 250) {
  const [ready, setReady] = useState(false);
  useEffect(() => { const t = setTimeout(() => setReady(true), ms); return () => clearTimeout(t); }, [ms]);
  return ready;
}

const Bar = ({ w, h = 12 }: { w: string; h?: number }) => <span className="sk" style={{ width: w, height: h }} />;

function Rows({ n = 5 }: { n?: number }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <div className="sk-row" key={i}>
          <span className="sk sk-circle" />
          <div className="sk-lines"><Bar w={`${55 - (i % 3) * 8}%`} /><Bar w={`${35 - (i % 2) * 6}%`} h={9} /></div>
        </div>
      ))}
    </>
  );
}

export function Skeleton({ shape }: { shape: 'profile' | 'list' | 'dashboard' | 'form' }) {
  const ready = useDelay();
  if (!ready) return null;
  if (shape === 'list') return <div className="sk-wrap" aria-busy="true" aria-label="Loading"><Rows /></div>;
  if (shape === 'profile') {
    return (
      <div className="person-grid sk-wrap" aria-busy="true" aria-label="Loading">
        <div className="card"><span className="sk sk-circle big" /><Bar w="70%" h={18} /><Bar w="50%" /><Rows n={4} /></div>
        <div className="card"><Bar w="60%" h={16} /><Rows n={6} /></div>
      </div>
    );
  }
  if (shape === 'dashboard') {
    return (
      <div className="sk-wrap" aria-busy="true" aria-label="Loading">
        <Bar w="30%" h={12} /><Bar w="45%" h={24} />
        <div className="sk-grid2"><div className="card"><Rows n={3} /></div><div className="card"><Rows n={3} /></div></div>
        <div className="sk-grid4">{[0, 1, 2, 3].map((i) => <div className="card" key={i}><Bar w="60%" /><Bar w="40%" h={22} /></div>)}</div>
      </div>
    );
  }
  return (
    <div className="card sk-wrap" aria-busy="true" aria-label="Loading">
      <Bar w="40%" h={18} />
      {[0, 1, 2, 3].map((i) => <div key={i} style={{ marginTop: 14 }}><Bar w="25%" h={9} /><Bar w="100%" h={38} /></div>)}
    </div>
  );
}
