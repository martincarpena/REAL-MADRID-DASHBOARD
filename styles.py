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

/* Less empty space above the banner */
.block-container {
    padding-top: 3rem;
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
    gap: 1.75rem;
    background: linear-gradient(120deg, var(--navy) 0%, var(--blue) 70%, #1B74C9 100%);
    border-radius: 16px;
    border-bottom: 5px solid var(--gold);
    padding: 2rem 2.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 8px 24px rgba(11, 31, 58, 0.25);
}
/* The crest sits on a white tile so it stays readable on the dark gradient */
.hero img {
    height: 110px;
    width: auto;
    background: rgba(255, 255, 255, 0.96);
    border-radius: 14px;
    padding: 8px 12px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}
.hero h1 {
    color: #FFFFFF !important;
    font-size: 2.4rem;
    font-weight: 800;
    margin: 0;
    padding: 0;
}
.hero p {
    color: rgba(255, 255, 255, 0.85);
    font-size: 1.05rem;
    margin: 0.5rem 0 0 0;
}

/* The summary under the banner: a row of rounded "chips" */
.chips {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
    margin: 0.25rem 0 1.25rem 0;
}
.chip {
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-radius: 999px;
    padding: 0.4rem 1rem;
    font-size: 0.95rem;
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

/* The metric cards: white, rounded, a soft shadow and a gold stripe */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid var(--line);
    border-left: 5px solid var(--gold);
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    min-height: 8rem;
    box-shadow: 0 2px 10px rgba(11, 31, 58, 0.08);
}
[data-testid="stMetricValue"] {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    color: var(--navy);
}

/* Tabs: bolder labels and a gold bar under the selected one */
button[data-baseweb="tab"] {
    font-weight: 600;
    font-size: 1.05rem;
}
[data-baseweb="tab-highlight"] {
    background-color: var(--gold) !important;
    height: 3px;
}

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

/* Tables and the "see the matches" boxes: rounded corners */
[data-testid="stExpander"] {
    border: 1px solid var(--line);
    border-radius: 12px;
}
[data-testid="stDataFrame"] {
    border-radius: 10px;
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