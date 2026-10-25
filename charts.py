"""The chart designs for the dashboard.

Every chart in the app is built here, so they all share one look: Real Madrid
blue for this season, grey for last season, light gridlines, no borders. The
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

THIS_COLOR = "#00529F"  # this season: Real Madrid blue
LAST_COLOR = "#9aa0a6"  # last season: grey
GOLD = "#C9A227"       # the highlight colour when you point at something
SEASONS = ["This season", "Last season"]

INK = "#0B1F3A"    # dark navy for labels that matter
MUTED = "#6B7280"  # soft grey for axes
GRID = "#ECE8DD"   # light warm grey for gridlines


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
            symbolSize=140,
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
        size=alt.Size("Season:N", scale=alt.Scale(domain=SEASONS, range=[3.5, 2]), legend=None),
        strokeDash=alt.StrokeDash(
            "Season:N",
            scale=alt.Scale(domain=SEASONS, range=[[1, 0], [5, 4]]),
            legend=None,
        ),
        opacity=faded,
    ).add_params(season_pick)
    points = base.mark_point(filled=True).encode(
        size=alt.condition(hover, alt.value(150), alt.value(44)),
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
            base.mark_text(align="left", dx=10, dy=shift, fontWeight="bold", fontSize=12)
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
    # The bar under the cursor turns gold (empty=False: no gold when nothing is hovered)
    hover = alt.selection_point(fields=["Player"], on="mouseover", clear="mouseout", empty=False)
    bars = base.mark_bar(cornerRadiusEnd=4, size=18).encode(
        color=alt.condition(hover, alt.value(GOLD), alt.value(THIS_COLOR)),
        tooltip=[alt.Tooltip("Player:N"), alt.Tooltip("Value:Q", title=label)],
    ).add_params(hover)
    numbers = base.mark_text(align="left", dx=5, color=INK, fontWeight="bold", fontSize=12).encode(
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
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
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
    blue), last season's whole run (grey, dashed) and the projection (gold,
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
        scale=alt.Scale(domain=names, range=[THIS_COLOR, LAST_COLOR, GOLD]),
        legend=alt.Legend(title=None),
    )
    base = alt.Chart(long).encode(x=x, y=y, color=color)

    lines = base.mark_line(strokeJoin="round").encode(
        size=alt.Size("Series:N", scale=alt.Scale(domain=names, range=[3.5, 2, 3.5]), legend=None),
        strokeDash=alt.StrokeDash(
            "Series:N",
            scale=alt.Scale(domain=names, range=[[1, 0], [5, 4], [7, 4]]),
            legend=None,
        ),
    )
    dots = base.transform_filter(alt.datum.Series == "This season").mark_point(filled=True, size=46).encode(
        tooltip=[alt.Tooltip("Game:Q", title="Games played"), alt.Tooltip("Points:Q")]
    )
    # The likely range: a soft band between the low and high paths
    band = alt.Chart(path).mark_area(color=GOLD, opacity=0.18).encode(
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
    label = alt.Chart(end).mark_text(align="right", dx=-4, dy=-16, fontWeight="bold", fontSize=12, color=INK).encode(
        x=x, y=alt.Y("Expected:Q", title="Points"), text="Label:N"
    )
    return _polish(band + lines + dots + now + label, height)


RESULT_COLORS = {"W": "#2E8B57", "D": "#8A94A6", "L": "#C0392B"}  # the same as the dots under the banner


def trend_chart(this, last, label, window, height=340, decimals=1, zero=True):
    """One metric, match by match. Each dot is one match, coloured by its
    result (point at it to see the opponent). The thick blue line is this
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

    dots = alt.Chart(this).mark_circle(size=110, opacity=0.9).encode(
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
        color=THIS_COLOR, strokeWidth=3.5, strokeJoin="round"
    ).encode(x=x, y=rolling_y("Rolling"))
    last_line = alt.Chart(last.dropna(subset=["Rolling"])).mark_line(
        color=LAST_COLOR, strokeWidth=2, strokeDash=[5, 4], strokeJoin="round"
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
    +1. Blue means more of it goes with a better result, red means more of it
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
    bars = base.mark_bar(cornerRadiusEnd=4, size=22).encode(
        color=alt.Color(
            "Kind:N",
            scale=alt.Scale(domain=kinds, range=[THIS_COLOR, "#C0392B", "#B8BDC6"]),
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
        align="left", dx=5, color=INK, fontWeight="bold", fontSize=12
    ).encode(text=alt.Text("r:Q", format="+.2f"))
    left = base.transform_filter(alt.datum.r < 0).mark_text(
        align="right", dx=-5, color=INK, fontWeight="bold", fontSize=12
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
    dots = base.mark_circle(size=90, opacity=0.8).encode(
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
    trend = base.transform_regression("X", "Y").mark_line(color=INK, strokeWidth=2.5, strokeDash=[6, 3])
    return _polish(dots + trend, height)