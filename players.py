"""Player numbers for the Player Stats tab.

clean_players() takes the table that data.get_players() returns: one row per
player from FBref's squad page, plus two total rows. Everything else here takes
the cleaned table that clean_players() builds.

There is no Streamlit in this file on purpose. It only does the maths, so it
can be tested on its own, and app.py only has to display the results.
"""
import pandas as pd

TOTAL_ROWS = ["Squad Total", "Opponent Total"]

# A blank here means the player has nothing yet (no minutes, no shots), so zero.
COUNT_COLUMNS = ["MP", "Starts", "Min", "Gls", "Ast", "G+A", "G-PK", "PK", "PKatt",
                 "CrdY", "CrdR", "Sh", "SoT"]

# Rates and percentages. A blank means the rate cannot be worked out (for
# example shooting accuracy for a player with no shots), so it stays blank.
RATE_COLUMNS = ["90s", "Gls/90", "Ast/90", "G+A/90", "G-PK/90", "G+A-PK/90",
                "SoT%", "Sh/90", "SoT/90", "G/Sh", "G/SoT"]

# Label shown in the app -> column in the player table.
LEADER_METRICS = {
    "Goals": "Gls",
    "Assists": "Ast",
    "Goals + assists": "G+A",
    "Shots": "Sh",
    "Shots on target": "SoT",
    "Minutes played": "Min",
    "Yellow cards": "CrdY",
}


def clean_players(raw):
    """One tidy row per player: no total rows, the nation as a three-letter
    code, the age as whole years, and real numbers in every number column."""
    players = raw[raw["Player"].notna() & ~raw["Player"].isin(TOTAL_ROWS)].copy()

    # FBref shows a flag-icon artifact in front of the nation: "fr FRA" -> "FRA"
    nation = players["Nation"].astype("string").str.strip()
    players["Nation"] = nation.str.split().str[-1]

    # Ages come as "27-293" (27 years and 293 days). Keep the whole years.
    age_years = players["Age"].astype("string").str.extract(r"^(\d+)", expand=False)
    players["Age"] = pd.to_numeric(age_years, errors="coerce")

    for col in COUNT_COLUMNS:
        players[col] = pd.to_numeric(players[col], errors="coerce").fillna(0).astype(int)
    for col in RATE_COLUMNS:
        players[col] = pd.to_numeric(players[col], errors="coerce")

    return players.reset_index(drop=True)


def leaders(players, column, n=10):
    """The top n players for one column, best first. Players on zero are left
    out, because a leaderboard of zeros says nothing. Ties are in name order."""
    ranked = players[players[column] > 0].sort_values([column, "Player"], ascending=[False, True])
    return ranked.head(n)[["Player", column]].reset_index(drop=True)


def top_player(players, column):
    """(name, value) of the single best player in a column, or None when
    nobody has anything yet."""
    best = leaders(players, column, n=1)
    if len(best) == 0:
        return None
    return best.iloc[0]["Player"], int(best.iloc[0][column])


def squad_table(this_players, last_players):
    """This season's squad with last season's full-season totals beside it.
    A player who was not in the squad last season has blanks there."""
    last = last_players[["Player", "MP", "Min", "Gls", "Ast"]].rename(columns={
        "MP": "MP last season",
        "Min": "Min last season",
        "Gls": "Gls last season",
        "Ast": "Ast last season",
    })
    return this_players.merge(last, on="Player", how="left")