"""Opponent numbers for the Opponent Analysis tab.

Every function here takes a cleaned league-wide fixtures table, the one that
standings.clean_fixtures() builds: one row per match with the columns
Wk, Date, Home, Away, HomeGoals, AwayGoals and Played.

There is no Streamlit in this file on purpose. It only does the maths, so it
can be tested on its own, and app.py only has to display the results.
"""
import pandas as pd

MATCH_COLUMNS = ["Wk", "Date", "Opponent", "Venue", "Score", "Result", "GF", "GA"]


def team_matches(fixtures, team):
    """Every match `team` has played, in date order, from the team's own side:
    who the opponent was, home or away, the score with the team's goals first,
    and W, D or L."""
    played = fixtures[
        fixtures["Played"] & ((fixtures["Home"] == team) | (fixtures["Away"] == team))
    ].copy()

    at_home = played["Home"] == team
    played["Venue"] = at_home.map({True: "Home", False: "Away"})
    played["Opponent"] = played["Away"].where(at_home, played["Home"])
    played["GF"] = played["HomeGoals"].where(at_home, played["AwayGoals"]).astype(int)
    played["GA"] = played["AwayGoals"].where(at_home, played["HomeGoals"]).astype(int)
    played["Score"] = played["GF"].astype(str) + "–" + played["GA"].astype(str)
    played["Result"] = "D"
    played["Result"] = played["Result"].mask(played["GF"] > played["GA"], "W")
    played["Result"] = played["Result"].mask(played["GF"] < played["GA"], "L")

    # Real date order. A match that was rescheduled sits where it was really
    # played, not where its matchweek number says.
    played["_when"] = pd.to_datetime(played["Date"], errors="coerce")
    played = played.sort_values(["_when", "Wk"]).reset_index(drop=True)
    return played[MATCH_COLUMNS]


def head_to_head(fixtures, team, opponent):
    """The matches `team` has played against `opponent` in this season's table."""
    matches = team_matches(fixtures, team)
    return matches[matches["Opponent"] == opponent].reset_index(drop=True)


def meetings_summary(matches):
    """Wins, draws, losses and goals across a set of matches."""
    return {
        "Played": len(matches),
        "W": int((matches["Result"] == "W").sum()),
        "D": int((matches["Result"] == "D").sum()),
        "L": int((matches["Result"] == "L").sum()),
        "GF": int(matches["GF"].sum()),
        "GA": int(matches["GA"].sum()),
    }


def form_text(fixtures, team, n=5):
    """The team's last n results, oldest first, such as 'W W D L W'.
    A dash when the team has not played yet."""
    results = list(team_matches(fixtures, team)["Result"].tail(n))
    return " ".join(results) if results else "–"


def opponents_of(fixtures, team):
    """Every other team in the fixtures, in alphabetical order."""
    teams = set(fixtures["Home"]) | set(fixtures["Away"])
    return sorted(teams - {team})


def next_opponent(fixtures, team):
    """The opponent in `team`'s earliest match that has not been played yet,
    or None when every match has been played."""
    left = fixtures[
        ~fixtures["Played"] & ((fixtures["Home"] == team) | (fixtures["Away"] == team))
    ].copy()
    if len(left) == 0:
        return None
    left["_when"] = pd.to_datetime(left["Date"], errors="coerce")
    first = left.sort_values(["_when", "Wk"]).iloc[0]
    return first["Away"] if first["Home"] == team else first["Home"]


def _results_text(matches):
    """'H 2–1 W, A 0–0 D' for a set of matches, or a dash if there are none."""
    if len(matches) == 0:
        return "–"
    parts = [f"{row.Venue[0]} {row.Score} {row.Result}" for row in matches.itertuples()]
    return ", ".join(parts)


def results_vs_everyone(this_fixtures, last_fixtures, team):
    """One row per team in this season's league: how `team` did against them
    last season and so far this season. H = home, A = away, and the team's own
    goals come first in every score."""
    rows = []
    for opponent in opponents_of(this_fixtures, team):
        rows.append({
            "Opponent": opponent,
            "Last season": _results_text(head_to_head(last_fixtures, team, opponent)),
            "This season": _results_text(head_to_head(this_fixtures, team, opponent)),
        })
    return pd.DataFrame(rows, columns=["Opponent", "Last season", "This season"])