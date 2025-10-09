from __future__ import annotations
import logging
import time
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.components import mqtt
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN, PLATFORMS, CONF_SERIAL, CONF_MODEL,
    DISPATCH_SIGNAL, model_max_step, cmd_topic, tele_topic, model_total_kw, model_element_kw,
    INFO_COMMAND_INTERVAL_MINUTES,
)
from .parser import parse_info_message
from .commands import build_info_command

_LOGGER = logging.getLogger(__name__)

class TeknixHub:
    def __init__(self, hass: HomeAssistant, serial: str, model: str, entry_id: str):
        self.hass = hass
        self.serial = serial
        self.model = model
        self.entry_id = entry_id
        self.firmware = None
        self.step_max = model_max_step(model)
        self.state: dict = {}
        self.device_id: str | None = None
        self._unsub_mqtt = None
        self._unsub_info_timer = None
        
        self._store = Store(hass, 1, f"{DOMAIN}.{serial}")
        
        # Pending overrides to suppress brief MQTT races after local writes
        self._pending_until: dict[str, float] = {}
        self._pending_values: dict[str, object] = {}
    
    @property
    def element_kw(self) -> float:
        return model_element_kw(self.model)

    async def async_start(self) -> None:
        await self._async_restore_state()
        
        topic = tele_topic(self.serial)
        _LOGGER.warning("TeknixHub subscribing to %s", topic)
        self._unsub_mqtt = await mqtt.async_subscribe(
            self.hass, topic, self._mqtt_message_received
        )
        
        # Start periodic INFO command sending every minute
        self._unsub_info_timer = async_track_time_interval(
            self.hass, self._send_info_command, timedelta(minutes=INFO_COMMAND_INTERVAL_MINUTES)
        )
        _LOGGER.info("Started periodic INFO command sending every minute")
        
        # Send initial INFO command to get current state
        self._send_info_command()

    async def async_stop(self) -> None:
        if self._unsub_mqtt:
            self._unsub_mqtt()
            self._unsub_mqtt = None
        
        if self._unsub_info_timer:
            self._unsub_info_timer()
            self._unsub_info_timer = None
            _LOGGER.info("Stopped periodic INFO command sending")

    @callback
    def _mqtt_message_received(self, msg) -> None:
        """Handle incoming MQTT tele frame."""
        payload = msg.payload
        if isinstance(payload, (bytes, bytearray)):
            try:
                payload = payload.decode("utf-8", "ignore")
            except Exception:
                payload = str(payload)

        parsed = parse_info_message(payload)
        if not parsed:
            return

        # Merge parsed telemetry into state, but respect pending suppressions
        now = time.monotonic()
        new_state = dict(self.state)

        # Cleanup expired pending entries
        expired_keys = [k for k, ts in self._pending_until.items() if ts <= now]
        for k in expired_keys:
            self._pending_until.pop(k, None)
            self._pending_values.pop(k, None)

        for key, value in parsed.items():
            pending_ts = self._pending_until.get(key)
            if pending_ts is not None and now < pending_ts:
                pending_value = self._pending_values.get(key)
                # If telemetry differs during the pending window, ignore it
                if pending_value is not None and pending_value != value:
                    continue
                # If telemetry matches our pending value, accept and clear pending
                if pending_value == value:
                    self._pending_until.pop(key, None)
                    self._pending_values.pop(key, None)
            new_state[key] = value

        self.state = new_state

        self.hass.create_task(self._async_save_state())

        async_dispatcher_send(self.hass, f"{DISPATCH_SIGNAL}_{self.entry_id}")

    @callback
    def _send_info_command(self, now=None) -> None:
        """Send INFO command to request current state from teknix."""
        info_cmd = build_info_command()
        self.hass.create_task(self.async_send_command(info_cmd))

    async def async_send_command(self, raw_cmd: str) -> None:
        topic = cmd_topic(self.serial)
        _LOGGER.info("Sending MQTT command to %s: %s", topic, raw_cmd)
        await mqtt.async_publish(self.hass, topic, raw_cmd)

    # Alias used by entities
    async def publish(self, raw_cmd: str) -> None:
        await self.async_send_command(raw_cmd)

    def set_pending(self, key: str, value: object, ttl: float = 2.0) -> None:
        """Mark a key as locally overridden for a brief period to avoid races.

        During the TTL, incoming differing telemetry for this key will be ignored.
        """
        self._pending_until[key] = time.monotonic() + max(0.1, float(ttl))
        self._pending_values[key] = value

    async def _async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            await self._store.async_save(self.state)
        except Exception as e:
            _LOGGER.warning("Failed to save teknix state: %s", e)

    async def _async_restore_state(self) -> None:
        """Restore state from storage."""
        try:
            stored_data = await self._store.async_load()
            if stored_data:
                self.state = stored_data
                _LOGGER.info("Restored teknix state from storage: %s", self.state)
        except Exception as e:
            _LOGGER.warning("Failed to restore teknix state: %s", e)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    serial = entry.data[CONF_SERIAL]
    model = entry.data[CONF_MODEL]

    hub = TeknixHub(hass, serial, model, entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = hub

    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, serial)},
        manufacturer="Teknix",
        model=model,
        name=f"Teknix {model}",
        sw_version=hub.firmware,
    )
    hub.device_id = device.id

    await hub.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub: TeknixHub = hass.data[DOMAIN][entry.entry_id]
    await hub.async_stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok