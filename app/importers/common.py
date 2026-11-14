"""Helpers shared by the exchange parsers"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.importers import ImportFormatError


def to_decimal(text, line, column):
    """'1,234.50', '$1,234.50', '-$5', '(5.00)' -> Decimal. Empty -> None."""
    raw = (text or '').strip()
    if raw == '':
        return None
    negative = raw.startswith('-') or (raw.startswith('(') and raw.endswith(')'))
    cleaned = raw.strip('()').lstrip('-').replace(',', '').replace(' ', '')
    cleaned = cleaned.lstrip('$€£')
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ImportFormatError(f'line {line}: "{raw}" in column "{column}" is not a number') from None
    if not value.is_finite():
        raise ImportFormatError(f'line {line}: "{raw}" in column "{column}" is not a number')
    return -value if negative else value


def to_datetime(text, line, column):
    """Exchange timestamps -> naive UTC datetime.

    Accepts '2024-01-05 14:03:21', '2024-01-05 14:03:21.1234', '2024-01-15 10:30:00 UTC',
    '2023-06-01T14:00:00Z' and ISO strings with an offset.
    """
    raw = (text or '').strip()
    value = raw[:-4] if raw.endswith(' UTC') else raw
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ImportFormatError(f'line {line}: "{raw}" in column "{column}" is not a date and time') from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0)
