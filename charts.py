"""The chart designs for the dashboard.

Every chart in the app is built here, so they all share one look: gold for
this season, slate grey for last season, faint gridlines, no borders. The
functions use Altair (installed with Streamlit) and return a chart. They
return None when Altair is not available, and app.py then falls back to
Streamlit's plain charts.

There is no Streamlit in this file on purpose. It only builds the charts.
"""

import pandas as pd

try:
    import altair as alt
except Exception:  # without Altair the app shows its plain fallback charts
    alt = None

THIS_COLOR = "#D4AF37"  # this season: gold
LAST_COLOR = "#7B8798"  # last season: slate grey
HIGHLIGHT = "#FFF0B3"   # the pale gold a bar turns when you point at it
PROJECTION = "#ECEAE4"  # the projection: warm white
SEASONS = ["This season", "Last season"]

INK = "#ECEAE4"    # warm white for labels that matter
MUTED = "#9AA1AD"  # soft grey for axes
GRID = "#2A2F38"   # faint line for gridlines


def _season_color():
    """One colour rule for both seasons, so every chart uses the same colours
    and the legend is only drawn once, at the top."""
    return alt.Color(
        "Season:N",
        scale=alt.Scale(domain=SEASONS, range=[THIS_COLOR, LAST_COLOR]),
        legend=alt.Legend(title=None),
    )


def _polish(chart, height, vertical_grid=False):
    """The finishing touches shared by every chart: a set height, no frame
    around the plot, soft gridlines and quiet axis text. Gridlines run
    sideways by default; vertical_grid=True gives lines going up and down
    instead (for the horizontal bar charts)."""
    chart = (
        chart.properties(height=height, padding={"left": 6, "right": 30, "top": 6, "bottom": 4})
        .configure(background="transparent")
        .configure_view(strokeWidth=0)
        .configure_axis(
            domain=False,
            ticks=False,
            gridColor=GRID,
            labelColor=MUTED,
            titleColor=MUTED,
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight="normal",
            labelPadding=6,
            titlePadding=10,
        )
        .configure_legend(
            orient="top",
            labelColor=INK,
            labelFontSize=12,
            symbolType="circle",
            symbolSize=80,
        )
    )
    if vertical_grid:
        return chart.configure_axisY(grid=False)
    return chart.configure_axisX(grid=False)


def line_chart(wide, x_title, y_title, height=240, y_domain=None, y_values=None, zero=False, decimals=0):
    """This season against last season as two lines you can point at.

    `wide` has one row per x value (the match or matchweek number) and the two
    columns "This season" and "Last season". Blanks are skipped, so a line
    simply stops where there is no data. This season is a thicker solid line,
    last season a thinner dashed one.

    Move the mouse over the chart: a vertical line follows it to the nearest
    match, the dots on that line grow, and both seasons' numbers appear next to
    them. Click a season in the legend to show only that season (click it again
    to bring the other one back).

    y_domain=[20, 1] flips the axis (used for league position, 1 at the top).
    y_values sets exactly which numbers the axis shows. zero=True makes the
    axis start at 0; otherwise it fits the data. decimals is how many
    decimals the numbers on the chart show."""
    if alt is None:
        return None
    long = (
        wide.rename_axis("X")
        .reset_index()
        .melt(id_vars="X", var_name="Season", value_name="Value")
        .dropna()
    )
    if long.empty:
        return None

    y_scale = alt.Scale(domain=y_domain) if y_domain else alt.Scale(zero=zero)
    if y_values:
        y_axis = alt.Axis(values=y_values)
    elif decimals == 0:
        y_axis = alt.Axis(tickMinStep=1, format="d")  # whole numbers only: no 0.5 or 1.5
    else:
        y_axis = alt.Axis()

    # Two "selections": things the chart remembers about what you did with the mouse.
    # `hover` remembers which match is nearest to the cursor (empty when the
    # cursor is away, so nothing is highlighted). `season_pick` remembers which
    # season you clicked in the legend.
    hover = alt.selection_point(fields=["X"], nearest=True, on="mouseover", clear="mouseout", empty=False)
    season_pick = alt.selection_point(fields=["Season"], bind="legend")

    x_axis = alt.X(
        "X:Q",
        title=x_title,
        scale=alt.Scale(padding=12),  # keeps the first and last dots off the edges
        axis=alt.Axis(tickMinStep=1, format="d"),
    )
    base = alt.Chart(long).encode(
        x=x_axis,
        y=alt.Y("Value:Q", title=y_title, scale=y_scale, axis=y_axis),
        color=_season_color(),
    )
    faded = alt.condition(season_pick, alt.value(1), alt.value(0.15))

    lines = base.mark_line(strokeJoin="round").encode(
        size=alt.Size("Season:N", scale=alt.Scale(domain=SEASONS, range=[2.5, 1.5]), legend=None),
        strokeDash=alt.StrokeDash(
            "Season:N",
            scale=alt.Scale(domain=SEASONS, range=[[1, 0], [5, 4]]),
            legend=None,
        ),
        opacity=faded,
    ).add_params(season_pick)
    points = base.mark_point(filled=True).encode(
        size=alt.condition(hover, alt.value(90), alt.value(30)),
        opacity=faded,
    )

    # An invisible layer that finds the match nearest to the cursor ...
    catcher = alt.Chart(long).mark_point().encode(x=x_axis, opacity=alt.value(0)).add_params(hover)
    # ... a thin vertical line drawn only at that match ...
    guide = (
        alt.Chart(long)
        .mark_rule(color=INK, opacity=0.35, strokeWidth=1)
        .encode(x=x_axis)
        .transform_filter(hover)
    )
    # ... and each season's number, written next to its dot.
    numbers = []
    for season, shift in [("This season", -12), ("Last season", 18)]:
        numbers.append(
            base.mark_text(align="left", dx=10, dy=shift, fontWeight="bold", fontSize=11)
            .encode(text=alt.Text("Value:Q", format=f".{decimals}f"))
            .transform_filter(hover)
            .transform_filter(alt.datum.Season == season)
        )

    return _polish(guide + lines + points + catcher + numbers[0] + numbers[1], height)


def leaders_bar_chart(data, label, height=300):
    """Horizontal bars for the top players in one statistic, longest bar at the
    top, with the number written at the end of each bar. `data` has the columns
    Player and Value."""
    if alt is None or data.empty:
        return None
    top = float(data["Value"].max())
    base = alt.Chart(data).encode(
        y=alt.Y(
            "Player:N",
            sort="-x",
            title=None,
            axis=alt.Axis(labelLimit=170, labelColor=INK, labelFontSize=12),
        ),
        x=alt.X(
            "Value:Q",
            title=label,
            scale=alt.Scale(domain=[0, top * 1.18 if top > 0 else 1]),
            axis=alt.Axis(tickMinStep=1, format="d"),
        ),
    )
    # The bar under the cursor turns pale gold (empty=False: no highlight when nothing is hovered)
    hover = alt.selection_point(fields=["Player"], on="mouseover", clear="mouseout", empty=False)
    bars = base.mark_bar(cornerRadiusEnd=2, size=14).encode(
        color=alt.condition(hover, alt.value(HIGHLIGHT), alt.value(THIS_COLOR)),
        tooltip=[alt.Tooltip("Player:N"), alt.Tooltip("Value:Q", title=label)],
    ).add_params(hover)
    numbers = base.mark_text(align="left", dx=5, color=INK, fontWeight="bold", fontSize=11).encode(
        text=alt.Text("Value:Q", format="d")
    )
    return _polish(bars + numbers, height, vertical_grid=True)


def result_bars_chart(data, height=240):
    """Average possession in wins, draws and losses, this season next to last
    season. `data` has the columns Result, Season and Average possession."""
    if alt is None or data.empty:
        return None
    data = data.rename(columns={"Average possession": "Possession"})
    top = float(data["Possession"].max())
    upper = 80 if top <= 70 else 100  # leave room above the bars for the numbers

    base = alt.Chart(data).encode(
        x=alt.X(
            "Result:N",
            sort=["Wins", "Draws", "Losses"],
            title=None,
            axis=alt.Axis(labelAngle=0, labelColor=INK, labelFontSize=12),
        ),
        xOffset=alt.XOffset("Season:N", sort=SEASONS),
        y=alt.Y(
            "Possession:Q",
            title="Average possession (%)",
            scale=alt.Scale(domain=[0, upper]),
        ),
        color=_season_color(),
    )
    # The bar under the cursor stays bright and the others dim (with nothing
    # hovered, all bars are bright)
    hover = alt.selection_point(fields=["Season", "Result"], on="mouseover", clear="mouseout")
    bars = base.mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0.45)),
        tooltip=[
            alt.Tooltip("Season:N"),
            alt.Tooltip("Result:N"),
            alt.Tooltip("Games:Q"),
            alt.Tooltip("Possession:Q", format=".1f"),
        ],
    ).add_params(hover)
    numbers = base.mark_text(dy=-8, color=INK, fontWeight="bold", fontSize=11).encode(
        text=alt.Text("Possession:Q", format=".1f")
    )
    return _polish(bars + numbers, height)


def projection_chart(actual, last, path, total_games=38, height=360):
    """The season so far and where it is heading: this season's points (solid
    gold), last season's whole run (grey, dashed) and the projection (white,
    dashed) with a shaded band for the likely range. `actual` and `last` have
    the columns Game and Points (the running total); `path` has Game, Expected,
    Low and High, from the last game played to the end of the season. Point at a
    dot to see its numbers."""
    if alt is None or actual.empty:
        return None
    names = ["This season", "Last season", "Projection"]
    long = pd.concat([
        actual.assign(Series="This season"),
        last.assign(Series="Last season"),
        path.rename(columns={"Expected": "Points"})[["Game", "Points"]].assign(Series="Projection"),
    ], ignore_index=True)

    x = alt.X(
        "Game:Q",
        title="Games played",
        scale=alt.Scale(domain=[0, total_games + 2]),
        axis=alt.Axis(values=[0, 5, 10, 15, 20, 25, 30, 35, total_games], format="d"),
    )
    y = alt.Y("Points:Q", title="Points", scale=alt.Scale(zero=True))
    color = alt.Color(
        "Series:N",
        scale=alt.Scale(domain=names, range=[THIS_COLOR, LAST_COLOR, PROJECTION]),
        legend=alt.Legend(title=None),
    )
    base = alt.Chart(long).encode(x=x, y=y, color=color)

    lines = base.mark_line(strokeJoin="round").encode(
        size=alt.Size("Series:N", scale=alt.Scale(domain=names, range=[2.5, 1.5, 2.5]), legend=None),
        strokeDash=alt.StrokeDash(
            "Series:N",
            scale=alt.Scale(domain=names, range=[[1, 0], [5, 4], [7, 4]]),
            legend=None,
        ),
    )
    dots = base.transform_filter(alt.datum.Series == "This season").mark_point(filled=True, size=32).encode(
        tooltip=[alt.Tooltip("Game:Q", title="Games played"), alt.Tooltip("Points:Q")]
    )
    # The likely range: a soft band between the low and high paths
    band = alt.Chart(path).mark_area(color=PROJECTION, opacity=0.12).encode(
        x=x, y=alt.Y("Low:Q", title="Points"), y2="High:Q"
    )
    # A faint line marking "now"
    now = alt.Chart(actual.tail(1)[["Game"]]).mark_rule(color=MUTED, strokeDash=[2, 3], opacity=0.6).encode(x=x)
    # The projected total at the end of the season, with its range
    end = path.tail(1).copy()
    end["Label"] = (
        "Expected " + end["Expected"].round().astype(int).astype(str)
        + " (" + end["Low"].round().astype(int).astype(str)
        + "-" + end["High"].round().astype(int).astype(str) + ")"
    )
    label = alt.Chart(end).mark_text(align="right", dx=-4, dy=-16, fontWeight="bold", fontSize=11, color=INK).encode(
        x=x, y=alt.Y("Expected:Q", title="Points"), text="Label:N"
    )
    return _polish(band + lines + dots + now + label, height)


RESULT_COLORS = {"W": "#2FA36F", "D": "#6F7886", "L": "#D9473D"}  # the same as the dots under the banner


def trend_chart(this, last, label, window, height=340, decimals=1, zero=True):
    """One metric, match by match. Each dot is one match, coloured by its
    result (point at it to see the opponent). The thick gold line is this
    season's average of the last `window` matches, the grey dashed line is last
    season's, and the faint dashed line across is this season's average.
    `this` has the columns Game, Value, Rolling, Opponent and Result; `last` has
    Game and Rolling."""
    if alt is None or this.empty:
        return None
    average = float(this["Value"].mean())
    first, last_game = float(this["Game"].min()), float(this["Game"].max())
    x = alt.X(
        "Game:Q",
        title="Match",
        scale=alt.Scale(domain=[first - 0.5, last_game + 0.5]),
        axis=alt.Axis(tickMinStep=1, format="d"),
    )
    y = alt.Y("Value:Q", title=label, scale=alt.Scale(zero=zero))

    def rolling_y(name):
        return alt.Y(f"{name}:Q", title=label, scale=alt.Scale(zero=zero))

    dots = alt.Chart(this).mark_circle(size=70, opacity=0.9).encode(
        x=x,
        y=y,
        color=alt.Color(
            "Result:N",
            scale=alt.Scale(domain=list(RESULT_COLORS), range=list(RESULT_COLORS.values())),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            alt.Tooltip("Opponent:N"),
            alt.Tooltip("Result:N"),
            alt.Tooltip("Value:Q", title=label, format=f".{decimals}f"),
        ],
    )
    this_line = alt.Chart(this.dropna(subset=["Rolling"])).mark_line(
        color=THIS_COLOR, strokeWidth=2.5, strokeJoin="round"
    ).encode(x=x, y=rolling_y("Rolling"))
    last_line = alt.Chart(last.dropna(subset=["Rolling"])).mark_line(
        color=LAST_COLOR, strokeWidth=1.5, strokeDash=[5, 4], strokeJoin="round"
    ).encode(x=x, y=rolling_y("Rolling"))

    avg_df = pd.DataFrame({"Average": [average], "Game": [first],
                           "Text": [f"Season average {average:.{decimals}f}"]})
    avg_rule = alt.Chart(avg_df).mark_rule(color=INK, strokeDash=[4, 4], opacity=0.4).encode(
        y=rolling_y("Average")
    )
    avg_text = alt.Chart(avg_df).mark_text(align="left", dx=4, dy=-8, fontSize=11, color=MUTED).encode(
        x=x, y=rolling_y("Average"), text="Text:N"
    )
    return _polish(avg_rule + avg_text + last_line + this_line + dots, height)


def correlation_chart(data, height=260):
    """How closely each number goes with winning, as horizontal bars from -1 to
    +1. Gold means more of it goes with a better result, red means more of it
    goes with a worse one, and grey means the link is too small to tell from
    luck (the grey band in the middle is that "could be chance" zone). `data`
    has the columns Metric, r, n, Chance, Clear and Kind, strongest first."""
    if alt is None or data.empty:
        return None
    kinds = ["Clear positive", "Clear negative", "Not clear"]
    chance = float(data["Chance"].max())
    order = data["Metric"].tolist()

    def axis_x(field):
        """The same horizontal axis for every layer, so they line up."""
        return alt.X(
            field,
            title="Correlation (-1 to +1)",
            scale=alt.Scale(domain=[-1, 1]),
            axis=alt.Axis(values=[-1, -0.5, 0, 0.5, 1], format="+.1f"),
        )

    base = alt.Chart(data).encode(
        y=alt.Y(
            "Metric:N",
            sort=order,
            title=None,
            axis=alt.Axis(labelLimit=170, labelColor=INK, labelFontSize=12),
        ),
        x=axis_x("r:Q"),
    )
    zone = alt.Chart(pd.DataFrame({"a": [-chance], "b": [chance]})).mark_rect(
        color=MUTED, opacity=0.14
    ).encode(x=axis_x("a:Q"), x2="b:Q")
    zero = alt.Chart(pd.DataFrame({"z": [0]})).mark_rule(color=INK, opacity=0.5).encode(x=axis_x("z:Q"))
    bars = base.mark_bar(cornerRadiusEnd=2, size=16).encode(
        color=alt.Color(
            "Kind:N",
            scale=alt.Scale(domain=kinds, range=[THIS_COLOR, "#D9473D", "#5B6573"]),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            alt.Tooltip("Metric:N"),
            alt.Tooltip("r:Q", title="Correlation", format="+.2f"),
            alt.Tooltip("n:Q", title="Matches"),
            alt.Tooltip("Kind:N", title="Link"),
        ],
    )
    right = base.transform_filter(alt.datum.r >= 0).mark_text(
        align="left", dx=5, color=INK, fontWeight="bold", fontSize=11
    ).encode(text=alt.Text("r:Q", format="+.2f"))
    left = base.transform_filter(alt.datum.r < 0).mark_text(
        align="right", dx=-5, color=INK, fontWeight="bold", fontSize=11
    ).encode(text=alt.Text("r:Q", format="+.2f"))
    return _polish(zone + zero + bars + right + left, height, vertical_grid=True)


def scatter_chart(data, x_label, y_label, height=260):
    """One number against the result, one dot per match (coloured by its
    result), with a straight line showing the overall tendency. If the line is
    nearly flat, the number does not tell you much about the result. `data` has
    the columns X, Y, Result, Opponent and Season; point at a dot for details."""
    if alt is None or data.empty:
        return None
    base = alt.Chart(data).encode(
        x=alt.X("X:Q", title=x_label, scale=alt.Scale(zero=False)),
        y=alt.Y("Y:Q", title=y_label, scale=alt.Scale(zero=False)),
    )
    dots = base.mark_circle(size=55, opacity=0.8).encode(
        color=alt.Color(
            "Result:N",
            scale=alt.Scale(domain=list(RESULT_COLORS), range=list(RESULT_COLORS.values())),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            alt.Tooltip("Opponent:N"),
            alt.Tooltip("Season:N"),
            alt.Tooltip("Result:N"),
            alt.Tooltip("X:Q", title=x_label, format=".1f"),
            alt.Tooltip("Y:Q", title=y_label),
        ],
    )
    trend = base.transform_regression("X", "Y").mark_line(color=INK, strokeWidth=1.8, strokeDash=[6, 3])
    return _polish(dots + trend, height)


# ---- The player report charts (the Player Reports page) ----
# They take the match table from player_report.club_matches(): one row per match,
# with the columns Played, Started, Min, Gls, Ast, Sh, SoT, Opponent, Comp, Date.

PLAYER_ROLES = ["Started", "Came on"]


def _numbered(matches):
    """The matches he played, oldest first, with a Match number (1, 2, 3...)."""
    played = matches[matches["Played"]].reset_index(drop=True)
    return played.assign(Match=range(1, len(played) + 1))


def _match_axis(title="Match (oldest to newest)"):
    return alt.X("Match:O", title=title, axis=alt.Axis(labelAngle=0, labelColor=INK))


def _match_tooltip(*extra):
    return [
        alt.Tooltip("Match:O"),
        alt.Tooltip("Opponent:N"),
        alt.Tooltip("Comp:N", title="Competition"),
        alt.Tooltip("Date:T", format="%d %b %Y"),
        *extra,
    ]


def minutes_chart(matches, height=240):
    """One bar per match he played, as tall as his minutes. Gold when he started,
    grey when he came on from the bench."""
    if alt is None:
        return None
    data = _numbered(matches)
    if data.empty:
        return None
    data = data.assign(Role=data["Started"].map({True: "Started", False: "Came on"}))
    top = max(95.0, float(data["Min"].max()) + 5)

    base = alt.Chart(data).encode(
        x=_match_axis(),
        y=alt.Y("Min:Q", title="Minutes", scale=alt.Scale(domain=[0, top])),
        color=alt.Color(
            "Role:N",
            scale=alt.Scale(domain=PLAYER_ROLES, range=[THIS_COLOR, LAST_COLOR]),
            legend=alt.Legend(title=None),
        ),
    )
    hover = alt.selection_point(fields=["Match"], on="mouseover", clear="mouseout")
    bars = base.mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0.5)),
        tooltip=_match_tooltip(alt.Tooltip("Role:N", title="He"), alt.Tooltip("Min:Q", title="Minutes")),
    ).add_params(hover)
    # The numbers are drawn from their own chart so that they stay warm white
    # instead of taking the colour of their bar.
    numbers = alt.Chart(data).mark_text(dy=-8, color=INK, fontSize=10).encode(
        x=_match_axis(),
        y=alt.Y("Min:Q", scale=alt.Scale(domain=[0, top])),
        text=alt.Text("Min:Q", format="d"),
    )
    return _polish(bars + numbers, height)


def _two_series(data, first, second):
    """Turns two columns of a match table into the long form a grouped chart
    needs: one row per match and per series, with the columns Type and Count."""
    keep = ["Match", "Opponent", "Comp", "Date"]
    return pd.concat([
        data[keep].assign(Type=first[0], Count=data[first[1]]),
        data[keep].assign(Type=second[0], Count=data[second[1]]),
    ], ignore_index=True)


def goals_assists_chart(matches, height=240):
    """Goals and assists in each match, stacked into one bar."""
    if alt is None:
        return None
    data = _numbered(matches)
    if data.empty:
        return None
    long = _two_series(data, ("Goals", "Gls"), ("Assists", "Ast"))
    top = max(2, int((data["Gls"] + data["Ast"]).max()) + 1)

    hover = alt.selection_point(fields=["Match", "Type"], on="mouseover", clear="mouseout")
    bars = alt.Chart(long).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=_match_axis(),
        y=alt.Y(
            "Count:Q",
            title="Goals and assists",
            scale=alt.Scale(domain=[0, top]),
            axis=alt.Axis(tickMinStep=1, format="d"),
        ),
        color=alt.Color(
            "Type:N",
            scale=alt.Scale(domain=["Goals", "Assists"], range=[THIS_COLOR, LAST_COLOR]),
            legend=alt.Legend(title=None),
        ),
        opacity=alt.condition(hover, alt.value(1), alt.value(0.55)),
        tooltip=_match_tooltip(alt.Tooltip("Type:N"), alt.Tooltip("Count:Q")),
    ).add_params(hover)
    return _polish(bars, height)


def shots_chart(matches, height=240):
    """Shots and shots on target in each match, side by side."""
    if alt is None:
        return None
    data = _numbered(matches)
    if data.empty:
        return None
    long = _two_series(data, ("Shots", "Sh"), ("On target", "SoT"))
    top = max(4, int(data["Sh"].max()) + 1)

    hover = alt.selection_point(fields=["Match", "Type"], on="mouseover", clear="mouseout")
    bars = alt.Chart(long).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=_match_axis(),
        xOffset=alt.XOffset("Type:N", sort=["Shots", "On target"]),
        y=alt.Y(
            "Count:Q",
            title="Shots",
            scale=alt.Scale(domain=[0, top]),
            axis=alt.Axis(tickMinStep=1, format="d"),
        ),
        color=alt.Color(
            "Type:N",
            scale=alt.Scale(domain=["Shots", "On target"], range=[LAST_COLOR, THIS_COLOR]),
            legend=alt.Legend(title=None),
        ),
        opacity=alt.condition(hover, alt.value(1), alt.value(0.55)),
        tooltip=_match_tooltip(alt.Tooltip("Type:N"), alt.Tooltip("Count:Q")),
    ).add_params(hover)
    return _polish(bars, height)


def running_total_chart(running, height=260):
    """His goals, assists and goals + assists adding up through the season.
    `running` is player_report.running_totals(): the columns Match, Date,
    Opponent, Goals, Assists and Goals + assists."""
    if alt is None or running.empty:
        return None
    names = ["Goals", "Assists", "Goals + assists"]
    long = running.melt(
        id_vars=["Match", "Date", "Opponent"], value_vars=names, var_name="Series", value_name="Total"
    )
    base = alt.Chart(long).encode(
        x=alt.X("Match:Q", title="Matches played", axis=alt.Axis(tickMinStep=1, format="d")),
        y=alt.Y(
            "Total:Q",
            title="Season total so far",
            scale=alt.Scale(zero=True),
            axis=alt.Axis(tickMinStep=1, format="d"),
        ),
        color=alt.Color(
            "Series:N",
            scale=alt.Scale(domain=names, range=[THIS_COLOR, LAST_COLOR, PROJECTION]),
            legend=alt.Legend(title=None),
        ),
    )
    # Goals + assists is dashed, so that when it lies exactly on top of the goals
    # line (a player with no assists) the gold still shows through the gaps.
    lines = base.mark_line(interpolate="step-after", strokeWidth=2).encode(
        strokeDash=alt.StrokeDash(
            "Series:N",
            scale=alt.Scale(domain=names, range=[[1, 0], [1, 0], [6, 4]]),
            legend=None,
        )
    )
    dots = base.mark_point(filled=True, size=30).encode(
        tooltip=[
            alt.Tooltip("Match:Q"),
            alt.Tooltip("Opponent:N"),
            alt.Tooltip("Date:T", format="%d %b %Y"),
            alt.Tooltip("Series:N"),
            alt.Tooltip("Total:Q"),
        ]
    )
    return _polish(lines + dots, height)