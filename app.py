import re
import pandas as pd
import streamlit as st
from data import (
    get_match_log,
    get_shooting_log,
    last_downloaded,
    CURRENT_SEASON,
    LAST_SEASON,
)

st.set_page_config(page_title="Real Madrid Dashboard", layout="wide")

THIS_COLOR = "#0068c9"  # this season: bold blue
LAST_COLOR = "#9aa0a6"  # last season: gray


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
    # Rows whose date doesn't parse (stray header rows) are dropped.
    league["Date"] = pd.to_datetime(league["Date"], format="%Y-%m-%d", errors="coerce")
    league = league[league["Date"].notna()]
    league = league.sort_values("Date").reset_index(drop=True)

    # GF/GA can come in as text — convert to real numbers
    league["GF"] = pd.to_numeric(league["GF"])
    league["GA"] = pd.to_numeric(league["GA"])
    league["Opponent"] = league["Opponent"].apply(clean_opponent)

    league["Points"] = league["Result"].map({"W": 3, "D": 1, "L": 0})
    league["Cumulative Points"] = league["Points"].cumsum()
    league["Game"] = league.index + 1
    league["Date"] = league["Date"].dt.strftime("%Y-%m-%d")
    return league


SHOOTING_NUMERIC_COLS = ["GF", "GA", "Gls", "Sh", "SoT", "SoT%", "G/Sh", "G/SoT", "PK", "PKatt"]


def prepare_shooting(shooting, league_only):
    """Clean the scraped shooting table, optionally keep only La Liga, then
    put the matches in date order and number them Game 1, 2, 3..."""
    shooting = shooting.copy()

    # Long FBref tables repeat their header row every ~25 rows, and the table
    # ends with a "Totals" row. pandas reads all of those as data rows. A real
    # match has a real date; header rows ("For Real Madrid", "Date") and the
    # totals row (blank date) don't. Keep only rows whose Date parses.
    shooting["Date"] = pd.to_datetime(shooting["Date"], format="%Y-%m-%d", errors="coerce")
    shooting = shooting[shooting["Date"].notna()].copy()

    if league_only:
        shooting = shooting[shooting["Comp"] == "La Liga"].copy()

    # Numbers can arrive as text — convert before any math
    for col in SHOOTING_NUMERIC_COLS:
        shooting[col] = pd.to_numeric(shooting[col])
    shooting["Opponent"] = shooting["Opponent"].apply(clean_opponent)

    shooting = shooting.sort_values("Date").reset_index(drop=True)
    shooting["Game"] = shooting.index + 1
    shooting["Date"] = shooting["Date"].dt.strftime("%Y-%m-%d")
    return shooting


def shot_summary(matches):
    shots = int(matches["Sh"].sum())
    on_target = int(matches["SoT"].sum())
    goals = int(matches["Gls"].sum())
    accuracy = on_target / shots * 100 if shots else 0.0
    conversion = goals / shots * 100 if shots else 0.0
    return shots, on_target, accuracy, conversion


st.title("Real Madrid Analytics Dashboard")

# ---- Sidebar: when the data was downloaded, and a button to refresh it ----
with st.sidebar:
    st.header("Data")
    st.caption(f"This season's data last downloaded: {last_downloaded(CURRENT_SEASON) or 'never'}")
    st.caption("Last season is final, so it is downloaded only once.")
    if st.button("Refresh this season's data"):
        with st.spinner("Downloading from FBref — opens Chrome twice, about a minute..."):
            try:
                get_match_log(CURRENT_SEASON, refresh=True)
                get_shooting_log(CURRENT_SEASON, refresh=True)
            except Exception as error:
                st.error(f"Refresh failed: {error}")
            else:
                st.rerun()

# ---- Load all four tables. They come from saved files on disk; anything ----
# ---- missing is downloaded once (slow), then saved for next time.        ----
with st.spinner("Loading data. The very first time, this downloads four pages from FBref and can take a few minutes..."):
    try:
        this_sched = get_match_log(CURRENT_SEASON)
        last_sched = get_match_log(LAST_SEASON)
        this_shoot = get_shooting_log(CURRENT_SEASON)
        last_shoot = get_shooting_log(LAST_SEASON)
    except Exception as error:
        st.error(f"Could not load the data: {error}")
        st.info("Run `python3 data.py` in the terminal to see the full error and to download the data files.")
        st.stop()

tab1, tab2 = st.tabs(["Season Dashboard", "Match Stats"])

with tab1:
    this_league = prepare_league_games(this_sched)
    last_league = prepare_league_games(last_sched)

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

        st.line_chart(
            chart,
            y=["This season", "Last season"],
            color=[THIS_COLOR, LAST_COLOR],
        )

        with st.expander("See the matches behind these numbers"):
            show = ["Game", "Date", "Opponent", "Venue", "Result", "GF", "GA"]
            left, right = st.columns(2)
            left.subheader("This season")
            left.dataframe(this_league[show], hide_index=True)
            right.subheader(f"Last season (first {n} games)")
            right.dataframe(last_same_point[show], hide_index=True)

with tab2:
    st.header("Match Stats")

    scope = st.radio(
        "Competitions",
        ["All competitions", "La Liga only"],
        horizontal=True,
    )
    league_only = scope == "La Liga only"

    this_matches = prepare_shooting(this_shoot, league_only)
    last_matches = prepare_shooting(last_shoot, league_only)
    n_matches = len(this_matches)

    if n_matches == 0:
        st.info("No matches played yet in this selection.")
    else:
        # Last season, cut off at the same number of matches
        last_same_point = last_matches[last_matches["Game"] <= n_matches]

        shots, sot, accuracy, conversion = shot_summary(this_matches)
        last_shots, last_sot, last_accuracy, last_conversion = shot_summary(last_same_point)

        st.caption(
            f"After {n_matches} matches: this season vs. the first {n_matches} matches last season. "
            "Accuracy = shots on target ÷ shots. Conversion = goals from shots ÷ shots, using "
            "FBref's shooting-table goals (Gls), which can be lower than the match score "
            "when the opponent scores an own goal."
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Shots", shots, delta=shots - last_shots)
        col2.metric("Shots on Target", sot, delta=sot - last_sot)
        col3.metric("Shot Accuracy", f"{accuracy:.1f}%",
                    delta=f"{accuracy - last_accuracy:.1f} pp")
        col4.metric("Conversion", f"{conversion:.1f}%",
                    delta=f"{conversion - last_conversion:.1f} pp")

        st.subheader("Trend by Match")
        trend_options = {
            "Shots": "Sh",
            "Shots on target": "SoT",
            "Shot accuracy (%)": "SoT%",
            "Goals (match score)": "GF",
            "Goals from shots": "Gls",
        }
        trend_label = st.selectbox("Trend metric", list(trend_options))
        trend_col = trend_options[trend_label]

        trend = pd.DataFrame({
            "This season": this_matches.set_index("Game")[trend_col],
            "Last season": last_same_point.set_index("Game")[trend_col],
        })
        st.line_chart(
            trend,
            y=["This season", "Last season"],
            color=[THIS_COLOR, LAST_COLOR],
        )

        table_cols = ["Game", "Date", "Comp", "Opponent", "Venue", "Result",
                      "GF", "GA", "Gls", "Sh", "SoT", "SoT%"]

        st.subheader("Match-by-Match Breakdown")
        st.dataframe(this_matches[table_cols], hide_index=True)

        with st.expander(f"Last season's first {n_matches} matches (to check the comparison)"):
            st.dataframe(last_same_point[table_cols], hide_index=True)