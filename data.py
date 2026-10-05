import io
import os
import time
from datetime import datetime

import pandas as pd
import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

CURRENT_SEASON = "2026-2027"
LAST_SEASON = "2025-2026"

BASE = "https://fbref.com/en/squads/53a2f082/{season}/matchlogs/all_comps"
SCHEDULE_PATH = "/schedule/Real-Madrid-Scores-and-Fixtures-All-Competitions"
SHOOTING_PATH = "/shooting/Real-Madrid-Match-Logs-All-Competitions"

# Every La Liga match of a season (all 20 teams), used to build the league table.
LEAGUE_URL = "https://fbref.com/en/comps/12/{season}/schedule/{season}-La-Liga-Scores-and-Fixtures"

# The major version of the Chrome installed on this Mac. If Chrome updates and
# you see "This version of ChromeDriver only supports Chrome version X",
# change this number to match your Chrome (chrome://version shows it).
CHROME_MAJOR_VERSION = 150

# Downloaded tables are saved here as CSV files, next to this file.
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_cache")

# Be polite to FBref: never open two pages less than this many seconds apart.
MIN_SECONDS_BETWEEN_PAGES = 6
_last_fetch_time = 0.0


def fetch_html(url):
    """Opens a real Chrome browser, goes to url, waits until the page actually
    contains a table, and returns the page's HTML. If no table ever shows up
    (for example Cloudflare's check never clears), raises an error that says
    what the page was, instead of failing later with a confusing message."""
    global _last_fetch_time

    wait = MIN_SECONDS_BETWEEN_PAGES - (time.time() - _last_fetch_time)
    if wait > 0:
        time.sleep(wait)

    driver = uc.Chrome(options=uc.ChromeOptions(), version_main=CHROME_MAJOR_VERSION)
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 60).until(
                lambda d: len(d.find_elements(By.TAG_NAME, "table")) > 0
            )
        except TimeoutException:
            raise RuntimeError(
                "No tables appeared on the page within 60 seconds. "
                f"The page title was {driver.title!r}. "
                "'Just a moment...' means Cloudflare's check did not clear; "
                "a title mentioning 'Too Many Requests' or an error means FBref "
                "is refusing us right now (wait a while before trying again)."
            )
        time.sleep(2)  # let the rest of the page finish loading
        return driver.page_source
    finally:
        driver.quit()
        _last_fetch_time = time.time()


def find_table(tables, required_columns):
    """Return the first table that has all the column names we need, instead
    of guessing its position on the page (positions change between pages)."""
    for table in tables:
        # Two-level headers come as pairs like ('Standard', 'Sh'); the real
        # name is the last part of the pair.
        names = {col[-1] if isinstance(col, tuple) else str(col) for col in table.columns}
        if set(required_columns).issubset(names):
            return table
    raise ValueError(f"No table found with columns: {required_columns}")


def _scrape_schedule(season):
    html = fetch_html(BASE.format(season=season) + SCHEDULE_PATH)
    tables = pd.read_html(io.StringIO(html))
    return find_table(tables, ["Date", "Result", "GF", "GA"])


def _scrape_shooting(season):
    html = fetch_html(BASE.format(season=season) + SHOOTING_PATH)
    tables = pd.read_html(io.StringIO(html))
    shooting = find_table(tables, ["Date", "Sh", "SoT"])

    # Keep only the second level of the two-row header (e.g. "Sh", "SoT")
    shooting.columns = [col[-1] if isinstance(col, tuple) else col for col in shooting.columns]
    return shooting


def _scrape_league(season):
    html = fetch_html(LEAGUE_URL.format(season=season))
    tables = pd.read_html(io.StringIO(html))
    return find_table(tables, ["Wk", "Home", "Score", "Away"])


def _cache_path(kind, season):
    return os.path.join(CACHE_DIR, f"{kind}_{season}.csv")


def _load_or_scrape(kind, season, refresh, scrape):
    """Read the saved CSV if there is one. Otherwise (or if refresh=True)
    scrape the page, save it as a CSV, and return it. The CSV files are the
    cache: the dashboard no longer re-downloads anything on every restart."""
    path = _cache_path(kind, season)
    if os.path.exists(path) and not refresh:
        return pd.read_csv(path)

    table = scrape(season)
    os.makedirs(CACHE_DIR, exist_ok=True)
    table.to_csv(path, index=False)
    return table


def get_match_log(season=CURRENT_SEASON, refresh=False):
    return _load_or_scrape("schedule", season, refresh, _scrape_schedule)


def get_shooting_log(season=CURRENT_SEASON, refresh=False):
    return _load_or_scrape("shooting", season, refresh, _scrape_shooting)


def get_league_fixtures(season=CURRENT_SEASON, refresh=False):
    return _load_or_scrape("league", season, refresh, _scrape_league)


def last_downloaded(season):
    """When this season's saved data was last downloaded, as readable text."""
    path = _cache_path("schedule", season)
    if not os.path.exists(path):
        return None
    return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")


if __name__ == "__main__":
    # `python3 data.py` updates the saved data files. This season is
    # downloaded fresh every time; last season is final, so it is only
    # downloaded if it is missing.
    print("Downloading this season's data...")
    schedule = get_match_log(CURRENT_SEASON, refresh=True)
    shooting = get_shooting_log(CURRENT_SEASON, refresh=True)
    league = get_league_fixtures(CURRENT_SEASON, refresh=True)
    print(f"  schedule: {len(schedule)} rows | shooting: {len(shooting)} rows | league: {len(league)} rows")

    print("Checking last season's data (downloads only if missing)...")
    schedule = get_match_log(LAST_SEASON)
    shooting = get_shooting_log(LAST_SEASON)
    league = get_league_fixtures(LAST_SEASON)
    print(f"  schedule: {len(schedule)} rows | shooting: {len(shooting)} rows | league: {len(league)} rows")

    print(f"\nDone. Files are in: {CACHE_DIR}")
    print("Now run: streamlit run app.py")