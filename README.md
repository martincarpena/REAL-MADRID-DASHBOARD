# Real Madrid Analytics Dashboard

A Streamlit dashboard that compares Real Madrid's current La Liga season with the same point last season, and looks at how the team scores, defends and fares against each opponent, which players are doing it, and how the team uses the ball and its formations. The data comes from [FBref](https://fbref.com).

## What it shows

- **Season Dashboard:** record, points, goals for and against, and league position, each compared with the same point last season. It also has a cumulative points chart, a league position chart (1st place at the top) and the full league tables.
- **Match Stats:** shots, shots on target, shot accuracy and conversion compared with last season, a trend chart and a match-by-match breakdown.
- **Efficiency Stats:** points, goals scored and conceded per game, shots per goal, win percentage, clean sheets and penalties, all compared with last season. It also has a rolling-average form chart (you pick the metric and the number of matches) and a home vs away table.
- **Opponent Analysis:** pick any La Liga team (it starts on Real Madrid's next match) to see both teams' league positions and recent results, the head-to-head record over last season and this season, the opponent's last five matches, and Real Madrid's results against every team.
- **Player Stats:** top scorer, most assists, most shots and most minutes (each next to last season's leader), a leaders bar chart for any statistic, and a full squad table with a minutes filter and last season's totals. You can switch the whole tab between this season and last season.
- **Tactics:** possession (average, highest, lowest) compared with last season, a rolling possession chart, the record in matches with little, medium and a lot of possession, and the record with each of Real Madrid's formations and against each opponent formation.
- **Champions League:** only Real Madrid's Champions League games: record, points, goals for and against and average possession compared with last season at the same point, charts of points and goals match by match, this season's games (including the ones still to play) and last season's whole run. It also shows the full 36-team league-phase table with Real Madrid highlighted and its place by matchweek against last season. Real Madrid's own games also count in the other tabs.
- **Analysis:** a key-findings summary in plain English, a season projection (a simple pace estimate with a likely range, and where that total would have finished last season), trend and form checks for points, goals, shots and possession, and a look at which numbers go with winning (correlations, with a warning that correlation is not causation). Every part says how few matches it is based on.

The charts are interactive: point at a chart and a line follows the mouse with the numbers for both seasons, bars light up in gold, and clicking a season in a chart's legend shows only that season. The look is dark charcoal with gold accents. You move between the pages with a menu on the left, and each page fits a lot on one screen, with charts and tables laid out side by side in cards. A footer shows where the data comes from and when this season's data was last downloaded.

The left sidebar also has a club panel that is always in view: league position, points, record, goal difference, the last five results as coloured circles (green win, grey draw, red loss) and the next opponent.

## Setup (first time)

You need Python 3 and Google Chrome. FBref sits behind a bot check, so the data is downloaded with a real Chrome window. No API keys are needed.

```
git clone https://github.com/martincarpena/REAL-MADRID-DASHBOARD.git
cd REAL-MADRID-DASHBOARD
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the dashboard

```
source venv/bin/activate
streamlit run app.py
```

The very first run downloads ten pages from FBref (several minutes; Chrome windows open and close by themselves, so leave them alone) and saves them in `data_cache/`. After that the dashboard opens instantly. Use Chrome to view it: in testing it rendered blank in Safari.

## Updating the data

- Click **Refresh this season's data** in the sidebar (opens Chrome five times, about three minutes), or run `python3 data.py` in the terminal.
- Last season is final, so it is downloaded only once.
- Be gentle with FBref. It blocks scripts that download too quickly, so `data.py` waits at least 6 seconds between pages. If you get blocked, wait a while before trying again.

## Project layout

| File | What it does |
|---|---|
| `app.py` | The dashboard (Streamlit) |
| `data.py` | Downloads the FBref tables with Chrome and saves them in `data_cache/` |
| `standings.py` | Cleans the league-wide fixtures and works out league tables and positions |
| `efficiency.py` | The maths behind the Efficiency Stats tab: per-game numbers, rolling averages, home vs away |
| `opponents.py` | The maths behind the Opponent Analysis tab: team results, head to head, recent form, next opponent |
| `players.py` | The maths behind the Player Stats tab: cleaning the squad table, leaderboards, this season vs last season |
| `tactics.py` | The maths behind the Tactics tab: possession summaries, possession bands, records by formation |
| `analysis.py` | The maths behind the Analysis tab: the season projection and its range, the trend checks, the correlations and the plain-English key findings |
| `champions.py` | The maths behind the Champions League tab: picks out Real Madrid's Champions League games and works out the record, points, goals and possession, and builds the 36-team league-phase table and Real Madrid's place in it |
| `charts.py` | The chart designs (Altair): the season-against-season line charts, the leaders bar chart and the possession bars, with their hover and click effects |
| `tables.py` | How the tables look: clean numbers, dashes for empty cells, coloured W/D/L results and the highlighted Real Madrid row in the league tables |
| `styles.py` | The look of the dashboard: the CSS (colours, fonts, cards, number tiles, the sidebar menu, footer) and the HTML for the sidebar crest, the club panel, the page titles and the footer |
| `.streamlit/config.toml` | Streamlit's theme: base colours and font |
| `check_league_data.py` | Checks the league-wide data against Real Madrid's own page (`python3 check_league_data.py`) |
| `inspect_page.py` | Prints the tables on any FBref page, to explore a new page before writing code for it |
| `data_cache/` | The saved downloads (not tracked by Git) |

## Look and feel

- The colours and fonts live in two places: `.streamlit/config.toml` (the base theme) and `styles.py` (cards, sidebar, fonts). Change a colour once at the top of the CSS in `styles.py` and it changes everywhere. The chart colours are set at the top of `charts.py`.
- Each chart or main table sits in a "card": a dark panel with a thin border and a small title in capitals. `app.py` makes them with the `card()` helper, and the CSS in `styles.py` finds them by name (`card_1`, `card_2`...). Cards in the same row stretch to the same height.
- Each page starts with its title in a serif font, a one-line description and a thin line with a short gold rule.
- The sidebar shows the club crest if a file called `logo.svg` sits next to `app.py`. It is not tracked by Git (it is in `.gitignore`), so a fresh clone shows the sidebar without it. Add your own `logo.svg` to see it.
- Streamlit reads `.streamlit/config.toml` only at startup, so restart `streamlit run app.py` after changing the theme. The CSS in `styles.py` updates when you refresh the page.

## How league positions are worked out

- The table after matchweek N counts every match played in matchweeks 1 to N.
- Teams are ordered by points, then goal difference, then goals scored. This is how LaLiga's own table orders teams during the season.
- Head-to-head decides ties only in the final standings, so it is used only for a final table (the whole season played).
- A postponed match shows up as a game in hand for the two teams involved.

## About the player numbers

- Player numbers cover La Liga only, so they can differ from the all-competitions numbers on the Efficiency Stats tab.
- Last season's columns are full-season totals, not totals at the same point of the season.
- Per-90 numbers are unreliable for players with few minutes, which is why the squad table has a minutes filter.
- A player's goals in the shooting table can be lower than the real total, because own goals are counted differently.

## Troubleshooting

- **`ModuleNotFoundError` for a package you installed:** the virtual environment isn't active. The terminal prompt should start with `(venv)`. If it doesn't, run `source venv/bin/activate`.
- **"This version of ChromeDriver only supports Chrome version X":** Chrome updated itself. Change `CHROME_MAJOR_VERSION` at the top of `data.py` to your Chrome's major version (`chrome://version` shows it).
- **"No tables appeared on the page... 'Just a moment...'":** FBref's bot check didn't clear, or it is refusing requests right now. Wait a while and try again.
- **A Chrome window shows "Verify you are human":** click the checkbox in that window. The download continues by itself once the check clears.

## Data

All data is from FBref (Sports Reference). Read their [data use terms](https://www.sports-reference.com/data_use.html) before publishing anything built on it.