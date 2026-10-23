"""The numbers behind the Champions League tab.

Real Madrid's match log (from FBref) has every competition in one table. The
Champions League games are the rows where the Comp column says "Champions Lg".
The functions here pick those rows out and work out the record, points and
goals. They are the same ideas as the La Liga tabs, just for one competition.

There is no Streamlit in this file on purpose. It only prepares the tables.
"""

import re

import pandas as pd

COMP = "Champions Lg"            # how FBref writes the competition's name
POINTS = {"W": 3, "D": 1, "L": 0}


def _clean_name(name):
    """FBref leaks a small country code in front of some team names ("it Inter").
    Strip it."""
    return re.sub(r"^[a-z]{2,3}\s+(?=[A-Z])", "", str(name))


def _champions_rows(schedule):
    """Every Champions League row of the match log, with a real date, in date
    order. Stray header rows (where Comp says "Comp") are left out, because
    only a row whose Comp is the Champions League is kept."""
    rows = schedule[schedule["Comp"] == COMP].copy()
    rows["Date"] = pd.to_datetime(rows["Date"], format="%Y-%m-%d", errors="coerce")
    rows = rows[rows["Date"].notna()].sort_values("Date").reset_index(drop=True)
    rows["Opponent"] = rows["Opponent"].apply(_clean_name)
    for column in ("GF", "GA", "Poss"):
        rows[column] = pd.to_numeric(rows[column], errors="coerce")
    rows["Date"] = rows["Date"].dt.strftime("%Y-%m-%d")
    return rows


def played_games(schedule):
    """The Champions League games already played, numbered Game 1, 2, 3...,
    with the points each one earned and the running total."""
    rows = _champions_rows(schedule)
    games = rows[rows["Result"].isin(POINTS)].reset_index(drop=True)
    games["Points"] = games["Result"].map(POINTS)
    games["Cumulative Points"] = games["Points"].cumsum()
    games["Game"] = games.index + 1
    return games


def upcoming_games(schedule):
    """The Champions League games still to play (the log lists them with the
    result left blank). Result, GF and GA stay empty."""
    rows = _champions_rows(schedule)
    return rows[~rows["Result"].isin(POINTS)].reset_index(drop=True)


def summary(games):
    """Record, points, goals and average possession for a set of played games.
    The average possession is None when there is no possession number."""
    possession = games["Poss"].dropna()
    return {
        "W": int((games["Result"] == "W").sum()),
        "D": int((games["Result"] == "D").sum()),
        "L": int((games["Result"] == "L").sum()),
        "Points": int(games["Points"].sum()),
        "GF": int(games["GF"].sum()),
        "GA": int(games["GA"].sum()),
        "Poss": float(possession.mean()) if len(possession) else None,
    }