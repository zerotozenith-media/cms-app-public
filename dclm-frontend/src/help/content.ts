export interface HelpEntry {
  h: string;
  p?: string;
  steps?: string[];
  note?: string;
  links?: { to: string; t: string }[];
}

export interface HelpSection {
  key: string;
  label: string;
  group: 'Getting going' | 'Reference';
}

export const HELP_SECTIONS: HelpSection[] = [
  { key: 'start', label: 'Start here', group: 'Getting going' },
  { key: 'usher', label: 'I record attendance', group: 'Getting going' },
  { key: 'shepherd', label: 'I follow up people', group: 'Getting going' },
  { key: 'welcome', label: 'I welcome newcomers', group: 'Getting going' },
  { key: 'setup', label: 'First-time setup', group: 'Getting going' },
  { key: 'situations', label: 'What do I do when...', group: 'Getting going' },
  { key: 'attendance', label: 'Attendance & check-in', group: 'Reference' },
  { key: 'members', label: 'Members & shepherds', group: 'Reference' },
  { key: 'followup', label: 'Follow-up workflow', group: 'Reference' },
  { key: 'newcomers', label: 'Newcomers', group: 'Reference' },
  { key: 'finance', label: 'Giving & finance', group: 'Reference' },
  { key: 'goals', label: 'Goals & reports', group: 'Reference' },
  { key: 'admin', label: 'Admin setup', group: 'Reference' },
  { key: 'faq', label: 'Common questions', group: 'Reference' },
];

export const HELP_CONTENT: Record<string, HelpEntry[]> = {
  start: [
    {
      h: 'New here? Pick what you do',
      p: 'This guide is split by job, not by menu. Find yours below and follow the steps. Everything else can wait until you need it.',
      links: [
        { to: 'usher', t: 'I record attendance at meetings' },
        { to: 'shepherd', t: 'I follow up members who miss church' },
        { to: 'welcome', t: 'I welcome and register newcomers' },
        { to: 'setup', t: 'I am setting this system up for the first time' },
        { to: 'situations', t: 'Something happened and I do not know what to do' },
      ],
    },
    {
      h: 'Two things worth knowing before you start',
      p: 'First: what you can see depends on your role, so your menu may be shorter than someone else\'s. That is normal, not a fault. Second: anywhere you see a small ? next to a label, tap it for a plain explanation of that one thing.',
    },
    {
      h: 'If you get stuck',
      p: 'Use the search box at the top of this guide. Type a word from what you are trying to do, like "absent", "receipt" or "shepherd". Single words find more than whole sentences.',
    },
  ],

  usher: [
    {
      h: 'Before the meeting starts',
      steps: [
        'Tap Attendance in the menu.',
        'Find today\'s meeting in the All sessions list. It is already there, you do not create it.',
        'Check the status says Pending. Filled means someone already recorded it.',
      ],
    },
    {
      h: 'Option A: just count heads (fastest)',
      steps: [
        'Tap the row for today\'s meeting.',
        'Type the numbers into the boxes: men, women, and if shown, youth and children.',
        'Tap Save. The status changes to Filled and you are done.',
      ],
      note: 'Use this when you only need the total. It takes under a minute.',
    },
    {
      h: 'Option B: tick people off by name',
      steps: [
        'On the Attendance list, tap the blue Check in button on today\'s row.',
        'You get every member grouped by category, with a counter at the top.',
        'Tap a person\'s name as they walk in. It turns green and saves straight away.',
        'Tapped the wrong person? Tap again to undo.',
        'For anyone joining online, tap Mark online next to their name.',
        'When the meeting ends, just leave the page. There is no Save or Finish button.',
      ],
      note: 'Do this when the church wants to know who came, not just how many. It is what makes follow-up work: anyone not ticked is treated as absent a few hours later and their shepherd gets a task.',
    },
    {
      h: 'Can two ushers do this at once?',
      p: 'Yes. Each tap saves on its own, so two people on different doors will not overwrite each other. Both should use Check in on the same session.',
    },
    {
      h: 'What if I forget to check anyone in?',
      p: 'Then everyone counts as absent and a lot of follow-up tasks are created. If that happens, tell an administrator, and the tasks can be closed. Better to check in nobody at all than to check in only half the room.',
    },
  ],

  shepherd: [
    {
      h: 'How you find out someone missed church',
      p: 'You do not have to watch for it. A few hours after a service, anyone not checked in gets a follow-up task created automatically, assigned to whoever is their shepherd. If that is you, it shows up in your list.',
    },
    {
      h: 'Seeing what is waiting for you',
      steps: [
        'Tap Members in the menu.',
        'Tap the Follow-up tab at the top.',
        'You see everyone needing a visit or call, soonest deadline first.',
        'Use the All shepherds dropdown and pick your own name to see only yours.',
      ],
    },
    {
      h: 'What the colours mean',
      p: 'Grey means not due yet. Amber means the deadline has passed. Red means it is more than three days overdue. Work down from red.',
    },
    {
      h: 'Making the visit or call count',
      p: 'The aim is not just to check a box. Go in with a goal, share a scripture that fits their situation, try to understand what is really keeping them away, and agree a concrete next step before you finish.',
    },
    {
      h: 'Recording what happened',
      steps: [
        'Find the person in the Follow-up tab and tap Mark done.',
        'Set the date and how you reached them: home visit, phone call, text, or spoke after service.',
        'Fill all four boxes. Goal of the visit. Scripture shared. Root cause. Next step agreed.',
        'Tap Save & mark done.',
      ],
      note: 'All four are required on purpose. Someone reading this in three months needs to know what actually happened, not just that a box was ticked. If there genuinely was no opening for scripture, write "None this time" rather than making something up.',
    },
    {
      h: 'I recorded it wrong',
      steps: [
        'In the Follow-up tab, change the first dropdown from Open only to Completed only.',
        'Find the record and tap Edit.',
        'Your original answers are already filled in. Correct them and save.',
      ],
    },
    {
      h: 'Reading someone\'s history before you visit',
      p: 'Tap their name to open their profile. The Follow-ups section shows every past visit and what was discussed. Worth two minutes before you knock on a door.',
    },
  ],

  welcome: [
    {
      h: 'Someone new is standing in front of you',
      p: 'Two ways to register them. Let them do it on their own phone with the QR code, or take their paper card and type it in yourself. Both end up in the same place.',
    },
    {
      h: 'Using the QR code',
      steps: [
        'Tap Newcomers & Follow-up, then the QR Registration tab.',
        'If you cover more than one location, choose this service\'s location in Code for. Each location has its own code, and a printed one keeps working.',
        'Show them the code on your screen, or have it projected during the announcement.',
        'They scan it with their phone camera and fill the form themselves.',
        'Their details appear straight away in the New column of that location\'s pipeline, with a shepherd from there.',
      ],
    },
    {
      h: 'Typing in a paper card',
      steps: [
        'Tap Newcomers & Follow-up, then the Manual Entry tab.',
        'Work down the form. It matches the paper card field for field.',
        'Do not skip the three tick boxes at the bottom. They create real follow-up tasks.',
        'Tap Add newcomer.',
      ],
    },
    {
      h: 'Why those tick boxes matter',
      p: 'If they tick Would like a visit, Would like to know more about the church, or Want to know about being a Christian, a task is created for someone to act on, with a deadline. The last of these gets a shorter deadline. Leave them unticked and nothing happens.',
    },
    {
      h: 'Moving someone through the pipeline',
      steps: [
        'Go to the Pipeline tab.',
        'Drag their card from one column to the next, or choose the new stage in the dropdown at the bottom of the card. On a phone only the dropdown works.',
        'Dropping a card on Member asks you to confirm, because it adds them to the member roll.',
        'New means not yet contacted. Contacted means someone reached out. Attending means they have come at least once. Member means they are on the member roll.',
      ],
    },
    {
      h: 'They said they are not interested',
      p: 'Open their profile and tap Mark as Not Interested, then write briefly why. They come out of the active pipeline but are not deleted, so they can be brought back later if things change.',
    },
  ],

  setup: [
    {
      h: 'Do these in order',
      p: 'Some steps depend on earlier ones, so the order matters. This is a one-time job for whoever administers the system.',
    },
    {
      h: '1. Set up your locations',
      steps: [
        'Go to Admin, then Config Lists, and find Locations.',
        'The main location, Bahrain HQ, is already there and cannot be deleted.',
        'Add any other location the church runs in. Use the pencil beside a location to rename it at any time. Records stay with it.',
      ],
    },
    {
      h: '2. Set up your meetings',
      steps: [
        'In Admin, go to Meeting types and add each regular meeting.',
        'Choose Detailed if you count men, women, youth and children separately. Choose Simple if you only count men and women.',
        'Switch on Absence follow-up only for meetings everyone is expected at. Friday Worship is on by default.',
      ],
      note: 'Get this right before adding members. Switching absence follow-up on for a meeting nobody is expected at will bury your workers in tasks.',
    },
    {
      h: '3. Create accounts for your team',
      steps: [
        'In Admin, use Add user for each person who needs access.',
        'Give the narrowest role that lets them do their job.',
        'An attendance recorder does not need to see giving figures.',
      ],
    },
    {
      h: '4. Add your members',
      steps: [
        'Go to Members and add people, or import them if you have a list.',
        'Link people who live together to the same household. This matters for the next step.',
      ],
    },
    {
      h: '5. Assign shepherds',
      steps: [
        'Still in Members, tap Auto-assign.',
        'Review what it proposes. Households are kept together, and the rest are spread evenly across your workers.',
        'Tap Apply if it looks right, or Cancel and assign people by hand instead.',
      ],
      note: 'Only members in the Worker category can be shepherds, so make sure your workers are set to that category first.',
    },
    {
      h: '6. Check your goals',
      p: 'Go to Goals. A starter set is already there. Adjust the targets to what your church is actually aiming for. Anything marked auto-tracked updates itself from real data.',
    },
    {
      h: 'One thing still to arrange',
      p: 'The absence check needs to be scheduled to run on its own on your server. That is a technical step for whoever installs the system, not something you can switch on from these screens.',
    },
  ],

  situations: [
    { h: 'Someone new walked in today', p: 'Register them before they leave. Newcomers & Follow-up, then either QR Registration for them to fill in themselves, or Manual Entry if you have their paper card.' },
    { h: 'A member has stopped coming', p: 'If the meeting has absence follow-up switched on, a task was already created for their shepherd. Check Members, Follow-up tab. If nothing is there, the meeting may not be set to track absences, or nobody checked them in that week.' },
    { h: 'I typed the wrong attendance number or count', p: 'Open the session again from the Attendance list, correct the numbers, and save. It simply overwrites the old figure.' },
    { h: 'I ticked the wrong person at check-in', p: 'Tap their name again. It unticks straight away.' },
    { h: 'Someone told us they would be away', p: 'A task will still be created. There is no way yet to log a planned absence in advance. The shepherd can close it, recording that the absence was already known.' },
    { h: 'A member has left the church', p: 'Do not delete them, or you lose their history. Leave the record in place. If they are a shepherd, reassign their people first using Auto-assign, then Reassign everyone instead.' },
    {
      h: 'A worker is leaving and has people assigned to them',
      steps: [
        'Go to Members and tap Auto-assign.',
        'In the panel, tap Reassign everyone instead.',
        'Review the proposed spread and tap Apply.',
      ],
    },
    { h: 'Two people have the same name', p: 'That is fine, they are separate records. Use the household column or their joined date to tell them apart. Adding a middle name in Other names helps.' },
    { h: 'I cannot see something I expect', p: 'Almost always your role. Finance in particular is hidden completely from anyone without access. Ask an administrator to check your role.' },
    { h: 'Someone gave money but is not a member', p: 'Record the giving and leave the member field blank. Anonymous or unlinked giving is normal and still counts in the totals.' },
  ],

  attendance: [
    { h: 'Two ways attendance is recorded', p: 'Headcounts are the official figure: how many men, women, youth and children were present. Named check-in records exactly which members came. Both are kept, and recording one does not change the other.' },
    { h: 'Recording a headcount', p: 'Open the session from the Attendance list and fill in the numbers. Whether you see six boxes or two depends on whether that meeting type is set to Detailed or Simple. If the meeting collects an offering, enter it in the Offering collected box on the same form. It is recorded as giving for that service, dated to it. Save it and the session moves from Pending to Filled. A service that has not happened yet cannot be recorded.' },
    { h: 'Live check-in during a service', p: 'On the day of the service, press Check in on its row in the Attendance list. You get the member list grouped by category. Tap a name as each person arrives and it saves immediately, so several ushers on different doors can work at the same time without overwriting each other. Tap again to undo. Use Mark online for anyone joining remotely.' },
    { h: 'Where sessions come from', p: 'Sessions for regular weekly meetings are created automatically. You do not need to make one each week. A house fellowship meeting gets one session per fellowship, at the location where each fellowship meets. Use New session only for one-off meetings.' },
  ],

  members: [
    { h: 'Member categories', p: 'General Member, Worker in Training, and Worker. To move someone, open their profile and use Move to category. This keeps a dated history so you can see when someone progressed, which also feeds the growth goals.' },
    { h: 'Households', p: 'Linking people to a household keeps families together in the records. It also matters for shepherd assignment: auto-assign keeps a household with the same shepherd rather than splitting them between workers.' },
    { h: 'What a shepherd is', p: 'Every member can be assigned a shepherd, a worker responsible for checking on them. When someone misses a tracked service, the follow-up task goes to their shepherd automatically.' },
    { h: 'Assigning shepherds', p: 'Three ways. One at a time on the member\'s profile. Several at once by ticking the boxes in the member list and choosing a shepherd. Or press Auto-assign to let the system propose assignments for everyone who has none.' },
    { h: 'How auto-assign decides', p: 'Household first, so families stay together. Then whoever currently carries the fewest people. Only Workers can be shepherds. Nothing is saved until you review the proposed list and press Apply. Before applying you can choose a different shepherd for any row, or leave someone unassigned, and each shepherd\'s load now and after is shown. By default it only fills people who have no shepherd, so deliberate pairings are left alone. Reassign everyone recalculates from scratch, which is useful when a worker leaves.' },
  ],

  followup: [
    { h: 'How a follow-up starts', p: 'Nobody has to press anything. A few hours after a service that counts toward absence follow-up, anyone not checked in is treated as absent and a task is created for their shepherd, due two days later.' },
    { h: 'Which meetings count', p: 'Only the ones switched on in Admin under Meeting types. Friday Worship is on by default. Leave it off for meetings where attendance is not expected of everyone.' },
    { h: 'No duplicate pile-ups', p: 'If someone already has an open follow-up, missing again does not stack another one on top. Once the first is resolved, a later absence does create a new task.' },
    { h: 'Recording what happened', p: 'Press Mark done and record four things: the goal of the visit, the scripture shared, the root cause, and the next step agreed. All four are required, because a tick with no record is not much use to whoever reads it next month. If there was genuinely no opening for scripture, write "None this time" rather than inventing one.' },
    { h: 'Seeing what has been done', p: 'The Follow-up tab defaults to open items, but switch the filter to Completed only or All to read past records. Completed entries can be edited if something was recorded wrongly, and deleted if created in error.' },
    { h: 'The same applies to newcomers', p: 'Newcomer tasks work identically, with the same four fields and the same Follow-up tab under Newcomers.' },
  ],

  newcomers: [
    { h: 'Two ways someone is registered', p: 'They scan the QR code and fill the form on their own phone, or a worker types in a paper card using Manual Entry. Both collect the same information and both land in the pipeline of the location they attended.' },
    { h: 'The pipeline', p: 'New means registered and nobody has reached them yet. Contacted means someone has spoken to them. Attending means they have come to a service at least once. Member means they are on the member roll. Drag a card between columns, or use the dropdown on each card, which is the only way on a phone.' },
    { h: 'Becoming a member', p: 'A newcomer is proposed for membership once three things are true: the Salvation milestone is recorded with its date, they have attended at least half the Friday services held at their location since they first came, and they first came at least six months ago. The system only proposes it. An administrator confirms, and can add anyone at any time regardless, for example someone relocating from another church. Dropping a card on the Member column asks you to confirm first, and needs permission to add members.' },
    { h: 'Who each meeting is for', p: 'Every meeting is marked Everyone, Workers or Leadership. This decides who is followed up when absent, so a general member is never asked why they missed a workers meeting. Leadership is a tick on the member record rather than a category, because a leader is a Worker who also leads.' },
    { h: 'Automatic tasks on registration', p: 'If someone ticks Would like a visit, Would like to know more about the church, or Want to know about being a Christian, the matching tasks are created straight away for whoever is assigned to them. The last of these is given a shorter deadline.' },
    { h: 'Not interested', p: 'Marking someone Not Interested takes them out of the active pipeline without deleting them, and records the reason. They can be reactivated later.' },
  ],

  finance: [
    { h: 'Recording giving', p: 'Set the date it was given, then the amount, the fund it belongs to, and how it was given. Offerings taken at a service are already recorded if they were entered on the session form, so only record giving that came in another way. Linking it to a member is optional, so anonymous giving is fine. Linked giving builds up a total on that member\'s profile.' },
    { h: 'Expenses and receipts', p: 'Set the date to the month the expense belongs to, then the amount, category and a short description. A receipt can be attached, and is worth doing for anything significant.' },
    { h: 'The monthly remittance', p: 'Once a month, after expenses, what is due is sent on. On Giving and Finance, the Remittance tab lists each month. Press Record, check the amount sent for each fund and where it went, add the date and bank reference, and save. If you send more or less than is due, say why in the box that appears. Each location records its own remittance, from its own figures.' },
    { h: 'Projects', p: 'A project is something being raised toward with a target. Giving tagged to it shows progress against that target.' },
    { h: 'Who can see this', p: 'Finance is permission-controlled. Someone without finance access does not see these figures anywhere, including on the dashboard.' },
  ],

  goals: [
    { h: 'Two kinds of goals', p: 'Auto-tracked goals calculate themselves from data already in the system, so there is nothing to update by hand. Manual goals are ones no data can measure, so someone types in the current figure as it changes.' },
    { h: 'Reading progress', p: 'A bar is green at 90% of its target or more, blue from 60% to 90%, and red below 60%. Every goal links through to the screen the number comes from, so you can see what is behind it.' },
    { h: 'Monthly reports', p: 'The report pulls the month\'s attendance, giving, newcomers and testimonies into one document you can download and share. Weekly notes and testimonies recorded during the month are included. An administrator covering every location chooses All locations or one location. Somebody limited to one location gets their own location\'s report. The cover says which.' },
  ],

  admin: [
    { h: 'Users and roles', p: 'Create an account for each person and give them a role. The role decides which menu items they see and what they can change. Give the narrowest role that lets someone do their job. A coordinator limited to one location can add accounts at that location only, with roles no more powerful than their own. Roles themselves apply to every location, so only an administrator covering every location changes them.' },
    { h: 'Meeting types', p: 'Each regular meeting is set up once: its name, its day chosen from the Day column, whether attendance is Detailed or Simple, who it is for, and whether it collects an offering. The absence follow-up switch decides whether missing it creates a follow-up task. Meetings apply to every location, so only an administrator covering every location changes them.' },
    { h: 'Follow-up assignment settings', p: 'Controls whether newcomers are included when auto-assign runs. Turn it off if whoever meets a newcomer should keep them rather than having the system reassign. Only an administrator covering every location changes it.' },
    { h: 'The lists', p: 'Funds, expense categories, newcomer sources and so on are all editable here, so the wording matches how this church actually speaks rather than being fixed in the software.' },
    { h: 'Audit log', p: 'Every significant action is recorded with who did it and when. Useful for answering "who changed this" without guesswork.' },
  ],

  faq: [
    { h: 'Someone missed a service but had told us they would be away. Can I stop the task?', p: 'Not yet. The task will be created and the shepherd can close it, recording that the absence was known. A way to log a planned absence in advance is worth adding later.' },
    { h: 'A member shows as Unassigned. Is that a problem?', p: 'The follow-up task is still created, it just has nobody attached, and it shows in the Unassigned count so someone can pick it up. Assigning a shepherd prevents it happening again.' },
    { h: 'Can I undo an auto-assign?', p: 'There is no single undo. Review the proposed changes carefully before pressing Apply. Individual assignments can be changed afterwards on each profile.' },
    { h: 'Why can I not see Giving?', p: 'Your role does not include finance access. That is deliberate, not a fault. Ask an administrator if you need it.' },
    { h: 'I marked a follow-up done but got the details wrong.', p: 'Switch the filter to Completed only, find the record, and press Edit. The original entries are pre-filled so you can correct them.' },
    { h: 'Do I need to create weekly sessions myself?', p: 'No. Sessions for regular weekly meetings appear automatically. Use New session only for one-off meetings.' },
  ],
};
