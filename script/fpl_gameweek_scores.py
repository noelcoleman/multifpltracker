"""
Fantasy Premier League — per-gameweek player scores
---------------------------------------------------------
Uses the public, unauthenticated FPL API:
  - https://fantasy.premierleague.com/api/bootstrap-static/
  - https://fantasy.premierleague.com/api/event/{gw}/live/

Writes one CSV per gameweek into a "weeks" subfolder next to this
script, named GW1.csv, GW2.csv, etc. Each CSV has every player's
stats for that gameweek, sorted by points scored, highest first.

Usage:
    python fpl_gameweek_scores.py                # current gameweek -> weeks/GW{n}.csv
    python fpl_gameweek_scores.py --gw 5          # one specific gameweek -> weeks/GW5.csv
    python fpl_gameweek_scores.py --gw 1-5        # a range of gameweeks -> weeks/GW1.csv ... GW5.csv
    python fpl_gameweek_scores.py --all           # every gameweek played so far -> weeks/GW1.csv ...
    python fpl_gameweek_scores.py --weeks-dir out # use a different subfolder name
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
    """Pick the current gw if flagged, otherwise fall back to the next one,
    otherwise the last finished one."""
    for e in events:
        if e.get("is_current"):
            return e["id"]
    for e in events:
        if e.get("is_next"):
            return e["id"]
    finished = [e["id"] for e in events if e.get("finished")]
    return max(finished) if finished else 1


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


def get_played_gameweeks(events):
    """All gameweeks that have kicked off (finished, or currently in progress)."""
    return sorted(
        e["id"] for e in events
        if e.get("finished") or e.get("is_current")
    )


def build_rows(live, players, teams, positions):
    rows = []
    for entry in live["elements"]:
        p = players.get(entry["id"])
        if not p:
            continue
        stats = entry["stats"]
        rows.append({
            "player": f'{p["first_name"]} {p["second_name"]}',
            "web_name": p["web_name"],
            "team": teams.get(p["team"], "?"),
            "position": positions.get(p["element_type"], "?"),
            "gw_points": stats["total_points"],
            "minutes": stats["minutes"],
            "goals": stats["goals_scored"],
            "assists": stats["assists"],
            "clean_sheets": stats["clean_sheets"],
            "bonus": stats["bonus"],
            "yellow_cards": stats["yellow_cards"],
            "red_cards": stats["red_cards"],
            "played": stats["played"],
        })
    rows.sort(key=lambda r: r["gw_points"], reverse=True)
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Export FPL player scores per gameweek into weeks/GW{n}.csv files.")
    parser.add_argument("--gw", type=str, default=None,
                         help="Gameweek number ('5') or range ('1-5'). Default: current gameweek only.")
    parser.add_argument("--all", action="store_true",
                         help="Export every gameweek played so far (finished or in progress).")
    parser.add_argument("--weeks-dir", type=str, default="weeks",
                         help="Subfolder to write the per-gameweek CSVs into (default: weeks)")
    args = parser.parse_args()

    print("Fetching player/team data...")
    bootstrap = fetch_json(f"{BASE}/bootstrap-static/")

    players = {p["id"]: p for p in bootstrap["elements"]}
    teams = {t["id"]: t["name"] for t in bootstrap["teams"]}
    positions = {pt["id"]: pt["singular_name_short"] for pt in bootstrap["element_types"]}
    events = bootstrap["events"]

    if args.all:
        gameweeks = get_played_gameweeks(events)
    else:
        gameweeks = parse_gw_arg(args.gw, events)

    os.makedirs(args.weeks_dir, exist_ok=True)

    for gw in gameweeks:
        print(f"Fetching live scores for Gameweek {gw}...")
        live = fetch_json(f"{BASE}/event/{gw}/live/")
        rows = build_rows(live, players, teams, positions)

        if not rows:
            print(f"  No data for Gameweek {gw}, skipping.")
            continue

        out_path = os.path.join(args.weeks_dir, f"GW{gw}.csv")
        write_csv(rows, out_path)
        print(f"  Wrote {len(rows)} players to {out_path}")

        top = rows[0]
        print(f"  Top scorer: {top['web_name']} ({top['team']}) — {top['gw_points']} pts")

    print(f"\nDone. {len(gameweeks)} gameweek file(s) written to '{args.weeks_dir}/'.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
