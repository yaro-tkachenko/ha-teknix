from __future__ import annotations
from dataclasses import dataclass
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfPower
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
        translation_key="house_loop_temp",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    TeknixSensorDescription(
        key="tank_water_temp",
        translation_key="tank_water_temp",
        icon="mdi:thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    TeknixSensorDescription(
        key="house_target_temp",
        translation_key="house_target_temp",
        icon="mdi:home-thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    TeknixSensorDescription(
        key="tank_target_temp",
        translation_key="tank_target_temp",
        icon="mdi:water-thermometer",
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
]

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    entities = [TeknixSensor(hub, entry.entry_id, d) for d in SENSOR_DESCS]
    entities.append(TeknixCurrentConsumptionSensor(hub, entry.entry_id))
    async_add_entities(entities)

class TeknixSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, hub, entry_id: str, desc: TeknixSensorDescription):
        self._hub = hub
        self._entry_id = entry_id
        self.entity_description = desc
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{desc.key}"
        self._attr_name = desc.name
        self._unsub = None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._hub.serial)},
            manufacturer="Teknix",
            model=self._hub.model,
            name=f"Teknix {self._hub.model}",
            sw_version=getattr(self._hub, "firmware", None),
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

class TeknixCurrentConsumptionSensor(SensorEntity):
    """Diagnostic sensor: instantaneous power (kW) computed from active mode and steps."""
    _attr_has_entity_name = True
    _attr_translation_key = "current_consumption"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_state_class = "measurement"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, entry_id: str):
        self._hub = hub
        self._entry_id = entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_current_energy_consumption"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._hub.serial)},
            manufacturer="Teknix",
            model=self._hub.model,
            name=f"Teknix {self._hub.model}",
            sw_version=getattr(self._hub, "firmware", None),
        )
        self._unsub = None

    @property
    def available(self) -> bool:
        return bool(getattr(self._hub, "state", None))

    @property
    def native_value(self):
        """Return instantaneous power in kW."""
        s = self._hub.state or {}

        house_active = bool(s.get("house_heating_active"))
        tank_active = bool(s.get("tank_heating_active"))

        step_max = int(getattr(self._hub, "step_max", 6) or 6)
        house_step = max(0, min(int(s.get("house_power_step", 0) or 0), step_max))
        tank_step = max(0, min(int(s.get("tank_power_step", 0) or 0), step_max))

        element_kw = float(getattr(self._hub, "element_kw", 0.0) or 0.0)
        if element_kw <= 0:
            return 0.0

        if tank_active and not house_active:
            step = tank_step
        elif house_active and not tank_active:
            step = house_step
        elif house_active and tank_active:
            step = max(house_step, tank_step)
        else:
            step = 0

        return round(step * element_kw, 2)

    @property
    def extra_state_attributes(self):
        s = self._hub.state or {}
        return {
            "model": self._hub.model,
            "element_kw": getattr(self._hub, "element_kw", None),
            "max_step": getattr(self._hub, "step_max", None),
            "house_heating_active": s.get("house_heating_active"),
            "tank_heating_active": s.get("tank_heating_active"),
            "house_power_step": s.get("house_power_step"),
            "tank_power_step": s.get("tank_power_step"),
        }

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