"""
Build the GW_PICKS data block for fpl_tracker_dashboard.html
---------------------------------------------------------
Reads every entries/<entry_id>/GW*.csv written by fpl_entry_team.py
(real picks pulled from the FPL API: captain/vice flags, points scored,
bench via multiplier) and injects them as a JSON blob into the dashboard
HTML, between the GW_PICKS_START/GW_PICKS_END marker comments.

Run this after fetching new gameweeks with fpl_entry_team.py:
    python script/build_gw_pitch_data.py
"""

import csv
import glob
import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENTRIES_DIR = os.path.join(SCRIPT_DIR, "entries", "entries")
DASHBOARD_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "fpl_tracker_dashboard.html")

ENTRY_TEAM = {
    3569788: "Claude",
    5416382: "ChatGPT",
    5421890: "Copilot",
}

GW_FILE_RE = re.compile(r"GW(\d+)\.csv$", re.IGNORECASE)


def to_bool(value):
    return str(value).strip().lower() == "true"


def load_gw_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = []
        for row in csv.DictReader(f):
            rows.append({
                "web_name": row["web_name"],
                "player": row["player"],
                "team": row["team"],
                "position": row["position"],
                "gw_points": int(row["gw_points"]),
                "total_points": int(row["total_points"]),
                "now_cost_m": float(row["now_cost_m"]),
                "squad_position": int(row["squad_position"]),
                "is_captain": to_bool(row["is_captain"]),
                "is_vice_captain": to_bool(row["is_vice_captain"]),
                "multiplier": int(row["multiplier"]),
            })
    rows.sort(key=lambda r: r["squad_position"])
    return rows


def build_gw_picks():
    gw_picks = {}
    for entry_id, team in ENTRY_TEAM.items():
        entry_dir = os.path.join(ENTRIES_DIR, str(entry_id))
        if not os.path.isdir(entry_dir):
            continue
        weeks = {}
        for path in glob.glob(os.path.join(entry_dir, "GW*.csv")):
            m = GW_FILE_RE.search(os.path.basename(path))
            if not m:
                continue
            gw = int(m.group(1))
            weeks[gw] = load_gw_csv(path)
        if weeks:
            gw_picks[team] = weeks
    return gw_picks


def inject_into_dashboard(gw_picks):
    with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    payload = json.dumps(gw_picks, ensure_ascii=False)
    replacement = (
        "/* GW_PICKS_START */\n"
        f"const GW_PICKS = {payload};\n"
        "/* GW_PICKS_END */"
    )

    pattern = re.compile(
        r"/\* GW_PICKS_START \*/.*?/\* GW_PICKS_END \*/",
        re.DOTALL,
    )
    if not pattern.search(html):
        raise SystemExit(
            "Could not find GW_PICKS_START/GW_PICKS_END markers in "
            f"{DASHBOARD_PATH}. Add the placeholder block first."
        )

    html = pattern.sub(lambda _: replacement, html, count=1)

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    gw_picks = build_gw_picks()
    total_files = sum(len(weeks) for weeks in gw_picks.values())
    inject_into_dashboard(gw_picks)
    print(f"Wrote GW_PICKS for {len(gw_picks)} team(s), {total_files} gameweek file(s) total.")
    for team, weeks in gw_picks.items():
        print(f"  {team}: GW{', GW'.join(str(gw) for gw in sorted(weeks))}")


if __name__ == "__main__":
    main()
