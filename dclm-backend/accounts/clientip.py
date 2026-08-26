"""
Working out the caller's IP address, in one place.

Both the login endpoint and the public registration form log the IP they
were called from, and both store it in a GenericIPAddressField. On
PostgreSQL that is an `inet` column, which rejects anything that is not
a bare address.

Azure App Service puts the source PORT in X-Forwarded-For, so the header
reads "102.91.5.47:152" rather than "102.91.5.47". Passing that straight
through raised a DataError and turned every affected request into a 500.
It never showed in development because SQLite stores the column as text
and validates nothing.

So the port is stripped here, and anything still unparseable falls back
to a placeholder rather than taking the request down with it. Logging an
imperfect address is a far smaller problem than refusing a visitor who
is trying to register.
"""
import ipaddress

FALLBACK = "0.0.0.0"


def _clean(candidate):
    """Return a bare IP address, or None if this cannot be one."""
    if not candidate:
        return None
    value = candidate.strip()

    # IPv6 with a port, as "[2001:db8::1]:443". Brackets are also valid
    # without a port.
    if value.startswith("["):
        value = value[1:].split("]")[0]
    elif value.count(":") == 1:
        # Exactly one colon means IPv4 with a port. Bare IPv6 always has
        # more than one, so this cannot strip a real address by mistake.
        value = value.rsplit(":", 1)[0]

    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return None


def get_client_ip(request):
    """
    The caller's address, safe to store in an inet column.

    X-Forwarded-For may hold a chain of proxies. The first entry is the
    original client, which is the one worth recording.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    for candidate in forwarded.split(","):
        cleaned = _clean(candidate)
        if cleaned:
            return cleaned

    return _clean(request.META.get("REMOTE_ADDR")) or FALLBACK
