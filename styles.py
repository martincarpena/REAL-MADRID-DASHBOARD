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
# The look: charcoal and gold. Gold is the accent, Inter is the text font and
# Playfair Display (a serif) is the title font.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

:root {
    --bg: #121418;
    --sidebar: #0E1013;
    --surface: #1A1D23;
    --surface2: #21252C;
    --line: #2C313A;
    --gold: #D4AF37;
    --gold-soft: #E6C768;
    --text: #ECEAE4;
    --muted: #9AA1AD;
}

/* A slightly smaller base size makes the whole page denser and calmer.
   Everything sized in "rem" scales with this. */
html {
    font-size: 15px;
}

/* The page itself: charcoal, with a very faint warm glow in the top right.
   The font for all normal text is Inter (clean, made for screens and numbers). */
.stApp {
    background:
        radial-gradient(1100px 520px at 88% -8%, rgba(212, 175, 55, 0.05), transparent 62%),
        var(--bg);
    font-family: 'Inter', sans-serif;
}
/* The strip at the very top (with the Deploy button). It is solid and a little
   blurred, so page content scrolling underneath does not show through it. */
[data-testid="stHeader"] {
    background: rgba(18, 20, 24, 0.92);
    backdrop-filter: blur(8px);
}

/* Use the whole width of the screen, with less empty space around the page */
.block-container {
    padding-top: 4.4rem;
    padding-left: 2rem;
    padding-right: 2rem;
    padding-bottom: 2rem;
    max-width: 100%;
}

/* Titles use an elegant serif (Playfair Display). If the font cannot load,
   the browser falls back to any serif font. */
h1, h2, h3 {
    font-family: 'Playfair Display', Georgia, serif !important;
    letter-spacing: 0;
}

/* The banner and chips from the first design (no longer used on the page, but
   the functions in this file can still build them) */
.hero {
    display: flex;
    align-items: center;
    gap: 1.4rem;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1rem 1.8rem;
    margin-bottom: 0.8rem;
}
.hero img {
    height: 60px;
    width: auto;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 8px;
    padding: 5px 8px;
}
.hero h1 {
    color: var(--text) !important;
    font-size: 1.7rem;
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
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 6px;
    padding: 0.25rem 0.7rem;
    font-size: 0.85rem;
    color: var(--muted);
}
.chip b {
    font-weight: 600;
    color: var(--gold-soft);
}
/* Last results: a small coloured circle for each win, draw and loss */
.dot {
    display: inline-block;
    width: 1.3rem;
    height: 1.3rem;
    line-height: 1.3rem;
    margin-left: 0.3rem;
    border-radius: 50%;
    text-align: center;
    font-size: 0.68rem;
    font-weight: 600;
    color: #FFFFFF;
}
.dot.W { background: #2A8F63; }
.dot.D { background: #5F6877; }
.dot.L { background: #C2423A; }

/* Every chart and main table sits in a "card": a dark panel with a thin border
   and a small title in capitals over a hairline. app.py names the boxes card_1,
   card_2... and body_1, body_2... and the rules below pick them up by name. */
[class*="st-key-card_"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: none;
    gap: 0 !important;
}
.card-title {
    color: var(--muted);
    font-weight: 600;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0.75rem 1rem 0.6rem 1rem;
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
    padding: 0.7rem 0.8rem 0.4rem 0.8rem;
}
/* A table inside a card does not need a border of its own */
[class*="st-key-body_"] [data-testid="stDataFrame"] {
    border: none;
    box-shadow: none;
    border-radius: 0;
}

/* The title of each page: plain serif text over a thin line, with a short gold
   rule at the left end of the line. */
.tab-band {
    position: relative;
    padding: 0 0 0.75rem 0;
    border-bottom: 1px solid var(--line);
    margin-bottom: 0.4rem;
}
.tab-band::after {
    content: "";
    position: absolute;
    left: 0;
    bottom: -1px;
    width: 64px;
    height: 2px;
    background: var(--gold);
}
.tab-band h2 {
    font-family: 'Playfair Display', Georgia, serif;
    color: var(--text) !important;
    font-size: 1.6rem;
    font-weight: 600;
    margin: 0 0 0.2rem 0;
    padding: 0;
}
.tab-band p {
    color: var(--muted);
    font-size: 0.85rem;
    margin: 0;
}
/* Same fix as for the card titles: switch off Streamlit's pull-up under the
   title, or the line of text that follows would slide underneath it. */
[data-testid="stMarkdownContainer"]:has(.tab-band),
[data-testid="stMarkdown"]:has(.tab-band) {
    margin-bottom: 0 !important;
}

/* Tighter spacing between the parts of the page */
[data-testid="stVerticalBlock"] {
    gap: 0.6rem;
}

/* The number tiles: a thin box, a small label in capitals, a calm number */
[data-testid="stMetric"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.6rem 0.9rem;
    min-height: 6.4rem;
    box-shadow: none;
}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p {
    color: var(--muted);
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
[data-testid="stMetricValue"] {
    font-weight: 600;
    font-size: 1.55rem;
    color: var(--text);
    font-variant-numeric: tabular-nums;
}
/* The change under each value (the green and red arrows). Streamlit already
   colours it green or red. */
[data-testid="stMetricDelta"] {
    font-weight: 600;
    font-size: 0.78rem;
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
    font-size: 1.5rem;
}
[data-testid="stHeading"] h2::after {
    content: "";
    display: block;
    width: 40px;
    height: 2px;
    margin-top: 0.4rem;
    background: var(--gold);
}
[data-testid="stHeading"] h3 {
    color: var(--text);
    font-weight: 600;
    font-size: 1.05rem;
    padding: 0.8rem 0 0.4rem 0;
}

/* Cards in the same row stretch to the height of the tallest one, so their
   bottom edges line up. */
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
    color: var(--muted);
    font-size: 0.8rem;
    border-top: 1px solid var(--line);
    margin-top: 0.8rem;
    padding-top: 0.8rem;
}
.footer b {
    color: var(--gold-soft);
    font-weight: 600;
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
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.35rem 0.4rem;
    border-bottom: 1px solid var(--line);
    background: transparent;
}
.trend-table td {
    padding: 0.5rem 0.4rem;
    color: var(--text);
    border-bottom: 1px solid var(--line);
    background: transparent;
}
.trend-table .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
.pill {
    display: inline-block;
    border-radius: 4px;
    padding: 0.1rem 0.55rem;
    font-weight: 600;
    font-size: 0.72rem;
    white-space: nowrap;
}
.pill.good { background: #173A2B; color: #6FE0A8; }
.pill.bad { background: #412522; color: #FF8F85; }
.pill.flat { background: #2B303A; color: #B4BBC8; }

/* The sidebar: a shade darker than the page */
[data-testid="stSidebar"] {
    background: var(--sidebar);
    border-right: 1px solid var(--line);
}

/* The name and crest at the top of the sidebar */
.brand {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.2rem 0 1rem 0;
    border-bottom: 1px solid var(--line);
}
.brand img {
    height: 42px;
    width: auto;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 8px;
    padding: 4px 6px;
}
.brand b {
    display: block;
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.15;
}
.brand span {
    font-size: 0.65rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--gold-soft);
}
/* Small grey headings that name a part of the sidebar */
.side-label {
    font-size: 0.65rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--muted);
    margin: 0.9rem 0 0.1rem 0.2rem;
}

/* The page menu: one button per page, stacked in a box that app.py names "nav".
   The page you are on is a "primary" button, which gets a dark fill and a gold
   edge. The others are plain text rows that light up when you point at them. */
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
    border-radius: 4px;
    padding: 0.2rem 0.8rem;
    min-height: 2.1rem;
    box-shadow: none;
}
.st-key-nav .stButton > button > div {
    width: 100%;
    justify-content: flex-start;
}
.st-key-nav .stButton > button p {
    color: var(--muted);
    font-size: 0.9rem;
    font-weight: 500;
    text-align: left;
}
.st-key-nav .stButton > button:hover {
    background: var(--surface);
    border-left-color: transparent;
}
.st-key-nav .stButton > button:hover p {
    color: var(--text);
}
.st-key-nav .stButton > button[kind="primary"],
.st-key-nav .stButton > button[data-testid="stBaseButton-primary"] {
    background: var(--surface);
    border-left-color: var(--gold);
}
.st-key-nav .stButton > button[kind="primary"] p,
.st-key-nav .stButton > button[data-testid="stBaseButton-primary"] p {
    color: var(--text);
    font-weight: 600;
}

/* Less empty space above the crest at the top of the sidebar */
[data-testid="stSidebarHeader"] {
    height: 2.2rem;
    padding-top: 0;
    padding-bottom: 0;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 0.5rem;
}

/* The club panel in the sidebar: where the team stands, always in view */
.club {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 0.8rem 1rem;
}
.club .place {
    font-family: 'Playfair Display', Georgia, serif;
    font-size: 2rem;
    font-weight: 600;
    color: var(--gold);
    line-height: 1;
}
.club .sub {
    color: var(--muted);
    font-size: 0.75rem;
    margin: 0.3rem 0 0.6rem 0;
}
.club .row {
    display: flex;
    justify-content: space-between;
    padding: 0.28rem 0;
    border-top: 1px solid var(--line);
    font-size: 0.82rem;
    color: var(--muted);
}
.club .row b {
    color: var(--text);
    font-weight: 600;
}
.club .dot {
    margin-left: 0;
    margin-right: 0.3rem;
}

/* Buttons: a thin outline that turns gold when you point at it */
.stButton > button {
    border: 1px solid #3A404B;
    border-radius: 6px;
    color: var(--text);
    background: transparent;
    font-weight: 500;
}
.stButton > button:hover {
    background: transparent;
    border-color: var(--gold);
    color: var(--gold-soft);
}

/* The player picker (the box app.py names "players"): the player whose report is
   open is the "primary" button, drawn with a gold edge and a soft gold fill. */
.st-key-players .stButton > button[kind="primary"],
.st-key-players .stButton > button[data-testid="stBaseButton-primary"] {
    border-color: var(--gold);
    background: rgba(212, 175, 55, 0.14);
    color: var(--gold-soft);
    font-weight: 700;
}

/* The "see the matches" boxes, and tables that are not in a card */
[data-testid="stExpander"] {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: none;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 6px;
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


def brand_html(logo_uri, subtitle):
    """The crest, the name and a small line under it, at the top of the sidebar.
    A single line with no blank lines, like the other blocks."""
    crest = f'<img src="{logo_uri}" alt="Crest">' if logo_uri else ""
    return f'<div class="brand">{crest}<div><b>Real Madrid</b><span>{subtitle}</span></div></div>'


def club_panel_html(place, played, points, record, goal_difference, form, next_match, note):
    """The panel in the sidebar: league place in big gold letters, then rows for
    points, record, goal difference, the last results and the next opponent.
    `form` is text such as "W W D L W"; only the letters W, D and L are turned
    into dots. `next_match` can be None. Single line, no blank lines."""
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