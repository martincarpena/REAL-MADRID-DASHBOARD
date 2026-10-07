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


def _record(matches):
    """Games played, goals for/against and points for each team, from a set of
    played matches. Each match counts twice: once from the home team's side,
    once from the away team's."""
    home = pd.DataFrame({"Team": matches["Home"], "GF": matches["HomeGoals"], "GA": matches["AwayGoals"]})
    away = pd.DataFrame({"Team": matches["Away"], "GF": matches["AwayGoals"], "GA": matches["HomeGoals"]})
    games = pd.concat([home, away], ignore_index=True)
    games["Pts"] = (games["GF"] > games["GA"]) * 3 + (games["GF"] == games["GA"]) * 1
    games["P"] = 1
    return games.groupby("Team")[["P", "GF", "GA", "Pts"]].sum()


def league_table(fixtures, week):
    """The league table after `week` matchweeks: every played match from
    matchweeks 1..week counts.

    Teams are ranked with La Liga's official order: points first. Teams level
    on points are then ordered by their head-to-head record (points, then
    goal difference in the matches played only between the teams that are
    level), then overall goal difference, then goals scored, then name.
    When more than two teams are level, the head-to-head record is worked out
    across all of them together, which is a slight simplification of the
    official procedure."""
    played = fixtures[fixtures["Played"] & (fixtures["Wk"] <= week)]

    # Include every team, even one that has not played yet (all zeros).
    teams = sorted(set(fixtures["Home"]) | set(fixtures["Away"]))
    table = _record(played).reindex(teams, fill_value=0)
    table.index.name = "Team"
    table = table.reset_index()
    table[["P", "GF", "GA", "Pts"]] = table[["P", "GF", "GA", "Pts"]].astype(int)
    table["GD"] = table["GF"] - table["GA"]

    # Head-to-head record, worked out separately for each group of teams that
    # are level on points. Teams that have not played each other get 0 and 0.
    h2h_points, h2h_goal_diff = {}, {}
    for _, level in table.groupby("Pts"):
        if len(level) < 2:
            continue
        group = set(level["Team"])
        between = played[played["Home"].isin(group) & played["Away"].isin(group)]
        mini = _record(between)
        for team in mini.index:
            h2h_points[team] = int(mini.loc[team, "Pts"])
            h2h_goal_diff[team] = int(mini.loc[team, "GF"] - mini.loc[team, "GA"])
    table["H2HPts"] = table["Team"].map(h2h_points).fillna(0).astype(int)
    table["H2HGD"] = table["Team"].map(h2h_goal_diff).fillna(0).astype(int)

    table = table.sort_values(
        ["Pts", "H2HPts", "H2HGD", "GD", "GF", "Team"],
        ascending=[False, False, False, False, False, True],
    ).reset_index(drop=True)
    table["Position"] = table.index + 1
    return table.drop(columns=["H2HPts", "H2HGD"])


def last_complete_week(fixtures):
    """The highest matchweek N such that every match in weeks 1..N has been
    played. A week with an unplayed (e.g. postponed) match is not complete."""
    all_played = fixtures.groupby("Wk")["Played"].all()
    week = 0
    while all_played.get(week + 1, False):
        week += 1
    return week


def latest_week_played(fixtures, team):
    """The latest matchweek in which `team` has played a match (0 if none)."""
    mine = fixtures[fixtures["Played"] & ((fixtures["Home"] == team) | (fixtures["Away"] == team))]
    return int(mine["Wk"].max()) if len(mine) else 0


def unplayed_through(fixtures, week):
    """Matches from matchweeks 1..week that have not been played yet, for
    example postponed ones."""
    late = fixtures[~fixtures["Played"] & (fixtures["Wk"] <= week)]
    return late[["Wk", "Date", "Home", "Away"]].reset_index(drop=True)


def position_history(fixtures, team):
    """The team's league position after each matchweek it has played, from
    matchweek 1 up to its latest played match.

    Each matchweek's table counts every match played so far in weeks 1..that
    week, like a real league table: if an earlier match was postponed, the
    teams involved simply have a game in hand.
    `Missing` is how many matches from weeks 1..that week are still unplayed.
    `Level` is how many other teams had exactly the same points that week,
    which is when the tiebreaker rules decide the order."""
    rows = []
    for week in range(1, latest_week_played(fixtures, team) + 1):
        table = league_table(fixtures, week)
        me = table[table["Team"] == team].iloc[0]
        rows.append({
            "Wk": week,
            "Position": int(me["Position"]),
            "Pts": int(me["Pts"]),
            "GD": int(me["GD"]),
            "Level": int((table["Pts"] == me["Pts"]).sum()) - 1,
            "Missing": int((~fixtures["Played"] & (fixtures["Wk"] <= week)).sum()),
        })
    return pd.DataFrame(rows, columns=["Wk", "Position", "Pts", "GD", "Level", "Missing"])