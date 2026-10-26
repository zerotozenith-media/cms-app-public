import { useState } from 'react';
import { useAdminUsers, useAdminLocations } from '../../api/admin';
import { useMeetingTypes } from '../../api/attendance';
import { useHouseholds } from '../../api/members';
import { StatRow, type StatItem } from '../../components/ui/StatRow';
import { UsersRolesTab } from './UsersRolesTab';
import { MeetingTypesHouseholdsTab } from './MeetingTypesHouseholdsTab';
import { ConfigListsTab } from './ConfigListsTab';
import { AuditLogTab } from './AuditLogTab';
import { MessageBankTab } from './MessageBankTab';
import { AlertsTab } from './AlertsTab';
import { FollowUpRulesTab } from './FollowUpRulesTab';

type Tab = 'users' | 'meetings' | 'rules' | 'config' | 'bank' | 'audit' | 'alerts';

export function AdminPage() {
  const [tab, setTab] = useState<Tab>('users');
  const { data: users } = useAdminUsers();
  const { data: meetingTypes } = useMeetingTypes();
  const { data: households } = useHouseholds();
  const { data: locations } = useAdminLocations();

  const stats: StatItem[] = [
    { icon: 'users', color: 'blue', label: 'Users', value: users?.length ?? 0 },
    { icon: 'check', color: 'blue', label: 'Meeting types', value: meetingTypes?.length ?? 0 },
    { icon: 'user', color: 'amber', label: 'Households', value: households?.length ?? 0 },
    { icon: 'gear', color: 'gray', label: 'Locations', value: locations?.length ?? 0 },
  ];

  return (
    <>
      <StatRow stats={stats} loading={!users || !meetingTypes || !households || !locations} />
      <div className="toolbar">
        <div className="tabs">
          <button className={`tab${tab === 'users' ? ' active' : ''}`} onClick={() => setTab('users')}>Users &amp; Roles</button>
          <button className={`tab${tab === 'meetings' ? ' active' : ''}`} onClick={() => setTab('meetings')}>Meeting Types &amp; Households</button>
          <button className={`tab${tab === 'rules' ? ' active' : ''}`} onClick={() => setTab('rules')}>Follow-up Rules</button>
          <button className={`tab${tab === 'config' ? ' active' : ''}`} onClick={() => setTab('config')}>Config Lists</button>
          <button className={`tab${tab === 'bank' ? ' active' : ''}`} onClick={() => setTab('bank')}>Message Bank</button>
          <button className={`tab${tab === 'audit' ? ' active' : ''}`} onClick={() => setTab('audit')}>Audit Log</button>
          <button className={`tab${tab === 'alerts' ? ' active' : ''}`} onClick={() => setTab('alerts')}>Alerts</button>
        </div>
      </div>
      {tab === 'users' && <UsersRolesTab />}
      {tab === 'meetings' && <MeetingTypesHouseholdsTab />}
      {tab === 'rules' && <FollowUpRulesTab />}
      {tab === 'config' && <ConfigListsTab />}
      {tab === 'bank' && <MessageBankTab />}
      {tab === 'audit' && <AuditLogTab />}
      {tab === 'alerts' && <AlertsTab />}
    </>
  );
}
