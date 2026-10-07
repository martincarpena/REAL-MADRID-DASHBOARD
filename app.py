import re
import pandas as pd
import streamlit as st
from data import (
    get_match_log,
    get_shooting_log,
    get_league_fixtures,
    last_downloaded,
    CURRENT_SEASON,
    LAST_SEASON,
)
from standings import clean_fixtures, league_table, position_history, unplayed_through

st.set_page_config(page_title="Real Madrid Dashboard", layout="wide")

THIS_COLOR = "#0068c9"  # this season: bold blue
LAST_COLOR = "#9aa0a6"  # last season: gray
TEAM = "Real Madrid"    # must match the team's name in FBref's league-wide table


def ordinal(n):
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4 -> '4th', 11 -> '11th', 21 -> '21st'"""
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def clean_opponent(name):
    # A flag-icon artifact leaks a 2-3 letter country code in front of some
    # opponent names (e.g. "it Inter"). Strip it.
    return re.sub(r"^[a-z]{2,3}\s+(?=[A-Z])", "", str(name))


def show_position_chart(positions):
    """Line chart of league position by matchweek with 1st place at the TOP.
    st.line_chart cannot flip its axis, so this uses Altair (installed with
    Streamlit). If anything about it fails, fall back to a plain line chart."""
    try:
        import altair as alt

        chart = (
            alt.Chart(positions)
            .mark_line(point=True)
            .encode(
                x=alt.X("Matchweek:Q", axis=alt.Axis(tickMinStep=1)),
                y=alt.Y(
                    "Position:Q",
                    title="League position (1 = top)",
                    scale=alt.Scale(domain=[20, 1]),  # reversed: 1 is at the top
                    axis=alt.Axis(values=[1, 5, 10, 15, 20]),
                ),
                color=alt.Color(
                    "Season:N",
                    scale=alt.Scale(domain=["This season", "Last season"], range=[THIS_COLOR, LAST_COLOR]),
                    legend=alt.Legend(title=None),
                ),
                tooltip=["Season", "Matchweek", "Position", "Pts"],
            )
            .properties(height=380)
        )
        try:
            st.altair_chart(chart, width="stretch")
        except TypeError:  # an older Streamlit without the width option
            st.altair_chart(chart)
    except Exception:
        wide = positions.pivot(index="Matchweek", columns="Season", values="Position")
        st.caption("Lower is better (1 = top of the table).")
        st.line_chart(wide, y=["This season", "Last season"], color=[THIS_COLOR, LAST_COLOR])


def prepare_league_games(schedule):
    """Played La Liga games only, in date