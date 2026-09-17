"""Strict scalar normalization shared by independent legacy oracles."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


CANONICAL_MONEY = re.compile(
    r"-?(?:0|[1-9][0-9]*)\.[0-9]{2}"
)


def canonical_money(value: object) -> str | None:
    """Return an exact scale-two money lexeme or reject it.

    Oracles compare observations; they must never repair observations by
    rounding, padding, accepting binary floats, or normalizing negative zero.
    PostgreSQL NUMERIC values and JSON/YAML strings are accepted only when
    their textual form is already canonical.
    """

    if isinstance(value, Decimal):
        lexeme = str(value)
    elif isinstance(value, str):
        lexeme = value
    else:
        return None
    if (
        CANONICAL_MONEY.fullmatch(lexeme) is None
        or lexeme == "-0.00"
    ):
        return None
    try:
        amount = Decimal(lexeme)
    except InvalidOperation:
        return None
    if not amount.is_finite():
        return None
    return lexeme
