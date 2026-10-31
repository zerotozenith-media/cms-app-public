/**
 * Every inline help topic in one place rather than scattered through
 * the markup, so the wording stays consistent and can be reviewed
 * together. Deliberately not on every field: only where the answer is
 * not obvious from the label itself, otherwise the markers become noise
 * and people stop reading them.
 */
export interface HelpTopic {
  title: string;
  body: string;
}

export const HELP_TOPICS: Record<string, HelpTopic> = {
  fuCounts: { title: 'The numbers', body: 'How many people in each journey have a message due today. Tap a journey to see only them.' },
  fuReplied: { title: 'Have they replied?', body: "If they have written back since your last message, send a personal reply instead. Today's planned message moves to tomorrow, so nothing is lost." },
  fuSwap: { title: 'Use another message', body: 'Choose another message from the bank, one of your saved messages, or write your own.' },
  fuSkip: { title: 'Skip today', body: 'Nothing is sent today. Their plan carries on at the next planned day.' },
  fuEditor: { title: 'Writing a good message', body: 'Keep it to one or two sentences, end with one easy question, and offer only one next step.' },
  fuPlan: { title: 'Standard or Daily', body: 'Standard spaces messages a few days apart, as set by the plan for their journey. Daily sends one every day. From their third visit, newcomers receive Belonging messages.' },
  fuStop: { title: 'Stop messages', body: 'Stops all planned messages. You can still message them yourself at any time, and restart later.' },
  fuFinal: { title: 'Final gentle message', body: 'Their last planned message. After it, only personal messages from you.' },
  fuBelonging: { title: 'Belonging', body: 'They have visited three times, so they now receive messages about belonging: house fellowship, serving and membership.' },
  fuSteps: { title: 'In-person steps', body: 'The discipler\'s steps alongside the messages for a new convert. Tick each one when done.' },
  fuMissed: { title: 'Missed messages', body: 'A planned message whose day passed without it being sent, or that was skipped. Send it now and it is recorded on that day of their plan, so the plan carries on in order. Dismiss when it no longer fits, for example a welcome sent in person.' },
  fuKeepInTouch: { title: 'Keep in touch', body: 'Ticked, they receive a short word of encouragement from the person following them up. They can ask to stop at any time.' },
  shepherd: {
    title: 'Assigned shepherd',
    body: 'The worker responsible for checking on this person if they miss a service. When an absence is detected, the follow-up task goes to them automatically. Someone with no shepherd still gets a task: it goes to the Follow-up Coordinator until a shepherd is chosen. Men shepherd men, women shepherd women, and nobody shepherds themselves.',
  },
  autoAssign: {
    title: 'How auto-assign decides',
    body: 'Two rules, in order. First, if someone else in the same household already has a shepherd, the same person is used so families are not split across different workers. Everyone else goes to whichever shepherd currently carries the fewest people. Men go to men, women to women, and nobody is given themselves. Only accounts ticked Can shepherd others in Admin can be shepherds. Anyone whose shepherd breaks those rules is also proposed for a new one, marked with the reason. Nothing is saved until you review the proposed changes and press Apply. You can change or skip any row first.',
  },
  reassignEveryone: {
    title: 'Reassign everyone',
    body: 'By default auto-assign only fills in people who have no shepherd, so pairings someone chose deliberately are left alone. Reassign everyone ignores that and recalculates from scratch, which can move people who were paired on purpose. Useful when a shepherd stops and their people need redistributing.',
  },
  absenceTracking: {
    title: 'Counts toward absence follow-up',
    body: 'When this is on, anyone the meeting is for who is not ticked is treated as absent 3 hours after it starts, and a follow-up task is created for their shepherd. The meeting needs a start time, set with Settings on its row, or nobody is followed up. Leave it off for meetings where attendance is not expected of everyone. No one needs to press anything, the check runs on its own.',
  },
  liveCheckIn: {
    title: 'Check-in vs headcount',
    body: 'These are two separate things and both are kept. The headcount on the session record stays the official attendance figure. Checking members in by name is what drives absence follow-up, and checking newcomers in builds their Friday attendance towards membership. Recording one does not change the other.',
  },
  followUpFields: {
    title: 'Why all four are required',
    body: 'A tick with no record of what happened is not much use to whoever reads it next month. Recording the goal, what scripture was shared, the root cause and the agreed next step turns a completed task into something a leader can actually act on. If there was genuinely no opening for scripture, write "None this time" rather than inventing one.',
  },
  detailLevel: {
    title: 'Detail level',
    body: 'Detailed records men, women, youth and children separately. Simple records men and women only. Choose based on what is actually counted at that meeting, since the attendance form changes to match.',
  },
  locationScope: {
    title: 'Location filter',
    body: 'The location your account covers. Someone tied to a single location only ever sees that one. An administrator covering every location sees them all combined, shown here as All locations.',
  },
  newcomerStages: {
    title: 'Pipeline stages',
    body: 'New means registered and nobody has reached them yet. Contacted means someone has spoken to them. Attending means they have come to a service at least once, which check-in confirms. Member means they are on the member roll. Drag a card between columns, or use the dropdown on each card, which is the only way on a phone.',
  },
  qrForm: {
    title: 'QR form vs manual entry',
    body: 'Both collect the same information. Each location has its own QR code, so a newcomer lands in the pipeline of the location they attended. The QR form is what a newcomer fills in themselves on their phone. Manual entry is for a worker typing in a paper card someone filled by hand.',
  },
  goalTracking: {
    title: 'Manual vs auto-tracked goals',
    body: 'Auto-tracked goals calculate themselves from real data already in the system, so there is nothing to update. Manual goals are ones no data can measure, so someone types in the current number as it changes.',
  },
  // Follow-up Rules, meetings and accounts (Kay, 26 October 2026).
  frClock: { title: 'Clock starts at', body: 'The time every follow-up clock starts on the day of a service. Example: 6:00 pm on Friday 30 October. When names are ticked after the absence check has run, the clock starts when the task is made, so a shepherd never starts out late because of a late entry.' },
  frDue: { title: 'Follow-up due after', body: "How long a shepherd has to reach the person and record the result. It applies to tasks for missed services and to a newcomer's first-visit task. Example: 24 hours from 6:00 pm on Friday is 6:00 pm on Saturday." },
  frReason: { title: 'Reason required after', body: 'When a task still open needs a reason from the shepherd. Each late task needs its own reason and a new date. The shepherd sees late tasks first and cannot record anything else until the reasons are given.' },
  frReview: { title: "On the Follow-up Coordinator's Review list after", body: 'When a task still open is flagged on the Follow-up Coordinator\'s Review list and the Follow-up Coordinator is alerted. Reasons appear on the list as soon as they are given.' },
  frDecide: { title: 'Follow-up Coordinator decides within', body: 'How long the Follow-up Coordinator has to choose Accept, Hand to another shepherd, Take it myself or Ask the shepherd. Not decided by then: it goes to the administrators with an alert.' },
  frMaxDate: { title: 'Furthest new date a shepherd can give', body: 'Stops a late task being pushed far away. If the new date passes with the task still open, it is late again and needs a new reason.' },
  frAlertFrom: { title: 'Alert the Follow-up Coordinator from the', body: 'Missing the same meeting several times in a row alerts the Follow-up Coordinator. Example: with 2, missing Friday 23 and 30 October alerts on 30 October, and again on 6 November if missed again.' },
  frVisit: { title: 'Follow-up Coordinator visit task at the', body: "The Follow-up Coordinator gets a visit task of their own, beside the shepherd's. Only one is made for a run of misses, so the list does not fill with repeats." },
  frAttempts: { title: 'Failed attempts before it goes to the Follow-up Coordinator', body: 'Calls, messages or visits with no answer. After this many, the task goes to the Follow-up Coordinator, because the shepherd has tried and needs help.' },
  frFalling: { title: 'Attendance falling task', body: 'Catches someone drifting away without missing several in a row. Example: attending 3 of the last 8 Fridays makes an "attendance falling" task.' },
  frLimit: { title: 'People per shepherd before a warning', body: 'Auto-assign warns when a shepherd would carry more than this, for example "7 of 6". It is a warning only, because sometimes there is nobody else suitable.' },
  frStages: { title: 'Newcomer stages followed up', body: 'Newcomers in the ticked stages get a task when they miss a tracked service. Member is not offered because members are followed up as members. Not Interested is not offered because it stops follow-up.' },
  frCheck: { title: 'Absence check and attendance reminder run', body: 'Hours after a tracked service starts before the app makes tasks for people not ticked, and reminds administrators to tick names. Example: Friday Worship starts at 6:00 pm, so 9:00 pm.' },
  frRemind: { title: 'Attendance reminder goes to', body: 'Who is reminded to fill in the attendance form and tick names after each tracked service. Not sent when names are already ticked.' },
  frMorning: { title: 'Morning alert to shepherds at', body: "When shepherds get the day's tasks as a phone alert and by email." },
  frOnTime: { title: 'On time', body: 'Tasks with a result recorded by their due time. Example: 90% means at least 18 of 20 tasks in a month.' },
  frFirst: { title: 'First contact within', body: 'From the clock start to the first call, message or visit recorded.' },
  frReached: { title: 'Reached', body: 'Tasks closed as Reached, out of all closed. Tried but could not reach does not count.' },
  mtStart: { title: 'Start time', body: 'Used for the absence check, the attendance reminder and the follow-up clock. A tracked meeting with no start time is never checked, so nobody gets a task when it is missed.' },
  mtCreate: { title: 'Create each session', body: 'How many days before the meeting its session appears in Attendance. 0 means on the day itself, at 2:07 am. Before its day a session shows Upcoming, so it is never mistaken for a service whose names were not ticked.' },
  mtHeldAt: { title: 'Held at', body: 'Sessions are created only at the ticked locations, so a location never sees a meeting it does not hold. Tick none to hold it at every location, including new ones.' },
  fuCoordinator: { title: 'Follow-up Coordinator', body: "Reviews late tasks and their reasons, gets alerts on repeated absences, and sees every shepherd's record for the locations chosen below. Works with any role, so an administrator or a Location Coordinator can be one too." },
  fuCoordinates: { title: 'Coordinates follow-up for', body: "All locations, or one location such as Bahrain HQ or Qatar. Late tasks and alerts go to the Follow-up Coordinator for the person's location first, then one for All locations, then the administrators." },
  fuReviewModule: { title: 'Follow-up review', body: 'The Review list, reasons for late tasks, handing a task to another shepherd, taking it over, and the shepherd performance table. Accounts with the Follow-up Coordinator tick get it for their chosen locations, whatever their role.' },
  userSwitchOff: { title: 'Switch off', body: 'The person can no longer sign in, and their open follow-up tasks go to the Follow-up Coordinator. Their records and history stay. Switch them on again at any time.' },
  userReset: { title: 'Send password reset link', body: 'Emails the person a link to choose a new password. It works once, for one hour. You never see or set their password.' },
  userAddToRoll: { title: 'Add to member roll', body: 'Creates a member record from this account, using its name, gender and location, and links the two, so nobody is ever given themselves to shepherd.' },
  // Follow-up screens (Kay, 26 October 2026).
  faMyList: { title: 'My follow-up', body: 'Everyone you follow up, members and newcomers together, with late tasks first. Each missed service has its own task, and one visit closes them all.' },
  faPriority: { title: 'Priority', body: 'They have missed the same meeting 2 or more times in a row, so your Follow-up Coordinator has been alerted. Each missed service has its own task, and one visit closes them all.' },
  faOneVisit: { title: 'One visit closes all', body: 'One visit covers every open absence task for this person. Each task shows this visit as its result, so nothing is recorded twice.' },
  faNextDate: { title: 'Next step date', body: 'A date here makes a new task for you on that date, so the next step is not forgotten.' },
  faNewDate: { title: 'New date', body: 'When you will have reached them. It can be up to 7 days ahead, as set in Follow-up Rules. If the new date passes with the task still open, it is late again and needs a new reason.' },
  faAway: { title: 'Away', body: 'For a known absence, such as travel, illness or a work shift abroad. No absence tasks are made while someone is away, so nobody is chased for an absence that was already explained.' },
  faChangeDue: { title: 'Change due time', body: 'For a Follow-up Coordinator or an administrator, for example when a shepherd agreed a visit date with the person. The change and who made it are kept on the task and in the Audit Log.' },
  faHandOn: { title: 'Hand to another shepherd', body: 'This one task only. The person keeps their shepherd, giving the shepherd the benefit of the doubt. Only shepherds of the same gender at the same location are offered. To change the shepherd for good, use the profile.' },
  faReviewList: { title: 'Review list', body: 'Late tasks with their reasons, tasks the shepherd could not reach after several attempts, matters that need you, and people with no shepherd. Choose Accept, Hand to another shepherd, Take it myself or Ask the shepherd. The shepherd is told on the task, in the bell and by phone alert.' },
  faMeasures: { title: 'Measures', body: 'How faithfully follow-up is happening, against the targets set in Admin, Follow-up Rules. Green meets the target, amber does not. Tasks closed as Was present or Cancelled are left out.' },
  faShepherds: { title: 'Shepherds', body: 'Every shepherd at the locations you coordinate. Press a row to see the people that shepherd follows up. People shows how many they carry against the limit set in Follow-up Rules.' },
  faStatus: { title: 'Status', body: 'Upcoming: its day has not come, so nothing is expected yet. Waiting for names: names can be ticked. Names not taken: still no names at 6:00 pm the next day, so nobody can be followed up. Done: names ticked. Did not hold: the service did not take place.' },
  faDidNotHold: { title: 'Did not hold', body: 'For a service that did not take place, such as a public holiday. Nobody is followed up for it and it is left out of averages. A reason is required. It can be undone.' },
  faNamesLate: { title: 'Names ticked late', body: 'The absence check had already run, so these tasks are made now. Their time starts now rather than at 6:00 pm on the service day, so shepherds are not late because of a late entry.' },
  faWasPresent: { title: 'Was present', body: 'When someone is ticked after their task was made, the task closes as Was present. It does not count against the shepherd, because the person was there.' },
  faAlerts: { title: 'Alerts', body: 'Follow-up alerts kept in the app: tasks given to you, late reasons, the Review list and repeated absences. The same alerts reach your phone when phone alerts are on.' },
  faStatusMember: { title: 'Status', body: 'Moved away or Left the church stops all follow-up tasks for them. They stay in the records and reports for the time they attended.' },
  faLocationMove: { title: 'Location', body: "Where they worship. Changing it moves their open tasks to that location's Follow-up Coordinator unless a shepherd there is chosen. Their history stays with them." },
  faStage: { title: 'Stage', body: 'New, Contacted and Attending: they get a task each time they miss a tracked service. Not Interested stops follow-up, and a note is required. Member moves them to the member roll.' },
  faLeader: { title: 'Leader', body: 'Expected at leadership meetings, so they are followed up when they miss one. Untick when they step down.' },
  // Month-end balance (Kay, 30 October 2026).
  meBalance: { title: 'Month-end balance', body: 'Each month the money held is balanced: what the records say should be there against what is actually there, counted or on the bank statement. A difference is found or explained, a second person approves, and the month is closed so its figures never change afterwards.' },
  meOpening: { title: 'Opening balance', body: "The previous month's approved closing balance. For the start month it is the opening balance set in Admin, Config Lists, Money. Example: July 2026 opens at BHD 0.00, August opens at July's closing balance." },
  meExpected: { title: 'Expected closing balance', body: 'Opening balance, plus giving, less expenses, less remittance sent in the month. What the records say should be held on the last day of the month.' },
  meRemit: { title: 'Remittance sent', body: 'Counted in the month the money left, by its sent date. Example: September\'s remittance sent on 3 October comes out of October.' },
  meCounted: { title: 'Money actually held', body: 'Count the cash on the last day of the month, or read the closing balance on the bank statement, and type it here. Example: 665.250.' },
  meCountedBy: { title: 'Counted by two people', body: 'Cash is counted by two people together, and both names are kept. General practice for church money, so nobody is ever left alone with an unchecked count.' },
  meDifference: { title: 'Difference', body: 'Money held less the expected closing balance. Look for a missing entry first: an expense not recorded, or giving recorded twice. If it cannot be found, explain it. Example: "BHD 5.00 bank charge on 31 October".' },
  meLock: { title: 'Why lock the month?', body: 'So the figures in the month-end report never change after they are approved. A month is closed once it is balanced and checked by a second person, and any later change is made by reopening it on purpose, with a reason kept in the Audit Log.' },
  meApprove: { title: 'Approve and close', body: 'Someone whose role includes Approve month-end checks the figures and closes the month. It is never the person who prepared it, so every month is checked by two people.' },
  meKeptAs: { title: 'Money kept as', body: 'Cash: the month is balanced against the cash counted by two people. Bank account: against the closing balance on the bank statement. Change it if the church opens a bank account.' },
  meStart: { title: 'Start month', body: 'The first month balanced. Example: July 2026, the month the church started. It can change until that month is sent for approval.' },
  meStartOpening: { title: 'Opening balance', body: 'The money held on the first day of the start month. Example: BHD 0.00 if there was no money yet.' },
  monthendModule: { title: 'Approve month-end', body: 'Approve or send back a month that has been balanced, which closes it. The person who prepared a month can never approve it. The Finance Approver role has it, and it can be given to any role.' },
};

export type HelpTopicKey = keyof typeof HELP_TOPICS;
