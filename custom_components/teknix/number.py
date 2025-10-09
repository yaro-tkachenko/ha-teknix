from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

TARGETS = [
    {
        "key": "house_target_temp",
        "name": "House Loop Target Temperature",
        "min": 30,
        "max": 80,
        "step": 1,
    },
    {
        "key": "tank_target_temp",
        "name": "Tank Target Temperature",
        "min": 30,
        "max": 80,
        "step": 1,
    },
]

POWER_STEPS = [
    {
        "key": "house_power_step",
        "name": "House Power Step",
    },
    {
        "key": "tank_power_step",
        "name": "Tank Power Step",
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
    _attr_mode = NumberMode.BOX  # можна поміняти на SLIDER

    def __init__(self, hub, entry_id: str, key: str, name: str):
        self._hub = hub
        self._entry_id = entry_id
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}:{entry_id}:num:{key}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, getattr(self._hub, "serial", self._entry_id))},
            manufacturer="Teknix",
            model=getattr(self._hub, "model", None),
            name=f"Teknix {getattr(self._hub, 'model', '')}".strip(),
            sw_version=getattr(self._hub, "firmware", None),
        )


class TeknixTargetTempNumber(BaseTeknixNumber):
    def __init__(self, hub, entry_id: str, cfg: dict):
        super().__init__(hub, entry_id, cfg["key"], cfg["name"])
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
        # TODO: тут надішли MQTT команду на зміну цільової температури
        self._hub.state[self._key] = int(value)
        self.async_write_ha_state()


class TeknixPowerStepNumber(BaseTeknixNumber):
    def __init__(self, hub, entry_id: str, cfg: dict):
        super().__init__(hub, entry_id, cfg["key"], cfg["name"])
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
        v = max(1, min(v, int(self.native_max_value)))
        self._hub.state[self._key] = v
        self.async_write_ha_state()