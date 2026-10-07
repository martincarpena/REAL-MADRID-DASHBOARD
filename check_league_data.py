from data import (
    get_league_fixtures,
    get_match_log,
    CURRENT_SEASON,
    LAST_SEASON,
)
from standings import clean_fixtures, last_complete_week, league_table, position_history
import pandas as pd

# Run this with:  python3 check_league_data.py
# It downloads the league-wide fixtures if they are not saved yet, cleans
# them, and then checks the result against a second, independent source:
# Real Madrid's own match log. If the two disagree, we find out here, before
# any dashboard is built on top of the numbers.

TEAM = "Real Madrid"

for season in [LAST_SEASON, CURRENT_SEASON]:
    print("=" * 64)
    print(f"  {season}")
    print("=" * 64)

    raw = get_league_fixtures(season)
    fixtures = clean_fixtures(raw)
    teams = sorted(set(fixtures["Home"]) | set(fixtures["Away"]))

    print(f"rows in the saved table: {len(raw)}  ->  real fixtures: {len(fixtures)}")
    print(f"teams: {len(teams)} | matchweeks: {fixtures['Wk'].min()} to {fixtures['Wk'].max()}")
    print(f"played: {int(fixtures['Played'].sum())} | not played yet: {int((~fixtures['Played']).sum())}")

    last = last_complete_week(fixtures)
    print(f"matchweeks fully played: {last}")
    if last < fixtures["Wk"].max():
        print(f"  first matchweek with an unplayed match: {last + 1}")

    # ---- Cross-check: Real Madrid's results, from two different pages ----
    mine = fixtures[fixtures["Played"] & ((fixtures["Home"] == TEAM) | (fixtures["Away"] == TEAM))]
    from_league_page = pd.DataFrame({
        "Date": mine["Date"].astype(str),
        "Opponent": mine["Away"].where(mine["Home"] == TEAM, mine["Home"]),
        "GF": mine["HomeGoals"].where(mine["Home"] == TEAM, mine["AwayGoals"]),
        "GA": mine["AwayGoals"].where(mine["Home"] == TEAM, mine["HomeGoals"]),
    })

    team_page = get_match_log(season)
    team_page = team_page[(team_page["Comp"] == "La Liga") & team_page["Result"].notna()]
    from_team_page = pd.DataFrame({
        "Date": team_page["Date"].astype(str),
        "GF": pd.to_numeric(team_page["GF"]),
        "GA": pd.to_numeric(team_page["GA"]),
    })

    both = from_league_page.merge(
        from_team_page, on="Date", how="outer", suffixes=("_league", "_team"), indicator=True
    )
    agree = (
        (both["_merge"] == "both")
        & (both["GF_league"] == both["GF_team"])
        & (both["GA_league"] == both["GA_team"])
    )
    print(f"\n{TEAM} cross-check: {int(agree.sum())} of {len(both)} matches agree "
          "between the league-wide page and Real Madrid's own page")
    if not agree.all():
        print("DISAGREEMENTS:")
        print(both[~agree].to_string(index=False))

    # ---- The result we actually want ----
    history = position_history(fixtures, TEAM)
    print(f"\n{TEAM}'s position after each fully played matchweek:")
    print(history.head(10).to_string(index=False))
    if len(history) > 10:
        print("   ...")
        print(history.tail(1).to_string(index=False))
    print(f"(weeks where {TEAM} was level on points with another team: "
          f"{int((history['Level'] > 0).sum())} of {len(history)}; the order within a tie can differ "
          "from the official one)")

    table = league_table(fixtures, last)
    print(f"\nTable after matchweek {last} (top 5):")
    print(table.head(5).to_string(index=False))
    print()