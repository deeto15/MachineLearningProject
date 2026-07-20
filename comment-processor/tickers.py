# Ticker validation and company-name resolution against the known symbol
# universe (training/data/stocks.csv, mounted at TICKER_FILE).
#
# resolve() turns whatever span the NER tagged into a real symbol:
#   "NVDA" / "$nvda"  -> "NVDA"   (symbol, any case)
#   "Sandisk"         -> "SNDK"   (company name lookup)
#   "lacist"          -> None     (not a real ticker - caller should drop it)
import csv
import os

TICKER_FILE = os.getenv("TICKER_FILE", "/tickers/stocks.csv")

_NAME_SUFFIXES = {"inc", "corp", "corporation", "ltd", "plc", "co", "company", "holdings",
                  "group", "technologies", "technology", "international", "incorporated",
                  "the", "class", "sa", "nv", "ag", "se"}


def _clean_name(name):
    words = [w.strip(",.").lower() for w in name.split()]
    return " ".join(w for w in words if w and w not in _NAME_SUFFIXES)


def load(path=None):
    """Returns (symbols, name_to_symbol). Empty structures if the file is missing."""
    path = path or TICKER_FILE
    symbols, names = set(), {}
    if not os.path.exists(path):
        return symbols, names
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            symbol = row["Symbol"].strip().upper()
            symbols.add(symbol)
            # length floor keeps junk like "x3" or "ai" out of the name map
            cleaned = _clean_name(row.get("Company Name", ""))
            if len(cleaned) >= 4 and cleaned not in names:
                names[cleaned] = symbol
            # also map the first word of multi-word names ("meta platforms" -> "meta")
            first = cleaned.split(" ")[0] if cleaned else ""
            if len(first) >= 4 and first not in names:
                names[first] = symbol
    return symbols, names


def resolve(span, symbols, names):
    """Maps an NER-extracted span to a real symbol, or None if it isn't one."""
    if not span:
        return None
    cleaned = span.strip().lstrip("$")
    if cleaned.upper() in symbols:
        return cleaned.upper()
    return names.get(_clean_name(cleaned))
