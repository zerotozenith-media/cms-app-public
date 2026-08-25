# DCLM Bahrain CMS: Outstanding Work Log

Last updated: 2026-08-24 (enquiries complete)

---

## SEQUENCE

### ✅ 1. Member Attendance Follow-up: demo (DONE, in working file)
- Live check-in screen (tap to check in, in-person/online toggle)
- Automatic absence detection (no "end service" button)
- Member follow-up tab with Open/Completed/All filter
- Newcomer follow-up tab (same pattern)
- Visitation logging with 4 required fields (Goal, Scripture, Root cause, Next step)
- Guidance block: "A follow-up should be purposeful, not just a chat"
- Edit + delete on completed records
- Admin: absence-tracking toggle per meeting type
- Manual Entry rebuilt with full intake-slip fields, name split
- Public QR form matching Manual Entry + church-appropriate welcome
- QR code redesigned to match approved DCLM design, embedded, verified scannable
- Name replaced (Chinedu Uguru → Daniel Adeyinka)
- Mobile overflow bug fixed (flex min-width) , verified at 390/360/320px

### ✅ 2. Shepherd assignment (DONE, in working file)
- Bulk assign via checkboxes
- Auto-assign: household first, then load balancing
- Preview-before-apply
- Only-unassigned by default, "reassign everyone" option
- Workers only as shepherds
- Admin toggle for including newcomers
- Applied to working file, regression tested desktop + mobile

### ✅ 3. Inline help tooltips (DONE, in working file)
- Clickable `?` icons, popup explanation, app-wide
- Candidates: auto-assign rules, reassign-everyone, absence toggle,
  shepherd field, 4 required follow-up fields, detail level,
  location scoping, check-in vs headcount
- 11 topics in one central dictionary; 9 markers placed
- Popup clears when navigating away

### ✅ 4. Help section (DONE, in working file)
- New nav item, comprehensive written guide
- 9 sections, searchable across all content, results tagged by section
- Visible to every role; mobile-friendly (section list becomes a scroll strip)

### ✅ 5. Real implementation: backend (DONE)
- Delivered UNAPPROVED earlier (dclm-backend-member-followup-UNAPPROVED.zip),
  205 tests passing, but built ahead of demo approval
- Will need revision to match where demo landed since
- Plus: bulk/auto-assign endpoints, tooltips/help content if server-driven

### ✅ 6. Real implementation: frontend (DONE)
- React equivalents of everything above
- None started

### ⬜ 7. Scheduling setup (Phase 5)
- `check_absences` command exists and is tested; nothing runs it yet
- Cost order: plain cron (free, recommended) > GitHub Actions >
  Azure Function > managed cron service
- Write instructions cron-first, not Azure-by-default

### ⬜ 8. Phase 4.4: UAT with real church staff
- Needs real people; cannot be done by me

### ⬜ 9. Phase 5: deployment
- Human-executed. My part: IaC, CI/CD config, production settings, runbook

---

## OPEN DECISIONS / DEFAULTS I CHOSE (change if wrong)
- Absence check fires **3 hours** after meeting start time
- Follow-up task due **2 days** after the missed service
- "Less busy" = count of people shepherded (not open task count)
- Only Friday Worship counts for absence by default

## ALSO DONE
- All 51 em dashes removed from the app, replaced contextually
  (en dash for empty cells, middot for separators, rewritten sentences)

### Online Enquiries (DONE, backend + frontend + docs)
- Separate pipeline for people who contacted the church online but have
  not attended. Converts to a Newcomer once they do, keeping the link so
  "how many online enquiries became members" stays answerable.
- Campaign and spend tracking behind an `outreach` permission: which
  advert produced people in the room, and what each cost. Hidden from
  follow-up workers entirely.

## POST GO-LIVE (agreed to defer)
- SECURE_HSTS_PRELOAD: turn on once live on HTTPS for a few weeks and
  stable. One line in config/settings/production.py. Deferred because
  preload submission is slow to reverse if anything goes wrong.

## KNOWN GAPS NOT YET RAISED
- No way to mark a **known/communicated absence** (travel, illness) to
  suppress the auto-task , deliberately deferred, worth deciding later
- No bulk assign for Newcomers (members only)
