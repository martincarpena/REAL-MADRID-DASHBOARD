"""Visual styling for the dashboard: the CSS and the page banner.

Streamlit's config file sets the base colours and font. Anything beyond that
(gradients, card borders, shadows, the banner) is done with CSS, which is the
language that styles web pages. app.py sends the CSS to the browser once, at
the top of the page.

There is no Streamlit in this file on purpose. It only builds text.
"""

import base64
import os

# The crest image sits next to this file. If it is missing, the banner simply
# shows without it.
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.svg")

# CSS "variables": the colours are defined once here, and every rule below
# uses them with var(--name). To change a colour everywhere, change it once.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&display=swap');

:root {
    --navy: #0B1F3A;
    --blue: #00529F;
    --gold: #C9A227;
    --cream: #F3F0E8;
    --line: #E4E0D5;
}

/* Use the whole width of the screen, with less empty space around the page */
.block-container {
    padding-top: 2.5rem;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 2rem;
    max-width: 100%;
}

/* Headings get a bolder, sportier font. If the font cannot load, the
   browser falls back to a plain sans-serif. */
h1, h2, h3 {
    font-family: 'Montserrat', sans-serif !important;
    letter-spacing: -0.01em;
}

/* The banner at the top: a gradient from navy to blue with a gold edge */
.hero {
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    gap: 1.25rem;
    background: linear-gradient(120deg, var(--navy) 0%, var(--blue) 70%, #1B74C9 100%);
    border-radius: 16px;
    border-bottom: 4px solid var(--gold);
    padding: 0.9rem 1.75rem;
    margin-bottom: 0.6rem;
    box-shadow: 0 8px 24px rgba(11, 31, 58, 0.25);
}
/* The crest sits on a white tile so it stays readable on the dark gradient */
.hero img {
    height: 72px;
    width: auto;
    background: rgba(255, 255, 255, 0.96);
    border-radius: 12px;
    padding: 6px 10px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
.hero h1 {
    color: #FFFFFF !important;
    font-size: 1.9rem;
    font-weight: 800;
    margin: 0;
    padding: 0;
}
.hero p {
    color: rgba(255, 255, 255, 0.85);
    font-size: 0.95rem;
    margin: 0.25rem 0 0 0;
}

/* The summary under the banner: a row of rounded "chips" */
.chips {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin: 0.1rem 0 0.7rem 0;
}
.chip {
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 0.3rem 0.85rem;
    font-size: 0.9rem;
    color: var(--navy);
    box-shadow: 0 1px 4px rgba(11, 31, 58, 0.06);
}
.chip b {
    font-weight: 700;
}
/* Last results: a small coloured circle for each win, draw and loss */
.dot {
    display: inline-block;
    width: 1.45rem;
    height: 1.45rem;
    line-height: 1.45rem;
    margin-left: 0.3rem;
    border-radius: 50%;
    text-align: center;
    font-size: 0.75rem;
    font-weight: 700;
    color: #FFFFFF;
}
.dot.W { background: #2E8B57; }
.dot.D { background: #8A94A6; }
.dot.L { background: #C0392B; }

/* Every chart and main table sits in a "card": a white box with a strong blue
   border, a navy title strip on top and the content below. app.py names the
   boxes card_1, card_2... and body_1, body_2... and the rules below pick them
   up by that name. */
[class*="st-key-card_"] {
    background: #FFFFFF;
    border: 2px solid var(--blue);
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(0, 82, 159, 0.18);
    gap: 0 !important;
}
.card-title {
    background: linear-gradient(100deg, var(--navy) 0%, var(--blue) 100%);
    color: #FFFFFF;
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 0.9rem;
    letter-spacing: 0.01em;
    padding: 0.5rem 0.9rem;
    border-bottom: 3px solid var(--gold);
}

/* Streamlit pulls the element after a text block up by 1rem. That pulled the
   table or chart over the gold line. Switch the pull off for the title, and
   keep the title strip on top of whatever sits under it. */
[class*="st-key-card_"] [data-testid="stMarkdownContainer"]:has(.card-title) {
    margin-bottom: 0 !important;
}
[class*="st-key-card_"] [data-testid="stMarkdown"]:has(.card-title) {
    margin-bottom: 0 !important;
    position: relative;
    z-index: 2;
}

[class*="st-key-body_"] {
    padding: 0.7rem 0.8rem 0.4rem 0.8rem;
}
/* A table inside a card does not need a border of its own */
[class*="st-key-body_"] [data-testid="stDataFrame"] {
    border: none;
    box-shadow: none;
    border-radius: 0;
}

/* The title of each tab: a slim navy band with a gold edge. The title and the
   one-line description sit side by side. */
.tab-band {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.2rem 1.1rem;
    background: linear-gradient(100deg, var(--navy) 0%, var(--blue) 100%);
    border-left: 6px solid var(--gold);
    border-radius: 12px;
    padding: 0.5rem 1.2rem;
    box-shadow: 0 4px 14px rgba(11, 31, 58, 0.20);
}
.tab-band h2 {
    font-family: 'Montserrat', sans-serif;
    color: #FFFFFF !important;
    font-size: 1.3rem;
    font-weight: 800;
    margin: 0;
    padding: 0;
}
.tab-band p {
    color: rgba(255, 255, 255, 0.85);
    font-size: 0.9rem;
    margin: 0;
}
/* Same fix as for the card titles: switch off Streamlit's pull-up under the band,
   or the line of text that follows would slide underneath it. */
[data-testid="stMarkdownContainer"]:has(.tab-band),
[data-testid="stMarkdown"]:has(.tab-band) {
    margin-bottom: 0 !important;
}

/* Tighter spacing between the parts of the page */
[data-testid="stVerticalBlock"] {
    gap: 0.6rem;
}

/* The metric cards: white, rounded, a soft shadow and a gold stripe. They are
   kept compact so a whole row of them takes little height. */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-left: 5px solid var(--gold);
    border-radius: 12px;
    padding: 0.55rem 0.9rem;
    min-height: 6.8rem;
    box-shadow: 0 2px 12px rgba(11, 31, 58, 0.10);
}
[data-testid="stMetricValue"] {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 1.75rem;
    color: var(--navy);
}
/* The change under each value (the green and red arrows): a little bolder so it
   reads at a glance. Streamlit already colours it green or red. */
[data-testid="stMetricDelta"] {
    font-weight: 700;
    font-size: 0.85rem;
}

/* Tabs: the bar spans the whole page and every tab takes an equal share of it.
   Streamlit draws each tab as a <div role="tab">, and the strip they sit in as
   <div role="tablist">. The gold bar under the selected tab is a small piece
   inside the tab that Streamlit paints blue, so it is repainted gold here. */
[role="tablist"] {
    width: 100% !important;
    gap: 0 !important;
}
[role="tab"] {
    flex: 1 1 0 !important;
    justify-content: center !important;
}
[role="tab"] p {
    font-weight: 600;
    font-size: 1.05rem;
}
[role="tab"][data-selected] .react-aria-SelectionIndicator {
    background-color: var(--gold) !important;
    height: 4px !important;
}
[role="tab"][data-selected] p {
    color: var(--navy);
}

/* Section headings: the big title at the top of each tab gets a short gold
   bar underneath, and the smaller subheadings are navy */
[data-testid="stHeading"] h2 {
    color: var(--navy);
    font-weight: 800;
}
[data-testid="stHeading"] h2::after {
    content: "";
    display: block;
    width: 56px;
    height: 4px;
    margin-top: 0.4rem;
    border-radius: 2px;
    background: var(--gold);
}
[data-testid="stHeading"] h3 {
    color: var(--navy);
    font-weight: 700;
    font-size: 1.2rem;
    padding: 0.8rem 0 0.4rem 0;
}

/* Cards in the same row stretch to the height of the tallest one, so their
   bottom edges line up. This is the one block that is a best guess without
   seeing the page: if cards look wrong after it, delete just this block. */
[data-testid="stColumn"]:has([class*="st-key-card_"]) {
    display: flex;
    flex-direction: column;
}
[data-testid="stColumn"]:has([class*="st-key-card_"]) > [data-testid="stVerticalBlock"] {
    flex: 1 1 auto;
}
[data-testid="stColumn"] [data-testid="stLayoutWrapper"]:has(> [class*="st-key-card_"]),
[data-testid="stColumn"] [data-testid="stLayoutWrapper"][class*="st-key-card_"] {
    flex: 1 1 auto;
}
[data-testid="stColumn"] [class*="st-key-card_"] {
    height: 100%;
}

/* The footer at the bottom of the page */
.footer {
    text-align: center;
    color: #6B7280;
    font-size: 0.85rem;
    border-top: 1px solid var(--line);
    margin-top: 0.8rem;
    padding-top: 0.8rem;
}
.footer b {
    color: var(--navy);
}

/* The trend check: a small table with a coloured pill for each verdict */
.trend-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}
.trend-table th {
    text-align: left;
    color: #6B7280;
    font-weight: 600;
    padding: 0.35rem 0.4rem;
    border-bottom: 2px solid var(--line);
    background: transparent;
}
.trend-table td {
    padding: 0.5rem 0.4rem;
    color: var(--navy);
    border-bottom: 1px solid var(--line);
    background: transparent;
}
.trend-table .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.pill {
    display: inline-block;
    border-radius: 999px;
    padding: 0.15rem 0.7rem;
    font-weight: 700;
    font-size: 0.8rem;
    white-space: nowrap;
}
.pill.good { background: #DDF3E4; color: #17653A; }
.pill.bad { background: #FADBD8; color: #9B2C20; }
.pill.flat { background: #E8ECF1; color: #4B5563; }

/* The sidebar fades from cream to white */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--cream) 0%, #FFFFFF 100%);
    border-right: 1px solid var(--line);
}

/* Buttons: blue outline that fills in when you point at it */
.stButton > button {
    border: 1px solid var(--blue);
    border-radius: 10px;
    color: var(--blue);
    font-weight: 600;
}
.stButton > button:hover {
    background: var(--blue);
    color: #FFFFFF;
}

/* The "see the matches" boxes, and tables that are not in a card */
[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 2px solid var(--blue);
    border-radius: 14px;
    box-shadow: 0 4px 16px rgba(0, 82, 159, 0.14);
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
}
</style>
"""


def logo_data_uri():
    """The crest as a "data URI": the whole image written out as text, so it
    can sit inside the banner's HTML. Returns None if the file is missing."""
    try:
        with open(LOGO_PATH, "rb") as file:
            encoded = base64.b64encode(file.read()).decode("ascii")
    except OSError:
        return None
    return f"data:image/svg+xml;base64,{encoded}"


def hero_html(title, subtitle, logo_uri=None):
    """The banner at the top of the page, as one block of HTML. It is written
    on a single line with no blank lines in it, because a blank line would end
    the HTML block and the rest would show up as plain text."""
    crest = f'<img src="{logo_uri}" alt="Crest">' if logo_uri else ""
    return f'<div class="hero">{crest}<div><h1>{title}</h1><p>{subtitle}</p></div></div>'


def summary_html(place, played, points, record, goal_difference, form):
    """The one-line summary as a row of chips. `form` is the last results as
    text such as "W W D L W" (or a dash when nothing has been played). Only the
    letters W, D and L are turned into dots, so nothing else can slip into the
    HTML. Like the banner, it is a single line with no blank lines in it."""
    dots = "".join(f'<span class="dot {r}">{r}</span>' for r in form.split() if r in ("W", "D", "L"))
    chips = [
        f"<b>{place}</b> in La Liga",
        f"<b>{points}</b> points after {played} games",
        f"<b>{record}</b> (W-D-L)",
        f"<b>{goal_difference:+d}</b> goal difference",
    ]
    if dots:
        chips.append(f"Last results {dots}")
    return '<div class="chips">' + "".join(f'<span class="chip">{c}</span>' for c in chips) + "</div>"


def tab_band_html(title, subtitle):
    """The banner at the top of a tab: the title and one line under it. Like
    the page banner, it is a single line with no blank lines in it."""
    return f'<div class="tab-band"><h2>{title}</h2><p>{subtitle}</p></div>'


def footer_html(source, downloaded):
    """The line at the very bottom: where the numbers come from and when this
    season's data was last downloaded. Single line, like the other blocks."""
    return f'<div class="footer">Data: <b>{source}</b> &nbsp;·&nbsp; This season\'s data last downloaded: {downloaded}</div>'


def trend_table_html(rows):
    """The trend check as an HTML table, one row per metric. Each row is a dict
    with Metric, Recent, Earlier, Change, Verdict and Kind (good, bad or flat,
    which picks the pill's colour). A single line with no blank lines, like the
    other blocks."""
    head = ('<tr><th>Metric</th><th class="num">Last matches</th><th class="num">Before</th>'
            '<th class="num">Change</th><th>Trend</th></tr>')
    body = "".join(
        f'<tr><td>{r["Metric"]}</td><td class="num">{r["Recent"]}</td><td class="num">{r["Earlier"]}</td>'
        f'<td class="num">{r["Change"]}</td><td><span class="pill {r["Kind"]}">{r["Verdict"]}</span></td></tr>'
        for r in rows
    )
    return f'<table class="trend-table">{head}{body}</table>'