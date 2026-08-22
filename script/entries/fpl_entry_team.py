"""
Fantasy Premier League — entry (manager) team lookup
---------------------------------------------------------
Uses the public, unauthenticated FPL API:
  - https://fantasy.premierleague.com/api/bootstrap-static/
  - https://fantasy.premierleague.com/api/entry/{entry_id}/
  - https://fantasy.premierleague.com/api/entry/{entry_id}/event/{gw}/picks/
  - https://fantasy.premierleague.com/api/entry/{entry_id}/history/

Given one or more entry IDs (the number in a manager's FPL URL, e.g.
fantasy.premierleague.com/entry/1234567/event/5), fetches each
manager's squad and writes one CSV per gameweek into a per-entry
subfolder:

    entries/
      1234567/
        GW1.csv
        GW2.csv
      7654321/
        GW1.csv
        GW2.csv

Usage:
    python fpl_entry_team.py --entry 1234567                       # current gameweek only
    python fpl_entry_team.py --entry 1234567,7654321,1112223       # multiple entries
    python fpl_entry_team.py --entry 1234567 --gw 5                # one specific gameweek
    python fpl_entry_team.py --entry 1234567 --gw 1-5              # a range of gameweeks
    python fpl_entry_team.py --entry 1234567 --all                 # every gameweek played so far
    python fpl_entry_team.py --entry 1234567 --entries-dir out     # use a different base folder
    python fpl_entry_team.py --entry 1234567 --history             # season-by-season summary instead
"""

import argparse
import csv
import os
import sys
import urllib.request
import json

BASE = "https://fantasy.premierleague.com/api"


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_current_gameweek(events):
    for e in events:
        if e.get("is_current"):
            return e["id"]
    for e in events:
        if e.get("is_next"):
            return e["id"]
    finished = [e["id"] for e in events if e.get("finished")]
    return max(finished) if finished else 1


def get_played_gameweeks(events):
    """All gameweeks that have kicked off (finished, or currently in progress)."""
    return sorted(
        e["id"] for e in events
        if e.get("finished") or e.get("is_current")
    )


def parse_gw_arg(gw_arg, events):
    """Turn --gw into a sorted list of gameweek numbers.
    Accepts a single number ("5"), a range ("1-5"), or None (current gw only)."""
    if gw_arg is None:
        return [get_current_gameweek(events)]
    gw_arg = gw_arg.strip()
    if "-" in gw_arg:
        start, end = gw_arg.split("-", 1)
        return list(range(int(start), int(end) + 1))
    return [int(gw_arg)]


def parse_entry_arg(entry_arg):
    """Turn --entry into a list of entry IDs. Accepts comma-separated values."""
    return [int(e.strip()) for e in entry_arg.split(",") if e.strip()]


def fetch_entry_info(entry_id):
    return fetch_json(f"{BASE}/entry/{entry_id}/")


def fetch_entry_history(entry_id):
    return fetch_json(f"{BASE}/entry/{entry_id}/history/")


def fetch_entry_picks(entry_id, gw):
    return fetch_json(f"{BASE}/entry/{entry_id}/event/{gw}/picks/")


def build_squad_rows(picks, players, teams, positions):
    rows = []
    for pick in picks["picks"]:
        p = players.get(pick["element"])
        if not p:
            continue
        rows.append({
            "web_name": p["web_name"],
            "player": f'{p["first_name"]} {p["second_name"]}',
            "team": teams.get(p["team"], "?"),
            "position": positions.get(p["element_type"], "?"),
            "gw_points": p.get("event_points", 0),
            "total_points": p.get("total_points", 0),
            "now_cost_m": p["now_cost"] / 10,
            "squad_position": pick["position"],
            "is_captain": pick["is_captain"],
            "is_vice_captain": pick["is_vice_captain"],
            "multiplier": pick["multiplier"],
        })
    rows.sort(key=lambda r: r["squad_position"])
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_squad_summary(entry_info, gw, rows, picks):
    name = f'{entry_info.get("player_first_name", "")} {entry_info.get("player_last_name", "")}'.strip()
    team_name = entry_info.get("name", "?")
    print(f"\n{team_name} ({name}) — Gameweek {gw}")
    print(f"GW points: {picks['entry_history'].get('points')}  |  "
          f"Overall rank: {picks['entry_history'].get('overall_rank')}  |  "
          f"Total points: {picks['entry_history'].get('total_points')}")
    print("\nSquad:")
    for r in rows:
        tag = " (C)" if r["is_captain"] else " (VC)" if r["is_vice_captain"] else ""
        bench = "" if r["multiplier"] > 0 else "  [bench]"
        print(f'  {r["squad_position"]:>2}. {r["web_name"]:<15}{tag:<5} '
              f'{r["team"]:<14} {r["position"]:<3} '
              f'{r["gw_points"]:>3} pts{bench}')


def print_history_summary(entry_info, history):
    name = f'{entry_info.get("player_first_name", "")} {entry_info.get("player_last_name", "")}'.strip()
    team_name = entry_info.get("name", "?")
    print(f"\n{team_name} ({name}) — season history")
    print(f"{'GW':>3}  {'Points':>6}  {'Total':>6}  {'Overall Rank':>13}")
    for gw in history["current"]:
        print(f'{gw["event"]:>3}  {gw["points"]:>6}  {gw["total_points"]:>6}  {gw["overall_rank"]:>13}')


def main():
    parser = argparse.ArgumentParser(description="Look up one or more FPL managers' teams by entry ID.")
    parser.add_argument("--entry", type=str, required=True,
                         help="Entry (manager/team) ID, or comma-separated list, e.g. 1234567,7654321")
    parser.add_argument("--gw", type=str, default=None,
                         help="Gameweek number ('5') or range ('1-5'). Default: current gameweek only.")
    parser.add_argument("--all", action="store_true",
                         help="Fetch every gameweek played so far (finished or in progress).")
    parser.add_argument("--entries-dir", type=str, default="entries",
                         help="Base folder to write entry subfolders into (default: entries)")
    parser.add_argument("--history", action="store_true",
                         help="Print season-by-season gameweek history instead of fetching squads")
    args = parser.parse_args()

    print("Fetching player/team data...")
    bootstrap = fetch_json(f"{BASE}/bootstrap-static/")
    players = {p["id"]: p for p in bootstrap["elements"]}
    teams = {t["id"]: t["name"] for t in bootstrap["teams"]}
    positions = {pt["id"]: pt["singular_name_short"] for pt in bootstrap["element_types"]}
    events = bootstrap["events"]

    entry_ids = parse_entry_arg(args.entry)

    if args.all:
        gameweeks = get_played_gameweeks(events)
    else:
        gameweeks = parse_gw_arg(args.gw, events)

    for entry_id in entry_ids:
        print(f"\n=== Entry {entry_id} ===")
        entry_info = fetch_entry_info(entry_id)

        if args.history:
            history = fetch_entry_history(entry_id)
            print_history_summary(entry_info, history)
            continue

        entry_dir = os.path.join(args.entries_dir, str(entry_id))
        os.makedirs(entry_dir, exist_ok=True)

        for gw in gameweeks:
            print(f"Fetching picks for Gameweek {gw}...")
            try:
                picks = fetch_entry_picks(entry_id, gw)
            except Exception as e:
                print(f"  Could not fetch GW{gw} for entry {entry_id}: {e}")
                continue

            rows = build_squad_rows(picks, players, teams, positions)
            if not rows:
                print(f"  No squad data for GW{gw}, skipping.")
                continue

            out_path = os.path.join(entry_dir, f"GW{gw}.csv")
            write_csv(rows, out_path)
            print(f"  Wrote {len(rows)} players to {out_path}")

            print_squad_summary(entry_info, gw, rows, picks)

    print(f"\nDone. {len(entry_ids)} entr{'y' if len(entry_ids) == 1 else 'ies'} processed.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
