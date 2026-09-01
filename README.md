# FPL 3-Team Tracker

Tracks and compares three Fantasy Premier League teams, each managed with the
help of a different AI assistant (Claude, ChatGPT, Copilot), over a full
season. The live dashboard and blog are static HTML pages published via
GitHub Pages — there's no backend, so "refreshing" the site each week means
re-running a couple of scripts and pushing the result.

## Layout

```
index.html                       Blog homepage (links to posts/)
posts/                           One HTML page per weekly write-up
fpl_tracker_dashboard.html       The live tracker (standings, squads, charts)
new_post.py                      Scaffolds a new posts/*.html from the template

script/
  build_dashboard_data.py        Pulls the Google Sheet -> DATA block in the dashboard
  build_gw_pitch_data.py         Pulls picks CSVs -> GW_PICKS block in the dashboard
  fpl_gameweek_scores.py         Whole-league player scores per gameweek (reference data)
  entries/
    fpl_entry_team.py            Fetches each team's actual picks from the FPL API
    entries/<entry_id>/GW*.csv   Output of fpl_entry_team.py, one file per team per GW
```

## Where the data comes from

There are two independent sources feeding the dashboard, pulled in by two
different build scripts:

1. **The Google Sheet** ("FPL 3-Team Tracker") — hand-maintained every week:
   Weekly Log, Transfer Log, and a Squad tab per team (including who's
   captain/vice). `build_dashboard_data.py` downloads it and regenerates the
   `DATA` block embedded in `fpl_tracker_dashboard.html` (standings, the
   Weekly log/Squad/Moves tabs, the cumulative points chart).
2. **The FPL API** — real, automated picks data per manager, fetched by
   `fpl_entry_team.py` into `script/entries/entries/<entry_id>/GW*.csv`.
   `build_gw_pitch_data.py` bundles those CSVs into the `GW_PICKS` block,
   which drives the "Gameweeks" pitch view (real captain/vice flags, actual
   points scored per player, no manual entry needed).

The three entry IDs map to teams like this (set in
`fpl_entry_team.py` calls and `build_gw_pitch_data.py`'s `ENTRY_TEAM` dict):

| Entry ID | Team    |
|----------|---------|
| 3569788  | Claude  |
| 5416382  | ChatGPT |
| 5421890  | Copilot |

## Weekly process

Do this after each gameweek's FPL deadline has passed and scores have locked:

1. **Update the Google Sheet.**
   - Add this week's row per team in **Weekly Log** (GW points, bench points,
     transfers, chip used, captain/vice, overall rank, team value, bank).
   - Update each **Squad - \<Team\>** tab if any transfers were made, and make
     sure the **Captain**/**Vice-Captain** column reflects who's currently
     armbanded (not just who was captain last week).
   - Add any moves to **Transfer Log**.
   - The sheet must stay shared as "Anyone with the link can view" — both
     build scripts read it over an unauthenticated export URL.

2. **Fetch real picks for the new gameweek:**
   ```
   python script/entries/fpl_entry_team.py --entry 3569788,5416382,5421890 --gw <N>
   ```
   (or `--all` to backfill every gameweek played so far). This writes
   `GW<N>.csv` into each entry's folder under `script/entries/entries/`.

3. **Regenerate the dashboard's embedded data:**
   ```
   python script/build_dashboard_data.py
   python script/build_gw_pitch_data.py
   ```
   The first rewrites `DATA` (standings/log/squad/moves/chart) from the
   Google Sheet; the second rewrites `GW_PICKS` (the Gameweeks pitch view)
   from the CSVs fetched in step 2. Both edit
   `fpl_tracker_dashboard.html` in place, between marker comments
   (`/* DATA_START */`, `/* GW_PICKS_START */`, etc.) — safe to re-run any
   time.

4. **(Optional) Write the week's blog post:**
   ```
   python new_post.py
   ```
   Fill in the generated `posts/*.html`, then add a matching card to
   `index.html`'s post list.

5. **Commit and push:**
   ```
   git add -A
   git commit -m "Gameweek <N> update"
   git push
   ```
   GitHub Pages serves straight from the pushed HTML — no deploy step.

## Requirements

- Python 3, with `openpyxl` installed (`pip install openpyxl`) for
  `build_dashboard_data.py`.
- No API key needed anywhere — both the FPL API and the Google Sheet export
  are used unauthenticated (the sheet must stay link-shareable).
