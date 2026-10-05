import re
import pandas as pd
import streamlit as st
from data import get_match_log, get_shooting_log, CURRENT_SEASON, LAST_SEASON

st.set_page_config(page_title="Real Madrid Dashboard", layout="wide")

# Streamlit remembers a cached function's result separately for each input,
# so load_schedule(CURRENT_SEASON) and load_schedule(LAST_SEASON) are two
# different cached scrapes.
@st.cache_data(ttl=3600)
def load_schedule(season):
    return get_match_log(season)

@st.cache_data(ttl=3600)
def load_shooting(season):
    return get_shooting_log(season)

def clean_opponent(name):
    # A flag-icon artifact leaks a 2-3 letter country code in front of some
    # opponent names (e.g. "it Inter"). Strip it.
    return re.sub(r"^[a-z]{2,3}\s+(?=[A-Z])", "", str(name))

def prepare_league_games(schedule):
    """Played La Liga games only, in date order, numbered Game 1, 2, 3..."""
    played = schedule[schedule["Result"].notna()].copy()
    league = played[played["Comp"] == "La Liga"].copy()

    # Sort by real date. Sorting by matchweek name breaks when a match is
    # rescheduled (this season's Matchweek 2 was played before Matchweek 1).
    league["Date"] = pd.to_datetime(league["Date"])
    league = league.sort_values("Date").reset_index(drop=True)

    # GF/GA come in as text from the scraped table — convert to real numbers
    league["GF"] = pd.to_numeric(league["GF"])
    league["GA"] = pd.to_numeric(league["GA"])
    league["Opponent"] = league["Opponent"].apply(clean_opponent)

    league["Points"] = league["Result"].map({"W": 3, "D": 1, "L": 0})
    league["Cumulative Points"] = league["Points"].cumsum()
    league["Game"] = league.index + 1
    league["Date"] = league["Date"].dt.strftime("%Y-%m-%d")
    return league

st.title("Real Madrid Analytics Dashboard")

tab1, tab2 = st.tabs(["Season Dashboard", "Match Stats"])

with tab1:
    with st.spinner("Loading this season and last season — first load takes about 20 seconds..."):
        this_league = prepare_league_games(load_schedule(CURRENT_SEASON))
        last_league = prepare_league_games(load_schedule(LAST_SEASON))

    st.header("Season Dashboard")
    n = len(this_league)

    if n == 0:
        st.info("No La Liga games played yet this season.")
    else:
        # Last season, cut off at the same number of games, for a fair comparison
        last_same_point = last_league[last_league["Game"] <= n]

        def record(games):
            return (
                int((games["Result"] == "W").sum()),
                int((games["Result"] == "D").sum()),
                int((games["Result"] == "L").sum()),
            )

        wins, draws, losses = record(this_league)
        last_wins, last_draws, last_losses = record(last_same_point)

        pts = int(this_league["Points"].sum())
        last_pts = int(last_same_point["Points"].sum())
        gf = int(this_league["GF"].sum())
        last_gf = int(last_same_point["GF"].sum())
        ga = int(this_league["GA"].sum())
        last_ga = int(last_same_point["GA"].sum())

        st.caption(f"After {n} La Liga games: this season vs. the same point last season")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Record (W-D-L)", f"{wins}-{draws}-{losses}")
        col1.caption(f"Last season: {last_wins}-{last_draws}-{last_losses}")
        col2.metric("Points", pts, delta=pts - last_pts)
        col3.metric("Goals For", gf, delta=gf - last_gf)
        col4.metric("Goals Against", ga, delta=ga - last_ga, delta_color="inverse")

        st.subheader("Cumulative Points by Games Played")
        view = st.radio(
            "Compare",
            ["Same point in the season", "Full last season"],
            horizontal=True,
        )

        # Both series are indexed by game number, so pandas lines them up
        # and leaves a gap where this season hasn't been played yet.
        chart = pd.DataFrame({
            "This season": this_league.set_index("Game")["Cumulative Points"],
            "Last season": last_league.set_index("Game")["Cumulative Points"],
        }).sort_index()

        if view == "Same point in the season":
            chart = chart.loc[:n]  # keep Game 1 through Game n only

        # Explicit colors: this season in bold blue, last season in gray.
        # Without this, Streamlit assigns its default colors alphabetically.
        st.line_chart(
            chart,
            y=["This season", "Last season"],
            color=["#0068c9", "#9aa0a6"],
        )

        with st.expander("See the matches behind these numbers"):
            show = ["Game", "Date", "Opponent", "Venue", "Result", "GF", "GA"]
            left, right = st.columns(2)
            left.subheader("This season")
            left.dataframe(this_league[show], hide_index=True)
            right.subheader(f"Last season (first {n} games)")
            right.dataframe(last_same_point[show], hide_index=True)

with tab2:
    with st.spinner("Loading shooting data — this takes about 10 seconds on first load..."):
        shooting = load_shooting(CURRENT_SEASON)

    # FBref bakes its own "Totals" summary row into this table (Date/Opponent
    # are blank, Sh/SoT hold the season sum). Drop it — it isn't a real match.
    shooting = shooting[shooting["Date"].notna()].copy()
    shooting["Opponent"] = shooting["Opponent"].apply(clean_opponent)

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
    st.dataframe(shooting[display_cols])