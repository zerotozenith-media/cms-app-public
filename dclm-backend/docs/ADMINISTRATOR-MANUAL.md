# Administrator Manual

For whoever runs this system for the church day to day. You do not need
to be technical. Where something genuinely needs a developer or the
server, it says so plainly.

The in-app **Help & Guide** covers how each person does their own job.
This covers the things only an administrator does.

---

## 1. Your first week: setting the church up

Do these in order. Later steps depend on earlier ones.

### Step 1: Locations

**Admin, Config Lists, Locations.**

Bahrain already exists and cannot be deleted, since it is the main
church. Add any other location the church runs in.

A location decides who sees what. A user tied to Bahrain sees only
Bahrain's members, attendance and giving. Leave a user's location blank
and they see everything.

### Step 2: Meeting types

**Admin, Meeting Types & Households.**

Add every regular meeting. For each one:

- **Name and day**, as the church actually calls it.
- **Detail level.** Choose *Detailed* if you count men, women, youth and
  children separately. Choose *Simple* if you only count men and women.
  The attendance form changes to match.
- **Counts toward absence follow-up.** See the warning below.

> **Get this switch right before adding members.**
> When it is on, anyone not checked in by name is treated as absent a
> few hours after the meeting starts, and a follow-up task is created
> for their shepherd. Switch it on for a meeting nobody is expected at,
> and you will bury your workers in tasks they will learn to ignore.
> Friday Worship is the usual one. Leave the rest off unless the church
> genuinely expects everyone.

A meeting also needs a **start time** for absence tracking to work. A
meeting with the switch on but no start time is simply never checked,
because there is nothing to measure "a few hours after" against.

### Step 3: Roles

**Admin, Users & Roles.**

A role is a set of permissions across seven areas: members, attendance,
newcomers, finance, goals, reports, and admin. For each area a role can
view, create, edit and delete, independently.

Suggested starting roles:

| Role | Give it |
|---|---|
| Administrator | Everything |
| Pastor / leadership | View on everything, edit on goals and reports |
| Attendance recorder | Attendance: view, create, edit. Members: view only |
| Shepherd / worker | Members: view and edit. Attendance: view |
| Follow-up team | Newcomers: view, create, edit. Members: view |
| Finance officer | Finance: view, create, edit. Nothing else |

**Give the narrowest role that lets someone do their job.** An
attendance recorder does not need to see giving figures, and the system
will hide them completely rather than merely discouraging access.

### Step 4: User accounts

**Admin, Users & Roles, Add user.**

For each person: name, email, password, role, and location.

Set a location for anyone who works at one location only. Leave it blank
for leadership who need to see everything.

Link each user to their member record where one exists. This matters:
the system uses the member record for their name, so an unlinked account
shows an email address on screens where a person's name belongs.

### Step 5: Members

**Members, Add member.**

For each person: name, contact details, category, joined date, and
household where they live with others.

**Categories** are General Member, Worker in Training, and Worker. Only
Workers can be shepherds, so set your workers correctly before the next
step.

**Households matter.** Linking family members to one household keeps
them with the same shepherd rather than being split between workers.

### Step 6: Shepherds

**Members, Auto-assign.**

Every member should have a shepherd: the worker who follows up if they
miss a service.

Press **Auto-assign** and the system proposes assignments. It shows every
proposed change with a reason:

- **Household** means someone in the same household already has that
  shepherd, so the family stays together.
- **Balanced load** means that worker currently carries the fewest
  people.

**Nothing is saved until you press Apply.** Read the list first. If it
looks wrong, press Cancel and assign people by hand instead, one at a
time on each member's profile, or several at once by ticking boxes in
the member list.

### Step 7: Goals

**Goals.**

A starter set already exists. Adjust the targets to what the church is
actually aiming for.

Goals marked **auto-tracked** calculate themselves from real records and
need no maintenance. **Manual** goals are ones no data can measure, so
someone types in the current figure as it changes.

### Step 8: The lists

**Admin, Config Lists.**

Funds, payment methods, expense categories, newcomer sources, milestone
types, services and departments are all editable, so the wording matches
how this church actually speaks.

Removing an item does not affect records that already reference it.

---

## 2. Things only you can do

### Adding someone to the team

Admin, Users & Roles, Add user. Choose the role first; it decides
everything they can see.

### Someone has left the church

**Do not delete them.** You lose their entire history: attendance,
giving, every follow-up visit. Leave the record in place.

If they were a **shepherd**, reassign their people first: Members,
Auto-assign, then **Reassign everyone instead**. Read the proposal
carefully, since this can move people who were paired deliberately.

If they had a **user account**, that is what to remove, so they can no
longer sign in.

### A worker is taking on more or fewer people

Members, tick the boxes next to the people to move, choose a shepherd
from the bar that appears, press Assign.

### Changing whether newcomers get auto-assigned

**Admin, Meeting Types & Households, Follow-up assignment.**

On by default. Turn it off if whoever meets a newcomer should keep them,
rather than the system spreading newcomers by workload.

### Checking who changed something

**Admin, Audit Log.**

Every significant action is recorded with who did it and when. Filter by
what kind of record you are interested in.

---

## 3. Monthly rhythm

**Weekly**
- Glance at Members, Follow-up. Anything red is more than three days
  overdue. Anything showing Unassigned has nobody responsible for it.
- Check Newcomers, Follow-up for the same.

**Monthly**
- Reports, generate the monthly report. It pulls the month's attendance,
  giving, newcomers and testimonies into one document.
- Goals, see where the church stands against its targets.
- Skim the audit log if anything looked unexpected.

**Occasionally**
- Review roles. People change jobs in the church; their access should
  follow.
- Review shepherd loads. If one worker has drifted into carrying far
  more than the rest, Auto-assign will even it out for anyone currently
  unassigned.

---

## 4. Questions you will be asked

**"Why can I not see Giving?"**
Their role does not include finance access. Deliberate, not a fault.
Change the role if they genuinely need it.

**"I stopped getting the follow-up emails."**
Either nothing was outstanding, which is normal since the digest is only
sent to people who actually have open follow-ups, or the scheduled job
has stopped. If nobody is receiving them at all, ask whoever runs the
server to check.

**"I did not get a follow-up task for someone who was absent."**
Three possible reasons, in order of likelihood: the meeting does not
have absence follow-up switched on; nobody checked people in by name
that week, so the system has no record of who was missing; or that
member already has an open follow-up, and the system does not stack a
second one on top.

**"Someone told us they would be away. Can I stop the task?"**
Not currently. The task is created and the shepherd closes it, recording
that the absence was already known. This is a known gap.

**"I marked a follow-up done but recorded it wrongly."**
Members, Follow-up, change the filter to **Completed only**, find the
record, press **Edit**. The original entries are pre-filled.

**"Two people have the same name."**
Fine, they are separate records. Tell them apart by household or joined
date. Adding a middle name in Other names helps.

**"Can I undo an auto-assign?"**
Not in one action. That is exactly why it shows you the proposal first.
Individual assignments can be changed afterwards on each profile.

---

## 5. Things that need a developer or server access

Be clear about these so you are not stuck trying to fix them from the
screens.

**Nothing is automatic yet after installation.** Two background jobs
must be scheduled on the server:

- The absence check, which creates follow-up tasks
- Recurring session creation, which makes each week's sessions appear

If follow-up tasks never appear, or sessions stop being created, the
scheduling has not been set up or has stopped. That is a server matter,
covered in the deployment runbook.

**Email notifications, if the church uses them.** Two more scheduled
jobs send shepherds a digest of their outstanding follow-ups the morning
after a service, and leadership a weekly summary on Monday. Nobody gets
an email per task, which would be unreadable within a week. If people
stop receiving them, that is a server matter rather than something to
fix from these screens.

**Also needing a developer:**
- Changing how long after a meeting the absence check runs (currently
  three hours) or how soon a follow-up is due (currently two days)
- Adding a new module or screen
- Restoring from backup
- Changing the domain

---

## 6. Protecting the records

The church's records are only as safe as the backups.

Ask whoever set the system up to confirm:
- Backups run automatically, every night
- They are copied somewhere other than the same server
- A restore has actually been tested, not just assumed

A backup that has never been restored is a guess, not a safeguard.

---

## 7. Good practice

**Give the narrowest role that works.** Access is easy to add later and
awkward to take back.

**Keep member records rather than deleting them.** History is the point.

**Read auto-assign proposals before applying.** It is quick, and it is
the only review step.

**Encourage real notes on follow-ups.** The four required fields stop
someone recording nothing at all, but they cannot make the content
useful. A worker who writes "visited, fine" has met the letter of it and
left the next person with nothing.

**Check the Unassigned count.** Anyone without a shepherd still
generates tasks, but with nobody attached to act on them.
