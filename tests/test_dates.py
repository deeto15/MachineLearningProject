from datetime import datetime, timezone

from dates import date_formatter

# Sunday 2026-07-19 12:00 UTC
SUNDAY = int(datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc).timestamp())
# Friday 2026-07-24 12:00 UTC
FRIDAY = int(datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc).timestamp())


def test_eow_is_friday_not_saturday():
    # regression: weekly options expire Friday; this used to resolve to Saturday
    assert date_formatter(SUNDAY, "eow") == "2026-07-24"
    assert date_formatter(SUNDAY, "weekly") == "2026-07-24"


def test_eow_on_a_friday_is_same_day():
    assert date_formatter(FRIDAY, "eow") == "2026-07-24"


def test_0dte_is_same_day():
    assert date_formatter(FRIDAY, "0dte") == "2026-07-24"


def test_tomorrow():
    assert date_formatter(SUNDAY, "tomorrow") == "2026-07-20"


def test_weekday_name_rolls_forward():
    assert date_formatter(SUNDAY, "friday") == "2026-07-24"


def test_slash_date():
    assert date_formatter(SUNDAY, "7/31") == "2026-07-31"


def test_month_day():
    assert date_formatter(SUNDAY, "jan 17") == "2026-01-17"


def test_end_of_month():
    assert date_formatter(SUNDAY, "eom") == "2026-07-31"


def test_unknown_keyword_returns_empty():
    assert date_formatter(SUNDAY, "whenever moon") == ""
