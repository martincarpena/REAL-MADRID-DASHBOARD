"""Turns one player's saved match log into the numbers a report needs.

player_data.py downloads and saves a match log for each player (one row per
match, every competition, club and national team together). This file only
does arithmetic on that table: it keeps the Real Madrid matches, adds a few
helpful columns, and adds things up. There is no Streamlit here on purpose,
so every function can be tested on its own.

Run `python3 player_report.py` to print the report of the player with the
most minutes. It is a quick way to check the numbers against FBref."""
import pandas as pd

TEAM = "Real Madrid"

# Plain counts: the number of goals, shots, cards... in a match.
COUNT_COLUMNS = ["Gls", "Ast", "PK", "PKatt", "Sh", "SoT", "CrdY", "CrdR",
                 "Fls", "Fld", "Off", "Crs", "TklW", "Int", "OG"]

# The totals shown at the top of a report: (label, column in the match table).
TOTAL_COLUMNS = [("Goals", "Gls"), ("Assists", "Ast"), ("Goals + assists", "G+A"),
                 ("Shots", "Sh"), ("Shots on target", "SoT"),
                 ("Yellow cards", "CrdY"), ("Red cards", "CrdR"),
                 ("Fouls committed", "Fls"), ("Fouls drawn", "Fld"),
                 ("Offsides", "Off"), ("Crosses", "Crs"),
                 ("Tackles won", "TklW"), ("Interceptions", "Int")]

# The numbers that are also shown per 90 minutes.
PER_90_COLUMNS = [("Goals", "Gls"), ("Assists", "Ast"), ("Goals + assists", "G+A"),
                  ("Shots", "Sh"), ("Shots on target", "SoT"),
                  ("Fouls committed", "Fls"), ("Fouls drawn", "Fld"),
                  ("Crosses", "Crs"), ("Tackles won", "TklW"), ("Interceptions", "Int")]


def _numbers(series):
    """Turns a column into numbers. Blanks become 0."""
    return pd.to_numeric(series, errors="coerce").fillna(0)


def club_matches(log, team=TEAM):
    """One row per match for `team`, oldest first, with the columns cleaned up
    and a few new ones:
      Played   True if he was on the pitch (more than 0 minutes)
      Started  True if he was in the starting eleven
      Outcome  W, D or L
      GF, GA   goals for and against, from the team's point of view
      G+A      goals plus assists"""
    log = log.copy()
    # In international competitions FBref puts the country code in front of a
    # team's name ("es Real Madrid", "it Inter"). Remove it so that the same
    # team always has the same name.
    for column in ["Squad", "Opponent"]:
        log[column] = log[column].str.replace(r"^[a-z]{2,3}\s+", "", regex=True)

    matches = log[log["Squad"] == team].copy()
    matches["Date"] = pd.to_datetime(matches["Date"], errors="coerce")
    matches = matches.sort_values("Date").reset_index(drop=True)

    matches["Min"] = _numbers(matches["Min"])
    for column in COUNT_COLUMNS:
        # A column missing from the saved table counts as zero.
        matches[column] = _numbers(matches[column]) if column in matches.columns else 0
    matches["G+A"] = matches["Gls"] + matches["Ast"]

    matches["Played"] = matches["Min"] > 0
    matches["Started"] = matches["Start"].astype(str).str.startswith("Y")

    # "W 2–1" -> W, 2, 1. A shoot-out like "D 1–1 (4–3)" uses the first score.
    result = matches["Result"].astype(str)
    matches["Outcome"] = result.str[0]
    scores = result.str.extract(r"(\d+)\s*[–-]\s*(\d+)").astype(float)
    matches["GF"] = scores[0]
    matches["GA"] = scores[1]
    return matches


def season_totals(matches):
    """The headline numbers, as an ordered dict {label: value}."""
    played = matches[matches["Played"]]
    totals = {
        "Matches played": len(played),
        "Starts": int(played["Started"].sum()),
        "Minutes": int(played["Min"].sum()),
    }
    for label, column in TOTAL_COLUMNS:
        totals[label] = int(played[column].sum())
    totals["Unused substitute"] = int((~matches["Played"]).sum())
    return totals


def per_90(matches):
    """Each of the numbers in PER_90_COLUMNS per 90 minutes played, as {label: value}.
    Empty when he has not played yet."""
    played = matches[matches["Played"]]
    minutes = played["Min"].sum()
    if minutes == 0:
        return {}
    return {label: played[column].sum() / minutes * 90 for label, column in PER_90_COLUMNS}


def _summary(played, group_column):
    """Adds up the matches for each value of group_column (for example each competition)."""
    grouped = played.groupby(group_column)
    table = pd.DataFrame({
        "Matches": grouped.size(),
        "Starts": grouped["Started"].sum().astype(int),
        "Min": grouped["Min"].sum().astype(int),
        "Gls": grouped["Gls"].sum().astype(int),
        "Ast": grouped["Ast"].sum().astype(int),
        "Sh": grouped["Sh"].sum().astype(int),
        "SoT": grouped["SoT"].sum().astype(int),
        "CrdY": grouped["CrdY"].sum().astype(int),
    })
    return table.sort_values("Min", ascending=False).reset_index()


def by_competition(matches):
    """One row per competition: matches, starts, minutes, goals, assists, shots, cards."""
    return _summary(matches[matches["Played"]], "Comp")


def by_venue(matches):
    """The same, split into Home and Away."""
    return _summary(matches[matches["Played"]], "Venue")


def positions_played(matches):
    """How many matches he played in each position, most common first."""
    played = matches[matches["Played"]]
    counts = played["Pos"].value_counts()
    return counts.rename_axis("Position").reset_index(name="Matches")


def running_totals(matches):
    """For each match he played, his goals, assists and goals + assists so far this season."""
    played = matches[matches["Played"]].reset_index(drop=True)
    table = pd.DataFrame({
        "Match": range(1, len(played) + 1),
        "Date": played["Date"],
        "Opponent": played["Opponent"],
        "Goals": played["Gls"].cumsum().astype(int),
        "Assists": played["Ast"].cumsum().astype(int),
    })
    table["Goals + assists"] = table["Goals"] + table["Assists"]
    return table


if __name__ == "__main__":
    from player_data import get_player_matches, get_roster, top_players

    star = top_players(get_roster()).iloc[0]
    matches = club_matches(get_player_matches(star["Link"]))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)

    print(f"{star['Player']}: {len(matches)} {TEAM} matches in his match log\n")
    print("TOTALS")
    for label, value in season_totals(matches).items():
        print(f"  {label:<20}{value}")
    print("\nPER 90 MINUTES")
    for label, value in per_90(matches).items():
        print(f"  {label:<20}{value:.2f}")
    print("\nBY COMPETITION")
    print(by_competition(matches).to_string(index=False))
    print("\nHOME / AWAY")
    print(by_venue(matches).to_string(index=False))
    print("\nPOSITIONS")
    print(positions_played(matches).to_string(index=False))
    print("\nRUNNING TOTALS (last 3 matches)")
    print(running_totals(matches).tail(3).to_string(index=False))