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


# ---- The league-phase table: all 36 teams ----------------------------------

LEAGUE_PHASE = "League phase"
TABLE_COLUMNS = ["Position", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "Zone"]


def clean_fixtures(raw):
    """The league-phase matches of a whole Champions League season, one row per
    match: Wk, Date, Home, Away, the two scores and whether it was Played.

    The scraped page also has repeated header rows and blank rows, and it writes
    each team with a small country code ("Real Madrid es" at home, "it Inter"
    away) and the score as text ("2-1" with a long dash). Only rows whose Round
    is the league phase are kept, which drops the junk rows too."""
    rows = raw[raw["Round"] == LEAGUE_PHASE].copy()
    rows["Wk"] = pd.to_numeric(rows["Wk"], errors="coerce")
    rows = rows[rows["Wk"].notna()].copy()
    rows["Wk"] = rows["Wk"].astype(int)
    scores = rows["Score"].astype(str).str.extract(r"(\d+)\s*[\u2013-]\s*(\d+)")
    rows["HomeGoals"] = pd.to_numeric(scores[0])
    rows["AwayGoals"] = pd.to_numeric(scores[1])
    rows["Played"] = rows["HomeGoals"].notna()
    rows["Home"] = rows["Home"].astype(str).str.replace(r"\s+[a-z]{2,3}$", "", regex=True)
    rows["Away"] = rows["Away"].astype(str).str.replace(r"^[a-z]{2,3}\s+", "", regex=True)
    columns = ["Wk", "Date", "Home", "Away", "HomeGoals", "AwayGoals", "Played"]
    return rows[columns].reset_index(drop=True)


def _zone(position):
    """Where a league-phase place leads: the top 8 go straight to the round of
    16, 9th to 24th to the knockout play-offs, and the rest are out."""
    if position <= 8:
        return "Round of 16"
    if position <= 24:
        return "Play-offs"
    return "Out"


def league_table(fixtures, week=None):
    """The league-phase table after `week` matchweeks (every played match
    counts when week is None).

    Teams are ordered like UEFA's table: points, goal difference, goals
    scored, away goals scored, wins, away wins. UEFA's later tie-breakers
    (the opponents' results, discipline, club coefficient) are not applied,
    so teams still level after those are put in alphabetical order."""
    played = fixtures[fixtures["Played"]]
    if week is not None:
        played = played[played["Wk"] <= week]
    teams = sorted(set(fixtures["Home"]) | set(fixtures["Away"]))

    # One row per team per match: the home side's view and the away side's view
    home = pd.DataFrame({"Team": played["Home"], "GF": played["HomeGoals"],
                         "GA": played["AwayGoals"], "Away": False})
    away = pd.DataFrame({"Team": played["Away"], "GF": played["AwayGoals"],
                         "GA": played["HomeGoals"], "Away": True})
    games = pd.concat([home, away], ignore_index=True)
    games["W"] = (games["GF"] > games["GA"]).astype(int)
    games["D"] = (games["GF"] == games["GA"]).astype(int)
    games["L"] = (games["GF"] < games["GA"]).astype(int)
    games["P"] = 1
    games["AwayGF"] = games["GF"].where(games["Away"], 0)
    games["AwayW"] = games["W"].where(games["Away"], 0)

    table = games.groupby("Team")[["P", "W", "D", "L", "GF", "GA", "AwayGF", "AwayW"]].sum()
    table = table.reindex(teams, fill_value=0).astype(int).reset_index()
    table["GD"] = table["GF"] - table["GA"]
    table["Pts"] = table["W"] * 3 + table["D"]
    table = table.sort_values(
        ["Pts", "GD", "GF", "AwayGF", "W", "AwayW", "Team"],
        ascending=[False, False, False, False, False, False, True],
    ).reset_index(drop=True)
    table["Position"] = table.index + 1
    table["Zone"] = table["Position"].map(_zone)
    return table[TABLE_COLUMNS]


def team_weeks_played(fixtures, team):
    """The matchweek numbers in which `team` has played a league-phase game."""
    mine = fixtures[fixtures["Played"] & ((fixtures["Home"] == team) | (fixtures["Away"] == team))]
    return sorted(mine["Wk"].unique().tolist())


def position_history(fixtures, team, last_week):
    """`team`'s place in the table after each matchweek from 1 to `last_week`,
    as a table with the columns Wk and Position."""
    rows = []
    for week in range(1, last_week + 1):
        table = league_table(fixtures, week)
        found = table[table["Team"] == team]
        if len(found):
            rows.append({"Wk": week, "Position": int(found.iloc[0]["Position"])})
    return pd.DataFrame(rows, columns=["Wk", "Position"])