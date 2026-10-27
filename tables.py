"""Looks for the tables.

Streamlit draws a table (a "dataframe") from a pandas table. Wrapping the pandas
table in a "Styler" lets us control how single cells look:

  - numbers print cleanly (2, not 2.000000), and an empty cell shows a dash
  - in a league table, the team's own row is tinted gold and bold
  - the W, D and L in a Result column are coloured like the circles under the banner

There is no Streamlit in this file on purpose. It only prepares the tables.
"""

import pandas as pd

# The look of one Result cell: a soft background with darker text of the same colour
RESULT_STYLES = {
    "W": "background-color: #173A2B; color: #6FE0A8; font-weight: 700",
    "D": "background-color: #2B303A; color: #B4BBC8; font-weight: 700",
    "L": "background-color: #412522; color: #FF8F85; font-weight: 700",
}

TEAM_ROW = "background-color: #3A3220; color: #F0D27A; font-weight: 700"   # the team's own row
EMPTY = "–"                                                # shown instead of a blank

# Streamlit draws one table row about this tall (the header is one more row)
ROW_HEIGHT = 35


def fit_height(rows):
    """The height in pixels that shows `rows` rows plus the header, with no
    empty grid underneath and no scrolling."""
    return ROW_HEIGHT * (rows + 1) + 3


def _decimals(column):
    """How many decimals a column of numbers needs, at most 2: a column of
    2.0 and 3.0 needs none, 55.1 and 28.6 needs one, 1.01 needs two."""
    needed = 0
    for value in column.dropna():
        for places in (0, 1, 2):
            if abs(round(value, places) - value) < 1e-9:
                needed = max(needed, places)
                break
        else:
            return 2
    return needed


def _result_style(value):
    """The style for one cell: the colours above for W, D and L, nothing else."""
    return RESULT_STYLES.get(value, "")


def _team_row(table, team):
    """A table of CSS, the same shape as `table`, with the team's row (found
    in the Team column) tinted gold and bold and every other cell empty."""
    styles = pd.DataFrame("", index=table.index, columns=table.columns)
    styles.loc[table["Team"] == team, :] = TEAM_ROW
    return styles


def _dash_empty(table):
    """A copy of the table where every empty cell reads "–". Streamlit draws an
    empty cell as "None" whatever the Styler says, so a column that has empty
    cells is turned into text. (A text column sorts as text, which only matters
    for the few columns that have a gap.)"""
    table = table.copy()
    for name in table.columns:
        if not table[name].isna().any():
            continue
        if pd.api.types.is_float_dtype(table[name]):
            places = _decimals(table[name])
            table[name] = table[name].map(lambda v: EMPTY if pd.isna(v) else f"{v:.{places}f}")
        else:
            table[name] = table[name].astype(object).where(table[name].notna(), EMPTY)
    return table


def style_table(table, team=None):
    """The table with every look above applied. `team` is the name to tint in
    a league table (needs a Team column); leave it out for other tables."""
    table = _dash_empty(table)
    styler = table.style

    # Numbers: whole numbers without decimals, and the same decimals down a column
    styler = styler.format(na_rep=EMPTY)
    for name in table.columns:
        if pd.api.types.is_float_dtype(table[name]):
            styler = styler.format(f"{{:.{_decimals(table[name])}f}}", subset=[name], na_rep=EMPTY)

    # The team's row, then the Result colours
    if team is not None and "Team" in table.columns:
        styler = styler.apply(_team_row, team=team, axis=None)
    if "Result" in table.columns:
        # Newer pandas calls this .map, older pandas .applymap
        paint = getattr(styler, "map", None) or styler.applymap
        styler = paint(_result_style, subset=["Result"])
    return styler