"""Possession and formation numbers for the Tactics tab.

Every function here takes the cleaned match table that clean_schedule() builds:
one row per played match, in date order, with the columns Game, Date, Comp,
Venue, Result, GF, GA, Opponent, Poss, Formation, Opp Formation and Points.

There is no Streamlit in this file on purpose. It only does the maths, so it
can be tested on its own, and app.py only has to display the results.
"""
import pandas as pd

POINTS = {"W": 3, "D": 1, "L": 0}

# Possession is grouped into three bands. The edges are 0, 45, 55 and 101, so
# a match with 45% possession goes in the middle band and 100% in the top one.
BAND_EDGES = [0, 45, 55, 101]
BAND_LABELS = ["Under 45%", "45% to 54%", "55% or more"]


def clean_schedule(schedule, league_only):
    """The played matches from the schedule table, in date order, numbered
    Game 1, 2, 3... With league_only=True only La Liga matches are kept."""
    played = schedule[schedule["Result"].notna()].copy()
    if league_only:
        played = played[played["Comp"] == "La Liga"].copy()

    # Rows whose date doesn't parse (the header row that repeats in the middle
    # of the table) are dropped here.
    played["Date"] = pd.to_datetime(played["Date"], format="%Y-%m-%d", errors="coerce")
    played = played[played["Date"].notna()]
    played = played.sort_values("Date").reset_index(drop=True)

    # These can come in as text. Anything that is not a number becomes blank.
    for column in ["GF", "GA", "Poss"]:
        played[column] = pd.to_numeric(played[column], errors="coerce")

    played["Points"] = played["Result"].map(POINTS)
    played["Game"] = played.index + 1
    played["Date"] = played["Date"].dt.strftime("%Y-%m-%d")
    return played


def possession_summary(matches):
    """A few headline possession numbers. Every value is None when there is
    no possession data at all (the app shows None as a dash)."""
    poss = matches["Poss"].dropna()
    if poss.empty:
        return {"Average": None, "Highest": None, "Lowest": None, "Most of the ball": None}
    return {
        "Average": float(poss.mean()),
        "Highest": float(poss.max()),
        "Lowest": float(poss.min()),
        "Most of the ball": int((poss > 50).sum()),  # matches with more than 50%
    }


def rolling_possession(matches, window):
    """Average possession over the last `window` matches, for every match.
    The first window-1 matches have no value yet, so the line starts at
    match number `window`."""
    values = pd.Series(matches["Poss"].to_numpy(), index=matches["Game"].to_numpy())
    return values.rolling(window).mean()


def _record(games):
    """W, D, L, points and goals for a group of matches."""
    points = int(games["Points"].sum())
    count = len(games)
    return {
        "Games": count,
        "W": int((games["Result"] == "W").sum()),
        "D": int((games["Result"] == "D").sum()),
        "L": int((games["Result"] == "L").sum()),
        "Points": points,
        "Points per game": round(points / count, 2) if count else None,
        "GF": int(games["GF"].sum()),
        "GA": int(games["GA"].sum()),
    }


def possession_bands(matches):
    """The record in matches with little, medium and a lot of possession.
    Matches with no possession number are left out. All three bands are
    always listed, so a band with no matches shows 0 games."""
    known = matches[matches["Poss"].notna()].copy()
    known["Band"] = pd.cut(known["Poss"], bins=BAND_EDGES, labels=BAND_LABELS, right=False)
    rows = []
    for label in BAND_LABELS:
        row = {"Possession": label}
        row.update(_record(known[known["Band"] == label]))
        rows.append(row)
    return pd.DataFrame(rows)


def possession_by_result(matches):
    """Average possession in wins, draws and losses (only the results that
    have happened)."""
    known = matches[matches["Poss"].notna()]
    rows = []
    for result, name in [("W", "Wins"), ("D", "Draws"), ("L", "Losses")]:
        games = known[known["Result"] == result]
        if len(games):
            rows.append({"Result": name, "Games": len(games),
                         "Average possession": round(float(games["Poss"].mean()), 1)})
    return pd.DataFrame(rows, columns=["Result", "Games", "Average possession"])


def formation_record(matches, column):
    """The record for each formation. column is "Formation" (Real Madrid's)
    or "Opp Formation" (the opponent's). Most-used formation first."""
    columns = ["Formation", "Games", "W", "D", "L", "Points", "Points per game", "GF", "GA"]
    known = matches[matches[column].notna()]
    rows = []
    for formation, games in known.groupby(column):
        row = {"Formation": formation}
        row.update(_record(games))
        rows.append(row)
    table = pd.DataFrame(rows, columns=columns)
    # Most games first; ties are broken by the formation's name so the order
    # never changes between runs.
    return table.sort_values(["Games", "Formation"], ascending=[False, True]).reset_index(drop=True)