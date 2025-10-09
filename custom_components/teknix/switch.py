from __future__ import annotations
import logging

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from .const import DOMAIN, DISPATCH_SIGNAL
from .commands import (
    build_boiler_power_command,
    build_house_heating_active_command,
    build_tank_heating_active_command,
)

_LOGGER = logging.getLogger(__name__)

SWITCH_DESCS: list[SwitchEntityDescription] = [
    SwitchEntityDescription(key="boiler_power_state", translation_key="boiler_power_state", icon="mdi:power"),
    SwitchEntityDescription(key="house_heating_active", translation_key="house_heating_active", icon="mdi:radiator"),
    SwitchEntityDescription(key="tank_heating_active", translation_key="tank_heating_active", icon="mdi:water-boiler"),
]

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    entities = [TeknixSwitch(hub, entry.entry_id, d) for d in SWITCH_DESCS]
    _LOGGER.debug("Teknix.switch: adding %d switches", len(entities))
    async_add_entities(entities, True)

class TeknixSwitch(SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, hub, entry_id: str, desc: SwitchEntityDescription):
        self._hub = hub
        self._entry_id = entry_id
        self.entity_description = desc
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:sw:{desc.key}"
        self._attr_name = desc.name
        self._unsub = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, getattr(self._hub, "serial", self._entry_id))},
            manufacturer="Teknix",
            model=getattr(self._hub, "model", None),
            name=f"Teknix {getattr(self._hub, 'model', '')}".strip(),
            sw_version=getattr(self._hub, "firmware", None),
        )
        _LOGGER.debug("Teknix.switch entity init: %s", self._attr_unique_id)

    @property
    def is_on(self) -> bool:
        state = (getattr(self._hub, "state", {}) or {}).get(self.entity_description.key)
        if isinstance(state, bool):
            return state
        return str(state).lower() in ("1", "true", "on")

    async def async_turn_on(self, **kwargs):
        await self._apply_state(True)

    async def async_turn_off(self, **kwargs):
        await self._apply_state(False)

    async def _apply_state(self, turn_on: bool):
        key = self.entity_description.key

        if key == "boiler_power_state":
            cmd = build_boiler_power_command(turn_on)
        elif key == "house_heating_active":
            cmd = build_house_heating_active_command(turn_on)
        elif key == "tank_heating_active":
            cmd = build_tank_heating_active_command(turn_on)
        else:
            _LOGGER.warning("Unknown switch key %s, not sending command", key)
            return

        await self._hub.publish(cmd)
        _LOGGER.debug("Sent switch cmd for %s = %s: %s", key, turn_on, cmd)

        # mark this key as pending to suppress racing telemetry for a short time
        if hasattr(self._hub, "set_pending"):
            self._hub.set_pending(key, 1 if turn_on else 0)

        (self._hub.state or {}).update({key: 1 if turn_on else 0})
        async_dispatcher_send(self.hass, f"{DISPATCH_SIGNAL}_{self._entry_id}")
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self._unsub = async_dispatcher_connect(
            self.hass, f"{DISPATCH_SIGNAL}_{self._entry_id}", self._handle_state
        )

    async def async_will_remove_from_hass(self):
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_state(self):
        self.async_write_ha_state()