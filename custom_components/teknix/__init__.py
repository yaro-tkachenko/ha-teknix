from __future__ import annotations
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.components import mqtt
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN, PLATFORMS, CONF_SERIAL, CONF_MODEL,
    DISPATCH_SIGNAL, model_max_step, cmd_topic, tele_topic
)
from .parser import parse_info_message

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

    async def async_start(self) -> None:
        topic = tele_topic(self.serial)
        _LOGGER.warning("TeknixHub subscribing to %s", topic)
        self._unsub_mqtt = await mqtt.async_subscribe(
            self.hass, topic, self._mqtt_message_received
        )

    async def async_stop(self) -> None:
        if self._unsub_mqtt:
            self._unsub_mqtt()
            self._unsub_mqtt = None

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

        
        self.state = parsed
        
        async_dispatcher_send(self.hass, f"{DISPATCH_SIGNAL}_{self.entry_id}")

    async def async_send_command(self, raw_cmd: str) -> None:
        topic = cmd_topic(self.serial)
        await mqtt.async_publish(self.hass, topic, raw_cmd)


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