import { useState } from 'react';
import { ReportGenerateTab } from './ReportGenerateTab';
import { WeeklyNotesTab } from './WeeklyNotesTab';
import { TestimoniesTab } from './TestimoniesTab';

type Tab = 'generate' | 'notes' | 'testimonies';

export function ReportsPage() {
  const [tab, setTab] = useState<Tab>('generate');

  return (
    <>
      <div className="toolbar">
        <div className="tabs">
          <button className={`tab${tab === 'generate' ? ' active' : ''}`} onClick={() => setTab('generate')}>
            Generate Monthly Report
          </button>
          <button className={`tab${tab === 'notes' ? ' active' : ''}`} onClick={() => setTab('notes')}>
            Weekly Leadership Notes
          </button>
          <button className={`tab${tab === 'testimonies' ? ' active' : ''}`} onClick={() => setTab('testimonies')}>
            Testimonies
          </button>
        </div>
      </div>
      {tab === 'generate' && <ReportGenerateTab />}
      {tab === 'notes' && <WeeklyNotesTab />}
      {tab === 'testimonies' && <TestimoniesTab />}
    </>
  );
}
