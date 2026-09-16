"""Config flow for Eredivisie."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FootballDataAuthError, Team, async_get_teams
from .const import COMPETITION, CONF_TEAM_CREST, CONF_TEAM_ID, CONF_TEAM_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_API_KEY_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


class EredivisieConfigFlow(ConfigFlow, domain=DOMAIN):
    """One config entry = one tracked club."""

    VERSION = 1

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._teams: list[Team] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                self._teams = await async_get_teams(session, COMPETITION, user_input[CONF_API_KEY])
            except FootballDataAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error fetching teams")
                errors["base"] = "cannot_connect"
            else:
                self._api_key = user_input[CONF_API_KEY]
                return await self.async_step_team()

        return self.async_show_form(step_id="user", data_schema=STEP_API_KEY_SCHEMA, errors=errors)

    async def async_step_team(self, user_input: dict[str, Any] | None = None) -> Any:
        team_choices = {str(t.id): t.name for t in self._teams}

        if user_input is not None:
            team_id = int(user_input[CONF_TEAM_ID])
            team = next(t for t in self._teams if t.id == team_id)

            await self.async_set_unique_id(str(team_id))
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=team.name,
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_TEAM_ID: team_id,
                    CONF_TEAM_NAME: team.name,
                    CONF_TEAM_CREST: team.crest,
                },
            )

        schema = vol.Schema({vol.Required(CONF_TEAM_ID): vol.In(team_choices)})
        return self.async_show_form(step_id="team", data_schema=schema)
