/**
 * Help for this page: the ? in the top bar, matched on the start of the
 * address. Kept apart from content.ts so every page does not have to load
 * the whole of Help just to show the top bar.
 */
export interface PageHelp { title: string; steps: string[]; links: { t: string; s: string; h?: string }[]; manual?: number }

export const HELP_PAGES: { path: RegExp; help: PageHelp }[] = [
  { path: /^\/follow-up/, help: { title: 'My follow-up', manual: 61, steps: [
    'If a red box says late tasks need a reason, press Give reasons first.',
    'Visit or call, then press Record result.',
    'Press Mark away for someone travelling or sick.',
  ], links: [{ t: "Why can't I record a result?", s: 'why', h: "Why can't I record a result?" }, { t: 'What Priority means', s: 'shepherd', h: 'Your list: My follow-up' }, { t: 'When is a task due?', s: 'shepherd', h: 'When is a task due?' }] } },
  { path: /^\/followup-review/, help: { title: 'Follow-up Review', manual: 64, steps: [
    'On the Review list, read the reason and choose Accept, Hand to another shepherd, Take it myself or Ask the shepherd.',
    'Press Confirm. The shepherd is told.',
    'Overview shows the measures and each shepherd\'s people.',
  ], links: [{ t: 'The four choices', s: 'coordinator', h: 'The four choices' }, { t: 'Why is a shepherd not offered?', s: 'why', h: 'Why is the shepherd I want not offered to hand on to?' }, { t: 'The Overview', s: 'coordinator', h: 'The Overview' }] } },
  { path: /^\/attendance\/\d+\/check-in/, help: { title: 'Ticking names', manual: 22, steps: [
    'Tap each name as the person arrives. Tap again to undo.',
    'Press Newcomers, Members or Not ticked to narrow the list.',
    'Tick newcomers too. Anyone not ticked gets a follow-up task.',
  ], links: [{ t: 'Why is a newcomer not on the list?', s: 'why', h: 'Why is a newcomer not on the check-in list?' }, { t: 'Ticking names after the service', s: 'usher', h: 'Ticking names after the service' }, { t: "Why can't I check people in?", s: 'why', h: "Why can't I check people in?" }] } },
  { path: /^\/attendance\/new/, help: { title: 'New session', manual: 23, steps: [
    'Use this only for one-off meetings. Weekly sessions are made for you.',
    'Choose the meeting, date and location, then press Create.',
  ], links: [{ t: "Why can't I add this session?", s: 'why', h: "Why can't I add this session?" }] } },
  { path: /^\/attendance\/\d+/, help: { title: 'Recording a service', manual: 21, steps: [
    'Type the headcount for each group, and new comers and converts.',
    'Type the offering for each fund.',
    'Press Save session.',
    'To tick names here, tick Track named attendance. Newcomers are listed too.',
  ], links: [{ t: 'Why is Save session greyed out?', s: 'why', h: 'Why is Save session greyed out?' }, { t: 'Ticking names on the session page', s: 'usher', h: 'Ticking names on the session page' }, { t: 'Recording the headcount and offering', s: 'usher', h: 'Recording the headcount and offering' }] } },
  { path: /^\/attendance/, help: { title: 'Attendance', manual: 21, steps: [
    "Press Check in on today's row to tick names as people arrive.",
    "Press the row to record the headcount and offering.",
    'Press Did not hold for a service that did not take place.',
  ], links: [{ t: 'What the Status words mean', s: 'usher', h: 'What the Status words mean' }, { t: "Why can't I mark it Did not hold?", s: 'why', h: "Why can't I mark it Did not hold?" }] } },
  { path: /^\/members\/follow-up/, help: { title: 'Members, Follow-up', manual: 19, steps: [
    'Every member task, for anyone overseeing. Shepherds use My follow-up.',
    'Press Mark done to record a visit.',
  ], links: [{ t: 'My follow-up', s: 'shepherd', h: 'Your list: My follow-up' }] } },
  { path: /^\/members\/new/, help: { title: 'Adding a member', manual: 15, steps: ['Fill in the form and press Add member.', 'Link them to a household if they live with other members.'], links: [{ t: 'Why is this phone number refused?', s: 'why', h: 'Why is this phone number refused?' }] } },
  { path: /^\/members\/\d+/, help: { title: "A member's profile", manual: 16, steps: [
    'Shepherd, Status, Away and Leader are on the left.',
    'The Tasks tab shows every task and its record.',
    'Use the pencil to edit details.',
  ], links: [{ t: 'A member has moved away or left', s: 'situations', h: 'A member has moved away or left the church' }, { t: 'Why is the shepherd I want not offered?', s: 'why', h: 'Why is the shepherd I want not offered?' }] } },
  { path: /^\/members/, help: { title: 'Members', manual: 14, steps: [
    'Search or filter the list. Status shows those who moved away or left.',
    'Tick rows and choose a shepherd to assign several.',
    'Press Auto-assign to give everyone a shepherd.',
  ], links: [{ t: 'How auto-assign decides', s: 'members', h: 'How auto-assign decides' }, { t: 'Why is my shepherd choice refused?', s: 'why', h: 'Why is my shepherd choice refused?' }] } },
  { path: /^\/newcomers\/qr/, help: { title: 'QR Registration', manual: 25, steps: ['Choose the location in Code for.', 'Show or project the code. Newcomers scan it and fill in the form.'], links: [{ t: 'Why was the QR form refused?', s: 'why', h: 'Why was the QR form refused?' }] } },
  { path: /^\/newcomers\/manual/, help: { title: 'Manual Entry', manual: 26, steps: ['Type in the paper card, field by field.', 'Tick the boxes as they ticked them, then press Add newcomer.'], links: [{ t: 'The first visit', s: 'welcome', h: 'The first visit' }] } },
  { path: /^\/newcomers\/messages/, help: { title: "Today's messages", manual: 33, steps: [
    'Press Send on WhatsApp, send it, then press Yes, record it.',
    'Missed lists messages from the last 14 days not sent.',
    'Start messages starts people on a journey.',
  ], links: [{ t: 'Messages you missed', s: 'messages', h: 'Messages you missed' }, { t: "Why can't I start messages for this newcomer?", s: 'why', h: "Why can't I start messages for this newcomer?" }] } },
  { path: /^\/newcomers\/follow-up/, help: { title: 'Newcomers, Follow-up', manual: 31, steps: ['Every newcomer task, for anyone overseeing. Shepherds use My follow-up.'], links: [{ t: 'My follow-up', s: 'shepherd', h: 'Your list: My follow-up' }] } },
  { path: /^\/newcomers\/\d+/, help: { title: "A newcomer's profile", manual: 30, steps: [
    'Choose their Shepherd, and set Away dates, on the left.',
    'Tick Salvation and other milestones on the Journey tab.',
    'The Tasks tab shows every task and its record.',
    'Mark as Not Interested needs a note and stops follow-up.',
  ], links: [{ t: 'Recording Salvation', s: 'welcome', h: 'Recording Salvation' }, { t: 'Why must I say why for Not Interested?', s: 'why', h: 'Why must I say why for Not Interested?' }] } },
  { path: /^\/newcomers/, help: { title: 'Newcomers', manual: 27, steps: [
    'Search by name, phone or email above the filters.',
    'Drag a card, or use its dropdown, to move someone along.',
    'In Table, tick several and press Assign to give them a shepherd.',
  ], links: [{ t: 'Giving several newcomers a shepherd', s: 'welcome', h: 'Giving several newcomers a shepherd' }, { t: 'Why is this shepherd refused?', s: 'why', h: 'Why is this shepherd refused for these newcomers?' }] } },
  { path: /^\/enquiries/, help: { title: 'Online enquiries', manual: 39, steps: ['Find a contact by name, phone, email or handle.', 'Press the pencil on a contact to correct their details.', 'Give each contact a follow-up person, and add them as a newcomer when they come.'], links: [{ t: 'Finding and correcting a contact', s: 'enquiries', h: 'Finding and correcting a contact' }, { t: 'Online enquiries', s: 'enquiries' }] } },
  { path: /^\/finance/, help: { title: 'Giving & Finance', manual: 42, steps: ['Record giving and expenses on the day, in the forms.', 'The Remittance tab records each month\'s remittance.', 'The Month-end balance tab balances, approves and closes each month.'], links: [{ t: 'Balancing the month', s: 'giving', h: 'Balancing the month' }, { t: "Why can't I add, change or delete this?", s: 'why', h: "Why can't I add, change or delete this giving or expense?" }, { t: "Why can't I change this giving entry?", s: 'why', h: "Why can't I change this giving entry?" }] } },
  { path: /^\/goals/, help: { title: 'Goals', manual: 46, steps: ['Type the figure for goals typed by hand.', 'Add goal, Automatically, makes a goal that updates itself.'], links: [{ t: 'Two kinds of goals', s: 'goals', h: 'Two kinds of goals' }, { t: 'Why is a goal refused?', s: 'why', h: 'Why is a goal refused?' }] } },
  { path: /^\/reports/, help: { title: 'Reports', manual: 48, steps: ['Choose the report and months, then press Generate.'], links: [{ t: 'Why is the report refused?', s: 'why', h: 'Why is the report refused?' }] } },
  { path: /^\/admin/, help: { title: 'Admin', manual: 51, steps: [
    'Users & Roles: Edit an account, its role, shepherd and Follow-up Coordinator ticks.',
    'Meeting Types: Settings sets start times and when sessions are made.',
    'Follow-up Rules: every follow-up time and number.',
  ], links: [{ t: 'Follow-up Rules', s: 'runchurch', h: 'Follow-up Rules' }, { t: 'Editing an account', s: 'runchurch', h: 'Editing an account' }, { t: "Why can't I give this role?", s: 'why', h: "Why can't I give this role?" }] } },
  { path: /^\/profile/, help: { title: 'My profile', manual: 7, steps: ['Correct your details, add a photo or change your password.', 'Turn on alerts for this device.'], links: [{ t: 'Turning on alerts', s: 'alerts', h: 'Turning on alerts' }] } },
  { path: /^\/help/, help: { title: 'Help & Guide', steps: ['Pick your job on the left, or search for a word from what you are doing.'], links: [{ t: "Why can't I...?", s: 'why' }] } },
  { path: /^\/$/, help: { title: 'Dashboard', manual: 12, steps: ['The cards show this month at a glance. Tap one to open its page.', 'The bell lists what needs your attention.'], links: [{ t: 'The bell', s: 'start', h: 'The bell' }] } },
];

export function helpForPath(pathname: string): PageHelp | null {
  return HELP_PAGES.find((p) => p.path.test(pathname))?.help ?? null;
}

export function slug(h: string) {
  return h.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60);
}
