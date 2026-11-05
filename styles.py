"""Visual styling for the dashboard: the CSS and the small pieces of HTML.

Streamlit's config file sets the base colours and font. Anything beyond that
(thin dividers, flat sections, the sidebar menu, the club panel) is done with
CSS, which is the language that styles web pages. app.py sends the CSS to the
browser once, at the top of the page.

There is no Streamlit in this file on purpose. It only builds text.
"""

import base64
import os

# The crest image sits next to this file. If it is missing, the sidebar simply
# shows without it.
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.svg")

# CSS "variables": the colours are defined once here, and every rule below
# uses them with var(--name). To change a colour everywhere, change it once.
# The look: near-black with one blue accent. No boxes: sections are separated
# by thin lines. Inter is the font for everything, and numbers line up.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #0B0C0E;
    --sidebar: #08090A;
    --hover: #14161A;
    --line: #23262B;
    --line2: #181A1E;
    --text: #EDEEF0;
    --muted: #8B9098;
    --dim: #5E636B;
    --accent: #4C8DFF;
    --accent-soft: #8DB4FF;
    --win: #34A874;
    --draw: #6B7280;
    --loss: #E5534B;
}

/* A smaller base size makes the whole page denser. Everything sized in "rem"
   scales with this. */
html {
    font-size: 14px;
}

/* The page itself: flat near-black. The font for all text is Inter, and
   "tabular" numbers give every digit the same width, so columns of numbers
   line up. */
.stApp {
    background: var(--bg);
    font-family: 'Inter', sans-serif;
    font-variant-numeric: tabular-nums;
}
/* The strip at the very top (with the Deploy button). It is solid and a little
   blurred, so page content scrolling underneath does not show through it. */
[data-testid="stHeader"] {
    background: rgba(11, 12, 14, 0.92);
    backdrop-filter: blur(8px);
}

/* Use the whole width of the screen, with little empty space around the page */
.block-container {
    padding-top: 3.4rem;
    padding-left: 1.6rem;
    padding-right: 1.6rem;
    padding-bottom: 1.5rem;
    max-width: 100%;
}

/* Titles use the same sans-serif font as everything else */
h1, h2, h3 {
    font-family: 'Inter', sans-serif !important;
    letter-spacing: 0;
}

/* The banner and chips from the first design (no longer used on the page, but
   the functions in this file can still build them) */
.hero {
    display: flex;
    align-items: center;
    gap: 1.4rem;
    border-bottom: 1px solid var(--line);
    padding: 0.6rem 0;
    margin-bottom: 0.8rem;
}
.hero img {
    height: 48px;
    width: auto;
}
.hero h1 {
    color: var(--text) !important;
    font-size: 1.4rem;
    font-weight: 600;
    margin: 0;
    padding: 0;
}
.hero p {
    color: var(--muted);
    font-size: 0.9rem;
    margin: 0.2rem 0 0 0;
}
.chips {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin: 0.1rem 0 0.8rem 0;
}
.chip {
    border: 1px solid var(--line);
    border-radius: 4px;
    padding: 0.2rem 0.6rem;
    font-size: 0.85rem;
    color: var(--muted);
}
.chip b {
    font-weight: 600;
    color: var(--accent-soft);
}
/* Results: a small coloured square for each win, draw and loss */
.dot {
    display: inline-block;
    width: 1.15rem;
    height: 1.15rem;
    line-height: 1.15rem;
    margin-left: 0.25rem;
    border-radius: 3px;
    text-align: center;
    font-size: 0.62rem;
    font-weight: 700;
    color: #FFFFFF;
}
.dot.W { background: var(--win); }
.dot.D { background: var(--draw); }
.dot.L { background: var(--loss); }

/* A section: no box and no border. app.py names the boxes card_1, card_2...
   and body_1, body_2... and the rules below pick them up by name. What is left
   of a "card" is a small grey title in capitals over a thin line. */
[class*="st-key-card_"] {
    background: transparent;
    border: none;
    border-radius: 0;
    overflow: visible;
    box-shadow: none;
    gap: 0 !important;
}
.card-title {
    color: var(--muted);
    font-weight: 500;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0.2rem 0 0.45rem 0;
    border-bottom: 1px solid var(--line);
}

/* Streamlit pulls the element after a text block up by 1rem. That pulled the
   table or chart over the title. Switch the pull off for the title, and keep
   the title on top of whatever sits under it. */
[class*="st-key-card_"] [data-testid="stMarkdownContainer"]:has(.card-title) {
    margin-bottom: 0 !important;
}
[class*="st-key-card_"] [data-testid="stMarkdown"]:has(.card-title) {
    margin-bottom: 0 !important;
    position: relative;
    z-index: 2;
}

[class*="st-key-body_"] {
    padding: 0.5rem 0 0.2rem 0;
}
/* A table inside a section does not need a border of its own */
[class*="st-key-body_"] [data-testid="stDataFrame"] {
    border: none;
    box-shadow: none;
    border-radius: 0;
}

/* The title of each page: the name and a grey line of text on the same row,
   over one thin line. */
.tab-band {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 0.3rem 1rem;
    padding: 0 0 0.6rem 0;
    border-bottom: 1px solid var(--line);
    margin-bottom: 0.3rem;
}
.tab-band h2 {
    font-family: 'Inter', sans-serif;
    color: var(--text) !important;
    font-size: 1.45rem;
    font-weight: 600;
    margin: 0;
    padding: 0;
}
.tab-band p {
    color: var(--muted);
    font-size: 0.85rem;
    margin: 0;
}
/* A logo in front of the page title (the Champions League page has one) */
.tab-band img {
    height: 34px;
    width: auto;
    align-self: center;
    margin-right: -0.2rem;
}
/* Same fix as for the section titles: switch off Streamlit's pull-up under the
   title, or the line of text that follows would slide underneath it. */
[data-testid="stMarkdownContainer"]:has(.tab-band),
[data-testid="stMarkdown"]:has(.tab-band) {
    margin-bottom: 0 !important;
}

/* Tight spacing between the parts of the page */
[data-testid="stVerticalBlock"] {
    gap: 0.5rem;
}

/* The number strip: no box, a small label in capitals, a big plain number.
   A thin vertical line separates one number from the next. */
[data-testid="stMetric"] {
    background: transparent;
    border: none;
    border-radius: 0;
    padding: 0.2rem 0;
    min-height: 0;
    box-shadow: none;
}
[data-testid="stColumn"]:has([data-testid="stMetric"]):not(:first-child) {
    border-left: 1px solid var(--line2);
    padding-left: 1rem;
}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p {
    color: var(--muted);
    font-size: 0.66rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    font-weight: 600;
    font-size: 1.6rem;
    color: var(--text);
    font-variant-numeric: tabular-nums;
}
/* A number is never cut off with "...": it may overflow its box instead */
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
    overflow: visible !important;
    text-overflow: clip !important;
    white-space: nowrap !important;
}
/* The change under each value (the green and red arrows). Streamlit already
   colours it green or red. Newer versions draw it as a filled pill; this draws
   plain coloured text instead, like the design. */
[data-testid="stMetricDelta"] {
    background: transparent !important;
    padding: 0 !important;
    font-weight: 500;
    font-size: 0.75rem;
}

/* Long labels and notes wrap onto a second line instead of being cut off with
   "..." (the page is narrower now that the menu takes the left side). */
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] *,
[data-testid="stMetricDelta"],
[data-testid="stMetricDelta"] * {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}

/* Section headings written with st.header and st.subheader */
[data-testid="stHeading"] h2 {
    color: var(--text);
    font-weight: 600;
    font-size: 1.3rem;
}
[data-testid="stHeading"] h3 {
    color: var(--text);
    font-weight: 600;
    font-size: 1.05rem;
    padding: 0.5rem 0 0.2rem 0;
}

/* A little air between one section and the next */
[class*="st-key-card_"] {
    margin-bottom: 0.4rem;
}

/* The footer at the bottom of the page */
.footer {
    text-align: center;
    color: var(--dim);
    font-size: 0.75rem;
    border-top: 1px solid var(--line);
    margin-top: 0.8rem;
    padding-top: 0.6rem;
}
.footer b {
    color: var(--muted);
    font-weight: 500;
}

/* The trend check: a small table with a coloured pill for each verdict */
.trend-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}
.trend-table th {
    text-align: left;
    color: var(--muted);
    font-size: 0.66rem;
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.35rem 0.4rem;
    border-bottom: 1px solid var(--line);
    background: transparent;
}
.trend-table td {
    padding: 0.4rem 0.4rem;
    color: var(--text);
    border-bottom: 1px solid var(--line2);
    background: transparent;
}
.trend-table .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.pill {
    display: inline-block;
    border-radius: 3px;
    padding: 0.1rem 0.5rem;
    font-weight: 600;
    font-size: 0.7rem;
    white-space: nowrap;
}
.pill.good { background: #12301F; color: #5FD39A; }
.pill.bad { background: #3A1E1C; color: #FF8F85; }
.pill.flat { background: #1E2127; color: #A5ABB6; }

/* The sidebar: a shade darker than the page */
[data-testid="stSidebar"] {
    background: var(--sidebar);
    border-right: 1px solid var(--line);
}

/* The crest, the name and a small blue line at the top of the sidebar */
.brand {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.2rem 0 0.9rem 0;
}
.brand img {
    height: 40px;
    width: auto;
}
.brand b {
    display: block;
    font-family: 'Inter', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1.15;
}
.brand span {
    font-size: 0.62rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--accent);
}
/* Small grey headings that name a part of the sidebar */
.side-label {
    font-size: 0.62rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--dim);
    margin: 1.1rem 0 0.6rem 0.2rem;
}

/* The page menu: one button per page, stacked in a box that app.py names "nav".
   The page you are on is a "primary" button, which gets a dark fill and a thin
   blue bar on the left. The others are plain text rows that light up when you
   point at them. */
.st-key-nav {
    gap: 0.05rem;
}
.st-key-nav .stButton,
.st-key-nav .stButton > button {
    width: 100%;
}
.st-key-nav .stButton > button {
    justify-content: flex-start;
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 3px;
    padding: 0.2rem 0.8rem;
    min-height: 2rem;
    box-shadow: none;
}
.st-key-nav .stButton > button > div {
    width: 100%;
    justify-content: flex-start;
}
.st-key-nav .stButton > button p {
    color: var(--muted);
    font-size: 0.9rem;
    font-weight: 400;
    text-align: left;
}
.st-key-nav .stButton > button:hover {
    background: var(--hover);
    border-left-color: transparent;
}
.st-key-nav .stButton > button:hover p {
    color: var(--text);
}
.st-key-nav .stButton > button[kind="primary"],
.st-key-nav .stButton > button[data-testid="stBaseButton-primary"] {
    background: var(--hover);
    border-left-color: var(--accent);
}
.st-key-nav .stButton > button[kind="primary"] p,
.st-key-nav .stButton > button[data-testid="stBaseButton-primary"] p {
    color: var(--text);
    font-weight: 500;
}

/* Less empty space above the crest at the top of the sidebar */
[data-testid="stSidebarHeader"] {
    height: 2rem;
    padding-top: 0;
    padding-bottom: 0;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 0.5rem;
}

/* The club panel in the sidebar: where the team stands, always in view. No box:
   a big place, then thin rows. */
.club {
    border-top: 1px solid var(--line);
    padding: 0.9rem 0 0 0;
}
.club .place {
    font-family: 'Inter', sans-serif;
    font-size: 2.4rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1;
}
.club .sub {
    color: var(--muted);
    font-size: 0.72rem;
    margin: 0.3rem 0 0.6rem 0;
}
.club .row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.3rem 0;
    border-top: 1px solid var(--line2);
    font-size: 0.8rem;
    color: var(--muted);
}
.club .row b {
    color: var(--text);
    font-weight: 600;
}
.club .dot {
    margin-left: 0;
    margin-right: 0.25rem;
}

/* Buttons: a thin outline that turns blue when you point at it */
.stButton > button {
    border: 1px solid var(--line);
    border-radius: 4px;
    color: var(--text);
    background: transparent;
    font-weight: 400;
}
.stButton > button:hover {
    background: var(--hover);
    border-color: var(--accent);
    color: var(--accent-soft);
}

/* The player picker (the box app.py names "players"): the player whose report is
   open is the "primary" button, drawn with a blue edge and a soft blue fill. */
.st-key-players .stButton > button[kind="primary"],
.st-key-players .stButton > button[data-testid="stBaseButton-primary"] {
    border-color: var(--accent);
    background: rgba(76, 141, 255, 0.14);
    color: var(--accent-soft);
    font-weight: 600;
}

/* The player picker buttons: smaller text that is never cut off with "..." */
.st-key-players .stButton > button {
    padding: 0.2rem 0.3rem;
    min-height: 2.1rem;
}
.st-key-players .stButton > button,
.st-key-players .stButton > button * {
    overflow: visible !important;
    text-overflow: clip !important;
    white-space: nowrap !important;
}
.st-key-players .stButton > button p {
    font-size: 0.8rem;
}

/* The "see the matches" boxes, and tables that are not in a section */
[data-testid="stExpander"] {
    background: transparent;
    border: 1px solid var(--line);
    border-radius: 4px;
    box-shadow: none;
}
[data-testid="stDataFrame"] {
    border: none;
    border-radius: 0;
    overflow: hidden;
}
</style>
"""


def _data_uri(path):
    """A picture file as a "data URI": the whole image written out as text, so it
    can sit inside HTML. The kind of picture comes from the file's ending (.svg,
    .png or .webp). Returns None if the file is missing."""
    kinds = {".svg": "image/svg+xml", ".png": "image/png", ".webp": "image/webp"}
    kind = kinds.get(os.path.splitext(path)[1].lower())
    if kind is None:
        return None
    try:
        with open(path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode("ascii")
    except OSError:
        return None
    return f"data:{kind};base64,{encoded}"


def logo_data_uri():
    """The club crest (logo.svg next to this file), or None if it is missing."""
    return _data_uri(LOGO_PATH)


def champions_logo_data_uri():
    """The Champions League logo: a file called champions_league.svg, .png or
    .webp next to this file. Returns None if there is none."""
    folder = os.path.dirname(os.path.abspath(__file__))
    for extension in (".svg", ".png", ".webp"):
        uri = _data_uri(os.path.join(folder, "champions_league" + extension))
        if uri:
            return uri
    return None


def brand_html(logo_uri, subtitle):
    """The crest, the name and a small line under it, at the top of the sidebar.
    A single line with no blank lines, like the other blocks."""
    crest = f'<img src="{logo_uri}" alt="Crest">' if logo_uri else ""
    return f'<div class="brand">{crest}<div><b>Real Madrid</b><span>{subtitle}</span></div></div>'


def club_panel_html(place, played, points, record, goal_difference, form, next_match, note):
    """The panel in the sidebar: league place in big letters, then rows for
    points, record, goal difference, the last results and the next opponent.
    `form` is text such as "W W D L W"; only the letters W, D and L are turned
    into squares. `next_match` can be None. Single line, no blank lines."""
    dots = "".join(f'<span class="dot {r}">{r}</span>' for r in form.split() if r in ("W", "D", "L")) or "–"
    rows = [
        ("Points", f"<b>{points}</b> in {played} games"),
        ("Record (W-D-L)", f"<b>{record}</b>"),
        ("Goal difference", f"<b>{goal_difference:+d}</b>"),
        ("Last results", dots),
    ]
    if next_match:
        rows.append(("Next match", f"<b>{next_match}</b>"))
    body = "".join(f'<div class="row"><span>{label}</span><span>{value}</span></div>' for label, value in rows)
    return f'<div class="club"><div class="place">{place}</div><div class="sub">{note}</div>{body}</div>'


def hero_html(title, subtitle, logo_uri=None):
    """The banner at the top of the page, as one block of HTML. It is written
    on a single line with no blank lines in it, because a blank line would end
    the HTML block and the rest would show up as plain text."""
    crest = f'<img src="{logo_uri}" alt="Crest">' if logo_uri else ""
    return f'<div class="hero">{crest}<div><h1>{title}</h1><p>{subtitle}</p></div></div>'


def summary_html(place, played, points, record, goal_difference, form):
    """The one-line summary as a row of chips. `form` is the last results as
    text such as "W W D L W" (or a dash when nothing has been played). Only the
    letters W, D and L are turned into squares, so nothing else can slip into
    the HTML. Like the banner, it is a single line with no blank lines in it."""
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


def tab_band_html(title, subtitle, logo_uri=None):
    """The title row at the top of a tab: the name and one grey line next to it,
    with a small logo in front when `logo_uri` is given. Like the other blocks,
    it is a single line with no blank lines in it."""
    logo = f'<img src="{logo_uri}" alt="Logo">' if logo_uri else ""
    return f'<div class="tab-band">{logo}<h2>{title}</h2><p>{subtitle}</p></div>'


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