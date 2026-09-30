import io
import time
import pandas as pd
import undetected_chromedriver as uc

URL = "https://fbref.com/en/squads/53a2f082/2026-2027/matchlogs/all_comps/schedule/Real-Madrid-Scores-and-Fixtures-All-Competitions"

def get_match_log():
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options, version_main=150)
    driver.get(URL)

    time.sleep(8)

    html = driver.page_source
    driver.quit()

    tables = pd.read_html(io.StringIO(html))
    match_log = tables[9]  # confirmed: this is the real Scores & Fixtures table
    return match_log

if __name__ == "__main__":
    df = get_match_log()
    print(df.head(10))
    print(f"\nTotal matches found: {len(df)}")