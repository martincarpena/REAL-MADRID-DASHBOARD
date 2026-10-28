"""Downloads and saves the data for the Player Reports page.

Like data.py, every download is saved as a CSV file in data_cache/, so a
player's page is only ever downloaded once. Nothing here uses Streamlit.

Run `python3 player_data.py` to download the squad list and then the match
log of every player in the top ROSTER_SIZE by minutes."""
import io
import os
import re

import pandas as pd

from data import CACHE_DIR, CURRENT_SEASON, SQUAD_URL, fetch_html

# How many players get a report (the ones with the most minutes this season).
ROSTER_SIZE = 20

# A player's match log for one season, all competitions in one table.
MATCH_LOG_URL = "https://fbref.com/en/players/{player_id}/matchlogs/{season}/summary/{slug}-Match-Logs"


def _read_one_table(table_html, **options):
    """Reads one <table>. A few FBref tables have a broken colspan/rowspan that
    makes pandas fail, so on an error we try again with those attributes removed."""
    try:
        return pd.read_html(io.StringIO(table_html), **options)[0]
    except ValueError:
        cleaned = re.sub(r"\s(?:colspan|rowspan)=[^\s>]*", "", table_html)
        return pd.read_html(io.StringIO(cleaned), **options)[0]


def _flatten(columns):
    """Two-level headers come as pairs like ('Playing Time', 'Min'); keep the last part."""
    return [col[-1] if isinstance(col, tuple) else str(col) for col in columns]


def _find_table(html, required_columns, **options):
    """Returns the first table on the page that has all the required column
    names. Tables that cannot be read are skipped."""
    for piece in re.findall(r"<table.*?</table>", html, flags=re.DOTALL):
        try:
            table = _read_one_table(piece, **options)
        except Exception:
            continue
        table = table.copy()
        table.columns = _flatten(table.columns)
        if set(required_columns).issubset(table.columns):
            return table
    raise ValueError(f"No table found with columns: {required_columns}")


def _cache_path(name):
    return os.path.join(CACHE_DIR, f"{name}.csv")


def _scrape_roster(season):
    """One row per player on the squad page: name, link to their page, and the
    standard numbers. extract_links='body' makes every cell come back as a
    (text, link) pair, so the link of each player is kept."""
    html = fetch_html(SQUAD_URL.format(season=season))
    table = _find_table(html, ["Player", "Starts", "Min"], extract_links="body")

    # The 'Squad Total' rows at the bottom are plain text (not pairs) and have no link.
    is_player = table["Player"].apply(lambda cell: isinstance(cell, tuple) and cell[1] is not None)
    table = table[is_player]

    roster = pd.DataFrame({
        "Player": table["Player"].apply(lambda cell: cell[0]),
        "Link": table["Player"].apply(lambda cell: cell[1]),
    })
    for name in ["Pos", "Age", "MP", "Starts", "Min"]:
        if name in table.columns:
            roster[name] = table[name].apply(lambda cell: cell[0])

    for name in ["MP", "Starts", "Min"]:
        roster[name] = pd.to_numeric(roster[name].astype(str).str.replace(",", ""), errors="coerce")
    return roster


def get_roster(season=CURRENT_SEASON, refresh=False):
    """Every player on the squad page with their link, most minutes first."""
    path = _cache_path(f"roster_{season}")
    if os.path.exists(path) and not refresh:
        return pd.read_csv(path)
    roster = _scrape_roster(season).sort_values("Min", ascending=False)
    os.makedirs(CACHE_DIR, exist_ok=True)
    roster.to_csv(path, index=False)
    return roster


def top_players(roster, count=ROSTER_SIZE):
    """The players with the most minutes."""
    return roster.sort_values("Min", ascending=False).head(count).reset_index(drop=True)


def _player_id_and_slug(link):
    """'/en/players/42fd9c7f/Kylian-Mbappe' -> ('42fd9c7f', 'Kylian-Mbappe')."""
    parts = link.strip("/").split("/")
    return parts[2], parts[3]


def _scrape_match_log(link, season):
    player_id, slug = _player_id_and_slug(link)
    url = MATCH_LOG_URL.format(player_id=player_id, season=season, slug=slug)
    html = fetch_html(url)
    log = _find_table(html, ["Date", "Min", "Start"])
    # The last row is the season total and has no date; it is not a match.
    return log[log["Date"].notna()].reset_index(drop=True)


def get_player_matches(link, season=CURRENT_SEASON, refresh=False):
    """One row per match this player was in the squad for, all competitions."""
    player_id, _ = _player_id_and_slug(link)
    path = _cache_path(f"playerlog_{player_id}_{season}")
    if os.path.exists(path) and not refresh:
        return pd.read_csv(path)
    log = _scrape_match_log(link, season)
    os.makedirs(CACHE_DIR, exist_ok=True)
    log.to_csv(path, index=False)
    return log


def is_saved(link, season=CURRENT_SEASON):
    player_id, _ = _player_id_and_slug(link)
    return os.path.exists(_cache_path(f"playerlog_{player_id}_{season}"))


if __name__ == "__main__":
    squad = top_players(get_roster())
    print(f"Top {len(squad)} players by minutes:\n")
    for position, row in squad.iterrows():
        label = f"{position + 1:>2}. {row['Player']} ({int(row['Min'])} min)"
        if is_saved(row["Link"]):
            print(f"{label} - already saved")
            continue
        try:
            log = get_player_matches(row["Link"])
        except Exception as error:
            print(f"{label} - FAILED: {error}")
            print("Stopping. The players saved so far are kept; run this again later.")
            break
        print(f"{label} - saved {len(log)} matches")
    else:
        print("\nAll done.")