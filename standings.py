import pandas as pd

# A score looks like "2–1" on FBref (an en dash). A hyphen or em dash is accepted too.
SCORE_PATTERN = r"^\s*(\d+)\s*[–—-]\s*(\d+)\s*$"


def clean_fixtures(raw):
    """Turn FBref's league-wide fixtures table into one row per real fixture:
    Wk, Date, Home, Away, HomeGoals, AwayGoals, Played.

    The scraped table also contains rows that are not matches: header rows
    repeated inside the table and blank spacer rows. A real fixture has a
    numeric matchweek and two team names, so only those rows are kept."""
    fixtures = raw.copy()

    fixtures["Wk"] = pd.to_numeric(fixtures["Wk"], errors="coerce")
    is_fixture = fixtures["Wk"].notna() & fixtures["Home"].notna() & fixtures["Away"].notna()
    fixtures = fixtures[is_fixture].copy()
    fixtures["Wk"] = fixtures["Wk"].astype(int)

    # A match with no score yet (or a postponed one) simply has no goals filled in.
    goals = fixtures["Score"].astype("string").str.extract(SCORE_PATTERN)
    fixtures["HomeGoals"] = pd.to_numeric(goals[0])
    fixtures["AwayGoals"] = pd.to_numeric(goals[1])
    fixtures["Played"] = fixtures["HomeGoals"].notna()

    keep = ["Wk", "Date", "Home", "Away", "HomeGoals", "AwayGoals", "Played"]
    return fixtures[keep].reset_index(drop=True)


def league_table(fixtures, week):
    """The league table after `week` matchweeks: every played match from
    matchweeks 1..week counts. Teams are ordered by points, then goal
    difference, then goals scored, then name. (La Liga's official first
    tiebreaker is head-to-head, so teams level on points can occasionally
    be in a different order than the official table.)"""
    played = fixtures[fixtures["Played"] & (fixtures["Wk"] <= week)]

    # Each match counts twice: once from the home team's side, once from the away team's.
    home = pd.DataFrame({"Team": played["Home"], "GF": played["HomeGoals"], "GA": played["AwayGoals"]})
    away = pd.DataFrame({"Team": played["Away"], "GF": played["AwayGoals"], "GA": played["HomeGoals"]})
    games = pd.concat([home, away], ignore_index=True)
    games["Pts"] = (games["GF"] > games["GA"]) * 3 + (games["GF"] == games["GA"]) * 1
    games["P"] = 1

    totals = games.groupby("Team")[["P", "GF", "GA", "Pts"]].sum()

    # Include every team, even one that has not played yet (all zeros).
    teams = sorted(set(fixtures["Home"]) | set(fixtures["Away"]))
    table = totals.reindex(teams, fill_value=0)
    table.index.name = "Team"
    table = table.reset_index()
    table[["P", "GF", "GA", "Pts"]] = table[["P", "GF", "GA", "Pts"]].astype(int)

    table["GD"] = table["GF"] - table["GA"]
    table = table.sort_values(
        ["Pts", "GD", "GF", "Team"], ascending=[False, False, False, True]
    ).reset_index(drop=True)
    table["Position"] = table.index + 1
    return table


def last_complete_week(fixtures):
    """The highest matchweek N such that every match in weeks 1..N has been
    played. A week with an unplayed (e.g. postponed) match is not complete."""
    all_played = fixtures.groupby("Wk")["Played"].all()
    week = 0
    while all_played.get(week + 1, False):
        week += 1
    return week


def position_history(fixtures, team):
    """The team's league position after each fully played matchweek.
    `Level` is how many other teams had exactly the same points that week,
    which is where the tiebreaker rule could change the order."""
    rows = []
    for week in range(1, last_complete_week(fixtures) + 1):
        table = league_table(fixtures, week)
        me = table[table["Team"] == team].iloc[0]
        rows.append({
            "Wk": week,
            "Position": int(me["Position"]),
            "Pts": int(me["Pts"]),
            "GD": int(me["GD"]),
            "Level": int((table["Pts"] == me["Pts"]).sum()) - 1,
        })
    return pd.DataFrame(rows, columns=["Wk", "Position", "Pts", "GD", "Level"])