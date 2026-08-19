# DCLM Bahrain Church Management System
## Business Case and Objectives

**Audience:** church leadership, anyone deciding whether to fund, adopt
or extend this system, and any developer who wants to understand why it
works the way it does before changing it.

---

## 1. The problem

Deeper Christian Life Ministry Bahrain runs several weekly meetings
across more than one location. Before this system, the church's records
lived in a mix of paper slips, spreadsheets and individual memory. That
created four specific, recurring problems.

**People slipped away unnoticed.** Attendance was counted as a headcount
only, so the church knew how many came but not who. A member could stop
attending for a month before anyone noticed, and by then the reason for
leaving had often hardened into a decision.

**Follow-up depended on who remembered.** When someone was noticed
missing, whether anyone visited depended on a leader happening to think
of it. There was no shared list, no deadline, and no record afterward
that the visit had happened or what came out of it. Two workers could
visit the same person while a third person was missed entirely.

**Newcomer information was lost between the slip and the follow-up.** A
visitor filled in a paper card, ticked that they would like a visit, and
the card went into a drawer. Whether anything happened depended on
whoever collected the cards that week.

**Nobody could answer basic questions with confidence.** How many
members do we have? Is attendance growing? How many newcomers did we
integrate this year? How much came in, and what did we spend it on?
Each answer required someone to reconstruct it from scattered sources.

---

## 2. What this system is for

One place holding the church's records, structured so that pastoral care
happens by design rather than by memory.

The central idea: **the church already collects the information needed
to notice when someone is drifting. It just was not connected to
anything.** Recording attendance by name, rather than only as a number,
turns an existing weekly task into an early warning that reaches the
right person automatically.

---

## 3. Objectives

### 3.1 Nobody drifts away unnoticed

Attendance can be recorded by name during a service. A few hours after a
meeting the church has marked as one everyone is expected at, anyone not
checked in is treated as absent, and a follow-up task is created and
assigned to the worker responsible for that member.

No leader has to notice, remember, or press anything.

**Measured by:** open follow-ups, how many are overdue, and how many
have nobody assigned.

### 3.2 Every member has someone responsible for them

Each member is assigned a shepherd, a worker who follows up when they
miss a service. Assignment can be done one at a time, in bulk, or by
letting the system propose assignments: households stay with one
shepherd so families are not split between workers, and the rest are
spread evenly so nobody carries an unreasonable share.

**Measured by:** the count of members with no shepherd assigned.

### 3.3 Follow-up produces a record worth reading

A visit is not complete until the worker records four things: the goal
of the visit, the scripture shared, the root cause behind the absence,
and the next step agreed. All four are required.

This is deliberate and was debated. A tick with no record tells the next
person nothing. Requiring the four fields turns a completed task into
something a leader can act on months later, and turns the visit itself
from a social call into a purposeful one.

**Measured by:** follow-ups completed versus opened, and the quality of
what is recorded, which is now readable rather than absent.

### 3.4 Newcomers are followed up, not filed away

A newcomer either fills in a form on their own phone after scanning a QR
code, or a worker types their paper card into the same form. Either way
the details land in the same pipeline. If they ask for a visit, want to
know more, or want to know about being a Christian, the matching task is
created immediately with a deadline, and salvation requests get a
shorter one.

**Measured by:** newcomers contacted within the target window, and how
many progress from New through to Integrated.

### 3.5 The church can answer questions about itself

Attendance trends, giving by fund, expenses by category, newcomer
progress and membership growth are all derived from the same records
staff are already keeping. A monthly report can be produced without
anyone reconstructing figures.

**Measured by:** progress against the church's own goals, which the
system tracks automatically where the data allows.

### 3.6 Information reaches only the people who should see it

Giving figures are visible to those with finance responsibility and
nobody else. An attendance recorder sees attendance. This is enforced by
the system, not by convention: someone without finance access does not
see those figures anywhere, including on the dashboard, and cannot
retrieve them by typing a web address directly.

---

## 4. Who uses it

| Role | What they do | What they see |
|---|---|---|
| Usher / attendance recorder | Records who attended each meeting | Attendance, member names |
| Shepherd / worker | Follows up members who miss services | Their follow-up list, member profiles |
| Follow-up / care team | Contacts and tracks newcomers | Newcomer pipeline and tasks |
| Finance officer | Records giving and expenses | Giving, expenses, projects |
| Pastor / leadership | Reviews how the church is doing | Dashboard, goals, monthly reports |
| Administrator | Sets the system up and manages accounts | Everything |

One person often holds several of these. Roles are configurable, so the
church defines them to match how it actually works rather than adapting
to fixed categories.

---

## 5. Scope

### In scope
- Members, households and category progression
- Attendance: headcounts and named check-in
- Automatic absence detection and follow-up assignment
- Newcomer registration, pipeline and follow-up
- Giving, expenses and projects
- Goals, monthly reports, testimonies and weekly notes
- Users, roles, permissions and an audit log
- Multiple locations

### Deliberately out of scope
- **Sending messages.** The system creates tasks for people to act on.
  It does not send emails or texts on the church's behalf. Pastoral
  contact should come from a person.
- **Accounting.** Giving and expenses are recorded for the church's own
  understanding. This is not a bookkeeping package.
- **Public website.** Separate, and already exists.
- **Online giving.** Payments are recorded, not processed.

---

## 6. Decisions worth knowing

These shaped the system and were each chosen for a reason.

**A single missed service triggers follow-up, not two or three.** The
alternative was waiting for a pattern, but by then someone has been
absent a fortnight. The cost of an unnecessary phone call is far lower
than the cost of noticing too late.

**Only meetings the church marks are tracked.** Not every meeting is one
everyone is expected at. Tracking all of them would bury workers in
tasks and train them to ignore the list.

**Follow-up tasks do not stack.** If someone already has an open
follow-up, missing again does not create a second one. A worker facing
three near-identical tasks for the same person acts on none of them.

**Nothing is auto-assigned without review.** Auto-assign proposes
changes and shows why each one was chosen. Nothing is saved until an
administrator approves it, and by default it only fills people who have
no shepherd, so pairings someone chose deliberately are left alone.

**Headcounts and named check-in are both kept.** The headcount remains
the official attendance figure. Named check-in drives follow-up. One
does not overwrite the other, because they answer different questions.

**Records are not deleted when people leave.** A member who leaves keeps
their history. Deleting them would destroy the record of years of
pastoral work.

---

## 7. What still needs a person

The system is deliberately not autonomous about pastoral matters.

- It creates tasks; it does not contact anyone.
- It proposes shepherd assignments; a person approves them.
- It flags an absence; a person decides what that absence means.

There is currently no way to log a planned absence in advance, so
someone who has told the church they will be away still generates a
task. The shepherd closes it, recording that the absence was already
known. This is a known gap, listed for a future decision rather than
quietly worked around.

---

## 8. Success, one year in

- No member is absent for more than a fortnight without someone having
  reached out.
- Every member has a shepherd who knows they are responsible for them.
- A leader can read what happened on any past visit.
- Every newcomer who asked for contact received it, within the target.
- The church can state its attendance, giving and growth figures without
  reconstructing them.
- No one has seen figures their role should not show them.
