from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .commands import (
    build_power_command,
    build_house_temp_command,
    build_tank_temp_command,
)

TARGETS = [
    {
        "key": "house_target_temp",
        "translation_key": "house_target_temp",
        "min": 30,
        "max": 80,
        "step": 1,
    },
    {
        "key": "tank_target_temp",
        "translation_key": "tank_target_temp",
        "min": 30,
        "max": 80,
        "step": 1,
    },
]

POWER_STEPS = [
    {
        "key": "house_heating_step",
        "translation_key": "house_heating_step",
    },
    {
        "key": "tank_heating_step",
        "translation_key": "tank_heating_step",
    },
]


async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]

    entities: list[NumberEntity] = []
    entities += [TeknixTargetTempNumber(hub, entry.entry_id, cfg) for cfg in TARGETS]
    entities += [TeknixPowerStepNumber(hub, entry.entry_id, cfg) for cfg in POWER_STEPS]

    async_add_entities(entities, True)


class BaseTeknixNumber(NumberEntity):
    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

    def __init__(self, hub, entry_id: str, key: str, translation_key: str):
        self._hub = hub
        self._entry_id = entry_id
        self._key = key
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:num:{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, getattr(self._hub, "serial", self._entry_id))},
            manufacturer="Teknix",
            model=getattr(self._hub, "model", None),
            name=f"Teknix {getattr(self._hub, 'model', '')}".strip(),
            sw_version=getattr(self._hub, "firmware", None),
        )


class TeknixTargetTempNumber(BaseTeknixNumber):
    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = "temperature"

    def __init__(self, hub, entry_id: str, cfg: dict):
        super().__init__(hub, entry_id, cfg["key"], cfg["translation_key"])
        self._min = cfg["min"]
        self._max = cfg["max"]
        self._step = cfg["step"]
        self._hub.state.setdefault(self._key, self._min)

    @property
    def native_min_value(self) -> float:
        return self._min

    @property
    def native_max_value(self) -> float:
        return self._max

    @property
    def native_step(self) -> float:
        return self._step

    @property
    def native_value(self):
        return int(self._hub.state.get(self._key, self._min))

    async def async_set_native_value(self, value: float) -> None:
        t = int(round(value))
        if t < self._min:
            t = self._min
        if t > self._max:
            t = self._max

        if self._key == "house_target_temp":
            cmd = build_house_temp_command(t) 
        else:
            cmd = build_tank_temp_command(t)

        await self._hub.publish(cmd)
        # mark this key as pending to suppress racing telemetry for a short time
        if hasattr(self._hub, "set_pending"):
            self._hub.set_pending(self._key, t)

        # локально оновлюємо стан (HA потім перепише з телеметрії)
        self._hub.state[self._key] = t
        self.async_write_ha_state()


class TeknixPowerStepNumber(BaseTeknixNumber):
    def __init__(self, hub, entry_id: str, cfg: dict):
        super().__init__(hub, entry_id, cfg["key"], cfg["translation_key"])
        self._hub.state.setdefault(self._key, 1)

    @property
    def native_min_value(self) -> float:
        return 1

    @property
    def native_max_value(self) -> float:
        return int(getattr(self._hub, "step_max", 6) or 6)

    @property
    def native_step(self) -> float:
        return 1

    @property
    def native_value(self):
        value = int(self._hub.state.get(self._key, 1))
        if value > self.native_max_value:
            value = int(self.native_max_value)
        if value < 1:
            value = 1
        return value

    async def async_set_native_value(self, value: float) -> None:
        v = int(round(value))
        maxv = int(self.native_max_value)
        if v < 1:
            v = 1
        if v > maxv:
            v = maxv

        house_step = int(self._hub.state.get("house_heating_step", 1))
        tank_step = int(self._hub.state.get("tank_heating_step", 1))

        if self._key == "house_heating_step":
            house_step = v
        else:
            tank_step = v

        other_max = maxv
        house_step = max(1, min(int(house_step), other_max))
        tank_step = max(1, min(int(tank_step), other_max))

        cmd = build_power_command(house_step, tank_step)
        await self._hub.publish(cmd)
        
        if hasattr(self._hub, "set_pending"):
            self._hub.set_pending("house_heating_step", house_step)
            self._hub.set_pending("tank_heating_step", tank_step)

        self._hub.state[self._key] = v
        self.async_write_ha_state()