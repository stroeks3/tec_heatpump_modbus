"""Hard-floor checks behind the Repairs notices and the Safety Floor Breach sensor.

Pure functions: no Home Assistant state, no I/O, so the rules can be tested
without an instance. The coordinator owns the clock and the notices; this
module only decides what is in breach.

The floors are empirical values for the RS07V/LF (SAFETY.md). They are checked
here and not enforced in the number entities, which keep the factory ranges on
purpose.
"""
from __future__ import annotations

from dataclasses import dataclass

from .const import (
    SAFETY_DEBOUNCE_S,
    SAFETY_FLOOR_UNITS,
    SAFETY_FLOORS,
    SAFETY_TOLERANCE,
)

ISSUE_INVERTER = "inverter_alarm"
ISSUE_IDS = tuple(f"floor_{key}" for key in SAFETY_FLOORS) + (ISSUE_INVERTER,)

# Values are homeassistant.helpers.issue_registry.IssueSeverity values.
# EV06 is "error", not "critical": critical is kept for the latched inverter
# alarm, which is an actual hardware failure rather than a risky setting.
SEVERITY = {
    "floor_ev06": "error",
    "floor_cm16": "warning",
    "floor_cm13": "warning",
    ISSUE_INVERTER: "critical",
}


@dataclass(frozen=True)
class Breach:
    """One condition that is currently in breach."""

    issue_id: str
    severity: str
    value: float | None = None
    floor: float | None = None
    unit: str | None = None


def evaluate(
    data: dict,
    now: float,
    below_since: dict[str, float],
    *,
    floors: dict[str, float] = SAFETY_FLOORS,
    debounce: float = SAFETY_DEBOUNCE_S,
) -> tuple[dict[str, Breach], set[str]]:
    """Return (breaches in force, issue ids whose input did not read).

    `below_since` maps a register to the monotonic time it was first seen under
    its floor. It is updated in place: set on the first poll under the floor,
    cleared the moment the value is back on or above it.

    A register that did not read (None) is neither a breach nor all clear:
    its id comes back in the second set so the caller can leave whatever it
    already shows alone, and its timer is not touched.
    """
    active: dict[str, Breach] = {}
    unknown: set[str] = set()

    for key, floor in floors.items():
        issue_id = f"floor_{key}"
        value = data.get(key)
        if value is None:
            unknown.add(issue_id)
            continue
        if value < floor - SAFETY_TOLERANCE:
            since = below_since.setdefault(key, now)
            if now - since >= debounce:
                active[issue_id] = Breach(
                    issue_id,
                    SEVERITY[issue_id],
                    round(value, 1),
                    floor,
                    SAFETY_FLOOR_UNITS[key],
                )
        else:
            below_since.pop(key, None)

    # A latched inverter alarm is not something to wait on.
    alarm = data.get("al_inv")
    if alarm is None:
        unknown.add(ISSUE_INVERTER)
    elif alarm:
        active[ISSUE_INVERTER] = Breach(ISSUE_INVERTER, SEVERITY[ISSUE_INVERTER])

    return active, unknown
