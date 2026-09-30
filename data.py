import io
import time
import pandas as pd
import undetected_chromedriver as uc

SCHEDULE_URL = "https://fbref.com/en/squads/53a2f082/2026-2027/matchlogs/all_comps/schedule/Real-Madrid-Scores-and-Fixtures-All-Competitions"
SHOOTING_URL = "https://fbref.com/en/squads/53a2f082/2026-2027/matchlogs/all_comps/shooting/Real-Madrid-Match-Logs-All-Competitions"

def fetch_html(url):
    """Opens a real Chrome browser, navigates to url, waits for Cloudflare's
    check to clear, and returns the fully-loaded page's HTML. Shared by every
    scraping function below so we only write this logic once."""
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=150)
    driver.get(url)
    time.sleep(8)
    html = driver.page_source
    driver.quit()
    return html

def get_match_log():
    html = fetch_html(SCHEDULE_URL)
    tables = pd.read_html(io.StringIO(html))
    return tables[9]

def get_shooting_log():
    html = fetch_html(SHOOTING_URL)
    tables = pd.read_html(io.StringIO(html))
    shooting = tables[9]  # "For Real Madrid" — one row per match actually played

    # This table has a two-row header (e.g. "Standard" over "Sh"). We only
    # need the second level — it's already unique and readable on its own.
    shooting.columns = [col[1] for col in shooting.columns]
    return shooting

if __name__ == "__main__":
    df = get_shooting_log()
    print(df.head())