"""The maths behind the Analysis tab.

The other tabs show the numbers. This file looks for what they mean: where the
season is heading, whether the team is improving, and which numbers go together
with winning. Everything here is a simple, explainable calculation on the
matches played so far, so it is an estimate and not a forecast. Samples are
small (a season has 38 league games), and the app says so next to every result.

There is no Streamlit in this file on purpose. It only does the maths.
"""

import re

import numpy as np
import pandas as pd

SEASON_GAMES = 38  # games in a La Liga season


# ---- Season projection -----------------------------------------------------

def project_season(this_points, last_points, total_games=SEASON_GAMES):
    """Project this season's final points from the games played so far.

    `this_points` is the points won in each game so far this season (3, 1 or 0)
    in order, and `last_points` the same for all of last season. Returns None
    when no game has been played.

    The expected points for the games still to play use a blend of two paces:
    this season's points per game so far, and last season's points per game in
    those same remaining games. The blend leans on last season at first and
    moves towards this season's pace as more games are played, because three
    games say little about a season and thirty say a lot.

    The range is one typical swing wide: the usual spread of points in a single
    match, scaled up for the number of games left (it grows with the square
    root of the games left, as random swings partly cancel). Roughly two out of
    three seasons like this would end inside it, if matches were independent."""
    this_points = pd.Series(this_points, dtype=float).reset_index(drop=True)
    last_points = pd.Series(last_points, dtype=float).reset_index(drop=True)
    played = len(this_points)
    if played == 0:
        return None
    left = max(total_games - played, 0)

    current = float(this_points.sum())
    pace_now = float(this_points.mean())
    last_rest = last_points.iloc[played:total_games]
    pace_last_rest = float(last_rest.mean()) if len(last_rest) else float(last_points.mean())

    weight = min(played / total_games, 1.0)  # how much to trust this season's pace
    pace = weight * pace_now + (1 - weight) * pace_last_rest

    everything = pd.concat([this_points, last_points])
    swing = float(everything.std(ddof=1)) if len(everything) > 1 else 1.2

    return {
        "played": played,
        "left": left,
        "current": current,
        "pace_now": pace_now,
        "pace_last_rest": pace_last_rest,
        "pace": pace,
        "weight": weight,
        "swing": swing,
        "expected": current + left * pace,
        "low": float(max(current, current + left * pace - swing * np.sqrt(left))),
        "high": float(min(current + 3 * left, current + left * pace + swing * np.sqrt(left))),
    }


def projection_path(info, total_games=SEASON_GAMES):
    """The projected points game by game, from the last game played to the end
    of the season: the expected path and the low and high edges of the range.
    The range starts at zero width and widens with the games ahead."""
    rows = []
    for ahead in range(info["left"] + 1):
        expected = info["current"] + ahead * info["pace"]
        spread = info["swing"] * np.sqrt(ahead)
        rows.append({
            "Game": info["played"] + ahead,
            "Expected": expected,
            "Low": max(info["current"], expected - spread),
            "High": min(info["current"] + 3 * ahead, expected + spread),
        })
    return pd.DataFrame(rows)


def equivalent_position(points, ladder_points):
    """Where a points total would have finished in a past table: one place
    below every team in `ladder_points` with strictly more points."""
    return 1 + int((pd.Series(ladder_points) > round(points)).sum())


# ---- Trends and form --------------------------------------------------------

# label shown, column in the match table, is a higher number better, decimals, suffix
TREND_METRICS = [
    ("Points", "Points", True, 2, ""),
    ("Goals scored", "GF", True, 2, ""),
    ("Goals conceded", "GA", False, 2, ""),
    ("Shots", "Sh", True, 1, ""),
    ("Shots on target", "SoT", True, 1, ""),
    ("Possession", "Poss", True, 1, "%"),
]


def _clean_name(name):
    """FBref puts a small country code in front of some team names ("it Inter").
    Strip it."""
    return re.sub(r"^[a-z]{2,3}\s+(?=[A-Z])", "", str(name))


def match_table(schedule, shooting):
    """One row per match played, with everything the analysis needs side by side:
    the result, goals and possession from the match log (`schedule`, cleaned by
    tactics.clean_schedule) and the shots from the shooting log (`shooting`,
    cleaned by prepare_shooting). The two are joined on the date, because Real
    Madrid never plays twice in one day. A match without shooting data keeps
    blank shots."""
    shots = shooting[["Date", "Sh", "SoT"]]
    table = schedule.merge(shots, on="Date", how="left")
    table["Opponent"] = table["Opponent"].apply(_clean_name)
    table["Home"] = (table["Venue"] == "Home").astype(int)
    table["GD"] = table["GF"] - table["GA"]
    table["Shot accuracy"] = (table["SoT"] / table["Sh"] * 100).where(table["Sh"] > 0)
    return table


def metric_series(matches, column, window):
    """One metric, match by match: the Value, and its Rolling average over the
    last `window` matches (blank until there are enough matches). Matches with
    no number for this metric are left out."""
    series = matches.dropna(subset=[column]).reset_index(drop=True)
    out = pd.DataFrame({
        "Game": series["Game"],
        "Value": series[column].astype(float),
        "Opponent": series["Opponent"],
        "Result": series["Result"],
    })
    out["Rolling"] = out["Value"].rolling(window).mean()
    return out


def trend_row(values, window, higher_is_better):
    """Is the last `window` matches different from the matches before them?

    Compares the average of the last `window` matches with the average of all
    the earlier ones. The change only counts if it is bigger than the usual
    match-to-match swings (the standard error of the difference). Otherwise the
    answer is "steady". With too few games to compare, the answer is "early".
    Returns the two averages and a verdict: "better", "worse", "steady" or "early"."""
    values = pd.Series(values, dtype=float).dropna().reset_index(drop=True)
    recent = values.iloc[-window:]
    earlier = values.iloc[:-window]
    if len(values) < window + 2 or len(earlier) < 2:
        return {"recent": float(recent.mean()) if len(recent) else None,
                "earlier": float(earlier.mean()) if len(earlier) else None,
                "verdict": "early"}
    change = float(recent.mean() - earlier.mean())
    noise = float(values.std(ddof=1) * np.sqrt(1 / len(recent) + 1 / len(earlier)))
    if abs(change) <= noise:
        verdict = "steady"
    elif (change > 0) == higher_is_better:
        verdict = "better"
    else:
        verdict = "worse"
    return {"recent": float(recent.mean()), "earlier": float(earlier.mean()), "verdict": verdict}


def trend_rows(matches, window):
    """The trend check for every metric in TREND_METRICS, as a list of rows
    ready to show: the metric, its two averages as text, and the verdict."""
    words = {"better": ("Improving", "good"), "worse": ("Slipping", "bad"),
             "steady": ("Steady", "flat"), "early": ("Too early", "flat")}
    rows = []
    for label, column, higher_is_better, decimals, suffix in TREND_METRICS:
        result = trend_row(matches[column], window, higher_is_better)
        text, kind = words[result["verdict"]]

        def show(number):
            return "–" if number is None else f"{number:.{decimals}f}{suffix}"

        if result["recent"] is None or result["earlier"] is None:
            change = "–"
        else:
            change = f"{result['recent'] - result['earlier']:+.{decimals}f}" + (" pp" if suffix else "")
        rows.append({"Metric": label, "Recent": show(result["recent"]), "Earlier": show(result["earlier"]),
                     "Change": change, "Verdict": text, "Kind": kind})
    return rows


# ---- Correlations: which numbers go with winning ----------------------------

# label shown, column in the match table
CORRELATION_PREDICTORS = [
    ("Possession", "Poss"),
    ("Shots", "Sh"),
    ("Shots on target", "SoT"),
    ("Shot accuracy", "Shot accuracy"),
    ("Home match", "Home"),
]
OUTCOMES = [("Goal difference", "GD"), ("Points", "Points")]


def strength_word(r):
    """A plain word for how strong a correlation is."""
    size = abs(r)
    if size < 0.1:
        return "no"
    if size < 0.3:
        return "a weak"
    if size < 0.5:
        return "a moderate"
    return "a strong"


def correlations(matches, outcome_column, minimum_matches=8):
    """How closely each number in CORRELATION_PREDICTORS goes with the outcome
    (goal difference or points), match by match.

    The number is the correlation r, from -1 to +1: +1 means the two rise
    together every time, -1 means one rises as the other falls, and 0 means
    no pattern. A correlation is only "clear" when it is bigger than the
    pure-chance level for that many matches (about 2 divided by the square
    root of the number of matches). Anything smaller could easily be luck.
    A metric with fewer than `minimum_matches` matches, or with the same value
    every time, is left out. Sorted by strength."""
    rows = []
    for label, column in CORRELATION_PREDICTORS:
        pair = matches[[column, outcome_column]].dropna()
        if len(pair) < minimum_matches or pair[column].nunique() < 2 or pair[outcome_column].nunique() < 2:
            continue
        r = float(pair[column].corr(pair[outcome_column]))
        chance = 2 / float(np.sqrt(len(pair)))
        clear = abs(r) > chance
        kind = "Not clear" if not clear else ("Clear positive" if r > 0 else "Clear negative")
        rows.append({"Metric": label, "r": r, "n": len(pair), "Chance": chance, "Clear": clear, "Kind": kind})
    table = pd.DataFrame(rows, columns=["Metric", "r", "n", "Chance", "Clear", "Kind"])
    return table.reindex(table["r"].abs().sort_values(ascending=False).index).reset_index(drop=True)


def describe_correlation(row, outcome_label):
    """One plain-English sentence about one correlation."""
    metric = row["Metric"].lower()
    outcome = outcome_label.lower()
    facts = f"r = {row['r']:+.2f}, {row['n']} matches"
    if not row["Clear"]:
        return (f"**{row['Metric']}**: no clear link with {outcome} ({facts}). "
                "Any pattern here could easily be luck.")
    word = strength_word(row["r"])
    if row["Metric"] == "Home match":
        direction = "better" if row["r"] > 0 else "worse"
        return f"**{row['Metric']}**: {word} link ({facts}). Home matches tend to have a {direction} {outcome}."
    direction = "better" if row["r"] > 0 else "worse"
    more = "higher" if row["Metric"] in ("Possession", "Shot accuracy") else "more"
    return (f"**{row['Metric']}**: {word} link ({facts}). Matches with {more} {metric} tend to "
            f"have a {direction} {outcome}.")


# ---- Key findings: the whole tab in a few plain sentences -------------------

def key_findings(info, last_same_points, trend_list, window, found, outcome_label, place_text):
    """A short list of plain-English sentences that sum up the other sections.

    info              the projection dictionary from project_season
    last_same_points  last season's points after the same number of games
    trend_list        the rows from trend_rows
    found             the table from correlations (can be empty)
    place_text        where the projected total would have finished, as text
    Every sentence says what the numbers show and nothing more."""
    sentences = []

    # 1. Points against last season at the same point
    played = info["played"]
    gap = int(info["current"]) - last_same_points
    if gap > 0:
        compare = f"{gap} more than"
    elif gap < 0:
        compare = f"{-gap} fewer than"
    else:
        compare = "the same as"
    sentences.append(f"**Points:** {int(info['current'])} after {played} games, {compare} "
                     f"last season at the same point ({last_same_points}).")

    # 2. The projection and its range
    sentences.append(f"**Where it is heading:** about {round(info['expected'])} points by the end "
                     f"(likely range {round(info['low'])} to {round(info['high'])}). {place_text}")

    # 3. Trends: only the ones the test says are real
    better = [r["Metric"].lower() for r in trend_list if r["Verdict"] == "Improving"]
    worse = [r["Metric"].lower() for r in trend_list if r["Verdict"] == "Slipping"]
    if all(r["Verdict"] == "Too early" for r in trend_list):
        sentences.append("**Form:** too few matches yet to say whether anything is changing.")
    elif better or worse:
        parts = []
        if better:
            parts.append("improving: " + ", ".join(better))
        if worse:
            parts.append("slipping: " + ", ".join(worse))
        sentences.append(f"**Form:** over the last {window} matches, " + "; ".join(parts) + ".")
    else:
        sentences.append(f"**Form:** nothing has moved clearly in the last {window} matches. "
                         "The recent games look like the earlier ones.")

    # 4. The strongest pattern that is bigger than chance
    clear = found[found["Clear"]] if len(found) else found
    if len(clear):
        top = clear.iloc[0]
        sentences.append(f"**What goes with winning:** {top['Metric'].lower()} has the strongest clear link "
                         f"with {outcome_label.lower()} (r = {top['r']:+.2f}, {int(top['n'])} matches). "
                         "It moves together with results. That does not prove it causes them.")
    elif len(found):
        sentences.append(f"**What goes with winning:** no number has a clear link with {outcome_label.lower()} "
                         "yet. The patterns seen could be luck.")
    return sentences