from __future__ import annotations
from dataclasses import dataclass, field
from collections.abc import Callable
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from .const import DOMAIN, DISPATCH_SIGNAL

@dataclass
class TeknixSensorDescription(SensorEntityDescription):
    entity_category: EntityCategory | None = None

SENSOR_DESCS: list[TeknixSensorDescription] = [
    TeknixSensorDescription(
        key="house_loop_temp",
        name="House Loop Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    TeknixSensorDescription(
        key="tank_water_temp",
        name="Tank Temperature",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC
    ),
]

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    entities = [TeknixSensor(hub, entry.entry_id, d) for d in SENSOR_DESCS]
    async_add_entities(entities)

class TeknixSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, hub, entry_id: str, desc: SensorEntityDescription):
        self._hub = hub
        self._entry_id = entry_id
        self.entity_description = desc
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{desc.key}"
        self._attr_name = desc.name
        self._unsub = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._hub.serial)},
            manufacturer="Teknix",
            model=self._hub.model,
            name=f"Teknix {self._hub.model}",
            sw_version=self._hub.firmware,
        )

    @property
    def available(self) -> bool:
        return bool(getattr(self._hub, "state", None))

    @property
    def native_value(self):
        return (self._hub.state or {}).get(self.entity_description.key)

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