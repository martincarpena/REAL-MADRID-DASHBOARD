import re
import pandas as pd
import streamlit as st
from data import get_match_log, get_shooting_log

st.set_page_config(page_title="Real Madrid Dashboard", layout="wide")

@st.cache_data(ttl=3600)
def load_schedule():
    return get_match_log()

@st.cache_data(ttl=3600)
def load_shooting():
    return get_shooting_log()

st.title("Real Madrid Analytics Dashboard")

tab1, tab2 = st.tabs(["Season Dashboard", "Match Stats"])

with tab1:
    with st.spinner("Loading match data — this takes about 10 seconds on first load..."):
        df = load_schedule()

    played = df[df["Result"].notna()].copy()
    league = played[played["Comp"] == "La Liga"].copy()
    league["GF"] = pd.to_numeric(league["GF"])
    league["GA"] = pd.to_numeric(league["GA"])

    st.header("Season Dashboard")

    wins = (league["Result"] == "W").sum()
    draws = (league["Result"] == "D").sum()
    losses = (league["Result"] == "L").sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("La Liga Record", f"{wins}-{draws}-{losses}")
    col2.metric("Goals For", int(league["GF"].sum()))
    col3.metric("Goals Against", int(league["GA"].sum()))

    def result_to_points(result):
        if result == "W":
            return 3
        elif result == "D":
            return 1
        return 0

    league["Points"] = league["Result"].apply(result_to_points)
    league["Cumulative Points"] = league["Points"].cumsum()

    st.subheader("Points by Matchweek")
    st.line_chart(league.set_index("Round")["Cumulative Points"])

with tab2:
    with st.spinner("Loading shooting data — this takes about 10 seconds on first load..."):
        shooting = load_shooting()

    # FBref bakes its own "Totals" summary row into this table (Date/Opponent
    # are blank, Sh/SoT hold the season sum). Drop it — it isn't a real match
    # and would throw off every stat below.
    shooting = shooting[shooting["Date"].notna()].copy()

    # A small flag-icon artifact leaks a 2-3 letter country code in front of
    # some opponent names (e.g. "it Inter" instead of "Inter"). Strip it.
    shooting["Opponent"] = shooting["Opponent"].apply(
        lambda name: re.sub(r"^[a-z]{2,3}\s+(?=[A-Z])", "", str(name))
    )

    numeric_cols = ["GF", "GA", "Gls", "Sh", "SoT", "SoT%", "G/Sh", "G/SoT", "PK", "PKatt"]
    for col in numeric_cols:
        shooting[col] = pd.to_numeric(shooting[col])

    st.header("Match Stats")

    total_shots = shooting["Sh"].sum()
    total_sot = shooting["SoT"].sum()
    shot_accuracy = (total_sot / total_shots * 100) if total_shots > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Shots", int(total_shots))
    col2.metric("Shots on Target", int(total_sot))
    col3.metric("Shot Accuracy", f"{shot_accuracy:.1f}%")

    st.subheader("Match-by-Match Breakdown")
    display_cols = ["Date", "Comp", "Opponent", "Result", "GF", "GA", "Sh", "SoT", "SoT%"]
    st.dataframe(shooting[display_cols], use_container_width=True)