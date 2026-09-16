"""Pilot validation for the Eredivisie integration: confirms the
football-data.org API shape and rate-limit headers before building the
real config_flow/coordinator/sensor code.

Usage:
    pip install -r dev/requirements.txt
    python dev/test_football_data.py
"""

from __future__ import annotations

import json
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
BASE_URL = "https://api.football-data.org/v4"
COMPETITION = "DED"  # Eredivisie
TEST_CLUB_NAME = "Ajax"


def load_api_key() -> str:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("FOOTBALL_DATA_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError(f"FOOTBALL_DATA_API_KEY not found in {env_path}")


def get_json(path: str, api_key: str) -> tuple[dict, dict]:
    req = urllib.request.Request(f"{BASE_URL}{path}", headers={"X-Auth-Token": api_key})
    with urllib.request.urlopen(req, context=SSL_CONTEXT) as resp:
        # Actual header names confirmed by inspecting a raw response --
        # differ in casing/naming from what the docs page described.
        headers = {
            "requests_available_this_minute": resp.headers.get("x-requests-available-minute"),
            "reset_in_seconds": resp.headers.get("X-RequestCounter-Reset"),
        }
        print(f"  HTTP {resp.status} | {path} | quota: {headers}")
        return json.loads(resp.read().decode("utf-8")), headers


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    api_key = load_api_key()

    print(f"Fetching {COMPETITION} standings...")
    standings, _ = get_json(f"/competitions/{COMPETITION}/standings", api_key)
    table = standings["standings"][0]["table"]
    print(f"\n--- {COMPETITION} standings (top 5) ---")
    for row in table[:5]:
        team = row["team"]["name"]
        print(f"  {row['position']:>2}. {team:20s} pts={row['points']:<3} "
              f"W{row['won']}-D{row['draw']}-L{row['lost']}  GD={row['goalDifference']}")

    club_row = next((r for r in table if TEST_CLUB_NAME.lower() in r["team"]["name"].lower()), None)
    if not club_row:
        print(f"\nCould not find '{TEST_CLUB_NAME}' in standings; skipping match lookup.")
        return

    team_id = club_row["team"]["id"]
    print(f"\nFetching matches for {club_row['team']['name']} (team id {team_id})...")

    # The API's default /teams/{id}/matches window only returned future
    # fixtures in testing -- explicit status filters are needed to reliably
    # get "last result" vs "next match" as two small, cheap calls. IMPORTANT:
    # the API's own ordering is NOT reliably chronological (confirmed: a
    # limit=1 query returned a later match than one visible further down an
    # unlimited query) -- always sort client-side, never trust API order +
    # a tight limit for "next"/"last".
    finished, _ = get_json(f"/teams/{team_id}/matches?status=FINISHED&limit=5", api_key)
    upcoming, _ = get_json(f"/teams/{team_id}/matches?status=SCHEDULED,TIMED&limit=20", api_key)

    finished_sorted = sorted(finished["matches"], key=lambda m: m["utcDate"])
    upcoming_sorted = sorted(upcoming["matches"], key=lambda m: m["utcDate"])

    if finished_sorted:
        last = finished_sorted[-1]
        h, a = last["homeTeam"]["name"], last["awayTeam"]["name"]
        score = last["score"]["fullTime"]
        print(f"\nLast result: {h} {score['home']}-{score['away']} {a}  ({last['utcDate']})")

    if upcoming_sorted:
        nxt = upcoming_sorted[0]
        h, a = nxt["homeTeam"]["name"], nxt["awayTeam"]["name"]
        print(f"Next match:  {h} vs {a}  ({nxt['utcDate']}, status={nxt['status']})")


if __name__ == "__main__":
    main()
