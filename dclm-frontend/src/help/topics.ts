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
  shepherd: {
    title: 'Assigned shepherd',
    body: 'The worker responsible for checking on this person if they miss a service. When an absence is detected, the follow-up task goes to them automatically. Someone with no shepherd still gets a task, it just shows as Unassigned so it can be picked up.',
  },
  autoAssign: {
    title: 'How auto-assign decides',
    body: 'Two rules, in order. First, if someone else in the same household already has a shepherd, the same person is used so families are not split across different workers. Everyone else goes to whichever worker currently carries the fewest people. Only members in the Worker category can be shepherds. Nothing is saved until you review the proposed changes and press Apply.',
  },
  reassignEveryone: {
    title: 'Reassign everyone',
    body: 'By default auto-assign only fills in people who have no shepherd, so pairings someone chose deliberately are left alone. Reassign everyone ignores that and recalculates from scratch, which can move people who were paired on purpose. Useful when a worker leaves the church and their people need redistributing.',
  },
  absenceTracking: {
    title: 'Counts toward absence follow-up',
    body: 'When this is on, anyone not checked in to this meeting is treated as absent a few hours after it starts, and a follow-up task is created for their shepherd. Leave it off for meetings where attendance is not expected of everyone. No one needs to press anything, the check runs on its own.',
  },
  liveCheckIn: {
    title: 'Check-in vs headcount',
    body: 'These are two separate things and both are kept. The headcount on the session record stays the official attendance figure. Checking people in by name is what drives absence follow-up. Recording one does not change the other.',
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
    body: 'Switches which location you are viewing. Users tied to a single location only ever see that one. Administrators can switch between all of them, and All locations shows everything combined.',
  },
  newcomerStages: {
    title: 'Pipeline stages',
    body: 'New means registered and nobody has reached them yet. Contacted means someone has spoken to them. Attending means they have come to a service at least once, which check-in confirms. Member means they are on the member roll. Drag a card between columns, or use the dropdown on each card, which is the only way on a phone.',
  },
  qrForm: {
    title: 'QR form vs manual entry',
    body: 'Both collect the same information and both feed the same pipeline. The QR form is what a newcomer fills in themselves on their phone. Manual entry is for a worker typing in a paper card someone filled by hand.',
  },
  goalTracking: {
    title: 'Manual vs auto-tracked goals',
    body: 'Auto-tracked goals calculate themselves from real data already in the system, so there is nothing to update. Manual goals are ones no data can measure, so someone types in the current number as it changes.',
  },
};

export type HelpTopicKey = keyof typeof HELP_TOPICS;
