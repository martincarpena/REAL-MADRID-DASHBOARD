"""The chart designs for the dashboard.

Every chart in the app is built here, so they all share one look: Real Madrid
blue for this season, grey for last season, light gridlines, no borders. The
functions use Altair (installed with Streamlit) and return a chart. They
return None when Altair is not available, and app.py then falls back to
Streamlit's plain charts.

There is no Streamlit in this file on purpose. It only builds the charts.
"""

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