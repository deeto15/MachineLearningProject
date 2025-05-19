import re
from datetime import datetime, timedelta, timezone

from dateutil.relativedelta import FR, MO, TH, relativedelta
# TODO formatter is still missing some formats, mainly sanitization of strings (feb. or 20th. where periods are used) or just missed %%% formats that I haven't seen yet


# Function to generate static mappings based on the comment's timestamp
def get_static_mappings(base_datetime):
    # Calculate the end of the week (Saturday)
    days_until_end_of_week = (5 - base_datetime.weekday() + 7) % 7  # Saturday = 5
    end_of_week = base_datetime + timedelta(days=days_until_end_of_week)
    next_week_start = base_datetime + relativedelta(weekday=MO(+1))
    next_week_end = base_datetime + relativedelta(weeks=1, weekday=FR)
    middle_of_week = base_datetime + timedelta(days=2 - base_datetime.weekday())
    tomorrow = base_datetime + timedelta(days=1)
    holidays = {
        "new year's day": datetime(base_datetime.year, 1, 1),
        "independence day": datetime(base_datetime.year, 7, 4),
        "christmas": datetime(base_datetime.year, 12, 25),
        "thanksgiving": (
            datetime(base_datetime.year, 11, 1) + relativedelta(weekday=TH(+4))
        ),  # 4th Thursday of November
        "memorial day": (
            datetime(base_datetime.year, 5, 31) + relativedelta(weekday=0, days=-7)
        ),  # Last Monday in May
        "labor day": datetime(base_datetime.year, 9, 1)
        + relativedelta(weekday=MO(+1)),  # 1st Monday in September
    }

    holidays["black friday"] = holidays["thanksgiving"] + timedelta(days=1)
    holidays["christmas eve"] = holidays["christmas"] + timedelta(days=-1)

    list_of_keywords = {
        "eoy": base_datetime.strftime("12/31/%Y"),  # End of the year
        "end of year": base_datetime.strftime("12/31/%Y"),
        "eom": (base_datetime + relativedelta(day=31)).strftime(
            "%m/%d/%Y"
        ),  # End of the month
        "end of month": (base_datetime + relativedelta(day=31)).strftime("%m/%d/%Y"),
        "eod": base_datetime.strftime("%m/%d/%Y"),  # End of the day
        "end of day": base_datetime.strftime("%m/%d/%Y"),
        "today": base_datetime.strftime("%m/%d/%Y"),
        "tomorrow": tomorrow.strftime("%m/%d/%Y"),
        "this week": middle_of_week.strftime("%m/%d/%Y"),
        "weekly": end_of_week.strftime("%m/%d/%Y"),
        "eow": end_of_week.strftime("%m/%d/%Y"),  # End of the week
        "eotw": end_of_week.strftime("%m/%d/%Y"),  # End of the week
        "end of the week": end_of_week.strftime("%m/%d/%Y"),  # End of the week
        "eotw next week": next_week_end.strftime("%m/%d/%Y"),  # End of the week
        "end of week": end_of_week.strftime("%m/%d/%Y"),
        "next week": next_week_start.strftime("%m/%d/%Y"),
        "spring": base_datetime.strftime("03/20/%Y"),  # Start of spring
        "summer": base_datetime.strftime("06/21/%Y"),  # Start of summer
        "fall": base_datetime.strftime("09/23/%Y"),  # Start of fall
        "winter": base_datetime.strftime("12/21/%Y"),
        "new year's day": holidays["new year's day"].strftime("%m/%d/%Y"),
        "new year's": holidays["new year's day"].strftime("%m/%d/%Y"),
        "new year": holidays["new year's day"].strftime("%m/%d/%Y"),
        "next year": holidays["new year's day"].strftime("%m/%d/%Y"),
        "new years": holidays["new year's day"].strftime("%m/%d/%Y"),
        "independence day": holidays["independence day"].strftime("%m/%d/%Y"),
        "christmas": holidays["christmas"].strftime("%m/%d/%Y"),
        "thanksgiving": holidays["thanksgiving"].strftime("%m/%d/%Y"),
        "memorial day": holidays["memorial day"].strftime("%m/%d/%Y"),
        "labor day": holidays["labor day"].strftime("%m/%d/%Y"),
        "black friday": holidays["black friday"].strftime("%m/%d/%Y"),
        "christmas eve": holidays["christmas eve"].strftime("%m/%d/%Y"),
    }
    # monday-sunday
    list_of_weekdays = {
        (base_datetime + timedelta(days=i)).strftime("%A").lower(): (
            base_datetime + timedelta(days=i)
        ).strftime("%m/%d/%Y")
        for i in range(7)
    }

    return list_of_keywords, list_of_weekdays


# Function to handle relative date keywords like "3d", "2w", "1m", etc.
def parse_relative_date(date_string, base_datetime):
    pattern = r"(\d+)\s*(hours?|days?|weeks?|months?|years?)"
    match = re.match(pattern, date_string, re.IGNORECASE)
    if match:
        value = int(match.group(1))
        unit = match.group(2).lower()
        if unit in ["hour", "hours"]:  # Weeks
            return base_datetime
        elif unit in ["day", "days"]:  # Days
            return base_datetime + timedelta(days=value)
        elif unit in ["week", "weeks"]:  # Weeks
            return base_datetime + timedelta(weeks=value)
        elif unit in ["month", "months"]:  # Months
            return base_datetime + relativedelta(months=value)
        elif unit in ["year", "years"]:  # Years
            return base_datetime + relativedelta(years=value)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")
    return None


def parse_specific_date_format(date_string, base_datetime):
    normalized_date_string = date_string.replace("-", " ").replace("/", " ")
    normalized_date_string = re.sub(
        r"(\d+)(st|nd|rd|th)\b", r"\1", normalized_date_string
    )

    # Check for month-only inputs (e.g. "aug" or "august")
    months = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "sept": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }
    s = normalized_date_string.strip().lower()
    if s in months:
        year = base_datetime.year
        # if the month has already passed this year, roll to next year
        if months[s] < base_datetime.month or (
            months[s] == base_datetime.month and base_datetime.day > 21
        ):
            year += 1
        dt = datetime(year, months[s], 1)
        third_friday = dt + relativedelta(weekday=FR(3))
        return third_friday

    date_formats = [
        "%m %d %y",
        "%m %d",
        "%b %d",
        "%b%d",
        "%B %d",
        "%d %b",
        "%d %B",
        "%d %m",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%b %d %Y",
        "%b %d %y",
        "%B %d %Y",
        "%B %d %y",
        "%B %d ‘%y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y %m %d",
        "%m/%d/%Y",
        "%B %Y",
        "%b %Y",
        "%b",
        "%B",
        "%Y",
    ]

    for date_format in date_formats:
        try:
            if date_format == "%Y":
                specific_date = datetime.strptime(normalized_date_string, date_format)
                specific_date = specific_date.replace(month=1, day=1)
            elif date_format in ("%b", "%B"):
                date_str = f"{normalized_date_string} {base_datetime.year}"
                format_str = f"{date_format} %Y"
                dt = datetime.strptime(date_str, format_str)
                dt = dt.replace(day=1)
                third_friday = dt + relativedelta(weekday=FR(3))
                return third_friday
            elif date_format in ("%b %Y", "%B %Y"):
                dt = datetime.strptime(normalized_date_string, date_format)
                dt = dt.replace(day=1)
                third_friday = dt + relativedelta(weekday=FR(3))
                return third_friday
            elif "%y" not in date_format and "%Y" not in date_format:
                date_str = f"{normalized_date_string} {base_datetime.year}"
                format_str = f"{date_format} %Y"
                specific_date = datetime.strptime(date_str, format_str)
            else:
                specific_date = datetime.strptime(normalized_date_string, date_format)
            return specific_date
        except ValueError:
            continue

    return None


def date_formatter(comment_timestamp, keyword):
    # Convert Unix timestamp to datetime object in UTC
    comment_utc_datetime = datetime.fromtimestamp(comment_timestamp, tz=timezone.utc)
    formatted_date = comment_utc_datetime.strftime("%m/%d/%Y %I:%M:%S %p")
    print(formatted_date)
    keyword = keyword.lower()
    list_of_keywords, list_of_weekdays = get_static_mappings(comment_utc_datetime)

    # Check for static keyword matches
    if keyword in list_of_keywords:
        return list_of_keywords[keyword]

    # Check for weekday matches
    if keyword.lower() in list_of_weekdays:
        return list_of_weekdays[keyword.lower()]

    # Handle relative date keywords
    relative_date = parse_relative_date(keyword, comment_utc_datetime)
    if relative_date:
        return relative_date.strftime("%m/%d/%Y")

    specific_date = parse_specific_date_format(keyword, comment_utc_datetime)
    if specific_date:
        return specific_date.strftime("%m/%d/%Y")
    # If no match, raise an error
    if keyword != "":
        print(f"keyword not found: {keyword}")
    return ""


print(date_formatter(1747690278, "aug 18th"))
