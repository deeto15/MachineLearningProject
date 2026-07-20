from pathlib import Path

import tickers

STOCKS = str(Path(__file__).resolve().parent.parent / "training" / "data" / "stocks.csv")
SYMBOLS, NAMES = tickers.load(STOCKS)


def test_symbol_passes_through_any_case():
    assert tickers.resolve("NVDA", SYMBOLS, NAMES) == "NVDA"
    assert tickers.resolve("nvda", SYMBOLS, NAMES) == "NVDA"
    assert tickers.resolve("$spy", SYMBOLS, NAMES) == "SPY"


def test_company_name_maps_to_symbol():
    assert tickers.resolve("Apple", SYMBOLS, NAMES) == "AAPL"
    assert tickers.resolve("Microsoft", SYMBOLS, NAMES) == "MSFT"
    assert tickers.resolve("nvidia", SYMBOLS, NAMES) == "NVDA"


def test_garbage_is_dropped():
    assert tickers.resolve("lacist", SYMBOLS, NAMES) is None
    assert tickers.resolve("x3", SYMBOLS, NAMES) is None
    assert tickers.resolve("", SYMBOLS, NAMES) is None


def test_missing_file_gives_empty_universe():
    symbols, names = tickers.load("does-not-exist.csv")
    assert symbols == set() and names == {}
