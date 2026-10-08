# Real Madrid Analytics Dashboard

A Streamlit dashboard that compares Real Madrid's current La Liga season with the same point last season, and looks at how the team scores, defends and fares against each opponent. The data comes from [FBref](https://fbref.com).

## What it shows

- **Season Dashboard:** record, points, goals for and against, and league position, each compared with the same point last season. It also has a cumulative points chart, a league position chart (1st place at the top) and the full league tables.
- **Match Stats:** shots, shots on target, shot accuracy and conversion compared with last season, a trend chart and a match-by-match breakdown.
- **Efficiency Stats:** points, goals scored and conceded per game, shots per goal, win percentage, clean sheets and penalties, all compared with last season. It also has a rolling-average form chart (you pick the metric and the number of matches) and a home vs away table.
- **Opponent Analysis:** pick any La Liga team (it starts on Real Madrid's next match) to see both teams' league positions and recent results, the head-to-head record over last season and this season, the opponent's last five matches, and Real Madrid's results against every team.

A one-line summary of Real Madrid's league position sits above the tabs.

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

The very first run downloads six pages from FBref (a few minutes; Chrome windows open and close by themselves, so leave them alone) and saves them in `data_cache/`. After that the dashboard opens instantly. Use Chrome to view it: in testing it rendered blank in Safari.

## Updating the data

- Click **Refresh this season's data** in the sidebar (opens Chrome three times, about a minute), or run `python3 data.py` in the terminal.
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
| `check_league_data.py` | Checks the league-wide data against Real Madrid's own page (`python3 check_league_data.py`) |
| `inspect_page.py` | Prints the tables on any FBref page, to explore a new page before writing code for it |
| `data_cache/` | The saved downloads (not tracked by Git) |

## How league positions are worked out

- The table after matchweek N counts every match played in matchweeks 1 to N.
- Teams are ordered by points, then goal difference, then goals scored. This is how LaLiga's own table orders teams during the season.
- Head-to-head decides ties only in the final standings, so it is used only for a final table (the whole season played).
- A postponed match shows up as a game in hand for the two teams involved.

## Troubleshooting

- **`ModuleNotFoundError` for a package you installed:** the virtual environment isn't active. The terminal prompt should start with `(venv)`. If it doesn't, run `source venv/bin/activate`.
- **"This version of ChromeDriver only supports Chrome version X":** Chrome updated itself. Change `CHROME_MAJOR_VERSION` at the top of `data.py` to your Chrome's major version (`chrome://version` shows it).
- **"No tables appeared on the page... 'Just a moment...'":** FBref's bot check didn't clear, or it is refusing requests right now. Wait a while and try again.

## Data

All data is from FBref (Sports Reference). Read their [data use terms](https://www.sports-reference.com/data_use.html) before publishing anything built on it.