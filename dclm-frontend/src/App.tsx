import { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { lazyPage } from './lib/lazyPage';
import { AppShell } from './components/layout/AppShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { TeamListPage } from './components/service/ServiceBadge';
import { PageLoadBoundary } from './components/ui/PageLoadBoundary';


// Opened only when needed, so signing in downloads less (Kay, 27 October 2026).
const FollowUpMessagesPage = lazyPage(() => import('./pages/newcomers/FollowUpMessagesPage'), 'FollowUpMessagesPage');
const ForgotPasswordPage = lazyPage(() => import('./pages/ForgotPasswordPage'), 'ForgotPasswordPage');
const ResetPasswordPage = lazyPage(() => import('./pages/ResetPasswordPage'), 'ResetPasswordPage');
const MyProfilePage = lazyPage(() => import('./pages/MyProfilePage'), 'MyProfilePage');
const MembersListPage = lazyPage(() => import('./pages/members/MembersListPage'), 'MembersListPage');
const MemberFollowUpTab = lazyPage(() => import('./pages/members/MemberFollowUpTab'), 'MemberFollowUpTab');
const MemberProfilePage = lazyPage(() => import('./pages/members/MemberProfilePage'), 'MemberProfilePage');
const AddMemberPage = lazyPage(() => import('./pages/members/AddMemberPage'), 'AddMemberPage');
const AttendanceListPage = lazyPage(() => import('./pages/attendance/AttendanceListPage'), 'AttendanceListPage');
const NewSessionPage = lazyPage(() => import('./pages/attendance/NewSessionPage'), 'NewSessionPage');
const SessionRecordPage = lazyPage(() => import('./pages/attendance/SessionRecordPage'), 'SessionRecordPage');
const LiveCheckInPage = lazyPage(() => import('./pages/attendance/LiveCheckInPage'), 'LiveCheckInPage');
const NewcomersListPage = lazyPage(() => import('./pages/newcomers/NewcomersListPage'), 'NewcomersListPage');
const EnquiriesPage = lazyPage(() => import('./pages/enquiries/EnquiriesPage'), 'EnquiriesPage');
const AddEnquiryPage = lazyPage(() => import('./pages/enquiries/AddEnquiryPage'), 'AddEnquiryPage');
const EnquiryProfilePage = lazyPage(() => import('./pages/enquiries/EnquiryProfilePage'), 'EnquiryProfilePage');
const OutreachPage = lazyPage(() => import('./pages/enquiries/OutreachPage'), 'OutreachPage');
const NewcomerFollowUpTab = lazyPage(() => import('./pages/newcomers/NewcomerFollowUpTab'), 'NewcomerFollowUpTab');
const NewcomerProfilePage = lazyPage(() => import('./pages/newcomers/NewcomerProfilePage'), 'NewcomerProfilePage');
const ManualEntryPage = lazyPage(() => import('./pages/newcomers/ManualEntryPage'), 'ManualEntryPage');
const QrRegistrationPage = lazyPage(() => import('./pages/newcomers/QrRegistrationPage'), 'QrRegistrationPage');
const FinancePage = lazyPage(() => import('./pages/finance/FinancePage'), 'FinancePage');
const GoalsPage = lazyPage(() => import('./pages/goals/GoalsPage'), 'GoalsPage');
const ReportsPage = lazyPage(() => import('./pages/reports/ReportsPage'), 'ReportsPage');
const AdminPage = lazyPage(() => import('./pages/admin/AdminPage'), 'AdminPage');
const PublicRegistrationPage = lazyPage(() => import('./pages/PublicRegistrationPage'), 'PublicRegistrationPage');
const HelpPage = lazyPage(() => import('./pages/HelpPage'), 'HelpPage');
const MyFollowUpPage = lazyPage(() => import('./pages/followup/MyFollowUpPage'), 'MyFollowUpPage');
const FollowUpReviewPage = lazyPage(() => import('./pages/followup/FollowUpReviewPage'), 'FollowUpReviewPage');

const LOADING = <div className="empty" role="status">Loading…</div>;

function page(title: string, module: string | undefined, children: React.ReactNode) {
  return (
    <ProtectedRoute requiredModule={module}>
      <AppShell pageTitle={title}><PageLoadBoundary><Suspense fallback={LOADING}>{children}</Suspense></PageLoadBoundary></AppShell>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <PageLoadBoundary>
    <Suspense fallback={LOADING}>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/register" element={<PublicRegistrationPage />} />
      <Route path="/" element={page('Dashboard', undefined, <DashboardPage />)} />
      <Route path="/profile" element={page('My profile', undefined, <MyProfilePage />)} />
      <Route path="/profile/team" element={page('My profile', undefined, <TeamListPage />)} />

      <Route path="/attendance" element={page('Attendance', 'attendance', <AttendanceListPage />)} />
      <Route path="/attendance/new" element={page('Attendance', 'attendance', <NewSessionPage />)} />
      <Route path="/attendance/:id/check-in" element={page('Attendance', 'attendance', <LiveCheckInPage />)} />
      <Route path="/attendance/:id" element={page('Attendance', 'attendance', <SessionRecordPage />)} />

      <Route path="/follow-up" element={page('My follow-up', undefined, <MyFollowUpPage />)} />
      <Route path="/followup-review" element={page('Follow-up Review', undefined, <FollowUpReviewPage />)} />
      <Route path="/members" element={page('Members', 'members', <MembersListPage />)} />
      <Route path="/members/new" element={page('Members', 'members', <AddMemberPage />)} />
      <Route path="/members/follow-up" element={page('Members', 'members', <MemberFollowUpTab />)} />
      <Route path="/members/:id" element={page('Members', 'members', <MemberProfilePage />)} />

      <Route path="/newcomers" element={page('Newcomers & Follow-up', 'newcomers', <NewcomersListPage />)} />
      <Route path="/newcomers/qr" element={page('Newcomers & Follow-up', 'newcomers', <QrRegistrationPage />)} />
      <Route path="/newcomers/manual" element={page('Newcomers & Follow-up', 'newcomers', <ManualEntryPage />)} />
      <Route path="/newcomers/messages" element={page('Newcomers & Follow-up', 'newcomers', <FollowUpMessagesPage />)} />
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
    </Suspense>
    </PageLoadBoundary>
  );
}
