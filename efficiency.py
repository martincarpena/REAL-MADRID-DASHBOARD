"""Efficiency numbers for the Efficiency Stats tab.

Every function here takes the cleaned match table that app.py builds with
prepare_shooting(): one row per match, with the columns Game, Venue, Result,
GF, GA, Gls, Sh, SoT, PK and PKatt.

There is no Streamlit in this file on purpose. It only does the maths, so it
can be tested on its own, and app.py only has to display the results.
"""
import pandas as pd

POINTS = {"W": 3, "D": 1, "L": 0}

# Label shown in the app -> column in the match table.
# "Points" is the one exception: it is worked out from the Result column.
ROLLING_METRICS = {
    "Points": "Points",
    "Goals scored": "GF",
    "Goals conceded": "GA",
    "Shots": "Sh",
    "Shots on target": "SoT",
}

VENUE_ORDER = {"Home": 0, "Away": 1}


def divide(top, bottom):
    """top / bottom, or None when bottom is 0 (for example shots per goal
    before a single goal has been scored). The app shows None as a dash."""
    return top / bottom if bottom else None


def efficiency_summary(matches):
    """One dictionary of efficiency numbers for a set of matches."""
    games = len(matches)
    points = int(matches["Result"].map(POINTS).sum())
    wins = int((matches["Result"] == "W").sum())
    goals_for = int(matches["GF"].sum())
    goals_against = int(matches["GA"].sum())
    shots = int(matches["Sh"].sum())
    on_target = int(matches["SoT"].sum())
    shooting_goals = int(matches["Gls"].sum())  # goals in FBref's shooting table

    return {
        "Games": games,
        "Points per game": divide(points, games),
        "Win %": divide(100 * wins, games),
        "Goals per game": divide(goals_for, games),
        "Conceded per game": divide(goals_against, games),
        "Shots per goal": divide(shots, shooting_goals),
        "Shots on target per goal": divide(on_target, shooting_goals),
        "Clean sheets": int((matches["GA"] == 0).sum()),
        "Failed to score": int((matches["GF"] == 0).sum()),
        "Penalties scored": int(matches["PK"].sum()),
        "Penalties taken": int(matches["PKatt"].sum()),
    }


def rolling_average(matches, label, window):
    """The average of one metric over the last `window` matches, for every
    match. The first window-1 matches have no value yet (not enough history),
    so the line starts at match number `window`."""
    column = ROLLING_METRICS[label]
    if column == "Points":
        values = matches["Result"].map(POINTS)
    else:
        values = matches[column]
    values = pd.Series(values.to_numpy(), index=matches["Game"].to_numpy())
    return values.rolling(window).mean()


def venue_split(matches):
    """Home vs away: one row per venue with record, points and goals."""
    columns = ["Venue", "Games", "W", "D", "L", "Points", "Points per game",
               "GF", "GA", "Shots", "Shots on target"]
    rows = []
    for venue, games in matches.groupby("Venue"):
        points = int(games["Result"].map(POINTS).sum())
        rows.append({
            "Venue": venue,
            "Games": len(games),
            "W": int((games["Result"] == "W").sum()),
            "D": int((games["Result"] == "D").sum()),
            "L": int((games["Result"] == "L").sum()),
            "Points": points,
            "Points per game": round(points / len(games), 2),
            "GF": int(games["GF"].sum()),
            "GA": int(games["GA"].sum()),
            "Shots": int(games["Sh"].sum()),
            "Shots on target": int(games["SoT"].sum()),
        })
    table = pd.DataFrame(rows, columns=columns)
    table["order"] = table["Venue"].map(VENUE_ORDER).fillna(2)
    return table.sort_values("order").drop(columns="order").reset_index(drop=True)