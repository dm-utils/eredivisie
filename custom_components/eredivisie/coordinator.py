"""DataUpdateCoordinator with adaptive polling: slow normally, fast around
a configured team's live match."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    FootballDataAuthError,
    FootballDataRateLimitError,
    Match,
    async_get_standing,
    async_get_team_matches,
)
from .const import (
    COMPETITION,
    CONF_TEAM_ID,
    DOMAIN,
    LIVE_INTERVAL,
    LIVE_STATUSES,
    NORMAL_INTERVAL,
    PRE_MATCH_WINDOW,
)

_LOGGER = logging.getLogger(__name__)

ALL_RELEVANT_STATUSES = "SCHEDULED,TIMED,IN_PLAY,PAUSED,FINISHED"


@dataclass
class EredivisieData:
    standing: dict | None
    last_match: Match | None
    next_match: Match | None
    live_match: Match | None


def _is_pre_match(match: Match) -> bool:
    kickoff = datetime.fromisoformat(match.utc_date.replace("Z", "+00:00"))
    return timedelta(0) <= (kickoff - datetime.now(timezone.utc)) <= PRE_MATCH_WINDOW


class EredivisieCoordinator(DataUpdateCoordinator[EredivisieData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.api_key: str = entry.data[CONF_API_KEY]
        self.team_id: int = entry.data[CONF_TEAM_ID]
        self._session = async_get_clientsession(hass)
        self._live_mode = False

        super().__init__(
            hass, _LOGGER, name=f"{DOMAIN}_{entry.data[CONF_TEAM_ID]}", update_interval=NORMAL_INTERVAL
        )

    async def _async_update_data(self) -> EredivisieData:
        try:
            matches = await async_get_team_matches(
                self._session, self.team_id, self.api_key, ALL_RELEVANT_STATUSES, limit=10
            )
        except FootballDataAuthError as err:
            raise UpdateFailed(f"Invalid API key: {err}") from err
        except FootballDataRateLimitError as err:
            # Don't escalate the interval further on a 429 -- just skip this
            # refresh and let the existing (already-conservative) interval
            # try again next time.
            raise UpdateFailed(f"Rate limited, will retry next interval: {err}") from err

        finished = [m for m in matches if m.status == "FINISHED"]
        upcoming = [m for m in matches if m.status in ("SCHEDULED", "TIMED")]
        live = [m for m in matches if m.status in LIVE_STATUSES]

        last_match = finished[-1] if finished else None
        next_match = upcoming[0] if upcoming else None
        live_match = live[0] if live else None

        should_be_live = bool(live_match) or (next_match is not None and _is_pre_match(next_match))
        if should_be_live != self._live_mode:
            self._live_mode = should_be_live
            self.update_interval = LIVE_INTERVAL if should_be_live else NORMAL_INTERVAL
            _LOGGER.debug("Switching to %s polling (%s)", "live" if should_be_live else "normal", self.update_interval)

        standing = None
        if not self._live_mode:
            # Skip during live mode: the table doesn't change mid-match, and
            # it saves a call from the shared per-minute budget right when
            # the live-mode calls are at their most frequent.
            standing = await async_get_standing(self._session, COMPETITION, self.api_key, self.team_id)

        return EredivisieData(standing=standing, last_match=last_match, next_match=next_match, live_match=live_match)
