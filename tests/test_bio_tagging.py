from bio_tagging import label_comment


def test_classic_trade_is_fully_tagged():
    tokens, labels = label_comment(
        "buying TSLA 250 calls expiring 7/25", "TSLA", "250", "7/25", "calls"
    )
    assert labels[tokens.index("TSLA")] == "B-TICKER"
    assert labels[tokens.index("250")] == "B-STRIKE"
    assert labels[tokens.index("7/25")] == "B-EXPIRY"
    assert labels[tokens.index("calls")] == "B-OPTIONTYPE"


def test_glued_strike_is_tagged_as_one_token():
    tokens, labels = label_comment("NVDA 450c eow lets ride", "NVDA", "450c", "eow", "")
    assert labels[tokens.index("450c")] == "B-STRIKE"
    assert labels[tokens.index("eow")] == "B-EXPIRY"


def test_dollar_prefixed_ticker_matches():
    tokens, labels = label_comment("$SPY 640 puts", "SPY", "640", "", "puts")
    assert labels[tokens.index("SPY")] == "B-TICKER"


def test_multiword_expiry_gets_b_and_i_tags():
    tokens, labels = label_comment("AMD 180 puts next friday", "AMD", "180", "next friday", "puts")
    assert labels[tokens.index("next")] == "B-EXPIRY"
    assert labels[tokens.index("friday")] == "I-EXPIRY"


def test_no_entities_means_all_o():
    tokens, labels = label_comment("just watching the game tonight", "", "", "", "")
    assert set(labels) == {"O"}
