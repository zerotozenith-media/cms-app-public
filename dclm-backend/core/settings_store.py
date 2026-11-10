"""
Church settings with a type and a default (Dashboard redesign, approved
10 November 2026). They live in AppSetting, so an Administrator changes
them in Admin, Settings and nothing is fixed in code.
"""
import datetime
from decimal import Decimal, InvalidOperation

PERIOD_CHOICES = ("this_month", "this_quarter", "this_year", "last_year")

# key: (default, kind, label for messages)
DEFINITIONS = {
    "finance_year_end_month": (12, "month", "Financial year ends in"),
    "records_start": ("2026-07", "yearmonth", "Records start"),
    "receipt_flag_over": ("25", "money", "Flag expenses with no receipt over"),
    "dashboard_opens_on": ("this_month", "period", "The dashboard opens on"),
    "two_step_remember_days": (30, "days", "Remember a device for"),
}


def clean(key, value):
    """The value to store, or a ValueError with words for the person."""
    default, kind, label = DEFINITIONS[key]
    if kind == "month":
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{label}: choose a month.")
        if not 1 <= n <= 12:
            raise ValueError(f"{label}: choose a month from January to December.")
        return str(n)
    if kind == "yearmonth":
        text = str(value or "")
        try:
            d = datetime.date(int(text[:4]), int(text[5:7]), 1)
            if len(text) != 7 or text[4] != "-":
                raise ValueError
        except ValueError:
            raise ValueError(f"{label}: choose a month, for example 2026-07.")
        if d.year < 2000 or d > datetime.date.today().replace(day=1):
            raise ValueError(f"{label}: choose a month from January 2000 to this month.")
        return text
    if kind == "money":
        try:
            n = Decimal(str(value))
        except (InvalidOperation, TypeError):
            raise ValueError(f"{label}: type an amount, for example 25.")
        if n < 0 or n > Decimal("1000000"):
            raise ValueError(f"{label}: type an amount from 0 to 1,000,000.")
        return str(n.quantize(Decimal("0.01")))
    if kind == "period":
        if value not in PERIOD_CHOICES:
            raise ValueError(f"{label}: choose This month, Quarter, Year to date or Last year.")
        return value
    if kind == "days":
        try:
            n = int(value)
        except (TypeError, ValueError):
            raise ValueError(f"{label}: type a number of days.")
        if not 0 <= n <= 90:
            raise ValueError(f"{label}: type a number from 0 to 90.")
        return str(n)
    raise ValueError(f"Unknown setting {key}.")


def _raw(key):
    from core.models import AppSetting
    row = AppSetting.objects.filter(key=key).first()
    return row.value if row else None


def get(key):
    default, kind, _ = DEFINITIONS[key]
    raw = _raw(key)
    if raw is None:
        raw = default
    try:
        v = clean(key, raw) if kind != "yearmonth" else str(raw)
    except ValueError:
        v = clean(key, default) if kind != "yearmonth" else default
    if kind in ("month", "days"):
        return int(v)
    if kind == "money":
        return Decimal(v)
    return v


def all_values():
    out = {}
    for key, (_, kind, _) in DEFINITIONS.items():
        v = get(key)
        out[key] = str(v) if kind == "money" else v
    return out


def set_value(key, value):
    from core.models import AppSetting
    v = clean(key, value)
    AppSetting.objects.update_or_create(key=key, defaults={"value": v})
    return v


def records_start():
    text = get("records_start")
    try:
        return datetime.date(int(text[:4]), int(text[5:7]), 1)
    except (TypeError, ValueError):
        return datetime.date(2026, 7, 1)
