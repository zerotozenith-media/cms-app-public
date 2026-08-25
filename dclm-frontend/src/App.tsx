import { Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { MembersListPage } from './pages/members/MembersListPage';
import { MemberFollowUpTab } from './pages/members/MemberFollowUpTab';
import { MemberProfilePage } from './pages/members/MemberProfilePage';
import { AddMemberPage } from './pages/members/AddMemberPage';
import { AttendanceListPage } from './pages/attendance/AttendanceListPage';
import { NewSessionPage } from './pages/attendance/NewSessionPage';
import { SessionRecordPage } from './pages/attendance/SessionRecordPage';
import { LiveCheckInPage } from './pages/attendance/LiveCheckInPage';
import { NewcomersListPage } from './pages/newcomers/NewcomersListPage';
import { EnquiriesPage } from './pages/enquiries/EnquiriesPage';
import { AddEnquiryPage } from './pages/enquiries/AddEnquiryPage';
import { EnquiryProfilePage } from './pages/enquiries/EnquiryProfilePage';
import { OutreachPage } from './pages/enquiries/OutreachPage';
import { NewcomerFollowUpTab } from './pages/newcomers/NewcomerFollowUpTab';
import { NewcomerProfilePage } from './pages/newcomers/NewcomerProfilePage';
import { ManualEntryPage } from './pages/newcomers/ManualEntryPage';
import { QrRegistrationPage } from './pages/newcomers/QrRegistrationPage';
import { FinancePage } from './pages/finance/FinancePage';
import { GoalsPage } from './pages/goals/GoalsPage';
import { ReportsPage } from './pages/reports/ReportsPage';
import { AdminPage } from './pages/admin/AdminPage';
import { PublicRegistrationPage } from './pages/PublicRegistrationPage';
import { HelpPage } from './pages/HelpPage';

function page(title: string, module: string | undefined, children: React.ReactNode) {
  return (
    <ProtectedRoute requiredModule={module}>
      <AppShell pageTitle={title}>{children}</AppShell>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<PublicRegistrationPage />} />
      <Route path="/" element={page('Dashboard', undefined, <DashboardPage />)} />

      <Route path="/attendance" element={page('Attendance', 'attendance', <AttendanceListPage />)} />
      <Route path="/attendance/new" element={page('Attendance', 'attendance', <NewSessionPage />)} />
      <Route path="/attendance/:id/check-in" element={page('Attendance', 'attendance', <LiveCheckInPage />)} />
      <Route path="/attendance/:id" element={page('Attendance', 'attendance', <SessionRecordPage />)} />

      <Route path="/members" element={page('Members', 'members', <MembersListPage />)} />
      <Route path="/members/new" element={page('Members', 'members', <AddMemberPage />)} />
      <Route path="/members/follow-up" element={page('Members', 'members', <MemberFollowUpTab />)} />
      <Route path="/members/:id" element={page('Members', 'members', <MemberProfilePage />)} />

      <Route path="/newcomers" element={page('Newcomers & Follow-up', 'newcomers', <NewcomersListPage />)} />
      <Route path="/newcomers/qr" element={page('Newcomers & Follow-up', 'newcomers', <QrRegistrationPage />)} />
      <Route path="/newcomers/manual" element={page('Newcomers & Follow-up', 'newcomers', <ManualEntryPage />)} />
      <Route path="/newcomers/follow-up" element={page('Newcomers & Follow-up', 'newcomers', <NewcomerFollowUpTab />)} />
      <Route path="/newcomers/:id" element={page('Newcomers & Follow-up', 'newcomers', <NewcomerProfilePage />)} />

      <Route path="/enquiries" element={page('Online Enquiries', 'newcomers', <EnquiriesPage />)} />
      <Route path="/enquiries/new" element={page('Online Enquiries', 'newcomers', <AddEnquiryPage />)} />
      <Route path="/enquiries/outreach" element={page('Outreach', 'outreach', <OutreachPage />)} />
      <Route path="/enquiries/:id" element={page('Online Enquiries', 'newcomers', <EnquiryProfilePage />)} />
      <Route path="/finance" element={page('Giving & Finance', 'finance', <FinancePage />)} />
      <Route path="/goals" element={page('Goals', 'goals', <GoalsPage />)} />
      <Route path="/reports" element={page('Reports', 'reports', <ReportsPage />)} />
      <Route path="/admin" element={page('Admin', 'admin', <AdminPage />)} />
      {/* No requiredModule: the guide is for everyone, whatever their role. */}
      <Route path="/help" element={page('Help & Guide', undefined, <HelpPage />)} />
    </Routes>
  );
}
