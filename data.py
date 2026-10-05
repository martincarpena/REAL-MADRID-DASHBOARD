import io
import time
import pandas as pd
import undetected_chromedriver as uc

CURRENT_SEASON = "2026-2027"
LAST_SEASON = "2025-2026"

BASE = "https://fbref.com/en/squads/53a2f082/{season}/matchlogs/all_comps"
SCHEDULE_PATH = "/schedule/Real-Madrid-Scores-and-Fixtures-All-Competitions"
SHOOTING_PATH = "/shooting/Real-Madrid-Match-Logs-All-Competitions"

def fetch_html(url):
    """Opens a real Chrome browser, navigates to url, waits for Cloudflare's
    check to clear, and returns the fully-loaded page's HTML."""
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=150)
    driver.get(url)
    time.sleep(8)
    html = driver.page_source
    driver.quit()
    return html

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

def get_match_log(season=CURRENT_SEASON):
    html = fetch_html(BASE.format(season=season) + SCHEDULE_PATH)
    tables = pd.read_html(io.StringIO(html))
    return find_table(tables, ["Date", "Result", "GF", "GA"])

def get_shooting_log(season=CURRENT_SEASON):
    html = fetch_html(BASE.format(season=season) + SHOOTING_PATH)
    tables = pd.read_html(io.StringIO(html))
    shooting = find_table(tables, ["Date", "Sh", "SoT"])

    # Keep only the second level of the two-row header (e.g. "Sh", "SoT")
    shooting.columns = [col[-1] if isinstance(col, tuple) else col for col in shooting.columns]
    return shooting

if __name__ == "__main__":
    last = get_match_log(LAST_SEASON)
    print(last.columns.tolist())
    print(last.head(10))
    print(f"\nTotal rows: {len(last)}")