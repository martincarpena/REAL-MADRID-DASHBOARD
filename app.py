import pandas as pd
import streamlit as st
from data import get_match_log

st.set_page_config(page_title="Real Madrid Dashboard", layout="wide")

@st.cache_data(ttl=3600)
def load_data():
    return get_match_log()

st.title("Real Madrid Analytics Dashboard")

with st.spinner("Loading match data — this takes about 10 seconds on first load..."):
    df = load_data()

# Future fixtures have no Result yet — drop those, we only want played matches
played = df[df["Result"].notna()].copy()

# For now, focus on La Liga only: it's the only competition here with clean
# "Matchweek N" rounds we can read in order. Champions League is a good next addition.
league = played[played["Comp"] == "La Liga"].copy()

# GF/GA come in as text from the scraped table — convert to real numbers
# before doing any math with them, or .sum() glues digits together instead
# of adding them.
league["GF"] = pd.to_numeric(league["GF"])
league["GA"] = pd.to_numeric(league["GA"])

st.header("Season Dashboard")

wins = (league["Result"] == "W").sum()
draws = (league["Result"] == "D").sum()
losses = (league["Result"] == "L").sum()
goals_for = league["GF"].sum()
goals_against = league["GA"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("La Liga Record", f"{wins}-{draws}-{losses}")
col2.metric("Goals For", int(goals_for))
col3.metric("Goals Against", int(goals_against))

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