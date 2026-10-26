/**
 * Help & Guide (rewritten for version 11.14, Kay, 26 October 2026).
 *
 * Written by job, so a new usher reads "what you do on Friday" rather than
 * a description of a screen. Each guide is short, with numbered steps, and
 * links to the manual page that has the full detail, so the long text lives
 * in one place only. "Why can't I...?" answers every message where the app
 * says no, in the app's own words, so nobody has to ask.
 */
export type HelpRole = 'Everyone' | 'Usher' | 'Shepherd' | 'Follow-up Coordinator' | 'Administrator' | 'Location Coordinator' | 'Finance' | 'Welcome team';

export interface HelpEntry {
  h: string;
  p?: string;
  steps?: string[];
  note?: string;
  links?: { to: string; t: string }[];
  /** Who it is for. */
  roles?: HelpRole[];
  /** Printed page number in the user manual. */
  manual?: number;
  /** A Help picture name, served to signed-in people only. */
  img?: string;
  /** For Why can't I: the words the app shows, and what to do. */
  say?: string;
  why?: string;
  fix?: string;
}

export interface HelpSection {
  key: string;
  label: string;
  group: 'My job' | 'When something goes wrong' | 'Reference' | "What's new";
  intro?: string;
}

export const HELP_SECTIONS: HelpSection[] = [
  { key: 'start', label: 'Start here', group: 'My job', intro: 'For everyone. How the system works around you, and where to find things.' },
  { key: 'usher', label: 'I record attendance', group: 'My job', intro: 'For ushers and anyone filling in a service.' },
  { key: 'shepherd', label: 'I follow up people', group: 'My job', intro: 'For shepherds. Everything you need, in the order you meet it.' },
  { key: 'coordinator', label: 'I coordinate follow-up', group: 'My job', intro: 'For the Follow-up Coordinator, and administrators who do the same work.' },
  { key: 'welcome', label: 'I welcome newcomers', group: 'My job', intro: 'For the welcome team: registering newcomers and moving them along.' },
  { key: 'messages', label: 'I send messages', group: 'My job', intro: "For anyone sending the planned WhatsApp messages to the people they look after." },
  { key: 'giving', label: 'I handle giving', group: 'My job', intro: 'For whoever records giving, expenses and the monthly remittance.' },
  { key: 'runchurch', label: 'I run the church', group: 'My job', intro: 'For administrators and Location Coordinators: accounts, settings and the rules.' },
  { key: 'setup', label: 'First-time setup', group: 'My job', intro: 'A one-time job for whoever sets the system up. Do the steps in order.' },
  { key: 'why', label: "Why can't I...?", group: 'When something goes wrong', intro: 'Every time the app says no, the reason and what to do. Words in quotes are what the app shows. Search for a word from the message.' },
  { key: 'situations', label: 'What do I do when...', group: 'When something goes wrong', intro: 'Everyday situations and what to do about them.' },
  { key: 'ask', label: 'Still stuck? Ask', group: 'When something goes wrong', intro: 'Who to ask, and what to tell them so they can help straight away.' },
  { key: 'attendance', label: 'Attendance', group: 'Reference' },
  { key: 'members', label: 'Members and shepherds', group: 'Reference' },
  { key: 'followup', label: 'Follow-up times and rules', group: 'Reference' },
  { key: 'newcomers', label: 'Newcomers', group: 'Reference' },
  { key: 'enquiries', label: 'Online enquiries', group: 'Reference' },
  { key: 'finance', label: 'Giving and finance', group: 'Reference' },
  { key: 'goals', label: 'Goals and reports', group: 'Reference' },
  { key: 'alerts', label: 'Alerts on your phone', group: 'Reference' },
  { key: 'admin', label: 'Accounts and roles', group: 'Reference' },
  { key: 'new', label: 'Version 11.14', group: "What's new", intro: 'What changed in version 11.14, and where to read about it.' },
];

const SH: HelpRole[] = ['Shepherd'];
const FC: HelpRole[] = ['Follow-up Coordinator', 'Administrator'];
const AD: HelpRole[] = ['Administrator'];
const ADL: HelpRole[] = ['Administrator', 'Location Coordinator'];
const ALL: HelpRole[] = ['Everyone'];

export const HELP_CONTENT: Record<string, HelpEntry[]> = {
  start: [
    { h: 'New here? Pick what you do', roles: ALL, p: 'This guide is split by job, not by menu. Find yours on the left and follow the steps. Everything else can wait until you need it.',
      links: [
        { to: 'usher', t: 'I record attendance at meetings' },
        { to: 'shepherd', t: 'I follow up people who miss church' },
        { to: 'coordinator', t: 'I coordinate follow-up' },
        { to: 'welcome', t: 'I welcome and register newcomers' },
        { to: 'why', t: "The app said no and I don't know why" },
      ] },
    { h: 'Help for the page you are on', roles: ALL, p: 'Press the ? at the top of any page for the steps for that page, the answers to what it may refuse, and the manual page. Anywhere you see a small ? next to a label, tap it for a plain explanation of that one thing.', manual: 6 },
    { h: 'What your role decides', roles: ALL, p: 'Your menu shows only what your role allows, so it may be shorter than someone else\'s. That is normal, not a fault. If something you need is missing, an administrator can check your role.', manual: 5 },
    { h: 'Your account', roles: ALL, p: 'Tap your round badge at the top right for your name, role and location, My profile and Sign out. In My profile you can add a photo, correct your name, phone and email, change your password, and turn on alerts for your phone.', manual: 7 },
    { h: 'Forgotten your password', roles: ALL, steps: [
      'On the sign-in page, press Forgotten your password? under the Sign in button.',
      'Type the email you sign in with and press Send reset link.',
      'Open the email and press Choose a new password. The link works once, for one hour.',
      'Type the new password twice and press Save and sign in.',
    ], note: 'If the email does not arrive, look in junk or spam. An administrator can also send you a fresh link from Admin, Users, Edit.', manual: 4 },
    { h: 'The bell', roles: ALL, p: 'The bell at the top shows what needs your attention, such as late tasks needing a reason or sessions not filled in, then your Alerts: tasks given to you, decisions on your tasks, repeated absences and reminders. Tap a line to open it. Opening the bell marks alerts as read.', img: 'bell', manual: 63 },
    { h: 'Viewing one location', roles: ['Administrator'], p: 'Administrators covering every location have a location picker at the top. Choose a location and every page narrows to it until you choose All locations again.', manual: 5 },
    { h: 'All times are Bahrain time', roles: ALL, p: 'Due times, alerts and session times are always Bahrain time, whatever time zone your phone is set to. A task due at 6:00 pm shows 6:00 pm for everyone.' },
    { h: 'The user manual', roles: ALL, p: 'Every guide here links to the manual page with the full detail. Press Download the manual at the top of Help for the whole manual. It opens for signed-in people only.' },
  ],

  usher: [
    { h: 'Before the meeting starts', roles: ['Usher'], steps: [
      'Tap Attendance in the menu.',
      "Find today's meeting in All sessions. It is already there: each meeting's session is made at 2:07 am on its day. You do not create it.",
      'Its Status says Waiting for names. Done means someone has already recorded it.',
    ], manual: 21 },
    { h: 'Ticking people off by name (what makes follow-up work)', roles: ['Usher'], img: 'checkin', steps: [
      "Press Check in on today's row.",
      'Every member is listed by category, then the newcomers at this location. Type part of a name to find someone fast.',
      'Tap each name as the person arrives. It turns green and saves straight away. Tap again to undo.',
      'Press Mark online for anyone joining remotely.',
      'Tick newcomers too. On Friday Worship each shows their Fridays so far, which counts towards membership.',
      'When the meeting ends just leave the page. There is no Save button.',
    ], note: 'Anyone not ticked is treated as absent and their shepherd gets a task. Tick everyone who came, newcomers included, or people who were there will be followed up.', manual: 22 },
    { h: 'Recording the headcount and offering', roles: ['Usher'], steps: [
      "Press the session's row in All sessions.",
      'Check the Mode: In person and online, Online or In person.',
      'Type the numbers for each group, in person and online.',
      'Fill in New comers and New converts if there were any.',
      'Under Offering collected, type the amount for each fund.',
      'Press Save session. Its Status changes to Done.',
    ], note: 'Reopening a session shows what was saved before. Saving again keeps the offering unless you change its boxes.', manual: 21 },
    { h: 'Can two ushers tick names at once?', roles: ['Usher'], p: 'Yes. Each tap saves on its own, so ushers at different doors never overwrite each other. Both use Check in on the same session.', manual: 22 },
    { h: 'Ticking names after the service', roles: ['Usher'], p: 'A session already filled in has a white Check in on its row. Tick everyone who came that day. If the absence check has already run, the page says Names ticked late: tasks for anyone not ticked are made at the next check, within 30 minutes, and their 24 hours start then. Someone ticked after their task was made closes it as Was present, and their shepherd is told.', manual: 68 },
    { h: 'The service did not take place', roles: ['Usher', 'Administrator'], steps: [
      'On its row in Attendance, press Did not hold.',
      'Say why, for example a public holiday, and press Save.',
    ], note: 'Nobody is followed up for it and it is left out of averages. Press Undo Did not hold if it did take place after all.', img: 'attendance', manual: 68 },
    { h: 'What the Status words mean', roles: ALL, p: 'Upcoming: its day has not come. Waiting for names: names can be ticked. Names not taken: still no names at 6:00 pm the next day, so nobody can be followed up, and the Follow-up Coordinator is alerted. Done: names ticked. Did not hold: the service did not take place.', manual: 68 },
    { h: 'A reminder to tick names', roles: ['Usher', 'Administrator'], p: 'If no names are ticked 3 hours after a tracked service starts, administrators get a reminder in the bell and on their phone. It is not sent once names are ticked.', manual: 60 },
  ],

  shepherd: [
    { h: 'How you find out someone missed church', roles: SH, p: 'You do not watch for it. Three hours after a tracked service starts, everyone you look after who was not ticked gets a task, and you get an alert. Each missed service has its own task. Newcomers in the New, Contacted or Attending stage are included.', manual: 60 },
    { h: 'Your list: My follow-up', roles: SH, img: 'my', steps: [
      'Open My follow-up in the menu.',
      'Everyone you follow up is listed, members and newcomers together, with late tasks first.',
      'Each person shows their tasks, when each is due and any attempts so far.',
    ], note: 'Priority means they have missed the same meeting twice or more in a row, so your Follow-up Coordinator has been alerted too.', manual: 61 },
    { h: 'When is a task due?', roles: SH, p: 'For a Friday 30 October service: due Saturday 31 October, 6:00 pm, which is 24 hours from 6:00 pm on the service day. A reason is needed from Sunday 1 November, 6:00 pm. A newcomer\'s first-visit task is also due in 24 hours.', manual: 60 },
    { h: 'Record what happened', roles: SH, img: 'record', steps: [
      'Visit or call the person.',
      'On My follow-up, press Record result on their card.',
      'Choose the result: Reached, Tried could not reach, Known reason, Needs the Follow-up Coordinator, or Moved away or left.',
      'For Reached, fill in Goal of the visit, Scripture shared, Root cause and Next step. A Next step date makes a new task for you on that day.',
      'Press Save. One visit closes every open absence task for that person.',
    ], note: 'If there was no opening for scripture, write "None this time" rather than inventing one.', manual: 61 },
    { h: 'Tried but could not reach them', roles: SH, p: 'Choose Tried, could not reach, how you tried, and an optional note. It is logged with the time and the task stays open. After 3 attempts it goes to the Follow-up Coordinator, who is told, because you have tried and need help.', manual: 62 },
    { h: 'Give a reason for a late task', roles: SH, img: 'reasons', steps: [
      'Open My follow-up. A red box says how many late tasks need a reason.',
      'Press Give reasons.',
      'For each task choose a Reason, add a short note and choose a New date, up to 7 days ahead.',
      'Press Send. All are checked together, and nothing is sent if one is wrong.',
    ], note: 'Until every late task has a reason, Record result is refused with a message saying so. That is on purpose: your Follow-up Coordinator reviews each one. If the new date passes with the task still open, it needs a new reason.', manual: 62 },
    { h: 'Someone is travelling, sick or working abroad', roles: SH, steps: [
      'Press Mark away on their card in My follow-up, or Away on their profile.',
      'Choose the dates, the reason and an optional note. Press Save.',
    ], note: 'No tasks are made while they are away. Press "… is back" to clear it early.', manual: 61 },
    { h: 'The Follow-up Coordinator asked you something', roles: SH, p: 'A question arrives in the bell and on your phone, and shows on the task under "Follow-up Coordinator:". Reply by doing what it asks and recording the result, or speak to them.', manual: 64 },
    { h: 'A task was handed to you', roles: SH, p: 'A task marked Handed to you by the Follow-up Coordinator is yours for that one task only, with a fresh 24 hours. The person keeps their own shepherd.', manual: 65 },
    { h: 'Making the visit count', roles: SH, p: 'Go in with a goal, share a scripture that fits, try to understand what is really keeping them away, and agree a concrete next step before you finish.', manual: 18 },
    { h: "Reading someone's history first", roles: SH, p: 'Tap their name to open their profile. The Tasks tab shows every past task with attempts, reasons and results. The Journey tab shows every contact. Worth two minutes before you knock on a door.', img: 'tasks', manual: 67 },
  ],

  coordinator: [
    { h: 'What the Follow-up Coordinator does', roles: FC, p: 'Reviews late tasks and their reasons, is alerted on repeated absences, decides what happens next, and sees every shepherd\'s people and record. Any account can be one through the Follow-up Coordinator tick in Admin, Users, covering All locations or one location.', manual: 64 },
    { h: 'Who gets late tasks and alerts', roles: FC, p: 'The Follow-up Coordinator for the person\'s location first, then one covering All locations, then the administrators. Someone with no shepherd has their tasks given to the Follow-up Coordinator until a shepherd is chosen.', manual: 64 },
    { h: 'The Review list', roles: FC, img: 'review', steps: [
      'Open Follow-up Review in the menu. The Review list tab opens.',
      'Each task shows the person, the shepherd, the reason given or why it is there, and Decide by.',
      'Choose Accept, Hand to another shepherd, Take it myself or Ask the shepherd, then press Confirm.',
    ], note: 'A task is on the list when it is still open 3 days after the service, when the shepherd could not reach the person after 3 attempts, when the shepherd asked for help, or when the person has no shepherd. Not decided within 5 days of the service, it goes to the administrators.', manual: 64 },
    { h: 'The four choices', roles: FC, p: 'Accept: the reason and new date stand. Hand to another shepherd: this one task goes to another shepherd of the same gender at the same location, with a fresh 24 hours, and the person keeps their shepherd. Take it myself: you take it, with a fresh 24 hours. Ask the shepherd: your question reaches them on the task, in the bell and by phone.', manual: 65 },
    { h: 'Change a due time, or cancel a task', roles: FC, p: 'Under each task on the Review list, or on a person\'s Tasks tab: Change due time needs the new time and why. Cancel task needs a reason, such as the person was at the service. Both are kept on the task and in the Audit Log.', manual: 66 },
    { h: 'The Overview', roles: FC, img: 'overview', steps: [
      'On Follow-up Review, press the Overview tab. Choose the location and month at the top.',
      'Measures shows On time, First contact, Reached, Late with no reason and repeated absences, against the targets.',
      'Shepherds lists each shepherd with their people against the limit of 6. Press a row to see that shepherd\'s people.',
    ], note: 'Tasks closed as Was present or Cancelled are left out of every measure. "Open this shepherd\'s list" shows a shepherd\'s My follow-up as they see it.', manual: 65 },
    { h: 'Your own visit tasks', roles: FC, p: 'When someone misses the same meeting 3 times in a row you get a visit task of your own, beside the shepherd\'s, one for the whole run. It is on your My follow-up.', manual: 64 },
    { h: 'Alerts you receive', roles: FC, p: 'Someone missing a meeting twice or more in a row, a reason given for a late task, a task reaching the Review list, 3 attempts without reaching someone, a shepherd asking for help, someone with no shepherd, and names not taken by 6:00 pm the day after a service.', manual: 63 },
  ],

  welcome: [
    { h: 'Someone new is standing in front of you', roles: ['Welcome team'], p: 'Register them before they leave: they fill in the QR form on their own phone, or you type in their paper card. Both end up in the same place, checked in for today\'s service.', manual: 25 },
    { h: 'Using the QR code', roles: ['Welcome team'], steps: [
      'Open Newcomers & Follow-up, then QR Registration.',
      "If you cover more than one location, choose this service's location in Code for.",
      'Show them the code on screen, or project it during the announcement.',
      'They scan it and fill in the form. They appear in the New column straight away.',
    ], note: 'Each phone can send 5 forms a day, enough for a family. Visitors on the church Wi-Fi are counted phone by phone, so they never block each other.', manual: 25 },
    { h: 'Typing in a paper card', roles: ['Welcome team'], steps: [
      'Open Newcomers & Follow-up, then Manual Entry.',
      'Work down the form. It matches the paper card field for field.',
      'Tick the boxes at the bottom as they ticked them. They create real tasks.',
      'Press Add newcomer.',
    ], manual: 26 },
    { h: 'The first visit', roles: ['Welcome team', 'Shepherd'], p: 'Ticks for Would like a visit, Would like to know more, or Want to know about being a Christian each make a task for their shepherd, due in 24 hours.', manual: 25 },
    { h: 'Moving someone along the pipeline', roles: ['Welcome team'], steps: [
      'Open the Pipeline.',
      'Drag their card to the next column, or choose the stage in the dropdown on the card. On a phone only the dropdown works.',
      'Dropping on Member asks you to confirm, because it adds them to the member roll.',
    ], manual: 28 },
    { h: 'Giving several newcomers a shepherd', roles: ['Welcome team', 'Administrator'], steps: [
      'On the Pipeline, switch to Table.',
      'Tick the newcomers.',
      'Choose the shepherd in the bar above the table and press Assign.',
    ], note: 'Only shepherds who may take everyone ticked are offered: men for men, women for women, at their location. Their open tasks move too. One newcomer\'s shepherd can also be chosen on their profile.', manual: 71 },
    { h: 'They said they are not interested', roles: ['Welcome team'], p: 'Open their profile and press Mark as Not Interested, then say why. A note is required, because Not Interested stops follow-up and closes their open tasks. They can be reactivated later.', manual: 37 },
  ],

  messages: [
    { h: 'What the messages are', roles: SH, p: 'Everyone we follow up gets a short planned message now and then, sent by the person looking after them from their own WhatsApp. There are three journeys: Online contacts, Newcomers and New converts. Each person is on one at a time.', manual: 32 },
    { h: "Sending today's messages", roles: SH, steps: [
      'Open Newcomers & Follow-up, then Messages.',
      'If they have not replied since your last message, leave it on No and press Send on WhatsApp.',
      'Send it in WhatsApp, come back, and press Yes, record it.',
    ], note: 'If they have replied, choose Yes and write a personal reply. Their planned message moves to the next day.', manual: 33 },
    { h: 'Messages you missed', roles: SH, p: 'Missed, at the top of Messages, lists planned messages from the last 14 days not sent, or skipped. Send now opens WhatsApp with it, and once you confirm it is recorded on that day\'s plan. Dismiss takes it off the list.', manual: 71 },
    { h: 'Starting messages for people', roles: SH, p: 'Press Start messages. Nobody is ticked to begin with: tick each person you know is happy to hear from us. Those who unticked Keep in touch on their form are listed apart and cannot be started.', manual: 71 },
    { h: 'Another message, or your own', roles: SH, p: 'Use another message opens the message bank for their journey. You can also use a saved message or write your own. Keep it to one or two sentences, end with one easy question, and offer one next step.', manual: 34 },
    { h: "A person's messages", roles: SH, p: 'The Messages tab on a profile shows their journey and what was sent. Switch between Standard and Daily, stop or restart messages, or record a decision for Christ, which moves them to New converts.', manual: 35 },
  ],

  giving: [
    { h: 'Recording giving', roles: ['Finance'], steps: [
      'Open Giving & Finance.',
      'Set the date it was given, the amount, the fund and how it was given.',
      'Link it to a member if known. Anonymous giving is fine.',
      'Press Save.',
    ], note: 'Offerings taken at a service are recorded on the session, so record only giving that came another way.', manual: 42 },
    { h: 'Entries marked From session', roles: ['Finance'], p: 'An offering recorded on a service shows From session with the meeting and date. It is changed on that session, not on Giving & Finance, so the two never disagree. Press Change on the session to open it.', manual: 71 },
    { h: 'Recording an expense', roles: ['Finance'], p: 'Set the date to the month the expense belongs to, the amount, category and a short description. Attach a receipt for anything significant.', manual: 43 },
    { h: 'The monthly remittance', roles: ['Finance'], steps: [
      'Open the Remittance tab.',
      'Press Record on the month.',
      'Check the amount sent for each fund and where it went, then the date and bank reference.',
      'If you send more or less than is due, say why in the box that appears. Press Save.',
    ], manual: 43 },
  ],

  runchurch: [
    { h: 'Follow-up Rules', roles: AD, img: 'rules', steps: [
      'Open Admin, then Follow-up Rules.',
      'Change any time or number: when the clock starts, when tasks are due, reasons, the Review list, repeated absences, the shepherd limit, newcomer stages, reminders and targets.',
      'Press Save changes. The worked example shows what the times mean for next Friday.',
    ], note: 'Only an administrator covering All locations can change them, because they apply at every location. Every change is in the Audit Log. Put back the decided values restores those decided on 26 October 2026.', manual: 69 },
    { h: 'A meeting\'s settings', roles: AD, img: 'meeting', steps: [
      'Open Admin, then Meeting Types & Households.',
      'Press Settings on the meeting.',
      'Set the Start time, Create each session (days before the meeting, 0 means the day itself) and Held at.',
      'Press Save changes.',
    ], note: 'A meeting that follows up absence needs a start time, or nobody missing it is followed up. Its row says so.', manual: 69 },
    { h: 'Editing an account', roles: ADL, img: 'user', steps: [
      'Open Admin, Users & Roles, and press Edit on the account.',
      'Change the name, email, role, location, gender, member record, Can shepherd others, or the Follow-up Coordinator tick and what it covers.',
      'Press Save changes.',
    ], note: 'Send password reset link emails a link that works once for an hour. Switch off stops them signing in and hands their open tasks to the Follow-up Coordinator, keeping their history. Add to member roll makes a member record from the account.', manual: 70 },
    { h: 'Choosing a Follow-up Coordinator', roles: AD, steps: [
      'In Admin, Users & Roles, press Edit on the account.',
      'Tick Follow-up Coordinator and choose what it covers: All locations or one location.',
      'Press Save changes.',
    ], note: 'Until one is chosen, late tasks and alerts go to the administrators. A Location Coordinator\'s account coordinates its own location only.', manual: 64 },
    { h: 'Someone is leaving', roles: ADL, p: 'Switch off their account in Admin, Users, Edit. Their open tasks go to the Follow-up Coordinator. If they shepherd people, untick Can shepherd others and run Auto-assign on Members to share their people out.', manual: 52 },
    { h: 'Removing a location', roles: AD, p: 'A location with accounts, house fellowships or a Follow-up Coordinator cannot be removed. The message names them. Move them to another location in Admin first.', manual: 55 },
  ],

  setup: [
    { h: 'Do these in order', roles: AD, p: 'Some steps depend on earlier ones. This is a one-time job for whoever administers the system.' },
    { h: '1. Locations', roles: AD, steps: [
      'Admin, Config Lists, Locations.',
      'The main location is already there and cannot be deleted.',
      'Add any other location. Use the pencil to rename one. Records stay with it.',
    ], manual: 55 },
    { h: '2. Meetings', roles: AD, steps: [
      'Admin, Meeting Types: add each regular meeting with its Day.',
      'Choose Detailed or Simple, who it is for, and whether it collects an offering.',
      'Tick Follows up absence only for meetings everyone is expected at.',
      'Press Settings to set its Start time, when sessions are created and where it is held.',
    ], note: 'Switching follow-up on for a meeting nobody is expected at buries your shepherds in tasks.', manual: 53 },
    { h: '3. Accounts', roles: AD, steps: [
      'Admin, Users & Roles: Add user for each person, with the narrowest role that lets them do their job.',
      'Tick Can shepherd others and set the Gender for every shepherd.',
      'Tick Follow-up Coordinator on whoever coordinates follow-up.',
    ], manual: 51 },
    { h: '4. Members and households', roles: AD, p: 'Add members, and link people who live together to one household, so they keep one shepherd.', manual: 15 },
    { h: '5. Shepherds', roles: AD, p: 'On Members, press Auto-assign, check the proposal and press Apply.', img: 'autoassign', manual: 17 },
    { h: '6. Follow-up Rules and goals', roles: AD, p: 'Check Admin, Follow-up Rules, then the targets on Goals. Goals can update themselves from the records with Automatically.', manual: 69 },
  ],

  why: [
    // Follow-up
    { h: "Why can't I record a result?", say: '"2 of your late tasks need a reason first. Give a reason and a new date for each, then record this result."', why: 'Your Follow-up Coordinator reviews every late task, so each needs a reason before anything else is recorded.', fix: 'On My follow-up press Give reasons in the red box, send them, then record the result.', roles: SH, manual: 62 },
    { h: "Why can't I give a reason?", say: '"This task is not late yet, so no reason is needed."', why: 'Reasons are only for late tasks.', fix: 'Record the result instead.', roles: SH, manual: 62 },
    { h: 'Why is my new date refused?', say: '"Choose a new date from today up to …, 7 days ahead"', why: 'So a late task is not pushed far away.', fix: 'Choose a date within 7 days. If more time is needed, give a reason again when that date passes.', roles: SH, manual: 62 },
    { h: 'Why are my reasons not sent?', say: '"Nothing was sent. Correct the reasons shown, then send again."', why: 'All reasons are checked together, so none is half sent.', fix: 'Each task with a problem says what. Choose a reason, or a date within 7 days, and press Send again.', roles: SH, manual: 62 },
    { h: "Why can't I give a reason for someone else's task?", say: '"Only the shepherd the task belongs to gives its reason."', why: 'The reason explains the shepherd\'s own work.', fix: 'Ask the shepherd, or if you are the Follow-up Coordinator, decide on it on the Review list.', roles: SH, manual: 62 },
    { h: 'Why must I say what the reason is?', say: '"Say what the reason is, for example travelling until 15 November."', why: 'Known reason closes the task, so the reason is kept with it.', fix: 'Type the reason. Add away dates if they are away for a while.', roles: SH, manual: 61 },
    { h: 'Why must I say what the matter is?', say: '"Say briefly what the matter is, so the Follow-up Coordinator knows before calling."', why: 'Needs the Follow-up Coordinator hands it on, and they need to know what to expect. Only the shepherd, the Follow-up Coordinator and administrators see it.', fix: 'Write a short line, such as "Family conflict, wants to speak to a pastor".', roles: SH, manual: 61 },
    { h: 'Why are the four boxes required?', say: '"Please complete: Goal of the visit, Scripture shared …"', why: 'A tick with no record is little use to whoever reads it next month.', fix: 'Fill in all four. If there was no opening for scripture, write "None this time".', roles: SH, manual: 61 },
    { h: 'Why is the next step date refused?', say: '"The next step date cannot be in the past."', why: 'It makes a new task for that day.', fix: 'Choose today or later, or leave it empty.', roles: SH, manual: 61 },
    { h: 'Why is Log an attempt greyed out?', why: 'You have late tasks that need a reason first.', fix: 'Give the reasons, then log the attempt.', roles: SH, manual: 62 },
    { h: "Why can't I mark someone away?", say: '"Only their shepherd, a Follow-up Coordinator or an administrator can mark someone away"', why: 'So nobody else\'s people stop being followed up by mistake.', fix: 'Ask their shepherd or the Follow-up Coordinator.', roles: ALL, manual: 61 },
    { h: 'Why are the away dates refused?', say: '"The end date must be on or after the start date." or "Away can be set for up to a year at a time."', why: 'Away stops follow-up, so it has a clear start and end.', fix: 'Check the dates. For longer than a year, set it again when it ends, or set their Status to Moved away.', roles: ALL, manual: 61 },
    { h: "Why can't I cancel a task?", say: '"Only a Follow-up Coordinator or an administrator can cancel a task"', why: 'A cancelled task never reaches the shepherd\'s record, so only they decide.', fix: 'Ask your Follow-up Coordinator. If the person was there, tick them on the check-in page: the task closes as Was present.', roles: ALL, manual: 65 },
    { h: "Why can't I change a due time?", say: '"Only a Follow-up Coordinator or an administrator can change a due time"', why: 'So the time limits stay the same for every shepherd.', fix: 'Give a reason and new date when it is late, or ask your Follow-up Coordinator.', roles: SH, manual: 66 },
    { h: 'Why is the new due time refused?', say: '"Choose a time that has not passed yet." or "Say why the due time changes."', why: 'A due time is in the future, and the reason is kept with the task.', fix: 'Choose a later time and type why.', roles: FC, manual: 66 },
    { h: "Why can't I open the Review list?", say: '"The Review list is for Follow-up Coordinators and administrators."', why: 'It decides on other shepherds\' late tasks.', fix: 'An administrator can tick Follow-up Coordinator on your account in Admin, Users.', roles: ALL, manual: 64 },
    { h: "Why can't I see another location on Follow-up Review?", say: '"You coordinate follow-up for one location only."', why: 'Your coordination covers one location.', fix: 'An administrator can change what you cover in Admin, Users, Edit.', roles: FC, manual: 64 },
    { h: "Why can't I decide on this task?", say: '"Only a Follow-up Coordinator for this person\'s location, or an administrator, decides on late tasks."', why: 'Each location\'s tasks are decided there.', fix: 'Ask the Follow-up Coordinator for that location.', roles: FC, manual: 64 },
    { h: 'Why is the shepherd I want not offered to hand on to?', say: '"Only women at Bahrain HQ are offered, because … is a woman."', why: 'Men follow up men and women follow up women, at the person\'s own location, and the shepherd already holding it is left out.', fix: 'If nobody suitable is free, choose Take it myself or Ask the shepherd.', roles: FC, manual: 65 },
    { h: 'Why must I write a question?', say: '"Write the question for the shepherd"', why: 'Ask the shepherd sends your question to them.', fix: 'Type it in the box, such as "Did you try her husband\'s number?"', roles: FC, manual: 65 },
    { h: "Why can't I accept?", why: 'Accept is greyed out when no reason has been given, so there is nothing to accept.', fix: 'Choose Ask the shepherd, Hand to another shepherd or Take it myself.', roles: FC, manual: 65 },
    // Attendance
    { h: 'Why is Save session greyed out?', say: '"This service is on …. Attendance can be recorded on the day or after."', why: 'A service that has not happened yet has no attendance.', fix: 'Record it on the day of the service or after.', roles: ['Usher'], manual: 22 },
    { h: "Why can't I check people in?", say: '"This service is on …. People can be checked in on the day."', why: 'Check-in is for the day of the service.', fix: 'Open it on the day.', roles: ['Usher'], manual: 22 },
    { h: "Why can't I check anyone in to this service?", say: '"This service is marked Did not hold, so nobody can be checked in."', why: 'It was marked as not taking place.', fix: 'If it did take place, press Undo Did not hold on its row, then check people in.', roles: ['Usher'], manual: 68 },
    { h: "Why can't I mark it Did not hold?", say: '"Attendance is already recorded for this service, so it did take place." or "It can be marked Did not hold on the day or after."', why: 'A service with attendance did take place, and a future one has not happened yet.', fix: 'Correct the attendance instead, or wait until the day.', roles: ['Usher'], manual: 68 },
    { h: 'Why must I say why it did not hold?', say: '"Say why it did not hold, for example a public holiday."', why: 'The reason is kept with the service.', fix: 'Type a short reason.', roles: ['Usher'], manual: 68 },
    { h: "Why can't I add this session?", say: '"… already exists. Open it to record attendance instead of adding a second one"', why: 'A second session would count the service twice.', fix: 'Press Open it beside the message and record attendance there.', roles: ['Usher', 'Administrator'], manual: 21 },
    { h: 'Why must youth and children be 0?', say: '"… records men and women only, so this must be 0."', why: 'The meeting is set to Simple.', fix: 'Count everyone as men or women, or ask an administrator to set the meeting to Detailed.', roles: ['Usher'], manual: 21 },
    { h: "Why is Follow up those not ticked refused?", say: '"This service is followed up automatically" or "Today\'s are followed up automatically."', why: 'Recent tracked services are followed up by the absence check.', fix: 'Just tick who came. Tasks for the others are made at the next check.', roles: ['Usher'], manual: 22 },
    { h: 'Why were no tasks made after the service?', why: 'Tasks are made only when names are ticked, and only for meetings that follow up absence and have a start time.', fix: 'Tick who came. An administrator can check the meeting\'s Settings for a start time.', roles: ALL, manual: 67 },
    // People
    { h: 'Why is the shepherd I want not offered?', why: 'Men follow up men and women follow up women, at the person\'s location, and nobody shepherds themselves. Only accounts ticked Can shepherd others are offered.', fix: 'Check the person\'s gender, and the shepherd\'s gender and tick in Admin, Users.', roles: ALL, manual: 17 },
    { h: 'Why is my shepherd choice refused?', say: '"Nobody can shepherd themselves." or "Men follow up men and women follow up women. Not saved, because of …"', why: 'The shepherd rules apply to every way of assigning.', fix: 'Untick the people named, or choose someone of the same gender.', roles: ALL, manual: 17 },
    { h: 'Why is this shepherd refused for these newcomers?', say: '"… serves … only. Not saved, because … is at another location."', why: 'A shepherd follows up people at their own location.', fix: 'Choose a shepherd at that location, or untick that person.', roles: ['Welcome team'], manual: 71 },
    { h: 'Why must I say why for Not Interested?', say: '"Say why, for example "Moved back home"."', why: 'Not Interested stops follow-up, so the reason is kept.', fix: 'Type a short reason.', roles: ['Welcome team'], manual: 37 },
    { h: "Why can't I start messages for this newcomer?", say: '"… unticked Keep in touch on their form, so planned messages are not started."', why: 'They asked not to be sent planned messages.', fix: 'Their shepherd can still message them personally.', roles: SH, manual: 71 },
    { h: 'Why is this phone number refused?', say: '"… already has this phone number. Search Members for it first: they may already be on the roll."', why: 'One phone number belongs to one member.', fix: 'Search Members for the number first. They may already be on the roll.', roles: ALL, manual: 15 },
    { h: 'Why is the date of birth refused?', say: '"Date of birth cannot be in the future."', why: 'It is checked so ages and birthdays are right.', fix: 'Check the year.', roles: ALL, manual: 15 },
    { h: 'Why are the away dates on a profile refused?', say: '"Give both the first and the last day away, or neither."', why: 'Away needs a start and an end.', fix: 'Fill in both dates.', roles: ALL, manual: 61 },
    // Messages
    { h: "Why can't I record today's message?", say: '"Today\'s message for this person is already recorded."', why: 'One planned message a day.', fix: 'Send anything more as your own message from their Messages tab.', roles: SH, manual: 33 },
    { h: 'Why is my missed message refused?', say: '"That message is no longer missed. It may have been sent or dismissed already."', why: 'Someone else has already dealt with it.', fix: 'Nothing to do. The list refreshes.', roles: SH, manual: 71 },
    { h: "Why can't I switch this message off?", say: '"This message is used by a plan, so it can\'t be switched off."', why: 'A plan would have a gap.', fix: 'Edit its wording instead.', roles: AD, manual: 55 },
    // Finance
    { h: "Why can't I change this giving entry?", say: '"This was recorded on …. Open that session in Attendance to change it."', why: 'It is the offering from a service, so it is changed there and the two never disagree.', fix: 'Press Change on the session and correct the offering boxes.', roles: ['Finance'], manual: 71 },
    { h: 'Why will the remittance not save?', say: '"The amount sent differs from the amount due. Say why before recording it."', why: 'A difference needs an explanation.', fix: 'Say why in the box that appears, then save.', roles: ['Finance'], manual: 43 },
    { h: 'Why is this remittance already there?', say: '"… is already recorded for …. Open it with Edit to change it."', why: 'One remittance a month for each location.', fix: 'Press Edit on that month.', roles: ['Finance'], manual: 43 },
    // Accounts and admin
    { h: "Why can't I change the Follow-up Rules?", say: '"These rules apply at every location, so only an administrator covering All locations can change them."', why: 'One set of rules for every location.', fix: 'Ask an administrator who covers All locations.', roles: ADL, manual: 69 },
    { h: 'Why is my Follow-up Rules change refused?', say: '"Use a number from … to …" or "… must be more hours than Follow-up due after."', why: 'The times must follow in order: due, then reason, then Review list, then decision.', fix: 'Correct the rule shown in red, then save.', roles: AD, manual: 69 },
    { h: "Why can't I give this role?", say: '"The … role can do things your own role cannot, so you cannot give it to anyone."', why: 'Nobody gives more rights than they have.', fix: 'Ask an administrator covering All locations.', roles: ADL, manual: 51 },
    { h: "Why can't I manage this account?", say: '"You can only manage accounts for your own location."', why: 'A Location Coordinator manages their own location.', fix: 'Ask an administrator covering All locations.', roles: ['Location Coordinator'], manual: 51 },
    { h: "Why can't I switch off my own account?", say: '"You cannot switch off your own account while signed in to it."', why: 'You would lock yourself out.', fix: 'Ask another administrator.', roles: ADL, manual: 70 },
    { h: 'Why is a change to the Administrator role refused?', say: '"This would leave no active account that covers All locations with full Admin rights"', why: 'Nobody could undo it.', fix: 'Give another account those rights first.', roles: AD, manual: 51 },
    { h: "Why can't I delete this account?", say: '"… produced … record(s) that keep their name … Switch it off instead"', why: 'Records such as reports keep the name of whoever made them.', fix: 'Press Edit, then Switch off. They can no longer sign in and the records stay correct.', roles: ADL, manual: 70 },
    { h: "Why can't I send a reset link?", say: '"This account is switched off. Switch it on first, then send the link."', why: 'A switched-off account cannot sign in.', fix: 'Switch it on in Edit, then send the link.', roles: ADL, manual: 70 },
    { h: "Why can't I add this account to the member roll?", say: '"Give the account a first and last name first" or "… is already linked to a member record."', why: 'The member record takes the account\'s name, and one person has one record.', fix: 'Add both names, or check Member record.', roles: ADL, manual: 70 },
    { h: 'Why is the member record refused?', say: '"… is already the member record of …"', why: 'One member record belongs to one account.', fix: 'Choose the right member, or unlink the other account first.', roles: ADL, manual: 52 },
    { h: 'Why is the Follow-up Coordinator location refused?', say: '"This account covers … only, so it can coordinate follow-up for … only."', why: 'An account limited to one location coordinates that location.', fix: 'Set its location to All locations first to coordinate elsewhere.', roles: AD, manual: 64 },
    { h: "Why can't I remove this location?", say: '"… still has … Move these to another location in Admin first"', why: 'Its accounts would quietly get every location, and its fellowships would meet nowhere.', fix: 'Move the accounts and fellowships named, then remove it.', roles: AD, manual: 55 },
    { h: "Why can't I remove this?", say: '"This is still used by … records, so it cannot be removed."', why: 'Records point to it.', fix: 'Leave it, or rename it if the wording is wrong.', roles: AD, manual: 55 },
    { h: 'Why is the location code refused?', say: '"A location\'s short code cannot be changed. Rename it instead."', why: 'Every record points to the code.', fix: 'Change the name with the pencil.', roles: AD, manual: 55 },
    { h: 'Why is creating sessions further ahead refused?', say: '"Sessions can be created at most 14 days ahead"', why: 'So the list never fills with services weeks away.', fix: 'Choose 14 days or fewer.', roles: AD, manual: 69 },
    { h: 'Why is a goal refused?', say: '"Choose what it measures." or "Choose the meeting." or "Choose the fund."', why: 'An automatic goal needs to know what to count.', fix: 'Choose the measure, then the meeting or fund it asks for.', roles: AD, manual: 71 },
    { h: 'Why is the report refused?', say: '"That month has not started yet." or "A report can cover up to … months." or "This report already exists"', why: 'Reports cover whole months that have started, one of each.', fix: 'Choose other months, or delete the old report first.', roles: AD, manual: 48 },
    // Everyone
    { h: 'Why is something missing from my menu?', say: '"Your role does not allow this."', why: 'Your role does not include it.', fix: 'Ask an administrator to check your role.', roles: ALL, manual: 5 },
    { h: "Why can't I find or open this person?", why: 'Your account covers one location, so people at other locations are not shown. They may also have moved away or left: Members, Status shows them.', fix: 'Ask someone who covers that location, or check the Status filter.', roles: ALL, manual: 5 },
    { h: 'Why is my password refused?', say: '"The two passwords don\'t match." or "That isn\'t your current password."', why: 'It is checked twice so it is typed right.', fix: 'Type it again carefully, or use Forgotten your password?', roles: ALL, manual: 4 },
    { h: 'Why am I locked out?', why: 'After five wrong passwords sign-in is locked for 15 minutes, to stop guessing. The fourth attempt warns you.', fix: 'Wait 15 minutes, or reset your password.', roles: ALL, manual: 3 },
    { h: 'Why is my photo refused?', say: '"That picture is too large. Choose one under 8 MB." or "Use a JPG or PNG."', why: 'Only ordinary pictures of a sensible size are kept.', fix: 'Choose a smaller JPG or PNG.', roles: ALL, manual: 7 },
    { h: 'Why do I not get alerts?', say: '"Turn alerts on for this device first."', why: 'Alerts are turned on once on each phone or computer.', fix: 'Open My profile on that device and press Turn on. If they are blocked, it shows the steps for your device.', roles: ALL, manual: 7 },
    { h: 'Why was the QR form refused?', say: '"This phone has already sent 5 forms today."', why: 'To stop a flood of false forms.', fix: 'A leader at the welcome desk adds them by Manual Entry, or an administrator presses Let them in under Phones turned away today on the QR page.', roles: ['Welcome team'], manual: 71 },
    { h: 'A box at the bottom says Not saved', why: 'The server refused the change, and the message says why in its own words.', fix: 'Do what it says. If it is not clear, search this Help for a word from the message.', roles: ALL },
  ],

  situations: [
    { h: 'A member has stopped coming', roles: ALL, p: 'If they were not ticked at a tracked service, their shepherd already has a task. Check My follow-up, or Follow-up Review if you coordinate. If nothing is there, names may not have been ticked, or the meeting may not follow up absence.', manual: 60 },
    { h: 'Someone was there but got a task', roles: ALL, p: 'Tick them on that session\'s check-in page. The task closes as Was present and does not count against the shepherd.', manual: 68 },
    { h: 'Someone told us they would be away', roles: SH, p: 'Press Mark away on their card in My follow-up, or Away on their profile, with the dates. No tasks are made while they are away.', manual: 61 },
    { h: 'A member has moved away or left the church', roles: ADL, p: 'Set their Status on their profile to Moved away or Left the church, with a note. Follow-up stops and their history is kept. Do not delete them: delete removes their attendance and follow-up records for good.', manual: 67 },
    { h: 'A newcomer stopped coming long ago but still gets tasks', roles: ['Welcome team', 'Shepherd'], p: 'Mark them Not Interested on their profile, with a note. Their tasks close and no more are made.', manual: 37 },
    { h: 'A shepherd is stopping', roles: ADL, p: 'In Admin, Users, Edit, untick Can shepherd others. Their open tasks go to the Follow-up Coordinator. Then on Members press Auto-assign, choose Reassign everyone instead, check and press Apply.', manual: 17 },
    { h: 'Too many tasks after a service', roles: ALL, p: 'Names were probably not ticked fully. Tick everyone who came on the check-in page: their tasks close as Was present. A Follow-up Coordinator can cancel the rest with a reason.', manual: 68 },
    { h: 'The service did not hold', roles: ['Usher'], p: 'Press Did not hold on its row in Attendance and say why.', manual: 68 },
    { h: 'I typed the wrong attendance number', roles: ['Usher'], p: 'Open the session again, correct it and save. The offering is kept unless you change its boxes.', manual: 21 },
    { h: 'I ticked the wrong person at check-in', roles: ['Usher'], p: 'Tap their name again. It unticks straight away.', manual: 22 },
    { h: 'Someone new walked in today', roles: ['Welcome team'], p: 'Register them before they leave, by QR Registration or Manual Entry.', manual: 25 },
    { h: 'Someone asked us to stop messaging them', roles: SH, p: 'On their profile, open Messages and press Stop messages. You can still message them yourself.', manual: 35 },
    { h: 'Someone has a shepherd of the other gender, or shepherds themselves', roles: ADL, p: 'On Members press Correct with Auto-assign in the box at the top, check the proposal and press Apply.', manual: 18 },
    { h: 'Two people have the same name', roles: ALL, p: 'That is fine. They are separate records. Use the household or joined date to tell them apart, or add a middle name in Other names.', manual: 14 },
    { h: 'Someone gave money but is not a member', roles: ['Finance'], p: 'Record the giving and leave the member blank. It still counts in the totals.', manual: 42 },
    { h: 'A newcomer landed at the wrong location', roles: ['Welcome team'], p: 'They scanned another location\'s QR code. Press the pencil on their profile, choose the right Location and save. Their open tasks move with them.', manual: 30 },
    { h: 'I get no alerts on my phone', roles: ALL, p: 'Open My profile on that phone and press Turn on. If alerts are blocked, it shows the steps for your phone. On an iPhone, open the system from its Home Screen icon first.', manual: 7 },
    { h: "Somebody else's alerts arrive on my phone", roles: ALL, p: 'They did not sign out on it. Sign them out, or press Turn off here in their My profile.', manual: 7 },
  ],

  ask: [
    { h: 'Before you ask', roles: ALL, p: 'Press the ? at the top of the page you are on, and search this Help for a word from any message you saw. Most answers are there.' },
    { h: 'What to tell them', roles: ALL, steps: [
      'Which page you were on, such as My follow-up.',
      'What you pressed.',
      'The exact words of any message, or a screenshot.',
      'The person or service it was about.',
    ], note: 'With these four, whoever helps you can usually answer straight away, without asking you back.' },
  ],

  attendance: [
    { h: 'Where sessions come from', roles: ALL, p: 'Each weekly meeting\'s session is made at 2:07 am on its day, at every location it is held, unless set to be made earlier in the meeting\'s Settings. A house fellowship meeting gets one session per fellowship. Use New session only for one-off meetings.', manual: 69 },
    { h: 'Two ways attendance is recorded', roles: ALL, p: 'The headcount is the official figure. Ticking names records exactly who came, and is what drives follow-up and newcomers\' progress to membership. Both are kept.', manual: 22 },
    { h: 'Occasional meetings', roles: ALL, p: 'For GCK, Ministerial Renewal and other occasional meetings, a new session asks for the Edition name and where it is held.', manual: 23 },
    { h: 'Status words', roles: ALL, p: 'Upcoming, Waiting for names, Names not taken, Done and Did not hold. The ? beside Status on the Attendance list explains each.', img: 'attendance', manual: 68 },
    { h: 'Older services', roles: ['Usher'], p: 'For a service more than 7 days old, or a meeting not followed up automatically, tick who came, then press Follow up under Follow up those not ticked at the bottom of the check-in page. It shows how many and asks before making tasks.', manual: 22 },
  ],

  members: [
    { h: 'Member categories', roles: ALL, p: 'General Member, Worker in Training and Worker. Move someone with Move to category on their Overview tab. It is church status only and gives no powers in the system.', manual: 18 },
    { h: 'Status, away and leader', roles: ADL, p: 'On the profile: Status is Active, Moved away or Left the church. Anyone not Active stops being followed up and is hidden from Members, but keeps their history. Away sets dates with no tasks. Leader means expected at leadership meetings. Members, Status filter shows those who moved away or left.', manual: 67 },
    { h: 'What a shepherd is', roles: ALL, p: 'The person responsible for checking on someone. Anyone whose account is ticked Can shepherd others can be one. Men shepherd men, women shepherd women, and nobody shepherds themselves.', manual: 17 },
    { h: 'Assigning shepherds', roles: ADL, p: 'One at a time on the profile, several at once by ticking rows in the list, or Auto-assign for everyone without one. Changing someone\'s shepherd moves their open tasks too.', img: 'autoassign', manual: 17 },
    { h: 'How auto-assign decides', roles: ADL, p: 'Household first, then whoever carries the fewest. Nothing is saved until you press Apply. A shepherd carrying more than 6 shows as, for example, 7 of 6: a warning only.', manual: 17 },
    { h: 'Deleting a member', roles: ADL, p: 'Delete shows what it would remove for good: check-ins, follow-ups, message plans and category history. Set status instead keeps everything and stops follow-up.', manual: 67 },
    { h: 'One profile for each person', roles: ALL, p: 'A newcomer who becomes a member keeps the same page and story. The Tasks tab lists every task with its attempts, reasons, decisions and result.', img: 'tasks', manual: 67 },
  ],

  followup: [
    { h: 'The follow-up clock', roles: ALL, p: 'For a Friday service starting 6:00 pm: tasks made at 9:00 pm, due Saturday 6:00 pm, a reason needed from Sunday 6:00 pm, on the Review list from Monday 6:00 pm, decided by Wednesday 6:00 pm. All set in Admin, Follow-up Rules.', manual: 60 },
    { h: 'Each missed service has its own task', roles: ALL, p: 'Missing again adds another task, even if one is still open, so every absence is followed up. One visit closes them all.', manual: 61 },
    { h: 'Repeated absences', roles: ALL, p: 'From the 2nd miss of the same meeting in a row, the Follow-up Coordinator is alerted each time. At the 3rd, they get a visit task of their own, one for the whole run.', manual: 64 },
    { h: 'Attendance falling', roles: ALL, p: 'Someone who came to fewer than half of the last 8 services, without missing several in a row, gets an Attendance falling task, checked each morning.', manual: 69 },
    { h: 'Which meetings count', roles: ALL, p: 'Only meetings with Follows up absence ticked and a start time. Friday Worship is on by default. Only the people a meeting is for are followed up: Everyone, Workers or Leadership.', manual: 53 },
    { h: 'Which newcomers are followed up', roles: ALL, p: 'Newcomers in the New, Contacted or Attending stage, until marked Not Interested or they become members. Set in Follow-up Rules.', manual: 69 },
    { h: 'Members, Follow-up and Newcomers, Follow-up tabs', roles: FC, p: 'These still list every task for members and for newcomers, with Mark done, for anyone overseeing. Shepherds use My follow-up.', manual: 19 },
    { h: 'Adding a task by hand', roles: ALL, p: 'On a member\'s profile open the Tasks tab, type the Task, choose the Due date and who it is For, and press Add task.', manual: 19 },
  ],

  newcomers: [
    { h: 'The pipeline', roles: ALL, p: 'New: registered, nobody has reached them. Contacted: someone has spoken to them. Attending: they have come to a service. Member: on the member roll. Not Interested stops follow-up.', manual: 27 },
    { h: 'Becoming a member', roles: ALL, p: 'Proposed once the Salvation milestone is recorded, they have been checked in at half or more of the Friday services since their first, and they first came six months ago or more. An administrator confirms, and can add anyone at any time.', manual: 38 },
    { h: 'A newcomer\'s profile', roles: ALL, p: 'Shepherd can be chosen there. Away sets dates with no tasks. The Tasks tab shows every task and its record.', manual: 30 },
    { h: 'The service ladder', roles: ALL, p: 'Everyone who follows people up has a level, from Sower to Good and Faithful Servant, from the last 90 days of follow-ups, messages and the people they look after. Tap the badge beside the bell.', manual: 8 },
  ],

  enquiries: [
    { h: 'Online enquiries', roles: ['Welcome team'], p: 'Contacts from social media and the website. Give each a follow-up person, answer them, and when they come to church, add them as a newcomer so their story continues.', manual: 39 },
    { h: 'A follow-up person for every contact', roles: ['Welcome team'], p: 'Tick several and assign, or press Auto-assign. Only people of the same gender are offered.', manual: 40 },
  ],

  finance: [
    { h: 'Who can see this', roles: ['Finance'], p: 'Giving and finance figures appear only for roles with finance access, including on the dashboard.', manual: 42 },
    { h: 'Projects', roles: ['Finance'], p: 'Giving tagged to a project shows progress against its target.', manual: 42 },
    { h: 'Correcting an entry', roles: ['Finance'], p: 'Press the pencil on the entry, correct it and save. An entry From session is corrected on the session.', manual: 43 },
  ],

  goals: [
    { h: 'Two kinds of goals', roles: ALL, p: 'Typed by hand: someone types the current figure. Automatically: it updates itself from the records, such as average attendance at a meeting and location, sessions held, people checked in by name, a fund total, or giving less expenses.', manual: 46 },
    { h: 'Reading progress', roles: ALL, p: 'A bar is green at 90% of target or more, blue from 60% to 90%, and red below 60%.', manual: 46 },
    { h: 'Reports', roles: AD, p: 'The overseer and zonal reports pull attendance, giving, newcomers, goals and testimonies together for the months chosen.', manual: 48 },
  ],

  alerts: [
    { h: 'Turning on alerts', roles: ALL, steps: [
      'Open My profile on the phone or computer.',
      'Press Turn on and allow notifications when asked.',
      'Press Send me a test alert to check.',
    ], note: 'Do this once on each device. On an iPhone, add the system to your Home Screen first and open it from there.', manual: 7 },
    { h: 'Blocked alerts', roles: ALL, p: 'If alerts are blocked, My profile shows the steps for your device: the Android app, Chrome, iPhone, or a computer.', manual: 7 },
    { h: 'Which alerts you get', roles: ALL, p: 'Choose them in My profile. Follow-up accountability covers late tasks and reasons, the Review list, repeated absences and reminders to tick names.', manual: 7 },
  ],

  admin: [
    { h: 'Users and roles', roles: ADL, p: 'Each person has an account and a role. The role decides what they see and change. Give the narrowest role that lets them do their job. A Location Coordinator manages accounts at their own location only.', manual: 51 },
    { h: 'The Follow-up Coordinator role', roles: AD, p: 'For people who do only follow-up coordination: view members, newcomers, attendance and reports, and use Follow-up review. No giving and no Admin.', manual: 64 },
    { h: 'Follow-up review in Roles & Permissions', roles: AD, p: 'The Review list, reasons, handing tasks on and the shepherd table. An account with the Follow-up Coordinator tick gets it whatever its role. Changing the Administrator role asks you to confirm.', manual: 51 },
    { h: 'Member record', roles: ADL, p: 'Which person on the member roll an account belongs to, so nobody is given themselves to shepherd. Add to member roll makes one from the account.', manual: 52 },
    { h: 'Audit log', roles: AD, p: 'Every significant action, including Follow-up Rules changes, decisions and cancelled tasks, with who and when.', manual: 56 },
  ],

  new: [
    { h: 'My follow-up and reasons for late tasks', roles: SH, p: 'One list for each shepherd, members and newcomers together. Late tasks need a reason and a new date.', links: [{ to: 'shepherd', t: 'I follow up people' }], manual: 60 },
    { h: 'The Follow-up Coordinator and Follow-up Review', roles: FC, p: 'The Review list, the four choices, the Overview with measures, and alerts on repeated absences.', links: [{ to: 'coordinator', t: 'I coordinate follow-up' }], manual: 64 },
    { h: 'Attendance', roles: ALL, p: 'Sessions made on the day, clear status words, Did not hold, and Was present when someone is ticked late.', links: [{ to: 'usher', t: 'I record attendance' }], manual: 67 },
    { h: 'Settings', roles: AD, p: 'Follow-up Rules, meeting Settings, Edit for accounts with reset link, Switch off and Add to member roll.', links: [{ to: 'runchurch', t: 'I run the church' }], manual: 69 },
    { h: 'Everything else', roles: ALL, p: 'Missed messages, Start messages leaving out those who said no, assigning several newcomers, automatic goals, Giving entries From session, the QR form counting each phone, a message whenever something is not saved, and steps for blocked alerts.', manual: 71 },
  ],
};

/**
 * Help for this page: the ? in the top bar. Matched on the start of the
 * address, longest first.
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
    'Press Mark online for anyone joining remotely.',
    'Tick newcomers too. Anyone not ticked gets a follow-up task.',
  ], links: [{ t: 'Ticking names after the service', s: 'usher', h: 'Ticking names after the service' }, { t: "Why can't I check people in?", s: 'why', h: "Why can't I check people in?" }] } },
  { path: /^\/attendance\/new/, help: { title: 'New session', manual: 23, steps: [
    'Use this only for one-off meetings. Weekly sessions are made for you.',
    'Choose the meeting, date and location, then press Create.',
  ], links: [{ t: "Why can't I add this session?", s: 'why', h: "Why can't I add this session?" }] } },
  { path: /^\/attendance\/\d+/, help: { title: 'Recording a service', manual: 21, steps: [
    'Type the headcount for each group, and new comers and converts.',
    'Type the offering for each fund.',
    'Press Save session.',
  ], links: [{ t: 'Why is Save session greyed out?', s: 'why', h: 'Why is Save session greyed out?' }, { t: 'Recording the headcount and offering', s: 'usher', h: 'Recording the headcount and offering' }] } },
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
    'The Tasks tab shows every task and its record.',
    'Mark as Not Interested needs a note and stops follow-up.',
  ], links: [{ t: 'Why must I say why for Not Interested?', s: 'why', h: 'Why must I say why for Not Interested?' }] } },
  { path: /^\/newcomers/, help: { title: 'Newcomers', manual: 27, steps: [
    'Drag a card, or use its dropdown, to move someone along.',
    'In Table, tick several and press Assign to give them a shepherd.',
  ], links: [{ t: 'Giving several newcomers a shepherd', s: 'welcome', h: 'Giving several newcomers a shepherd' }, { t: 'Why is this shepherd refused?', s: 'why', h: 'Why is this shepherd refused for these newcomers?' }] } },
  { path: /^\/enquiries/, help: { title: 'Online enquiries', manual: 39, steps: ['Give each contact a follow-up person.', 'Answer them, and add them as a newcomer when they come.'], links: [{ t: 'Online enquiries', s: 'enquiries' }] } },
  { path: /^\/finance/, help: { title: 'Giving & Finance', manual: 42, steps: ['Record giving and expenses in the forms.', 'Entries From session are changed on the session.', 'The Remittance tab records each month.'], links: [{ t: "Why can't I change this giving entry?", s: 'why', h: "Why can't I change this giving entry?" }, { t: 'Why will the remittance not save?', s: 'why', h: 'Why will the remittance not save?' }] } },
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
