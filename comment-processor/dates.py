import calendar
import re
from datetime import datetime, timedelta, timezone

from dateutil.relativedelta import FR, MO, TH, relativedelta

# TODO if the format %b %d occurs in the past, its year gets set to the current year
# instead of the next year. %b works, its only %b %d. %m %d doesnt matter since that
# format is most likely someone actually talking about a past trade, but %b %d is
# highly likely to indicate a future trade so needs fixed somehow.

PROPER_FORMAT = "%Y-%m-%d"


# Generates static keyword mappings based on the comment's timestamp
def get_static_mappings(base_datetime):
    # End of week means Friday: the last trading day, when weekly options expire
    days_until_end_of_week = (4 - base_datetime.weekday() + 7) % 7  # Friday = 4
    end_of_week = base_datetime + timedelta(days=days_until_end_of_week)
    next_week_start = base_datetime + relativedelta(weekday=MO(+1))
    next_week_end = base_datetime + relativedelta(weeks=1, weekday=FR)
    middle_of_week = base_datetime + timedelta(days=2 - base_datetime.weekday())
    tomorrow = base_datetime + timedelta(days=1)
    holidays = {
        "new year's day": datetime(base_datetime.year, 1, 1),
        "independence day": datetime(base_datetime.year, 7, 4),
        "christmas": datetime(base_datetime.year, 12, 25),
        # 4th Thursday of November
        "thanksgiving": datetime(base_datetime.year, 11, 1) + relativedelta(weekday=TH(+4)),
        # Last Monday in May
        "memorial day": datetime(base_datetime.year, 5, 31) + relativedelta(weekday=0, days=-7),
        # 1st Monday in September
        "labor day": datetime(base_datetime.year, 9, 1) + relativedelta(weekday=MO(+1)),
    }
    holidays["black friday"] = holidays["thanksgiving"] + timedelta(days=1)
    holidays["christmas eve"] = holidays["christmas"] + timedelta(days=-1)

    end_of_month = (base_datetime + relativedelta(day=31)).strftime(PROPER_FORMAT)
    list_of_keywords = {
        "eoy": base_datetime.strftime("%Y-12-31"),
        "end of year": base_datetime.strftime("%Y-12-31"),
        "eom": end_of_month,
        "end of month": end_of_month,
        "eod": base_datetime.strftime(PROPER_FORMAT),
        "end of day": base_datetime.strftime(PROPER_FORMAT),
        "0dte": base_datetime.strftime(PROPER_FORMAT),
        "0dtes": base_datetime.strftime(PROPER_FORMAT),
        "today": base_datetime.strftime(PROPER_FORMAT),
        "tonight": base_datetime.strftime(PROPER_FORMAT),
        "tomorrow": tomorrow.strftime(PROPER_FORMAT),
        "this week": middle_of_week.strftime(PROPER_FORMAT),
        "weekly": end_of_week.strftime(PROPER_FORMAT),
        "eow": end_of_week.strftime(PROPER_FORMAT),
        "eotw": end_of_week.strftime(PROPER_FORMAT),
        "end of the week": end_of_week.strftime(PROPER_FORMAT),
        "eotw next week": next_week_end.strftime(PROPER_FORMAT),
        "end of week": end_of_week.strftime(PROPER_FORMAT),
        "next week": next_week_start.strftime(PROPER_FORMAT),
        "spring": base_datetime.strftime("%Y-03-20"),
        "summer": base_datetime.strftime("%Y-06-21"),
        "fall": base_datetime.strftime("%Y-09-23"),
        "winter": base_datetime.strftime("%Y-12-21"),
        "new year's day": holidays["new year's day"].strftime(PROPER_FORMAT),
        "new year's": holidays["new year's day"].strftime(PROPER_FORMAT),
        "new year": holidays["new year's day"].strftime(PROPER_FORMAT),
        "next year": holidays["new year's day"].strftime(PROPER_FORMAT),
        "new years": holidays["new year's day"].strftime(PROPER_FORMAT),
        "independence day": holidays["independence day"].strftime(PROPER_FORMAT),
        "christmas": holidays["christmas"].strftime(PROPER_FORMAT),
        "thanksgiving": holidays["thanksgiving"].strftime(PROPER_FORMAT),
        "memorial day": holidays["memorial day"].strftime(PROPER_FORMAT),
        "labor day": holidays["labor day"].strftime(PROPER_FORMAT),
        "black friday": holidays["black friday"].strftime(PROPER_FORMAT),
        "christmas eve": holidays["christmas eve"].strftime(PROPER_FORMAT),
    }
    # monday-sunday
    list_of_weekdays = {
        (base_datetime + timedelta(days=i)).strftime("%A").lower(): (
            base_datetime + timedelta(days=i)
        ).strftime(PROPER_FORMAT)
        for i in range(7)
    }

    return list_of_keywords, list_of_weekdays


# Handles relative date keywords like "3 days", "2 weeks", "1 month", etc.
def parse_relative_date(date_string, base_datetime):
    pattern = r"(\d+)\s*(hours?|days?|weeks?|months?|years?)"
    match = re.match(pattern, date_string, re.IGNORECASE)
    if not match:
        return None
    value = int(match.group(1))
    unit = match.group(2).lower().rstrip("s")
    if unit == "hour":
        return base_datetime
    if unit == "day":
        return base_datetime + timedelta(days=value)
    if unit == "week":
        return base_datetime + timedelta(weeks=value)
    if unit == "month":
        return base_datetime + relativedelta(months=value)
    if unit == "year":
        return base_datetime + relativedelta(years=value)
    return None


MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

DATE_FORMATS = [
    "%m %d %y",
    "%m %d",
    "%m %Y",
    "%m %y",
    "%b %d",
    "%B %d",
    "%d %b",
    "%d %B",
    "%d %m",
    "%m %Y %d",
    "%b %Y %d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%b %d %Y",
    "%b %d %y",
    "%B %d %Y",
    "%B %d %y",
    "%B %d '%y",
    "%Y-%m-%d",
    "%m-%d-%Y",
    "%Y/%m/%d",
    "%Y %m %d",
    "%m/%d/%Y",
    "%B %Y",
    "%b %Y",
    "%b",
    "%B",
    "%Y",
    "%m%d%Y",
    "%b%d%Y",
    "%b%Y",
    "%b%d %y",
    "%b%d %Y",
    "%d%b%y",
    "%d %b %y",
    "%d %b %Y",
    "%b'%y",
    "%B'%y",
    "%b '%y",
]


def parse_specific_date_format(date_string, base_datetime):
    # normalize separators & strip ordinals
    s = date_string.replace("/", " ").replace("-", " ")
    s = re.sub(r"[‘’`]", "'", s)
    s = re.sub(r"[,\.\"]", " ", s)
    s = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    s = re.sub(r"\bsept\b", "sep", s)

    # "jan 17 '26"
    m = re.fullmatch(r"([a-z]+)\s+(\d{1,2})\s*'(\d{2})", s)
    if m:
        mon_abbr, day, yy = m.groups()
        month = MONTHS.get(mon_abbr)
        if month:
            return datetime(2000 + int(yy), month, int(day))

    # "jan '26" -> third Friday of that month (standard options expiry)
    m = re.fullmatch(r"([a-z]+)\s*'(\d{2})", s)
    if m:
        mon_abbr, yy = m.groups()
        month = MONTHS.get(mon_abbr)
        if month:
            return datetime(2000 + int(yy), month, 1) + relativedelta(weekday=FR(3))

    # "1/17/26" style with slashes intact
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", date_string)
    if m:
        mo_str, da_str, yr_str = m.groups()
        yr = int(yr_str)
        if yr < 100:
            yr += 2000
        mo, da = int(mo_str), int(da_str)
        # if we somehow got an invalid month, assume the user meant day/month/year and swap
        if mo < 1 or mo > 12:
            mo, da = da, mo
        # clamp into valid ranges
        mo = max(1, min(mo, 12))
        last_day = calendar.monthrange(yr, mo)[1]
        da = max(1, min(da, last_day))
        return datetime(yr, mo, da)

    # "jan 17" / "jan 17 '26"
    m = re.match(r"^([a-z]+)\s*(\d{1,2})(?:st|nd|rd|th)?(?:'(\d{2}))?$", s)
    if m:
        mon, day, yy = m.groups()
        month = MONTHS.get(mon)
        if month:
            year = base_datetime.year if yy is None else 2000 + int(yy)
            day_int = min(int(day), calendar.monthrange(year, month)[1])
            return datetime(year, month, day_int)

    # bare month name -> third Friday, rolling to next year if the month has passed
    if s in MONTHS:
        year = base_datetime.year
        if MONTHS[s] < base_datetime.month or (
            MONTHS[s] == base_datetime.month and base_datetime.day > 21
        ):
            year += 1
        return datetime(year, MONTHS[s], 1) + relativedelta(weekday=FR(3))

    for date_format in DATE_FORMATS:
        try:
            if date_format == "%Y":
                return datetime.strptime(s, date_format).replace(month=1, day=1)
            elif date_format in ("%b", "%B"):
                dt = datetime.strptime(f"{s} {base_datetime.year}", f"{date_format} %Y")
                return dt.replace(day=1) + relativedelta(weekday=FR(3))
            elif date_format in ("%b %Y", "%B %Y", "%m %y", "%m %Y"):
                dt = datetime.strptime(s, date_format)
                return dt.replace(day=1) + relativedelta(weekday=FR(3))
            elif "%y" not in date_format and "%Y" not in date_format:
                return datetime.strptime(f"{s} {base_datetime.year}", f"{date_format} %Y")
            else:
                return datetime.strptime(s, date_format)
        except ValueError:
            continue

    return None


# Turns an extracted date phrase into YYYY-MM-DD relative to when the comment was written
def date_formatter(comment_timestamp, keyword):
    comment_utc_datetime = datetime.fromtimestamp(comment_timestamp, tz=timezone.utc)
    keyword = keyword.lower()
    list_of_keywords, list_of_weekdays = get_static_mappings(comment_utc_datetime)

    if keyword in list_of_keywords:
        return list_of_keywords[keyword]

    if keyword in list_of_weekdays:
        return list_of_weekdays[keyword]

    relative_date = parse_relative_date(keyword, comment_utc_datetime)
    if relative_date:
        return relative_date.strftime(PROPER_FORMAT)

    specific_date = parse_specific_date_format(keyword, comment_utc_datetime)
    if specific_date:
        return specific_date.strftime(PROPER_FORMAT)

    if keyword != "":
        print(f"keyword not found: {keyword}")
    return ""
