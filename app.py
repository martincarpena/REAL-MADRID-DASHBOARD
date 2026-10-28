import re
from contextlib import contextmanager

import pandas as pd
import streamlit as st
from data import (
    get_champions_fixtures,
    get_match_log,
    get_shooting_log,
    get_league_fixtures,
    get_players,
    last_downloaded,
    CURRENT_SEASON,
    LAST_SEASON,
)
from standings import clean_fixtures, league_table, position_history, unplayed_through
from efficiency import ROLLING_METRICS, efficiency_summary, rolling_average, venue_split
from players import (
    LEADER_METRICS,
    clean_players,
    leaders,
    squad_table,
    top_player,
)
from analysis import (
    CORRELATION_PREDICTORS,
    OUTCOMES,
    SEASON_GAMES,
    TREND_METRICS,
    correlations,
    describe_correlation,
    equivalent_position,
    key_findings,
    match_table,
    metric_series,
    project_season,
    projection_path,
    trend_rows,
)
from charts import (
    correlation_chart,
    goals_assists_chart,
    leaders_bar_chart,
    line_chart,
    minutes_chart,
    projection_chart,
    result_bars_chart,
    running_total_chart,
    scatter_chart,
    shots_chart,
    trend_chart,
)
from champions import (
    clean_fixtures as clean_cl_fixtures,
    league_table as cl_league_table,
    played_games,
    position_history as cl_position_history,
    summary as cl_summary,
    team_weeks_played,
    upcoming_games,
)
from styles import CSS, brand_html, club_panel_html, footer_html, logo_data_uri, tab_band_html, trend_table_html
from tables import fit_height, style_table
from tactics import (
    clean_schedule,
    formation_record,
    possession_bands,
    possession_by_result,
    possession_summary,
    rolling_possession,
)
from opponents import (
    form_text,
    head_to_head,
    meetings_summary,
    next_opponent,
    opponents_of,
    results_vs_everyone,
    team_matches,
)
from player_data import ROSTER_SIZE, get_player_matches, get_roster, top_players
from player_report import (
    by_competition,
    by_venue,
    club_matches,
    per_90,
    positions_played,
    running_totals,
    season_totals,
)

st.set_page_config(page_title="Real Madrid Dashboard", page_icon="⚽", layout="wide")

THIS_COLOR = "#D4AF37"  # this season: gold (the same gold as the theme)
LAST_COLOR = "#7B8798"  # last season: slate grey
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


CARD_COUNTER = {"count": 0}


def _box(key):
    """A Streamlit container with a name, so styles.py can find it. Falls back
    to a plain container in an older Streamlit that cannot name containers."""
    try:
        return st.container(key=key)
    except TypeError:
        return st.container()


@contextmanager
def card(title):
    """A dark box with a title strip on top. Everything drawn inside a
    `with card("Title"):` block goes in the box. The boxes are numbered
    card_1, card_2... (the counter starts again at 1 on every run of the page)
    and styles.py gives anything with that name its look."""
    CARD_COUNTER["count"] += 1
    number = CARD_COUNTER["count"]
    with _box(f"card_{number}"):
        st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
        with _box(f"body_{number}"):
            yield


def fit_columns(table, config=None):
    """Column settings that give every number column just enough width for its
    heading, so a table with many columns fits its card instead of running off
    the right edge. A column that already has its own setting (a progress bar,
    say) is left alone. Returns a new dictionary."""
    config = dict(config or {})
    for name in table.columns:
        if name not in config and pd.api.types.is_numeric_dtype(table[name]):
            # "Position" is shown as the shorter "Pos"
            label = "Pos" if name == "Position" else None
            config[name] = st.column_config.Column(label, width=max(46, int(7.5 * len(str(label or name)) + 20)))
    return config


def show_table(table, team=None, **options):
    """A table with clean numbers, dashes for empty cells and the W, D and L in
    its Result column coloured. `team` tints that team's row in a league table.
    If anything about the styling fails, show the plain table."""
    try:
        config = fit_columns(table, options.pop("column_config", None))
        st.dataframe(style_table(table, team), hide_index=True, column_config=config, **options)
    except Exception:
        st.dataframe(table, hide_index=True, **options)


def points_bar(label="Points per game"):
    """Column setting that draws points per game as a small bar (0 to 3)."""
    return st.column_config.ProgressColumn(label, min_value=0, max_value=3, format="%.2f", width=88)


def metric_note(column, label, value, note):
    """A metric card with a small grey note under the value, without an arrow.
    Used for 'Last season: ...' so the note sits inside the card. Falls back to a
    caption under the card in a Streamlit that has no delta_arrow option."""
    try:
        column.metric(label, value, delta=note, delta_color="off", delta_arrow="off")
    except TypeError:
        column.metric(label, value)
        column.caption(note)


def tab_header(title, subtitle):
    """The dark band at the top of a tab."""
    st.markdown(tab_band_html(title, subtitle), unsafe_allow_html=True)


def show_chart(chart):
    """Draw a chart built in charts.py, as wide as the column it sits in."""
    try:
        st.altair_chart(chart, width="stretch")
    except TypeError:  # an older Streamlit without the width option
        st.altair_chart(chart, use_container_width=True)


def show_lines(wide, x_title, y_title, **options):
    """This season against last season as a line chart (the design lives in
    charts.py). If anything about it fails, fall back to a plain line chart."""
    try:
        chart = line_chart(wide, x_title, y_title, **options)
        if chart is None:
            raise ValueError("no chart")
        show_chart(chart)
    except Exception:
        st.line_chart(wide, y=["This season", "Last season"], color=[THIS_COLOR, LAST_COLOR])


def show_leaders(top, column, label):
    """Horizontal bars for the top players in one statistic. If anything about
    it fails, fall back to a plain bar chart."""
    data = top.rename(columns={column: "Value"})[["Player", "Value"]]
    try:
        chart = leaders_bar_chart(data, label, height=28 * len(data) + 50)
        if chart is None:
            raise ValueError("no chart")
        show_chart(chart)
    except Exception:
        st.bar_chart(data.set_index("Player")["Value"])


def show_result_bars(data, height=260):
    """Average possession in wins, draws and losses as bars. If anything about
    it fails, fall back to a table."""
    try:
        chart = result_bars_chart(data, height=height)
        if chart is None:
            raise ValueError("no chart")
        show_chart(chart)
    except Exception:
        st.dataframe(data, hide_index=True)


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


# ---- Styling and the banner at the top (the CSS lives in styles.py) ----
st.markdown(CSS, unsafe_allow_html=True)

# ---- Sidebar: the crest, the page menu, the club panel and the data controls ----
PAGES = ["Season Dashboard", "Match Stats", "Efficiency Stats", "Opponent Analysis", "Player Stats",
         "Player Reports", "Tactics", "Champions League", "Analysis"]

with st.sidebar:
    st.markdown(brand_html(logo_data_uri(), "Analytics"), unsafe_allow_html=True)
    st.markdown('<div class="side-label">Pages</div>', unsafe_allow_html=True)
    # One button per page. The page you are on is drawn as a "primary" button
    # (styles.py gives it the gold edge). Clicking a button runs go_to, which
    # remembers the page in st.session_state, Streamlit's memory between clicks.
    if "page" not in st.session_state:
        st.session_state["page"] = PAGES[0]

    def go_to(name):
        st.session_state["page"] = name

    with st.container(key="nav"):
        for name in PAGES:
            st.button(name, key=f"nav_{name}", on_click=go_to, args=(name,),
                      type="primary" if st.session_state["page"] == name else "secondary")
    page = st.session_state["page"]

    # An empty box for the club panel. It is filled in below, once the data has loaded.
    club_slot = st.container()

    st.markdown('<div class="side-label">Data</div>', unsafe_allow_html=True)
    st.caption(f"This season's data last downloaded: {last_downloaded(CURRENT_SEASON) or 'never'}")
    st.caption("Last season is final, so it is downloaded only once.")
    if st.button("Refresh this season's data"):
        with st.spinner("Downloading from FBref — opens Chrome five times, about three minutes..."):
            try:
                get_match_log(CURRENT_SEASON, refresh=True)
                get_shooting_log(CURRENT_SEASON, refresh=True)
                get_league_fixtures(CURRENT_SEASON, refresh=True)
                get_players(CURRENT_SEASON, refresh=True)
                get_champions_fixtures(CURRENT_SEASON, refresh=True)
            except Exception as error:
                st.error(f"Refresh failed: {error}")
            else:
                st.rerun()

# ---- Load all eight tables. They come from saved files on disk; anything ----
# ---- missing is downloaded once (slow), then saved for next time.       ----
with st.spinner("Loading data. The very first time, this downloads eight pages from FBref and can take several minutes..."):
    try:
        this_sched = get_match_log(CURRENT_SEASON)
        last_sched = get_match_log(LAST_SEASON)
        this_shoot = get_shooting_log(CURRENT_SEASON)
        last_shoot = get_shooting_log(LAST_SEASON)
        this_fixtures = clean_fixtures(get_league_fixtures(CURRENT_SEASON))
        last_fixtures = clean_fixtures(get_league_fixtures(LAST_SEASON))
        this_players = clean_players(get_players(CURRENT_SEASON))
        last_players = clean_players(get_players(LAST_SEASON))
    except Exception as error:
        st.error(f"Could not load the data: {error}")
        st.info("Run `python3 data.py` in the terminal to see the full error and to download the data files.")
        st.stop()

# ---- The club panel in the sidebar: where the season stands, always in view ----
if this_fixtures["Played"].any():
    summary_week = int(this_fixtures.loc[this_fixtures["Played"], "Wk"].max())
    summary_table = league_table(this_fixtures, summary_week)
    summary_row = summary_table[summary_table["Team"] == TEAM].iloc[0]
    summary_record = meetings_summary(team_matches(this_fixtures, TEAM))
    with club_slot:
        st.markdown(
            club_panel_html(
                ordinal(int(summary_row["Position"])),
                int(summary_row["P"]),
                int(summary_row["Pts"]),
                f"{summary_record['W']}-{summary_record['D']}-{summary_record['L']}",
                int(summary_row["GD"]),
                form_text(this_fixtures, TEAM),
                next_opponent(this_fixtures, TEAM),
                f"La Liga {CURRENT_SEASON}, compared with {LAST_SEASON}",
            ),
            unsafe_allow_html=True,
        )

# Only the page chosen in the sidebar menu is drawn: each page below sits in an
# `if page == ...:` block, so the other pages are skipped (and the app is faster).

if page == "Season Dashboard":
    this_league = prepare_league_games(this_sched)
    last_league = prepare_league_games(last_sched)

    tab_header("Season Dashboard", "La Liga results and league position so far this season, set against "
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

        # What the numbers mean on the left, the comparison switch on the right
        note, switch = st.columns([3, 2])
        note.caption(f"After {n} La Liga games: this season vs. the same point last season")
        view = switch.radio(
            "Compare",
            ["Same point in the season", "Full last season"],
            horizontal=True,
            label_visibility="collapsed",
        )

        col1, col2, col3, col4, col5 = st.columns(5)
        metric_note(col1, "Record (W-D-L)", f"{wins}-{draws}-{losses}",
                    f"Last season: {last_wins}-{last_draws}-{last_losses}")
        col2.metric("Points", pts, delta=pts - last_pts)
        col3.metric("Goals For", gf, delta=gf - last_gf)
        col4.metric("Goals Against", ga, delta=ga - last_ga, delta_color="inverse")

        if weeks > 0:
            this_place = int(this_pos.iloc[-1]["Position"])
            last_at_week = last_pos[last_pos["Wk"] == weeks]
            if len(last_at_week) > 0:
                last_place = int(last_at_week.iloc[0]["Position"])
                # Positive = higher up the table than last season at this point
                moved = last_place - this_place
                if moved == 0:
                    metric_note(col5, "League position", ordinal(this_place),
                                f"Same as last season: {ordinal(last_place)}")
                else:
                    col5.metric("League position", ordinal(this_place),
                                delta=f"{moved:+d} (was {ordinal(last_place)})")
            else:
                col5.metric("League position", ordinal(this_place))
        else:
            col5.metric("League position", "–")

        # Both series are indexed by game number, so pandas lines them up
        # and leaves a gap where this season hasn't been played yet.
        chart = pd.DataFrame({
            "This season": this_league.set_index("Game")["Cumulative Points"],
            "Last season": last_league.set_index("Game")["Cumulative Points"],
        }).sort_index()

        if view == "Same point in the season":
            chart = chart.loc[:n]  # keep Game 1 through Game n only

        positions = None
        if weeks > 0:
            last_pos_view = last_pos if view == "Full last season" else last_pos[last_pos["Wk"] <= weeks]
            positions = pd.concat([
                this_pos.assign(Season="This season"),
                last_pos_view.assign(Season="Last season"),
            ])[["Wk", "Season", "Position", "Pts"]].rename(columns={"Wk": "Matchweek"})

        standing_cols = ["Position", "Team", "P", "GF", "GA", "GD", "Pts"]
        chart_height = 330
        table_height = chart_height - 45  # the table card has more fixed parts around it than a chart card, so it is shorter

        # First row: points and position as charts, and the league table beside them
        left, middle, right = st.columns([1, 1, 1.9])
        with left, card("Cumulative points by games played"):
            show_lines(chart, "Games played", "Points", height=chart_height, zero=True)
        with middle, card("League position by matchweek"):
            if positions is None:
                st.info("No matchweek has been fully played yet this season.")
            else:
                wide_positions = positions.pivot(index="Matchweek", columns="Season", values="Position")
                show_lines(wide_positions, "Matchweek", "League position (1 = top)", height=chart_height,
                           y_domain=[20, 1], y_values=[1, 5, 10, 15, 20])
        with right, card(f"League table after matchweek {weeks}"):
            if positions is None:
                st.info("No matchweek has been fully played yet this season.")
            else:
                # One card, two tables: pick which season's table to look at
                table_view = st.radio("Table", ["This season", "Same matchweek last season"], horizontal=True,
                                      key="dash_table_view", label_visibility="collapsed")
                shown = this_fixtures if table_view == "This season" else last_fixtures
                show_table(league_table(shown, weeks)[standing_cols], team=TEAM,
                           height=table_height - 40)

        # Second row: the matches behind the numbers, this season and last season side by side
        show = ["Game", "Date", "Opponent", "Venue", "Result", "GF", "GA"]
        left, right = st.columns(2)
        with left, card("Matches this season"):
            show_table(this_league[show], height=300)
        with right, card(f"Last season's first {n} matches"):
            show_table(last_same_point[show], height=300)

        if positions is not None:
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

if page == "Match Stats":
    tab_header("Match Stats", "Shots, shots on target and shooting accuracy, match by match, "
               "this season against last season.")

    control, note = st.columns([1, 3])
    scope = control.radio(
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

        note.caption(
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

        # Shots, shots on target and goals next to each other, to see how they relate
        for slot, (title, column) in zip(st.columns(3), [("Shots", "Sh"), ("Shots on target", "SoT"), ("Goals", "GF")]):
            with slot, card(f"{title}, match by match"):
                trend = pd.DataFrame({
                    "This season": this_matches.set_index("Game")[column],
                    "Last season": last_same_point.set_index("Game")[column],
                })
                show_lines(trend, "Match", title, height=200)

        table_cols = ["Game", "Date", "Comp", "Opponent", "Venue", "Result",
                      "GF", "GA", "Gls", "Sh", "SoT", "SoT%"]

        left, right = st.columns(2)
        with left, card("Match-by-match breakdown: this season"):
            show_table(this_matches[table_cols], height=300)
        with right, card(f"Last season's first {n_matches} matches"):
            show_table(last_same_point[table_cols], height=300)

if page == "Efficiency Stats":
    tab_header("Efficiency Stats", "How efficiently the team scores and defends: per-game numbers, recent form, "
               "and the home and away split.")

    control, slide = st.columns(2)
    eff_scope = control.radio(
        "Competitions",
        ["All competitions", "La Liga only"],
        horizontal=True,
        key="efficiency_scope",  # a key keeps this radio separate from the one in Match Stats
    )
    eff_league_only = eff_scope == "La Liga only"
    window = slide.slider("Matches in the average (for the form charts)", 2, 10, 5, key="efficiency_window")

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

        col6, col7, col8, col9, col10 = st.columns(5)
        col6.metric("Win %", fmt(now["Win %"], 1, "%"),
                    delta=change(now["Win %"], before["Win %"], 1, " pp"))
        col7.metric("Clean sheets", now["Clean sheets"],
                    delta=now["Clean sheets"] - before["Clean sheets"])
        col8.metric("Failed to score", now["Failed to score"],
                    delta=now["Failed to score"] - before["Failed to score"],
                    delta_color="inverse")
        metric_note(col9, "Penalties scored", f"{now['Penalties scored']} of {now['Penalties taken']}",
                    f"Last season: {before['Penalties scored']} of {before['Penalties taken']}")
        col10.caption(
            f"After {eff_n} matches: this season vs. the first {eff_n} matches last season. "
            "For goals conceded, shots per goal and failed-to-score, LOWER is better, so a drop "
            "shows in green. Shots per goal uses FBref's shooting-table goals (Gls)."
        )

        venues = pd.concat([
            venue_split(eff_this).assign(Season="This season"),
            venue_split(eff_last).assign(Season="Last season"),
        ], ignore_index=True)
        # The most useful columns come first; the rest are a scroll to the right
        venue_columns = ["Season", "Venue", "W", "D", "L", "Points per game", "GF", "GA",
                         "Games", "Points", "Shots", "Shots on target"]

        # Two form charts (pick the metric inside each card) and the home/away table
        left, middle, right = st.columns([1, 1, 1.6])
        for slot, key, start in [(left, "efficiency_metric", 0), (middle, "efficiency_metric_2", 1)]:
            with slot, card(f"Form: average of the last {window} matches"):
                if eff_n < window:
                    st.info(f"Only {eff_n} matches played so far, so there is nothing to show for a "
                            f"{window}-match average yet. Pick a smaller window.")
                else:
                    form_label = st.selectbox("Metric", list(ROLLING_METRICS), index=start, key=key,
                                              label_visibility="collapsed")
                    form = pd.DataFrame({
                        "This season": rolling_average(eff_this, form_label, window),
                        "Last season": rolling_average(eff_last, form_label, window),
                    })
                    show_lines(form, "Match", form_label, height=280, decimals=2)
        with right, card("Home vs away"):
            st.dataframe(venues[venue_columns], hide_index=True,
                         column_config=fit_columns(venues[venue_columns], {"Points per game": points_bar("Pts/game")}),
                         height=fit_height(len(venues)))

        st.caption("Each point on a form chart is the average over the previous matches, which smooths out "
                   "one-off results; the line starts once there are enough matches to fill the window. "
                   f"Last season covers its first {eff_n} matches, the same number played so far this season.")

if page == "Opponent Analysis":
    tab_header("Opponent Analysis", "Pick any La Liga team to see where it stands, how the two teams have done "
               "against each other, and how the opponent has been playing lately.")

    all_opponents = opponents_of(this_fixtures, TEAM)

    if not all_opponents:
        st.info("No fixtures found for this season yet.")
    else:
        coming = next_opponent(this_fixtures, TEAM)
        start = all_opponents.index(coming) if coming in all_opponents else 0
        pick, note = st.columns([1, 3])
        opponent = pick.selectbox("Choose an opponent", all_opponents, index=start, key="opponent_pick")
        if coming:
            note.caption(f"{TEAM}'s next match to be played is against {coming}.")

        # ---- Where the two teams stand in the league right now ----
        pair = None
        if this_fixtures["Played"].any():
            current_week = int(this_fixtures.loc[this_fixtures["Played"], "Wk"].max())
            standing = league_table(this_fixtures, current_week)
            pair = standing[standing["Team"].isin([TEAM, opponent])][
                ["Position", "Team", "P", "GF", "GA", "GD", "Pts"]
            ].copy()
            pair["Last 5"] = pair["Team"].map(lambda team: form_text(this_fixtures, team))

        # ---- Head to head: last season and this season ----
        meetings = pd.concat([
            head_to_head(last_fixtures, TEAM, opponent).assign(Season="Last season"),
            head_to_head(this_fixtures, TEAM, opponent).assign(Season="This season"),
        ], ignore_index=True)

        if len(meetings) > 0:
            summary = meetings_summary(meetings)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Head-to-head meetings", summary["Played"])
            col2.metric("Head-to-head record (W-D-L)", f"{summary['W']}-{summary['D']}-{summary['L']}")
            col3.metric(f"{TEAM} goals", summary["GF"])
            col4.metric(f"{opponent} goals", summary["GA"])

        left, right = st.columns(2)
        with left, card("Where the two teams stand"):
            if pair is None:
                st.info("No matches have been played yet this season.")
            else:
                show_table(pair, height=190)
        with right, card(f"{TEAM} vs {opponent}: every meeting"):
            if len(meetings) == 0:
                st.info(f"{TEAM} and {opponent} have not played each other in the last two seasons of data.")
            else:
                show_table(meetings[["Season", "Date", "Venue", "Score", "Result"]], height=190)

        # ---- The opponent's own recent form, and Real Madrid against everyone ----
        recent = team_matches(this_fixtures, opponent).tail(5).iloc[::-1]
        left, right = st.columns(2)
        with left, card(f"{opponent}: last 5 matches this season"):
            if len(recent) == 0:
                st.info(f"{opponent} has not played yet this season.")
            else:
                show_table(recent[["Date", "Opponent", "Venue", "Score", "Result"]], height=250)
        with right, card(f"{TEAM}'s results against every team"):
            st.dataframe(results_vs_everyone(this_fixtures, last_fixtures, TEAM), hide_index=True, height=250)

        st.caption(
            "The league table counts every match played so far this season, and Last 5 shows each team's most "
            "recent results, oldest first. In the meetings table, Venue and Score are from "
            f"{TEAM}'s side: its own goals come first. In the last-5 table they are from {opponent}'s side, "
            "most recent first. In the table of every team, H = home, A = away, and a dash means the two "
            "teams have not met (a promoted team, or a match not yet played)."
        )

if page == "Player Stats":
    tab_header("Player Stats", "Who is scoring, creating and playing the minutes. Player numbers cover La Liga only.")

    minutes_options = {"All players": 0, "90+ minutes": 90, "450+ minutes": 450, "900+ minutes": 900}
    control, filter_slot = st.columns(2)
    player_season = control.radio(
        "Season",
        ["This season", "Last season (full)"],
        horizontal=True,
        key="player_season",
    )
    minutes_label = filter_slot.selectbox("Squad table: show players with", list(minutes_options),
                                          key="player_minutes")
    shown = this_players if player_season == "This season" else last_players

    # ---- The best player in four key statistics ----
    cards = [("Top scorer", "Gls"), ("Most assists", "Ast"), ("Most shots", "Sh"), ("Most minutes", "Min")]
    for slot, (title, stat) in zip(st.columns(4), cards):
        best = top_player(shown, stat)
        if best is None:
            slot.metric(title, "–")
            continue
        label = f"{title}: {best[0]}"
        last_best = top_player(last_players, stat) if player_season == "This season" else None
        if last_best is not None:
            metric_note(slot, label, best[1], f"Last season (full): {last_best[0]}, {last_best[1]}")
        else:
            slot.metric(label, best[1])

    # ---- Two leaders charts side by side ----
    left, right = st.columns(2)
    for slot, key, start in [(left, "player_metric", 0), (right, "player_metric_2", 1)]:
        with slot:
            leader_label = st.selectbox("Statistic", list(LEADER_METRICS), index=start, key=key,
                                        label_visibility="collapsed")
            leader_column = LEADER_METRICS[leader_label]
            top = leaders(shown, leader_column, n=10)
            if len(top) == 0:
                st.info(f"Nobody has any {leader_label.lower()} yet.")
            else:
                with card(f"Top 10: {leader_label}"):
                    show_leaders(top, leader_column, leader_label)

    # ---- The whole squad ----
    if player_season == "This season":
        squad = squad_table(this_players, last_players)
        squad_columns = ["Player", "Pos", "Nation", "Age", "MP", "Starts", "Min", "Gls", "Ast", "G+A",
                         "Gls/90", "Ast/90", "Sh", "SoT", "SoT%", "CrdY", "CrdR",
                         "Gls last season", "Ast last season"]
    else:
        squad = last_players
        squad_columns = ["Player", "Pos", "Nation", "Age", "MP", "Starts", "Min", "Gls", "Ast", "G+A",
                         "Gls/90", "Ast/90", "Sh", "SoT", "SoT%", "CrdY", "CrdR"]

    squad = squad[squad["Min"] >= minutes_options[minutes_label]].sort_values("Min", ascending=False)
    if len(squad) == 0:
        st.info("No players match this filter yet.")
    else:
        with card("Full squad"):
            show_table(squad[squad_columns], height=340)
        st.caption("Click a column heading to sort by it. Per-90 numbers are only reliable for players "
                   "with a lot of minutes, so use the filter above. Last season's columns are full-season totals.")


if page == "Player Reports":
    tab_header("Player Reports", f"A full report for each of the {ROSTER_SIZE} players with the most minutes. "
               "Click a name to open his report. Real Madrid matches only.")

    try:
        roster = top_players(get_roster(CURRENT_SEASON))
    except Exception as error:
        st.error(f"Could not load the list of players: {error}")
        st.info("Run `python3 player_data.py` in the terminal to download the player data.")
        st.stop()

    # The player whose report is open. Clicking a name button runs choose_player
    # first, which remembers the name in st.session_state between clicks.
    if st.session_state.get("report_player") not in set(roster["Player"]):
        st.session_state["report_player"] = roster.iloc[0]["Player"]
    chosen = st.session_state["report_player"]

    def choose_player(name):
        st.session_state["report_player"] = name

    def wide_button(label, **options):
        """A button as wide as its column (the option has been renamed in newer Streamlit)."""
        try:
            return st.button(label, width="stretch", **options)
        except TypeError:
            return st.button(label, use_container_width=True, **options)

    def player_age(value):
        """FBref writes an age as '27-123' (years-days). Keep the years."""
        return str(value).split("-")[0].split(".")[0] if pd.notna(value) else ""

    def draw_chart(builder, *arguments):
        """Draws a chart from charts.py. If it cannot be drawn, say why."""
        try:
            chart = builder(*arguments)
            if chart is None:
                raise ValueError("there is nothing to draw yet")
            show_chart(chart)
        except Exception as error:
            st.warning(f"Could not draw this chart: {error}")

    with card("Choose a player"):
        # The box is named "players" so that styles.py can give the open player's button a gold edge.
        with _box("players"):
            for start in range(0, len(roster), 5):
                for slot, (_, person) in zip(st.columns(5), roster.iloc[start:start + 5].iterrows()):
                    with slot:
                        wide_button(person["Player"], key=f"pick_{person['Player']}", on_click=choose_player,
                                    args=(person["Player"],),
                                    type="primary" if person["Player"] == chosen else "secondary")
                        st.caption(" · ".join(part for part in [str(person["Pos"]) if pd.notna(person["Pos"]) else "",
                                                                player_age(person["Age"]) + " yrs" if pd.notna(person["Age"]) else ""] if part))

    person = roster[roster["Player"] == chosen].iloc[0]
    try:
        with st.spinner(f"Loading {chosen}'s match log. The first time, this downloads one page from FBref..."):
            log = get_player_matches(person["Link"], CURRENT_SEASON)
    except Exception as error:
        st.error(f"Could not load {chosen}'s match log: {error}")
        st.info("Run `python3 player_data.py` in the terminal to see the full error and to download the data.")
        st.stop()

    matches = club_matches(log)
    st.subheader(chosen)
    details = [str(person["Pos"]) if pd.notna(person["Pos"]) else "",
               f"{player_age(person['Age'])} years old" if pd.notna(person["Age"]) else "",
               f"Real Madrid, {CURRENT_SEASON}"]
    st.caption(" · ".join(part for part in details if part))

    if not matches["Played"].any():
        st.info(f"{chosen} has not played for Real Madrid yet this season.")
    else:
        totals = season_totals(matches)
        with card("Season so far"):
            for labels in [
                [("Matches", "Matches played"), ("Starts", "Starts"), ("Minutes", "Minutes"),
                 ("Goals", "Goals"), ("Assists", "Assists"), ("G + A", "Goals + assists")],
                [("Shots", "Shots"), ("On target", "Shots on target"), ("Yellow cards", "Yellow cards"),
                 ("Red cards", "Red cards"), ("Fouls drawn", "Fouls drawn"), ("Tackles won", "Tackles won")],
            ]:
                for slot, (label, key) in zip(st.columns(6), labels):
                    slot.metric(label, f"{totals[key]:,}")
            if totals["Unused substitute"]:
                st.caption(f"Also on the bench without playing in {totals['Unused substitute']} matches.")

        rates = per_90(matches)
        with card("Per 90 minutes"):
            for slot, (label, key) in zip(st.columns(6), [
                ("Goals / 90", "Goals"), ("Assists / 90", "Assists"), ("Shots / 90", "Shots"),
                ("On target / 90", "Shots on target"), ("Fouls drawn / 90", "Fouls drawn"),
                ("Tackles won / 90", "Tackles won"),
            ]):
                slot.metric(label, f"{rates[key]:.2f}")

        left, right = st.columns(2)
        with left:
            with card("Minutes in each match"):
                draw_chart(minutes_chart, matches)
        with right:
            with card("Goals and assists in each match"):
                draw_chart(goals_assists_chart, matches)

        left, right = st.columns(2)
        with left:
            with card("Shots in each match"):
                draw_chart(shots_chart, matches)
        with right:
            with card("Goals and assists through the season"):
                draw_chart(running_total_chart, running_totals(matches))

        with card("By competition"):
            competitions = by_competition(matches).rename(columns={"Comp": "Competition", "Matches": "MP"})
            show_table(competitions, height=fit_height(len(competitions)))
        with card("Home and away"):
            venues = by_venue(matches).rename(columns={"Matches": "MP"})
            show_table(venues, height=fit_height(len(venues)))

        positions = positions_played(matches)
        st.caption("Positions played: " + ", ".join(f"{row['Position']} ({row['Matches']})"
                                                    for _, row in positions.iterrows()))

        # ---- Every match, newest first ----
        def score_text(row):
            return f"{int(row['GF'])}\u2013{int(row['GA'])}" if pd.notna(row["GF"]) else "\u2013"

        every_match = pd.DataFrame({
            "Date": matches["Date"].dt.strftime("%Y-%m-%d"),
            "Competition": matches["Comp"],
            "Venue": matches["Venue"],
            "Opponent": matches["Opponent"],
            "Result": matches["Outcome"],
            "Score": matches.apply(score_text, axis=1),
            "Start": matches["Start"],
            "Pos": matches["Pos"],
            "Min": matches["Min"].astype(int),
            "Gls": matches["Gls"].astype(int),
            "Ast": matches["Ast"].astype(int),
            "Sh": matches["Sh"].astype(int),
            "SoT": matches["SoT"].astype(int),
            "CrdY": matches["CrdY"].astype(int),
            "CrdR": matches["CrdR"].astype(int),
            "Fls": matches["Fls"].astype(int),
            "Fld": matches["Fld"].astype(int),
            "Off": matches["Off"].astype(int),
            "Crs": matches["Crs"].astype(int),
            "TklW": matches["TklW"].astype(int),
            "Int": matches["Int"].astype(int),
        }).iloc[::-1]
        with card("Match by match"):
            show_table(every_match, height=min(fit_height(len(every_match)), 460))
        st.caption("The numbers come from FBref's match logs for Real Madrid matches only (La Liga, Champions League "
                   "and cups); his national-team matches are left out. A bench player who did not come on shows "
                   "0 minutes. Players are ranked by their La Liga minutes. Click a column heading to sort by it.")


if page == "Tactics":
    tab_header("Tactics", "How much of the ball Real Madrid have, how possession relates to results, "
               "and how the team does with each formation.")

    control, slide, compare = st.columns([2, 2, 3])
    tactics_scope = control.radio(
        "Competitions",
        ["All competitions", "La Liga only"],
        horizontal=True,
        key="tactics_scope",
    )
    tactics_window = slide.slider("Matches in the average", 2, 10, 5, key="tactics_window")
    tactics_compare = compare.radio(
        "Compare this season with",
        ["Same point last season", "Full last season"],
        horizontal=True,
        key="tactics_compare",
    )
    tactics_league_only = tactics_scope == "La Liga only"

    tac_this = clean_schedule(this_sched, tactics_league_only)
    tac_last_all = clean_schedule(last_sched, tactics_league_only)
    tac_this["Opponent"] = tac_this["Opponent"].apply(clean_opponent)
    tac_last_all["Opponent"] = tac_last_all["Opponent"].apply(clean_opponent)
    tac_n = len(tac_this)

    if tac_n == 0:
        st.info("No matches played yet in this selection.")
    else:
        # Last season, cut off at the same number of matches
        tac_last = tac_last_all[tac_last_all["Game"] <= tac_n]
        tac_other = tac_last if tactics_compare == "Same point last season" else tac_last_all

        poss_now = possession_summary(tac_this)
        poss_before = possession_summary(tac_last)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Average possession", fmt(poss_now["Average"], 1, "%"),
                    delta=change(poss_now["Average"], poss_before["Average"], 1, " pp"))
        col2.metric("Most possession in a match", fmt(poss_now["Highest"], 0, "%"),
                    delta=change(poss_now["Highest"], poss_before["Highest"], 0, " pp"))
        col3.metric("Least possession in a match", fmt(poss_now["Lowest"], 0, "%"),
                    delta=change(poss_now["Lowest"], poss_before["Lowest"], 0, " pp"))
        col4.metric("Matches with most of the ball", fmt(poss_now["Most of the ball"], 0),
                    delta=change(poss_now["Most of the ball"], poss_before["Most of the ball"], 0))

        bands = pd.concat([
            possession_bands(tac_this).assign(Season="This season"),
            possession_bands(tac_other).assign(Season="Last season"),
        ], ignore_index=True)
        band_columns = ["Season"] + [col for col in bands.columns if col not in ("Season", "Points")]
        chart_height = 250
        table_height = fit_height(len(bands))  # exactly its rows, so there is no empty grid under it

        # First row: possession over time, possession by result, and the record by possession
        left, middle, right = st.columns([1, 1, 1.9])
        with left, card(f"Average possession over the last {tactics_window} matches"):
            if tac_n < tactics_window:
                st.info(f"Only {tac_n} matches played so far, so there is nothing to show for a "
                        f"{tactics_window}-match average yet. Pick a smaller window.")
            else:
                poss_trend = pd.DataFrame({
                    "This season": rolling_possession(tac_this, tactics_window),
                    "Last season": rolling_possession(tac_last, tactics_window),
                })
                show_lines(poss_trend, "Match", "Average possession (%)", height=chart_height, decimals=1)
        with middle, card("Average possession in wins, draws and losses"):
            by_result = pd.concat([
                possession_by_result(tac_this).assign(Season="This season"),
                possession_by_result(tac_other).assign(Season="Last season"),
            ], ignore_index=True)
            show_result_bars(by_result, height=chart_height)
        with right, card("Record by possession in the match"):
            # Show points per game as a small bar
            st.dataframe(
                bands[band_columns],
                hide_index=True,
                column_config=fit_columns(bands[band_columns], {"Points per game": points_bar("Pts/game")}),
                height=table_height,
            )

        # Second row: Real Madrid's formations and the opponents' formations.
        # Each table has both seasons in it, so it needs a Season column and
        # fewer other columns (no goals, no total points) to fit in half the page.
        # Both tables get the same height (the longer one's rows, at most 8, then
        # it scrolls), so their cards line up and nothing empty is drawn under a table.
        formation_columns = ["Season", "Formation", "Games", "W", "D", "L", "Points per game"]
        formation_config = {"Points per game": points_bar("Pts/game")}
        my_formations = pd.concat([
            formation_record(tac_this, "Formation").assign(Season="This season"),
            formation_record(tac_other, "Formation").assign(Season="Last season"),
        ], ignore_index=True)[formation_columns]
        their_formations = pd.concat([
            formation_record(tac_this, "Opp Formation").assign(Season="This season"),
            formation_record(tac_other, "Opp Formation").assign(Season="Last season"),
        ], ignore_index=True)[formation_columns]
        formation_height = fit_height(min(max(len(my_formations), len(their_formations)), 8))

        left, right = st.columns(2)
        with left, card("Real Madrid's formations"):
            st.dataframe(my_formations, hide_index=True, column_config=fit_columns(my_formations, formation_config),
                         height=formation_height)
        with right, card("Real Madrid against each opponent formation"):
            st.dataframe(their_formations, hide_index=True, column_config=fit_columns(their_formations, formation_config),
                         height=formation_height)

        tactics_columns = ["Game", "Date", "Comp", "Opponent", "Venue", "Result",
                           "GF", "GA", "Poss", "Formation", "Opp Formation"]
        with card("The matches behind these numbers"):
            show_table(tac_this[tactics_columns], height=300)

        st.caption(
            f"After {tac_n} matches: this season vs. the first {tac_n} matches last season. "
            "Possession is the share of the ball Real Madrid had, from FBref. Each point on the "
            "possession line is the average over the previous matches, which smooths out one-off "
            "games; the line starts once there are enough matches to fill the window. A full season "
            "has many more matches than the first few, so its percentages are steadier."
        )

if page == "Champions League":
    tab_header("Champions League", "Real Madrid's Champions League games only: results, goals and the games "
               "still to come. These matches also count in the other tabs.")
    this_cl = played_games(this_sched)
    last_cl = played_games(last_sched)
    n_cl = len(this_cl)

    if n_cl == 0:
        st.info("No Champions League games played yet this season.")
    else:
        # Last season, cut off at the same number of games, for a fair comparison
        last_cl_same = last_cl[last_cl["Game"] <= n_cl]
        now_cl = cl_summary(this_cl)
        before_cl = cl_summary(last_cl_same)

        note, switch = st.columns([3, 2])
        note.caption(f"After {n_cl} Champions League games: this season vs. the same point last season")
        cl_view = switch.radio(
            "Compare",
            ["Same point in the season", "Full last season"],
            horizontal=True,
            label_visibility="collapsed",
            key="champions_view",
        )

        # The league-phase table needs the whole competition's fixtures (a separate download).
        # If they are missing, the rest of the tab still works.
        try:
            this_cl_fixtures = clean_cl_fixtures(get_champions_fixtures(CURRENT_SEASON))
            last_cl_fixtures = clean_cl_fixtures(get_champions_fixtures(LAST_SEASON))
            weeks_played = team_weeks_played(this_cl_fixtures, TEAM)
            cl_weeks = max(weeks_played) if weeks_played else None
        except Exception as error:
            st.warning(f"The Champions League table could not be loaded ({error}). "
                       "Run `python3 data.py` in the terminal to download it.")
            this_cl_fixtures = last_cl_fixtures = cl_weeks = None

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        metric_note(col1, "Record (W-D-L)", f"{now_cl['W']}-{now_cl['D']}-{now_cl['L']}",
                    f"Last season: {before_cl['W']}-{before_cl['D']}-{before_cl['L']}")
        col2.metric("Points", now_cl["Points"], delta=now_cl["Points"] - before_cl["Points"])
        col3.metric("Goals For", now_cl["GF"], delta=now_cl["GF"] - before_cl["GF"])
        col4.metric("Goals Against", now_cl["GA"], delta=now_cl["GA"] - before_cl["GA"],
                    delta_color="inverse")
        col5.metric("Average possession", fmt(now_cl["Poss"], 1, "%"),
                    delta=change(now_cl["Poss"], before_cl["Poss"], 1, " pp"))

        # Real Madrid's place in the 36-team league-phase table, against the same matchweek last season
        this_cl_places = last_cl_places = None
        if cl_weeks is None:
            col6.metric("League phase position", "–")
        else:
            this_cl_places = cl_position_history(this_cl_fixtures, TEAM, cl_weeks)
            last_cl_places = cl_position_history(last_cl_fixtures, TEAM, int(last_cl_fixtures["Wk"].max()))
            this_place = int(this_cl_places.iloc[-1]["Position"])
            last_at_week = last_cl_places[last_cl_places["Wk"] == cl_weeks]
            if len(last_at_week) == 0:
                col6.metric("League phase position", ordinal(this_place))
            else:
                last_place = int(last_at_week.iloc[0]["Position"])
                moved = last_place - this_place  # positive = higher up than last season
                if moved == 0:
                    metric_note(col6, "League phase position", ordinal(this_place),
                                f"Same as last season: {ordinal(last_place)}")
                else:
                    col6.metric("League phase position", ordinal(this_place),
                                delta=f"{moved:+d} (was {ordinal(last_place)})")

        # The full table (all 36 teams) next to Real Madrid's place after each matchweek
        if cl_weeks is not None:
            if cl_view == "Full last season":
                last_cl_shown = last_cl_places
            else:
                last_cl_shown = last_cl_places[last_cl_places["Wk"] <= cl_weeks]
            places = pd.DataFrame({
                "This season": this_cl_places.set_index("Wk")["Position"],
                "Last season": last_cl_shown.set_index("Wk")["Position"],
            }).sort_index()
            left, right = st.columns([5, 3])
            with left, card(f"League phase table after matchweek {cl_weeks}"):
                show_table(cl_league_table(this_cl_fixtures, cl_weeks), team=TEAM, height=fit_height(10))
            with right, card("Real Madrid's place in the table by matchweek"):
                show_lines(places, "Matchweek", "League phase position (1 = top)", height=280,
                           y_domain=[36, 1], y_values=[1, 8, 16, 24, 36])

        # Three charts side by side. Each one lines both seasons up by game number.
        last_cl_view = last_cl if cl_view == "Full last season" else last_cl_same

        def per_game(column):
            return pd.DataFrame({
                "This season": this_cl.set_index("Game")[column],
                "Last season": last_cl_view.set_index("Game")[column],
            }).sort_index()

        left, middle, right = st.columns(3)
        with left, card("Cumulative points by games played"):
            show_lines(per_game("Cumulative Points"), "Games played", "Points", height=260, zero=True)
        with middle, card("Goals scored in each match"):
            show_lines(per_game("GF"), "Games played", "Goals scored", height=260, zero=True)
        with right, card("Goals conceded in each match"):
            show_lines(per_game("GA"), "Games played", "Goals conceded", height=260, zero=True)

        # Two tables: this season (played and still to come) and last season's whole run
        table_cols = ["Date", "Round", "Opponent", "Venue", "Result", "GF", "GA"]
        this_games = pd.concat([this_cl[table_cols], upcoming_games(this_sched)[table_cols]],
                               ignore_index=True)
        cl_table_height = fit_height(8)  # the league phase has 8 games; longer tables scroll
        left, right = st.columns(2)
        with left, card("This season's Champions League games"):
            show_table(this_games, height=cl_table_height)
        with right, card("Last season's Champions League run"):
            show_table(last_cl[table_cols], height=cl_table_height)

        st.caption(
            "The Champions League starts with a league phase of 8 games per team, then knockout rounds. "
            "Points use the same rule as La Liga (3 for a win, 1 for a draw). Games still to play are "
            "listed with empty results. The league-phase table is worked out from every Champions League "
            "match on FBref, ordered like UEFA's: points, goal difference, goals scored, away goals, wins "
            "and away wins. UEFA's later tie-breakers (the opponents' results, discipline, club ranking) "
            "are not applied, so teams still level are listed alphabetically. The top 8 go straight to the "
            "round of 16, 9th to 24th play the knockout play-offs and the rest are out."
        )

if page == "Analysis":
    tab_header("Analysis", "What the numbers mean: where the season is heading and why. Everything here is "
               "worked out from the games played so far, so read it as an estimate, not a forecast.")
    analysis_this = prepare_league_games(this_sched)
    analysis_last = prepare_league_games(last_sched)
    games_played = len(analysis_this)

    # An empty box placed here, at the top. The findings are written into it at the
    # very end of the tab, once every section below has worked out its numbers.
    findings_slot = st.container()

    if games_played == 0:
        st.info("No La Liga games played yet this season, so there is nothing to analyse.")
    else:
        # ---- Season projection (La Liga) ----
        info = project_season(analysis_this["Points"], analysis_last["Points"])
        last_same_points = int(analysis_last[analysis_last["Game"] <= games_played]["Points"].sum())

        # Where a points total would have finished in last season's final table
        # (without Real Madrid, so it is a comparison with the other 19 teams)
        last_final = league_table(last_fixtures, int(last_fixtures["Wk"].max()))
        ladder = last_final[last_final["Team"] != TEAM]["Pts"]
        place_expected = equivalent_position(info["expected"], ladder)
        place_best = equivalent_position(info["high"], ladder)
        place_worst = equivalent_position(info["low"], ladder)

        col1, col2, col3, col4 = st.columns(4)
        metric_note(col1, "Projected final points", f"{round(info['expected'])}",
                    f"Likely range: {round(info['low'])} to {round(info['high'])}")
        col2.metric(f"Points after {games_played} games", int(info["current"]),
                    delta=int(info["current"]) - last_same_points)
        col3.metric("Points per game", fmt(info["pace_now"], 2),
                    delta=change(info["pace_now"], last_same_points / games_played, 2))
        if place_best == place_worst:
            finish_note = "Same across the likely range"
        else:
            finish_note = f"Range: {ordinal(place_best)} to {ordinal(place_worst)}"
        metric_note(col4, "Would have finished (last season's table)", ordinal(place_expected), finish_note)

        # The chart: the running points total, this season, last season and the projection
        def running_total(games):
            start = pd.DataFrame({"Game": [0], "Points": [0]})
            return pd.concat([start, pd.DataFrame({"Game": games["Game"],
                                                   "Points": games["Cumulative Points"]})], ignore_index=True)

        left, right = st.columns([2, 1])
        with left, card("Where the season is heading: points by games played"):
            try:
                chart = projection_chart(running_total(analysis_this), running_total(analysis_last),
                                         projection_path(info), height=380)
                if chart is None:
                    raise ValueError("no chart")
                show_chart(chart)
            except Exception:
                st.line_chart(running_total(analysis_this).set_index("Game")["Points"])
        with right, card("How this projection works"):
            st.markdown(
                f"**Expected points** = points so far + games left × a blended pace.\n\n"
                f"- This season's pace: **{info['pace_now']:.2f}** points per game\n"
                f"- Last season's pace in these same remaining games: **{info['pace_last_rest']:.2f}**\n"
                f"- Weight on this season's pace: **{info['weight']:.0%}** (games played ÷ 38). "
                f"It grows as the season goes on.\n"
                f"- Blended pace: **{info['pace']:.2f}**, so about **{round(info['expected'])}** points.\n\n"
                f"**Range** = expected ± one typical swing (**{info['swing'] * (info['left'] ** 0.5):.0f}** points). "
                f"About two seasons in three would end inside it, if every match were independent.\n\n"
                f"**Finish** compares the projected points with last season's final table, without "
                f"Real Madrid. It shows where this total would have finished last year, not where "
                f"it will finish this year."
            )

        st.caption(f"Based on {games_played} of {SEASON_GAMES} La Liga games. A projection this early moves a "
                   "lot with every result. It ignores the opponents still to come, injuries and transfers.")

        # ---- Trends and form: is the team getting better or worse? ----
        st.markdown(
            '<div class="tab-band"><h2>Trends and form</h2>'
            '<p>Is the team improving? The last few matches against the ones before them.</p></div>',
            unsafe_allow_html=True,
        )
        scope_col, window_col = st.columns(2)
        trend_scope = scope_col.radio("Competitions", ["All competitions", "La Liga only"],
                                      horizontal=True, key="analysis_scope")
        trend_window = window_col.slider("Matches in the average", 2, 10, 5, key="analysis_window")
        trend_league_only = trend_scope == "La Liga only"

        this_matches = match_table(clean_schedule(this_sched, trend_league_only),
                                   prepare_shooting(this_shoot, trend_league_only))
        last_matches = match_table(clean_schedule(last_sched, trend_league_only),
                                   prepare_shooting(last_shoot, trend_league_only))

        left, right = st.columns([3, 2])
        with left, card("Match by match: dots are single matches, the gold line is the recent average"):
            metric_choice = st.selectbox("Metric", [m[0] for m in TREND_METRICS], key="analysis_metric",
                                         label_visibility="collapsed")
            _, column, _, decimals, _ = next(m for m in TREND_METRICS if m[0] == metric_choice)
            if len(this_matches) < trend_window:
                st.info(f"Only {len(this_matches)} matches played so far, so there is nothing to show for a "
                        f"{trend_window}-match average yet. Pick a smaller number.")
            else:
                this_series = metric_series(this_matches, column, trend_window)
                last_series = metric_series(last_matches[last_matches["Game"] <= len(this_matches)],
                                            column, trend_window)
                try:
                    chart = trend_chart(this_series, last_series, metric_choice, trend_window,
                                        height=300, decimals=decimals, zero=column != "Poss")
                    if chart is None:
                        raise ValueError("no chart")
                    show_chart(chart)
                except Exception:
                    st.line_chart(this_series.set_index("Game")["Value"])
        with right, card(f"Trend check: last {trend_window} matches against the games before"):
            st.markdown(trend_table_html(trend_rows(this_matches, trend_window)), unsafe_allow_html=True)
            st.caption("Green means better, red means worse, whichever way the number moves (fewer goals "
                       "conceded is better). A change only counts if it is bigger than the usual "
                       "match-to-match swings, so with few games most things read as Steady.")
        st.caption("Grey dashed line: last season's average over the same number of matches. Shots come from "
                   "the shooting table, so a match without shooting data is left out of the shots lines.")

        # ---- Correlations: which numbers go with winning? ----
        st.markdown(
            '<div class="tab-band"><h2>What goes with winning</h2>'
            '<p>Which numbers move together with the result, over this season and last season combined.</p></div>',
            unsafe_allow_html=True,
        )
        outcome_label = st.radio("Compare each number with", [o[0] for o in OUTCOMES],
                                 horizontal=True, key="analysis_outcome")
        outcome_column = dict(OUTCOMES)[outcome_label]

        # Both seasons together give more matches, so the pattern is less of a fluke.
        # The competitions filter above (All competitions or La Liga only) applies here too.
        both_seasons = pd.concat([this_matches.assign(Season="This season"),
                                  last_matches.assign(Season="Last season")], ignore_index=True)
        found = correlations(both_seasons, outcome_column)

        if found.empty:
            st.info("Not enough matches with shots and possession data yet to look for patterns.")
        else:
            left, right = st.columns([2, 3])
            with left, card(f"How closely each number goes with {outcome_label.lower()}"):
                try:
                    chart = correlation_chart(found, height=300)
                    if chart is None:
                        raise ValueError("no chart")
                    show_chart(chart)
                except Exception:
                    st.dataframe(found[["Metric", "r", "n", "Kind"]], hide_index=True)
            with right, card(f"A closer look: one dot per match, against {outcome_label.lower()}"):
                scatter_options = [m for m in CORRELATION_PREDICTORS if m[0] != "Home match"]
                scatter_label = st.selectbox("Number", [m[0] for m in scatter_options],
                                             key="analysis_scatter", label_visibility="collapsed")
                scatter_column = dict(scatter_options)[scatter_label]
                dots = both_seasons[[scatter_column, outcome_column, "Result", "Opponent", "Season"]].dropna(
                    subset=[scatter_column, outcome_column]
                ).rename(columns={scatter_column: "X", outcome_column: "Y"})
                try:
                    chart = scatter_chart(dots, scatter_label, outcome_label, height=270)
                    if chart is None:
                        raise ValueError("no chart")
                    show_chart(chart)
                except Exception:
                    st.scatter_chart(dots, x="X", y="Y")

            with card("In plain English"):
                st.markdown("\n".join(f"- {describe_correlation(row, outcome_label)}"
                                      for _, row in found.iterrows()))
            st.caption("Correlation shows which numbers move together, not what causes what. For example, a team "
                       "that is winning often gives up the ball, so possession can mislead. The grey band in the "
                       "bar chart is the zone where a pattern could easily be luck for this many matches. Home "
                       "matches are scored 1 and away matches 0.")

        # ---- Key findings: written into the box at the top of the tab ----
        with findings_slot, card("Key findings"):
            st.markdown("\n".join(f"- {line}" for line in key_findings(
                info, last_same_points, trend_rows(this_matches, trend_window), trend_window,
                found, outcome_label,
                f"Last season that total would have finished {ordinal(place_expected)}.")))
            st.caption("These sentences update with the filters further down (competitions, matches in the "
                       "average and the comparison). With few matches, treat every line as a first impression.")

# ---- Footer: where the data comes from ----
st.markdown(
    footer_html("FBref", last_downloaded(CURRENT_SEASON) or "never"),
    unsafe_allow_html=True,
)