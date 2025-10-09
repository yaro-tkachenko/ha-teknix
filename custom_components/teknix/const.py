from homeassistant.const import Platform
DOMAIN = "teknix"

CONF_SERIAL = "serial_number"
CONF_MODEL  = "model"

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

DISPATCH_SIGNAL = f"{DOMAIN}_update"

# MQTT topics (derived from serial)
def cmd_topic(serial: str) -> str:
    return f"cmnd/tasmota_{serial}/SerialSend"

def tele_topic(serial: str) -> str:
    # wildcard, we subscribe to all tele from that device
    return f"tele/tasmota_{serial}/#"

MODELS = {
    "ESPRO 4.5": {"elements_count": 3, "element_kw": 1.50},
    "ESPRO 6":   {"elements_count": 6, "element_kw": 1.00},
    "ESPRO 7.5": {"elements_count": 6, "element_kw": 1.25},
    "ESPRO 9":   {"elements_count": 6, "element_kw": 1.50},
    "ESPRO 12":  {"elements_count": 6, "element_kw": 2.00},
    "ESPRO 15":  {"elements_count": 6, "element_kw": 2.50},
    "ESPRO 18":  {"elements_count": 6, "element_kw": 3.00},
    "ESPRO 21":  {"elements_count": 9, "element_kw": 2.33},
    "ESPRO 24":  {"elements_count": 9, "element_kw": 2.66},
}

def model_total_kw(model_name: str) -> float:
    m = MODELS[model_name]
    return round(m["elements_count"] * m["element_kw"], 2)

def model_max_step(model_name: str) -> int:
    return min(6, MODELS[model_name]["elements_count"])

def model_element_kw(model_name: str) -> float:
    m = MODELS[model_name]
    return float(m["element_kw"])

IDX = {
    "boiler_power_state": 0,
    "house_target_temp": 1,
    "tank_target_temp": 8,
    "house_heating_active": 11,
    "tank_heating_active": 12,
    "house_power_step": 18,
    "tank_power_step": 19,
    "house_loop_temp": 38,   # /10
    "tank_water_temp": 39,   # /10
}