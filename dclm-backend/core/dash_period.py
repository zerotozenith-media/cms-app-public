"""
The dashboard's periods and what each is compared with (Dashboard
redesign, approved 10 November 2026).

Periods: This month, Quarter, Year to date and Last year follow the
financial year in Settings. More offers Last month, a year and a range of
months.

Comparison, per period:
  1. The same days a year earlier, once every one of those months is on or
     after "Records start" in Settings (July 2026 at first).
  2. Otherwise the period just before, of the same length and to the same
     day: 1 to 10 November against 1 to 10 October.
  3. Otherwise nothing ("No earlier figure"), because the earlier months
     have no records and a comparison with nothing would be misleading.
"""
import calendar
import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core import settings_store

LABELS = {"this_month": "This month", "this_quarter": "This quarter", "this_year": "Year to date",
          "last_year": "Last year", "last_month": "Last month"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def add_months(d, n):
    """The same day n months later (or earlier), kept inside the month."""
    i = d.year * 12 + d.month - 1 + n
    y, m = i // 12, i % 12 + 1
    return datetime.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def month_end(d):
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def fiscal_start(today):
    end_month = settings_store.get("finance_year_end_month")
    start_month = end_month % 12 + 1
    year = today.year if today.month >= start_month else today.year - 1
    return datetime.date(year, start_month, 1)


def _whole_months(start, end):
    return start.day == 1 and end == month_end(end)


def span_label(start, end):
    """"October 2026", "July to September 2026", "1 to 10 November 2026"."""
    if _whole_months(start, end):
        if (start.year, start.month) == (end.year, end.month):
            return f"{MONTHS[start.month - 1]} {start.year}"
        if start.year == end.year:
            return f"{MONTHS[start.month - 1]} to {MONTHS[end.month - 1]} {end.year}"
        return f"{MONTHS[start.month - 1]} {start.year} to {MONTHS[end.month - 1]} {end.year}"
    if (start.year, start.month) == (end.year, end.month):
        return f"{start.day} to {end.day} {MONTHS[end.month - 1]} {end.year}"
    if start.year == end.year:
        return f"{start.day} {MONTHS[start.month - 1]} to {end.day} {MONTHS[end.month - 1]} {end.year}"
    return f"{start.day} {MONTHS[start.month - 1]} {start.year} to {end.day} {MONTHS[end.month - 1]} {end.year}"


def resolve(params, today=None):
    """{key, label, start, end, step, span} for the period asked for.
    step is the number of months the period before lies back."""
    today = today or timezone.localdate()
    key = params.get("period") or settings_store.get("dashboard_opens_on")
    this = today.replace(day=1)
    first_year = settings_store.records_start().year
    if key == "this_month":
        start, end, step = this, today, 1
    elif key == "last_month":
        start = add_months(this, -1)
        start, end, step = start, month_end(start), 1
    elif key in ("this_quarter", "this_year", "last_year"):
        fs = fiscal_start(today)
        if key == "this_year":
            start, end, step = fs, today, 12
        elif key == "last_year":
            start = add_months(fs, -12)
            start, end, step = start, month_end(add_months(fs, -1)), 12
        else:
            gone = (this.year * 12 + this.month) - (fs.year * 12 + fs.month)
            start, end, step = add_months(fs, gone - gone % 3), today, 3
    elif key == "year":
        try:
            year = int(params.get("year"))
        except (TypeError, ValueError):
            raise ValidationError({"year": f"Choose a year from {first_year}."})
        if not first_year <= year <= today.year:
            raise ValidationError({"year": f"Choose a year from {first_year} to {today.year}."})
        start = datetime.date(year, 1, 1)
        end = min(datetime.date(year, 12, 31), today)
        step = 12
    elif key == "range":
        def month(k):
            text = str(params.get(k) or "")
            try:
                if len(text) != 7 or text[4] != "-":
                    raise ValueError
                return datetime.date(int(text[:4]), int(text[5:7]), 1)
            except ValueError:
                raise ValidationError({k: "Choose a month, for example 2026-09."})
        start, last = month("from"), month("to")
        if last < start:
            raise ValidationError({"to": "The last month comes before the first."})
        rs = settings_store.records_start()
        if start < rs or last > this:
            raise ValidationError({"to": f"Choose months from {MONTHS[rs.month - 1]} {rs.year} to this month."})
        end = min(month_end(last), today)
        step = (last.year * 12 + last.month) - (start.year * 12 + start.month) + 1
    else:
        raise ValidationError({"period": "Choose This month, Quarter, Year to date, Last year, Last month, "
                                         "a year or a range of months."})
    label = LABELS.get(key) or (str(start.year) if key == "year" else span_label(start, end))
    return {"key": key, "label": label, "start": start, "end": end, "step": step,
            "span": span_label(start, end)}


def comparison(p):
    """(start, end, label, kind) of what the period is compared with, or
    None. kind is "year" (a year earlier) or "before" (the period before)."""
    rs = settings_store.records_start()
    ys, ye = add_months(p["start"], -12), add_months(p["end"], -12)
    if ys >= rs:
        return ys, ye, span_label(ys, ye), "year"
    if p["step"] != 12:
        bs, be = add_months(p["start"], -p["step"]), add_months(p["end"], -p["step"])
        if p["end"] == month_end(p["end"]):
            be = month_end(be)
        if bs >= rs:
            return bs, be, span_label(bs, be), "before"
    return None


def chart_months(p):
    """The months a by-month chart shows: the period's, or for a period
    under 3 months, up to 12 months ending with it. Never before Records
    start, since those months have no records."""
    rs = settings_store.records_start()
    first = p["start"].replace(day=1)
    last = p["end"].replace(day=1)
    n = (last.year * 12 + last.month) - (first.year * 12 + first.month) + 1
    if n < 3:
        first = add_months(last, -11)
    first = max(first, rs)
    out, m = [], first
    while m <= last:
        out.append(m)
        m = add_months(m, 1)
    return out or [last]
