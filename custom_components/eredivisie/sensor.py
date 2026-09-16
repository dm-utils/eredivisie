"""Sensor platform for Eredivisie."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_TEAM_CREST, CONF_TEAM_NAME, DOMAIN
from .coordinator import EredivisieCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: EredivisieCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PositionSensor(coordinator, entry),
            NextMatchSensor(coordinator, entry),
            LastResultSensor(coordinator, entry),
            LiveScoreSensor(coordinator, entry),
        ]
    )


class _BaseEredivisieSensor(CoordinatorEntity[EredivisieCoordinator], SensorEntity):
    _attr_icon = "mdi:soccer"

    def __init__(self, coordinator: EredivisieCoordinator, entry: ConfigEntry, suffix: str, name_suffix: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_name = f"{entry.data[CONF_TEAM_NAME]} {name_suffix}"
        self._attr_entity_picture = entry.data.get(CONF_TEAM_CREST)


class PositionSensor(_BaseEredivisieSensor):
    def __init__(self, coordinator: EredivisieCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "position", "positie")

    @property
    def native_value(self):
        standing = self.coordinator.data.standing
        return standing["position"] if standing else None

    @property
    def extra_state_attributes(self) -> dict:
        standing = self.coordinator.data.standing
        if not standing:
            return {}
        return {
            "points": standing["points"],
            "played": standing["playedGames"],
            "won": standing["won"],
            "draw": standing["draw"],
            "lost": standing["lost"],
            "goal_difference": standing["goalDifference"],
        }


class NextMatchSensor(_BaseEredivisieSensor):
    def __init__(self, coordinator: EredivisieCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "next_match", "volgende wedstrijd")

    @property
    def native_value(self):
        match = self.coordinator.data.next_match
        return match.utc_date if match else None

    @property
    def extra_state_attributes(self) -> dict:
        match = self.coordinator.data.next_match
        if not match:
            return {}
        team = self._entry.data[CONF_TEAM_NAME]
        home = match.home_team == team
        return {
            "opponent": match.away_team if home else match.home_team,
            "home_away": "thuis" if home else "uit",
            "status": match.status,
        }


class LastResultSensor(_BaseEredivisieSensor):
    def __init__(self, coordinator: EredivisieCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "last_result", "laatste uitslag")

    @property
    def native_value(self):
        match = self.coordinator.data.last_match
        if not match:
            return None
        return f"{match.home_team} {match.home_score}-{match.away_score} {match.away_team}"

    @property
    def extra_state_attributes(self) -> dict:
        match = self.coordinator.data.last_match
        if not match:
            return {}
        return {"date": match.utc_date, "home_team": match.home_team, "away_team": match.away_team}


class LiveScoreSensor(_BaseEredivisieSensor):
    def __init__(self, coordinator: EredivisieCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "live", "live")

    @property
    def native_value(self):
        match = self.coordinator.data.live_match
        if not match:
            return "geen wedstrijd bezig"
        return f"{match.home_score}-{match.away_score}"

    @property
    def extra_state_attributes(self) -> dict:
        match = self.coordinator.data.live_match
        if not match:
            return {}
        return {"home_team": match.home_team, "away_team": match.away_team, "status": match.status}
