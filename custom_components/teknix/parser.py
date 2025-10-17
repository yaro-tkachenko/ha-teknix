from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from .const import IDX


FRAME_PREFIX = "I"
FRAME_SUFFIX = "Z"
SERIAL_KEY = "SerialReceived"


def _extract_frame_from_payload(payload: str) -> Optional[str]:
    p = (payload or "").strip()
    if not p:
        return None

    if p.startswith(FRAME_PREFIX) and p.endswith(FRAME_SUFFIX):
        return p

    try:
        obj = json.loads(p)
    except json.JSONDecodeError:
        return None

    val = obj.get(SERIAL_KEY)
    if isinstance(val, str) and val.startswith(FRAME_PREFIX) and val.endswith(FRAME_SUFFIX):
        return val

    return None


def parse_info_message(payload: str, *, strict: bool = False) -> Optional[Dict[str, Any]]:
    frame = _extract_frame_from_payload(payload)
    if not frame:
        return None
    try:
        return parse_info_frame(frame)
    except ValueError:
        # Silently ignore invalid frames to avoid error logs
        return None


def parse_info_frame(frame: str, *, idx_map: Mapping[str, int] = IDX) -> Dict[str, Any]:
    if not (frame and frame[0] == FRAME_PREFIX and frame[-1] == FRAME_SUFFIX):
        raise ValueError("Invalid frame: must start with 'I' and end with 'Z'.")

    parts = frame[1:-1].split("&")
    try:
        vals: List[int] = [int(x) for x in parts]
    except ValueError:
        # Silently ignore frames with non-integer tokens
        raise ValueError("Non-integer token in frame")

    if not idx_map:
        raise ValueError("IDX mapping is empty.")
    max_needed = max(idx_map.values())
    if len(vals) <= max_needed:
        # Silently ignore frames that are too short
        raise ValueError("Frame too short")

    def g(name: str, default: int = 0) -> int:
        idx = idx_map[name]
        return vals[idx] if 0 <= idx < len(vals) else default

    def deci_to_celsius(v: int) -> float:
        return round(v / 10.0, 1)

    return {
        "boiler_power_state": bool(g("boiler_power_state")),
        "house_target_temp": g("house_target_temp"),
        "tank_target_temp": g("tank_target_temp"),
        "house_heating_active": bool(g("house_heating_active")),
        "tank_heating_active": bool(g("tank_heating_active")),
        "house_heating_step": g("house_heating_step"),
        "tank_heating_step": g("tank_heating_step"),
        "house_loop_temp": deci_to_celsius(g("house_loop_temp")),
        "tank_water_temp": deci_to_celsius(g("tank_water_temp")),
        "raw": vals,
    }