from __future__ import annotations

def build_power_command(house_step: int, tank_step: int) -> str:
    _validate_step(house_step)
    _validate_step(tank_step)

    HH = f"{house_step:02d}"
    WW = f"{tank_step:02d}"
    SS = f"{12 + house_step + tank_step:02d}"
    return f"T19{HH}20{WW}00{SS}Z"


def build_house_temp_command(temp_c: int, legacy_hex: bool = False) -> str:
    _validate_temp(temp_c)

    tens, ones = divmod(temp_c, 10)
    base = 5 + (tens - 3)
    raw = base + ones

    suffix = f"{raw:02d}" if not legacy_hex else f"{raw:02X}"

    return f"T02{temp_c:02d}00{suffix}Z"


def build_tank_temp_command(temp_c: int) -> str:
    _validate_temp(temp_c)

    tens, ones = divmod(temp_c, 10)
    suffix_dec = f"{9 + tens + ones:02d}"
    return f"T09{temp_c:02d}00{suffix_dec}Z"

# --- switch command builders ---

def build_boiler_power_command(turn_on: bool) -> str:
    return "T01010002Z" if turn_on else "T01000001Z"


def build_house_heating_active_command(turn_on: bool) -> str:
    return "T120111010007Z" if turn_on else "T120011010006Z"


def build_tank_heating_active_command(turn_on: bool) -> str:
    return "T13000005Z" if turn_on else "T13000004Z"

# --- info command ---

def build_info_command() -> str:
    """Build INFO command to request current state from teknix."""
    return "INFO"

# --- helpers ---

def _validate_step(step: int) -> None:
    if not (1 <= step <= 6):
        raise ValueError("Step must be in range 1..6.")


def _validate_temp(temp_c: int) -> None:
    if not (30 <= temp_c <= 80):
        raise ValueError("Temperature must be in range 30..80 °C.")