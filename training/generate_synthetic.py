# Generates synthetic WSB-style training data to close the gap between the
# original 2012-2015 StockTwits training set and modern r/wallstreetbets text.
#
# Produces three kinds of rows in the same CSV schema as
# regression_model_training_data.csv:
#   Label 1 - options trades with slot-filled entities (ticker/strike/expiry/type),
#             including modern forms the old data never had: glued strikes ("450c"),
#             "eow"/"0dte" expiries, $-prefixed tickers, emoji noise.
#   Label 2 - price targets ("NVDA to $200 by friday") with only the ticker tagged.
#   Label 0 - negatives: real comments mined from data/comments.db (filtered so
#             they contain no trade language) plus synthetic "trap" comments full
#             of ticker-lookalike words (RAM, AI, CEO...) and bare numbers.
#
# The template and trap banks were authored by Claude to mimic real WSB phrasing.
# Because the slots are filled programmatically, entity labels are exact - no
# hand labeling. Template rules that keep the BIO tagging exact:
#   - each entity slot appears exactly once per template
#   - no bare numbers or option words (call/put) in the template text itself
#
# Usage:
#   python training/generate_synthetic.py                 # 3000 rows, seeded
#   python training/generate_synthetic.py --n 6000 --seed 7
#
# Output: training/data/synthetic_training_data.csv (picked up automatically by
# train_ner.py and train_binary.py).
import argparse
import csv
import random
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUT_FILE = DATA_DIR / "synthetic_training_data.csv"
STOCKS_FILE = DATA_DIR / "stocks.csv"
COMMENTS_DB = ROOT.parent / "data" / "comments.db"

FIELDS = ["Comment", "Ticker", "Strike", "Expiry", "OptionType", "Quantity", "Premium", "Label"]


NAME_SUFFIXES = {"inc", "corp", "corporation", "ltd", "plc", "co", "company", "holdings",
                 "group", "technologies", "technology", "international", "incorporated"}


def clean_company_name(name):
    words = [w.strip(",.") for w in name.split()]
    words = [w for w in words if w.lower().strip(",.") not in NAME_SUFFIXES]
    cleaned = " ".join(words[:2])
    return cleaned if 4 <= len(cleaned) <= 20 else ""


def load_tickers():
    with open(STOCKS_FILE, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    symbols = [r["Symbol"].strip() for r in rows if r["Symbol"].strip().isalpha()]
    names = [clean_company_name(r["Company Name"]) for r in rows[:400]]
    names = [n for n in names if n and " " not in n]  # single-word big names only
    # weight toward the big names people actually post about, keep a long tail
    popular, tail = symbols[:300], symbols[300:]
    return popular, tail, set(symbols), names


def rand_ticker(popular, tail, names):
    # sometimes people write the company name instead of the symbol
    if names and random.random() < 0.12:
        return random.choice(names)
    tick = random.choice(popular) if random.random() < 0.7 else random.choice(tail)
    # case augmentation: real comments write spy, Soxl, NVDA interchangeably
    r = random.random()
    if r < 0.15:
        tick = tick.lower()
    elif r < 0.25:
        tick = tick.title()
    return f"${tick}" if random.random() < 0.25 else tick


def rand_strike():
    if random.random() < 0.2:
        return f"{random.choice([2, 5, 7, 12, 17, 22, 62, 122])}.5"
    return str(random.choice([5, 10, 15, 20, 25, 30, 40, 50, 69, 75, 100, 120, 150, 180, 200,
                              220, 250, 300, 350, 400, 420, 450, 500, 550, 600, 640, 700, 1000]))


def rand_expiry():
    forms = [
        lambda: f"{random.randint(1, 12)}/{random.randint(1, 28)}",
        lambda: f"{random.randint(1, 12)}/{random.randint(1, 28)}/{random.choice(['25', '26', '2026'])}",
        lambda: f"{random.choice(['jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'Jan', 'Sep', 'Dec'])} {random.randint(1, 28)}",
        lambda: random.choice(["eow", "EOW", "eom", "0dte", "0DTE", "opex"]),
        lambda: random.choice(["friday", "Friday", "next friday", "tomorrow", "next week",
                               "this week", "weekly", "monday", "end of week", "next month"]),
    ]
    return random.choice(forms)()


# ---------------------------------------------------------------------------
# Claude-authored template banks. Slots: {t}=ticker  {s}{cp}=glued strike
# {k}=strike  {o}=option type word  {e}=expiry
# ---------------------------------------------------------------------------

GLUED_TEMPLATES = [
    "{t} {s}{cp} {e} lets ride",
    "yolod my whole account into {t} {s}{cp} {e}",
    "just picked up some {t} {s}{cp} expiring {e}",
    "{t} {s}{cp} {e} cant go tits up",
    "all in on {t} {s}{cp} {e} see you on the moon",
    "grabbed a stack of {t} {s}{cp} {e} on the dip",
    "{t} {s}{cp} {e} either lambo or food stamps",
    "rolling my winnings into {t} {s}{cp} {e}",
    "averaging down on {t} {s}{cp} {e} like an idiot",
    "wife doesnt know about the {t} {s}{cp} {e} yet",
    "{t} {s}{cp} {e} printing tendies as we speak",
    "bag holding {t} {s}{cp} {e} down bad",
    "who told me to buy {t} {s}{cp} {e}, come collect your beating",
    "screenshot this: {t} {s}{cp} {e} is free money",
    "market open cant come soon enough, loading {t} {s}{cp} {e}",
    "dumped my savings into {t} {s}{cp} {e} at close",
    "trimming everything else, going heavy {t} {s}{cp} {e}",
    "the play is {t} {s}{cp} {e}, thank me later",
    "im not smart but {t} {s}{cp} {e} feels right",
    "{t} {s}{cp} {e} because my horoscope said so",
    "theta gang can pry my {t} {s}{cp} {e} from my cold dead hands",
    "revenge trade: {t} {s}{cp} {e}",
    "inverse me and buy {t} {s}{cp} {e}",
    "one more paycheck into {t} {s}{cp} {e} and im done i swear",
    "cant stop wont stop, {t} {s}{cp} {e} again",
]

SPELLED_TEMPLATES = [
    "buying {t} {k} {o} at open, {e} expiry",
    "loaded up on {t} {k} {o} for {e}",
    "going long {t} with {e} {k} {o}",
    "{t} {k} {o} {e} this is the way",
    "sold my car for {t} {k} {o} expiring {e}",
    "thoughts on {t} {k} {o} for {e}? already down bad",
    "avg into {t} {e} {k} {o} whenever it dips",
    "my {t} {k} {o} print {e} or i sleep under a bridge",
    "just yoloed rent money on {t} {k} {o} {e}",
    "{e} {k} {o} on {t}, wish me luck",
    "holding {t} {k} {o} through {e} earnings",
    "who else is in {t} {k} {o} for {e}",
    "doubling down on my {t} {k} {o} {e} position",
    "opened a fat {t} {k} {o} position for {e}",
    "exit plan? never heard of her. {t} {k} {o} {e}",
    "the dd wrote itself, {t} {k} strike {o} for {e}",
    "scooped {t} {o} at the {k} strike, {e} expiry",
    "im in {t} {e} {o} at {k}, no stop loss we die like men",
    "somebody talk me out of {t} {k} {o} expiring {e}",
    "diamond handing my {t} {k} {o} until {e}",
    "took profit on everything except the {t} {k} {o} {e}",
    "watching my {t} {k} {o} bleed into {e} like a champ",
    "fomo got me, chased {t} {k} {o} {e} at the top",
    "adding to {t} {k} {o} {e} every red day",
    "cant believe the {t} {k} {o} for {e} filled that cheap",
    "sold a kidney, went long {t} {k} {o} {e}",
    "the fed cant stop my {t} {k} {o} {e}",
    "closing my shorts and flipping to {t} {k} {o} {e}",
    "textbook cup and handle on {t}, grabbed {k} {o} for {e}",
    "earnings play: {t} {k} {o} expiring {e}, iv be damned",
]

QUANTITY_TEMPLATES = [
    "just filled {q} contracts of {t} {k} {o} for {e}",
    "{q} {t} {k} {o} {e}, send it",
    "picked up {q} more {t} {k} {o} expiring {e}",
    "sitting on {q} {t} {k} {o} into {e}",
]

TARGET_TEMPLATES = [
    "{t} to ${p} by {e}",
    "{t} hits ${p} {e}, screenshot this",
    "calling it now: {t} ${p} by {e}",
    "{t} is going to ${p}, trust the dd",
    "if {t} doesnt hit ${p} by {e} ill eat my shoe",
    "{t} ${p} pt, dont say i didnt warn you",
    "my price target for {t} is ${p}, cope harder bears",
    "{t} ${p} incoming, the chart never lies",
    "remind me when {t} taps ${p} {e}",
    "{t} to ${p} and thats being conservative",
    "bears in shambles when {t} prints ${p} by {e}",
    "wrote it on my mirror: {t} ${p} {e}",
    "{t} wont stay under ${p} past {e}, mark my words",
    "analysts sleeping on {t}, easy ${p} by {e}",
    "load the boat, {t} sees ${p} before {e}",
    "unpopular opinion: {t} craters to ${p} by {e}",
    "{t} ${p} was my call in january and im still right",
    "the algo wants {t} at ${p} by {e}",
    # messier real-world phrasings (no $ sign, terse, banbet-style)
    "{t} will dump to {p} then rebound",
    "see you at {t} {p}",
    "i need {t} to {p} tmrw so i can reload",
    "{t} {p} or im deleting the app",
    "!banbet {t} {p} 3d",
    "{t} gonna rip to {p} after earnings",
    "next stop {p} for {t}, cope",
    "{t} breaks {p} and shorts get vaporized",
    "we did it boys, {t} {p}",
    "{t} to {p}, my uncle works at the exchange",
    "{t} gonna double pump",
    "if you are not buying {t} at these prices you hate money",
    "{t} holders brace for impact, this thing sees {p} soon",
    "{t} rocket ship taking off this qeek",
]

# directional market calls with no ticker at all - very common in the daily thread
TARGET_NOTICKER = [
    "green by open",
    "red till market open",
    "we are going to pump tomorrow lol",
    "futes red then green an hour after",
    "futes will be -2% in a few hours, screenshot it",
    "new aths this week",
    "gonna gap up huge at open trust",
    "everything dumps at 2:30, always does",
    "relief rally until tuesday then the rug",
    "oil gonna rocket up in five minutes",
    "this whole market pumps the second the fed blinks",
    "eoy rally already priced in, we crab from here",
]

TRAP_COMMENTS = [
    "just upgraded my rig with 64gb RAM and a new GPU",
    "the CEO said AI will replace half the DD on this sub",
    "my wife's boyfriend gave me twenty bucks for the arcade",
    "this sub is 90% FOMO and 10% cope",
    "up 5% today, feels good man",
    "lost 300 on the game last night, classic",
    "IMO the FED is going to keep rates high forever",
    "watched the game at 7, what a blowout",
    "inflation at 3.2 and everyone acting surprised",
    "my GPA was 2.5 and i still made it out",
    "the IPO market has been dead for 2 years",
    "bro really said trust me x3 in one paragraph",
    "GDP numbers come out thursday i think",
    "ordered a large pizza for 12.99, best decision of my year",
    "SPACE looks cool but im not touching meme coins",
    "been to the ER twice this month, ATH for me",
    "PSA: dont marry someone with a shopping addiction",
    "my landlord raised rent 200 a month, USA baby",
    "the DMV took 4 hours today",
    "CPI print tomorrow, gonna watch from the sidelines",
    "new PC build: 32gb RAM, RTX card, cost me a fortune",
    "HR scheduled my performance review for friday, pray for me",
    "the GOAT retired and the league got boring",
    "my IQ drops 10 points every time i open this app",
    "TIL you can microwave a peep for 8 seconds before it explodes",
    "the WIFI at my office went down and everyone celebrated",
    "ordered from that new BBQ place, 45 minute wait",
    "using PTO on a tuesday is elite behavior",
    "the NBA finals were rigged and i will die on this hill",
    "my UBER driver gave me a life lecture at 6am",
    "the VA finally processed my claim after 8 months",
    "EPA says the water is fine, sure buddy",
    "roommate ate my leftovers again, day 47",
    "gym was packed at 5, new years resolution crowd",
    "my dog ate a sock and the vet bill was 800",
    "the DLC costs more than the base game now",
    "grandma turned 90 and still sharper than me",
    "why is cereal 8 dollars, genuinely asking",
    "team lost by 30 and the coach blamed the refs",
    "the ATM ate my card on a sunday, incredible",
    "finals week and the library is a warzone",
    "my barber raised prices again, everything is up",
    "the HOA fined me for grass being 1 inch too tall",
    "spent my whole weekend fixing a leaky faucet",
    "the API at work went down for 6 hours, chaos",
    "brother in law wont stop talking about his CROSSFIT gym",
    "got ghosted after a great first date, story of my life",
    "the ML model at work predicts everything except revenue",
    "my kid asked for 60 dollars for a skin in a video game",
    "the DOW documentary last night was actually good",
    "traffic on the 405 turned a 20 minute drive into 90",
    "boss said return to office 5 days, morale is in the floor",
    "the NFL draft is basically a lottery for hope",
    "my sourdough starter died and im in mourning",
    "power went out during the boss fight, rage quit irl",
    "the IRS letter turned out to be 12 dollars i owed",
    "neighbors party ended at 4am on a wednesday",
    "the FDA recalled my favorite snack, dark times",
    "my therapist said to stop checking my phone at 3am, no",
    "airline lost my bag and offered a 10 dollar voucher",
]

NOISE = ["", "", "", "", " 🚀🚀🚀", " 💎🙌", " not financial advice", " lfg", " 🌙",
         " ape strong", " to the moon", " 🦍", " positions or ban", " this is not a drill"]

TRADE_WORDS = re.compile(
    r"(\$[A-Za-z]{1,5}\b|\b\d+(\.\d+)?\s*[cpCP]\b|\b(call|calls|put|puts|strike|expiry|0dte|dte|leaps?|fds?|otm|itm|contracts?)\b)",
    re.IGNORECASE,
)


def make_trade_row(popular, tail, names):
    tick = rand_ticker(popular, tail, names)
    strike = rand_strike()
    expiry = rand_expiry()
    kind = random.random()

    if kind < 0.4:
        # glued form: "450c" - the whole token is tagged STRIKE, no separate type word
        cp = random.choice(["c", "p", "c", "p", "C", "P"])
        glued = f"{strike}{cp}"
        comment = random.choice(GLUED_TEMPLATES).format(t=tick, s=strike, cp=cp, e=expiry) + random.choice(NOISE)
        return {"Comment": comment, "Ticker": tick.lstrip("$"), "Strike": glued,
                "Expiry": expiry, "OptionType": "", "Quantity": "", "Premium": "", "Label": 1}

    otype = random.choice(["calls", "puts", "calls", "puts", "call", "put", "Calls", "Puts"])
    if kind < 0.9:
        comment = random.choice(SPELLED_TEMPLATES).format(t=tick, k=strike, o=otype, e=expiry) + random.choice(NOISE)
        quantity = ""
    else:
        # quantity must differ from the strike or the tagger would label the
        # first occurrence of the number (the quantity) as the strike
        quantity = strike
        while quantity == strike:
            quantity = str(random.choice([2, 3, 4, 5, 6, 8, 15, 20, 50]))
        comment = random.choice(QUANTITY_TEMPLATES).format(t=tick, k=strike, o=otype, e=expiry, q=quantity) + random.choice(NOISE)
    return {"Comment": comment, "Ticker": tick.lstrip("$"), "Strike": strike,
            "Expiry": expiry, "OptionType": otype, "Quantity": quantity, "Premium": "", "Label": 1}


def make_target_row(popular, tail, names):
    # some directional calls name no ticker at all
    if random.random() < 0.15:
        comment = random.choice(TARGET_NOTICKER) + random.choice(NOISE)
        return {"Comment": comment, "Ticker": "", "Strike": "", "Expiry": "",
                "OptionType": "", "Quantity": "", "Premium": "", "Label": 2}
    tick = rand_ticker(popular, tail, names)
    price = rand_strike()
    expiry = rand_expiry()
    comment = random.choice(TARGET_TEMPLATES).format(t=tick, p=price, e=expiry) + random.choice(NOISE)
    return {"Comment": comment, "Ticker": tick.lstrip("$"), "Strike": "", "Expiry": "",
            "OptionType": "", "Quantity": "", "Premium": "", "Label": 2}


def make_trap_row():
    comment = random.choice(TRAP_COMMENTS) + random.choice(NOISE)
    return {"Comment": comment, "Ticker": "", "Strike": "", "Expiry": "",
            "OptionType": "", "Quantity": "", "Premium": "", "Label": 0}


def mine_real_negatives(ticker_set, limit):
    """Pull real comments that clearly contain no trade language as label-0 rows.
    Filters on the text itself (not on model predictions) to avoid feeding the
    model's own mistakes back into training."""
    if not COMMENTS_DB.exists():
        print(f"note: {COMMENTS_DB} not found, skipping real-comment negatives")
        return []
    conn = sqlite3.connect(COMMENTS_DB)
    rows = conn.execute("SELECT body FROM comments ORDER BY RANDOM() LIMIT ?", (limit * 5,)).fetchall()
    conn.close()

    out = []
    for (body,) in rows:
        text = " ".join((body or "").split())
        if not (20 <= len(text) <= 200) or text in ("[deleted]", "[removed]"):
            continue
        if TRADE_WORDS.search(text):
            continue
        # reject anything containing an all-caps token that is a real ticker
        if any(w in ticker_set for w in re.findall(r"\b[A-Z]{2,5}\b", text)):
            continue
        out.append({"Comment": text, "Ticker": "", "Strike": "", "Expiry": "",
                    "OptionType": "", "Quantity": "", "Premium": "", "Label": 0})
        if len(out) >= limit:
            break
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=3000, help="total rows to generate")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    popular, tail, ticker_set, names = load_tickers()

    n_trades = int(args.n * 0.45)
    n_targets = int(args.n * 0.20)
    n_negatives = args.n - n_trades - n_targets
    real_negatives = mine_real_negatives(ticker_set, n_negatives // 2)

    rows, seen = [], set()
    for maker, count in ((lambda: make_trade_row(popular, tail, names), n_trades),
                         (lambda: make_target_row(popular, tail, names), n_targets),
                         (make_trap_row, n_negatives - len(real_negatives))):
        made = 0
        while made < count:
            row = maker()
            if row["Comment"] in seen and row["Label"] != 0:
                continue
            seen.add(row["Comment"])
            rows.append(row)
            made += 1
    rows.extend(real_negatives)

    random.shuffle(rows)
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    counts = {label: sum(1 for r in rows if r["Label"] == label) for label in (0, 1, 2)}
    print(f"wrote {len(rows)} rows to {OUT_FILE}")
    print(f"  label 1 (trades):        {counts[1]}")
    print(f"  label 2 (price targets): {counts[2]}")
    print(f"  label 0 (negatives):     {counts[0]} ({len(real_negatives)} mined from comments.db)")


if __name__ == "__main__":
    main()
