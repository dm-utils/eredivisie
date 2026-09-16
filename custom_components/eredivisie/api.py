"""Thin async client for football-data.org's v4 API."""

from __future__ import annotations

from dataclasses import dataclass

from aiohttp import ClientSession

BASE_URL = "https://api.football-data.org/v4"


class FootballDataAuthError(Exception):
    """Raised on 400/403 -- bad or missing API key."""


class FootballDataRateLimitError(Exception):
    """Raised on 429 -- out of requests for this minute."""


@dataclass
class Team:
    id: int
    name: str
    short_name: str
    crest: str


@dataclass
class Match:
    utc_date: str
    status: str
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None


async def _get(session: ClientSession, path: str, api_key: str, params: dict | None = None) -> dict:
    async with session.get(
        f"{BASE_URL}{path}", headers={"X-Auth-Token": api_key}, params=params
    ) as resp:
        if resp.status in (400, 403):
            raise FootballDataAuthError(await resp.text())
        if resp.status == 429:
            raise FootballDataRateLimitError(await resp.text())
        resp.raise_for_status()
        return await resp.json()


async def async_get_teams(session: ClientSession, competition: str, api_key: str) -> list[Team]:
    data = await _get(session, f"/competitions/{competition}/teams", api_key)
    return [
        Team(id=t["id"], name=t["name"], short_name=t.get("shortName") or t["name"], crest=t.get("crest", ""))
        for t in data["teams"]
    ]


async def async_get_standing(session: ClientSession, competition: str, api_key: str, team_id: int) -> dict | None:
    data = await _get(session, f"/competitions/{competition}/standings", api_key)
    table = data["standings"][0]["table"]
    return next((row for row in table if row["team"]["id"] == team_id), None)


def _to_match(m: dict) -> Match:
    score = m.get("score", {}).get("fullTime", {})
    return Match(
        utc_date=m["utcDate"],
        status=m["status"],
        home_team=m["homeTeam"]["name"],
        away_team=m["awayTeam"]["name"],
        home_score=score.get("home"),
        away_score=score.get("away"),
    )


async def async_get_team_matches(
    session: ClientSession, team_id: int, api_key: str, statuses: str, limit: int = 20
) -> list[Match]:
    """Fetch a team's matches for the given status filter, sorted by date.

    football-data.org's own ordering is NOT reliably chronological (confirmed
    via dev/test_football_data.py: a limit=1 query returned a later match
    than one visible further down an unlimited query) -- always sort
    client-side, never trust API order + a tight limit.
    """
    data = await _get(
        session, f"/teams/{team_id}/matches", api_key, params={"status": statuses, "limit": limit}
    )
    matches = [_to_match(m) for m in data["matches"]]
    return sorted(matches, key=lambda m: m.utc_date)
