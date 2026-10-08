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
from efficiency import ROLLING_METRICS, efficiency_summary, rolling_average, venue_split
from opponents import (
    form_text,
    head_to_head,
    meetings_summary,
    next_opponent,
    opponents_of,
    results_vs_everyone,
    team_matches,
)

st.set_page_config(page_title="Real Madrid Dashboard", page_icon="⚽", layout="wide")

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


def fmt(value, decimals=2, suffix=""):
    """A number as text for a metric card, or a dash when there is no number."""
    return "–" if value is None else f"{value:.{decimals}f}{suffix}"


def change(value, last, decimals=2, suffix=""):
    """This season minus last season as text for a metric card's delta,
    or None (no arrow shown) when either number is missing."""
    if value is None or last is None:
        return None
    difference = round(value - last, decimals)
    if difference == 0:
        return None
    return f"{difference:.{decimals}f}{suffix}"


st.title("Real Madrid Analytics Dashboard")

# ---- Sidebar: when the data was downloaded, and a button to refresh it ----
with st.sidebar:
    st.header("Data")
    st.caption(f"This season's data last downloaded: {last_downloaded(CURRENT_SEASON) or 'never'}")
    st.caption("Last season is final, so it is downloaded only once.")
    if st.button("Refresh this season's data"):
        with st.spinner("Downloading from FBref — opens Chrome three times, about a minute..."):
            try:
                get_match_log(CURRENT_SEASON, refresh=True)
                get_shooting_log(CURRENT_SEASON, refresh=True)
                get_league_fixtures(CURRENT_SEASON, refresh=True)
            except Exception as error:
                st.error(f"Refresh failed: {error}")
            else:
                st.rerun()

# ---- Load all six tables. They come from saved files on disk; anything ----
# ---- missing is downloaded once (slow), then saved for next time.       ----
with st.spinner("Loading data. The very first time, this downloads six pages from FBref and can take a few minutes..."):
    try:
        this_sched = get_match_log(CURRENT_SEASON)
        last_sched = get_match_log(LAST_SEASON)
        this_shoot = get_shooting_log(CURRENT_SEASON)
        last_shoot = get_shooting_log(LAST_SEASON)
        this_fixtures = clean_fixtures(get_league_fixtures(CURRENT_SEASON))
        last_fixtures = clean_fixtures(get_league_fixtures(LAST_SEASON))
    except Exception as error:
        st.error(f"Could not load the data: {error}")
        st.info("Run `python3 data.py` in the terminal to see the full error and to download the data files.")
        st.stop()

# ---- One-line summary of where the season stands, shown above the tabs ----
if this_fixtures["Played"].any():
    summary_week = int(this_fixtures.loc[this_fixtures["Played"], "Wk"].max())
    summary_table = league_table(this_fixtures, summary_week)
    summary_row = summary_table[summary_table["Team"] == TEAM].iloc[0]
    summary_record = meetings_summary(team_matches(this_fixtures, TEAM))
    st.markdown(
        f"**{TEAM}** are **{ordinal(int(summary_row['Position']))}** in La Liga after "
        f"{int(summary_row['P'])} games: **{int(summary_row['Pts'])} points** "
        f"({summary_record['W']}-{summary_record['D']}-{summary_record['L']}), "
        f"goal difference {int(summary_row['GD']):+d}."
    )

tab1, tab2, tab3, tab4 = st.tabs(["Season Dashboard", "Match Stats", "Efficiency Stats", "Opponent Analysis"])

with tab1:
    this_league = prepare_league_games(this_sched)
    last_league = prepare_league_games(last_sched)

    st.header("Season Dashboard")
    st.caption("La Liga results and league position so far this season, set against "
               "the same point last season.")
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

        # League position comes from the league-wide fixtures (all 20 teams).
        # `weeks` = the latest matchweek Real Madrid has played this season.
        this_pos = position_history(this_fixtures, TEAM)
        last_pos = position_history(last_fixtures, TEAM)
        weeks = len(this_pos)

        st.caption(f"After {n} La Liga games: this season vs. the same point last season")

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Record (W-D-L)", f"{wins}-{draws}-{losses}")
        col1.caption(f"Last season: {last_wins}-{last_draws}-{last_losses}")
        col2.metric("Points", pts, delta=pts - last_pts)
        col3.metric("Goals For", gf, delta=gf - last_gf)
        col4.metric("Goals Against", ga, delta=ga - last_ga, delta_color="inverse")

        if weeks > 0:
            this_place = int(this_pos.iloc[-1]["Position"])
            last_at_week = last_pos[last_pos["Wk"] == weeks]
            if len(last_at_week) > 0:
                last_place = int(last_at_week.iloc[0]["Position"])
                # Positive = higher up the table than last season at this point
                col5.metric(f"League position (matchweek {weeks})", ordinal(this_place),
                            delta=last_place - this_place)
                col5.caption(f"Last season: {ordinal(last_place)}")
            else:
                col5.metric(f"League position (matchweek {weeks})", ordinal(this_place))
        else:
            col5.metric("League position", "–")

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

        st.subheader("League Position by Matchweek")
        if weeks == 0:
            st.info("No matchweek has been fully played yet this season.")
        else:
            last_pos_view = last_pos if view == "Full last season" else last_pos[last_pos["Wk"] <= weeks]
            positions = pd.concat([
                this_pos.assign(Season="This season"),
                last_pos_view.assign(Season="Last season"),
            ])[["Wk", "Season", "Position", "Pts"]].rename(columns={"Wk": "Matchweek"})
            show_position_chart(positions)

            this_ties = int((this_pos["Level"] > 0).sum())
            last_ties = int((last_pos_view["Level"] > 0).sum())
            st.caption(
                "Teams are ordered like LaLiga's own table during the season: points, then goal difference, "
                "then goals scored. Head-to-head decides ties only in the final standings, so it is used only "
                f"for a final table. {TEAM} was level on points with another team in {this_ties} of "
                f"{len(this_pos)} matchweeks this season and {last_ties} of {len(last_pos_view)} last season, "
                "so the ordering rule above decided those positions."
            )

            unplayed = unplayed_through(this_fixtures, weeks)
            if len(unplayed) > 0:
                missing = ", ".join(f"{row.Home} vs {row.Away} ({row.Date})" for row in unplayed.itertuples())
                st.caption(
                    f"Not yet played from matchweeks 1-{weeks}: {missing}. The teams involved have a game "
                    "in hand, so this season's table counts every match played so far."
                )

            with st.expander(f"League table after matchweek {weeks}"):
                standing_cols = ["Position", "Team", "P", "GF", "GA", "GD", "Pts"]
                left, right = st.columns(2)
                left.subheader("This season")
                left.dataframe(league_table(this_fixtures, weeks)[standing_cols], hide_index=True, height=740)
                right.subheader("Last season (same matchweek)")
                right.dataframe(league_table(last_fixtures, weeks)[standing_cols], hide_index=True, height=740)

        with st.expander("See the matches behind these numbers"):
            show = ["Game", "Date", "Opponent", "Venue", "Result", "GF", "GA"]
            left, right = st.columns(2)
            left.subheader("This season")
            left.dataframe(this_league[show], hide_index=True)
            right.subheader(f"Last season (first {n} games)")
            right.dataframe(last_same_point[show], hide_index=True)

with tab2:
    st.header("Match Stats")
    st.caption("Shots, shots on target and shooting accuracy, match by match, "
               "this season against last season.")

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

with tab3:
    st.header("Efficiency Stats")
    st.caption("How efficiently the team scores and defends: per-game numbers, recent form, "
               "and the home and away split.")

    eff_scope = st.radio(
        "Competitions",
        ["All competitions", "La Liga only"],
        horizontal=True,
        key="efficiency_scope",  # a key keeps this radio separate from the one in Match Stats
    )
    eff_league_only = eff_scope == "La Liga only"

    eff_this = prepare_shooting(this_shoot, eff_league_only)
    eff_last_all = prepare_shooting(last_shoot, eff_league_only)
    eff_n = len(eff_this)

    if eff_n == 0:
        st.info("No matches played yet in this selection.")
    else:
        # Last season, cut off at the same number of matches
        eff_last = eff_last_all[eff_last_all["Game"] <= eff_n]

        now = efficiency_summary(eff_this)
        before = efficiency_summary(eff_last)

        st.caption(
            f"After {eff_n} matches: this season vs. the first {eff_n} matches last season. "
            "For goals conceded, shots per goal and failed-to-score, LOWER is better, so a drop "
            "shows in green. Shots per goal uses FBref's shooting-table goals (Gls)."
        )

        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Points per game", fmt(now["Points per game"]),
                    delta=change(now["Points per game"], before["Points per game"]))
        col2.metric("Goals per game", fmt(now["Goals per game"]),
                    delta=change(now["Goals per game"], before["Goals per game"]))
        col3.metric("Conceded per game", fmt(now["Conceded per game"]),
                    delta=change(now["Conceded per game"], before["Conceded per game"]),
                    delta_color="inverse")
        col4.metric("Shots per goal", fmt(now["Shots per goal"], 1),
                    delta=change(now["Shots per goal"], before["Shots per goal"], 1),
                    delta_color="inverse")
        col5.metric("Shots on target per goal", fmt(now["Shots on target per goal"], 1),
                    delta=change(now["Shots on target per goal"], before["Shots on target per goal"], 1),
                    delta_color="inverse")

        col6, col7, col8, col9 = st.columns(4)
        col6.metric("Win %", fmt(now["Win %"], 1, "%"),
                    delta=change(now["Win %"], before["Win %"], 1, " pp"))
        col7.metric("Clean sheets", now["Clean sheets"],
                    delta=now["Clean sheets"] - before["Clean sheets"])
        col8.metric("Failed to score", now["Failed to score"],
                    delta=now["Failed to score"] - before["Failed to score"],
                    delta_color="inverse")
        col9.metric("Penalties scored", f"{now['Penalties scored']} of {now['Penalties taken']}")
        col9.caption(f"Last season: {before['Penalties scored']} of {before['Penalties taken']}")

        st.subheader("Form Over the Last Few Matches")
        st.caption("Each point is the average over the previous matches, which smooths out one-off results. "
                   "The line starts once there are enough matches to fill the window.")
        form_label = st.selectbox("Metric", list(ROLLING_METRICS), key="efficiency_metric")
        window = st.slider("Matches in the average", 2, 10, 5, key="efficiency_window")

        if eff_n < window:
            st.info(f"Only {eff_n} matches played so far, so there is nothing to show for a {window}-match average yet. "
                    "Pick a smaller window.")
        else:
            form = pd.DataFrame({
                "This season": rolling_average(eff_this, form_label, window),
                "Last season": rolling_average(eff_last, form_label, window),
            })
            st.line_chart(
                form,
                y=["This season", "Last season"],
                color=[THIS_COLOR, LAST_COLOR],
            )

        st.subheader("Home vs Away")
        st.caption(f"Last season covers its first {eff_n} matches, the same number played so far this season.")
        venues = pd.concat([
            venue_split(eff_this).assign(Season="This season"),
            venue_split(eff_last).assign(Season="Last season"),
        ], ignore_index=True)
        venue_columns = ["Season"] + [col for col in venues.columns if col != "Season"]
        st.dataframe(venues[venue_columns], hide_index=True)

with tab4:
    st.header("Opponent Analysis")
    st.caption("Pick any La Liga team to see where it stands, how the two teams have done "
               "against each other, and how the opponent has been playing lately.")

    all_opponents = opponents_of(this_fixtures, TEAM)

    if not all_opponents:
        st.info("No fixtures found for this season yet.")
    else:
        coming = next_opponent(this_fixtures, TEAM)
        start = all_opponents.index(coming) if coming in all_opponents else 0
        opponent = st.selectbox("Choose an opponent", all_opponents, index=start, key="opponent_pick")
        if coming:
            st.caption(f"{TEAM}'s next match to be played is against {coming}.")

        # ---- Where the two teams stand in the league right now ----
        st.subheader("Where the Two Teams Stand")
        if this_fixtures["Played"].any():
            current_week = int(this_fixtures.loc[this_fixtures["Played"], "Wk"].max())
            standing = league_table(this_fixtures, current_week)
            pair = standing[standing["Team"].isin([TEAM, opponent])][
                ["Position", "Team", "P", "GF", "GA", "GD", "Pts"]
            ].copy()
            pair["Last 5"] = pair["Team"].map(lambda team: form_text(this_fixtures, team))
            st.dataframe(pair, hide_index=True)
            st.caption("The league table counts every match played so far this season. "
                       "Last 5 shows each team's most recent results, oldest first.")
        else:
            st.info("No matches have been played yet this season.")

        # ---- Head to head: last season and this season ----
        st.subheader(f"{TEAM} vs {opponent}: Head to Head")
        meetings = pd.concat([
            head_to_head(last_fixtures, TEAM, opponent).assign(Season="Last season"),
            head_to_head(this_fixtures, TEAM, opponent).assign(Season="This season"),
        ], ignore_index=True)

        if len(meetings) == 0:
            st.info(f"{TEAM} and {opponent} have not played each other in the last two seasons of data.")
        else:
            summary = meetings_summary(meetings)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Meetings", summary["Played"])
            col2.metric("Record (W-D-L)", f"{summary['W']}-{summary['D']}-{summary['L']}")
            col3.metric(f"{TEAM} goals", summary["GF"])
            col4.metric(f"{opponent} goals", summary["GA"])
            st.dataframe(meetings[["Season", "Date", "Venue", "Score", "Result"]], hide_index=True)
            st.caption(f"Venue and Score are from {TEAM}'s side: its own goals come first.")

        # ---- The opponent's own recent form ----
        st.subheader(f"{opponent}: Last 5 Matches This Season")
        recent = team_matches(this_fixtures, opponent).tail(5).iloc[::-1]
        if len(recent) == 0:
            st.info(f"{opponent} has not played yet this season.")
        else:
            st.dataframe(recent[["Date", "Opponent", "Venue", "Score", "Result"]], hide_index=True)
            st.caption(f"Most recent first. Venue and Score are from {opponent}'s side: its own goals come first.")

        # ---- All opponents at a glance ----
        with st.expander(f"{TEAM}'s results against every team"):
            st.caption(f"H = home, A = away. Scores show {TEAM}'s goals first. "
                       "A dash means the two teams have not met (a promoted team, or a match not yet played).")
            st.dataframe(results_vs_everyone(this_fixtures, last_fixtures, TEAM), hide_index=True, height=740)