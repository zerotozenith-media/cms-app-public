interface CompletedLog {
  contact_date: string | null;
  contact_method: string;
  contact_goal: string;
  contact_scripture: string;
  contact_root_cause: string;
  contact_next_step: string;
  /** Records created before the four structured fields existed. */
  contact_notes?: string;
}

function Row({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="completed-log-notes">
      <span className="completed-log-label">{label}</span>
      {value}
    </div>
  );
}

/**
 * Each field on its own labelled row rather than one run-together
 * sentence, so a leader can scan several completed records quickly.
 * Older records only have contact_notes; those still display.
 */
export function CompletedFollowUpLog({ log }: { log: CompletedLog }) {
  return (
    <div className="completed-log">
      <div>
        <span className="completed-log-label">Method</span>
        {log.contact_method || 'Not recorded'}
      </div>
      <Row label="Date" value={log.contact_date} />
      <Row label="Goal of the visit" value={log.contact_goal} />
      <Row label="Scripture shared" value={log.contact_scripture} />
      <Row label="Root cause" value={log.contact_root_cause} />
      <Row label="Next step agreed" value={log.contact_next_step} />
      <Row label="Notes" value={log.contact_notes ?? null} />
    </div>
  );
}
