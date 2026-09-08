import type { JourneyEvent } from '../../api/newcomers';

const DOT: Record<string, string> = {
  registered: 'blue',
  stage: 'green',
  contact: 'plain',
  attempt: 'attempt',
  milestone: 'green',
  member: 'amber',
};

/**
 * One person's history in order.
 *
 * Includes contacts that did not reach them. Without those the record
 * flatters the work: three unanswered calls would look like nobody
 * tried at all.
 */
export function JourneyTimeline({ events }: { events: JourneyEvent[] }) {
  if (!events.length) return <div className="empty">Nothing recorded yet.</div>;

  return (
    <div className="jt">
      {events.map((e, i) => (
        <div className="jt-item" key={`${e.date}-${i}`}>
          <span className={`jt-dot ${DOT[e.kind] ?? 'plain'}`} />
          <div className="jt-title">
            {e.title}
            <span className="jt-meta">
              {' · '}{[e.date, e.by, e.method].filter(Boolean).join(' · ')}
            </span>
          </div>
          {e.detail && <div className="jt-detail">{e.detail}</div>}
          {e.log && (
            <div className="jt-log">
              <div><span>Goal</span>{e.log.goal}</div>
              <div><span>Scripture</span>{e.log.scripture}</div>
              <div><span>Root cause</span>{e.log.root_cause}</div>
              <div><span>Next step</span>{e.log.next_step}</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
