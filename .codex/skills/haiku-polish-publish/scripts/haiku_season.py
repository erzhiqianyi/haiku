#!/usr/bin/env python3
from datetime import date


SEASONS = ("春", "夏", "秋", "冬")


def season_for_date(value):
    """Return the Japanese haiku season for an ISO calendar date.

    The fixed boundaries approximate the traditional starts of spring,
    summer, autumn, and winter while keeping generation deterministic.
    """
    parsed = date.fromisoformat(str(value))
    month_day = (parsed.month, parsed.day)
    if (2, 4) <= month_day <= (5, 5):
        return "春"
    if (5, 6) <= month_day <= (8, 7):
        return "夏"
    if (8, 8) <= month_day <= (11, 6):
        return "秋"
    return "冬"


def validate_poem_season(poem):
    expected = season_for_date(poem.get("date"))
    actual = poem.get("season")
    if actual != expected:
        raise ValueError(
            f"season must match the poem date for {poem.get('date')}: "
            f"expected {expected}, found {actual!r}"
        )
    return expected
