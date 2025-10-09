# custom_components/teknix_boiler/commands.py
from __future__ import annotations

def build_power_command(house_step: int, tank_step: int) -> str:
    _validate_step(house_step)
    _validate_step(tank_step)

    HH = f"{house_step:02d}"
    WW = f"{tank_step:02d}"
    SS = f"{12 + house_step + tank_step:02d}"
    return f"T19{HH}20{WW}00{SS}Z"


def build_house_temp_command(temp_c: int) -> str:
    _validate_temp(temp_c)

    tens, ones = divmod(temp_c, 10)
    base = 5 + (tens - 3)
    suffix_hex = f"{base + ones:02X}"
    return f"T02{temp_c:02d}00{suffix_hex}Z"


def build_tank_temp_command(temp_c: int) -> str:
    _validate_temp(temp_c)

    tens, ones = divmod(temp_c, 10)
    suffix_dec = f"{9 + tens + ones:02d}"
    return f"T09{temp_c:02d}00{suffix_dec}Z"


def _validate_step(step: int) -> None:
    if not isinstance(step, int):
        raise ValueError("Step must be an integer.")
    if not (1 <= step <= 6):
        raise ValueError("Step must be in range 1..6.")


def _validate_temp(temp_c: int) -> None:
    if not isinstance(temp_c, int):
        raise ValueError("Temperature must be an integer.")
    if not (30 <= temp_c <= 80):
        raise ValueError("Temperature must be in range 30..80 °C.")