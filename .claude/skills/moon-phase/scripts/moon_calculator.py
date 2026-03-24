#!/usr/bin/env python3
"""
Moon phase calculator using astronomical algorithms.
Reference: Jean Meeus, "Astronomical Algorithms" (2nd ed.)

Usage:
    python3 moon_calculator.py              # today
    python3 moon_calculator.py 2025-07-04   # specific date (YYYY-MM-DD)

Outputs JSON with current phase info and upcoming milestones.
"""

import json
import math
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Julian Date helpers
# ---------------------------------------------------------------------------

def to_jd(dt: datetime) -> float:
    """Convert a datetime (UTC) to Julian Date."""
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn + (dt.hour - 12) / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0


def jd_to_datetime(jd: float) -> datetime:
    """Convert Julian Date to UTC datetime."""
    jd = jd + 0.5
    z = int(jd)
    f = jd - z
    if z < 2299161:
        a = z
    else:
        alpha = int((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - alpha // 4
    b = a + 1524
    c = int((b - 122.1) / 365.25)
    d = int(365.25 * c)
    e = int((b - d) / 30.6001)

    day = b - d - int(30.6001 * e)
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715

    frac = f
    hour = int(frac * 24)
    frac = frac * 24 - hour
    minute = int(frac * 60)
    frac = frac * 60 - minute
    second = int(frac * 60)

    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Moon phase calculation (Meeus, chapter 49)
# ---------------------------------------------------------------------------

SYNODIC_MONTH = 29.530588853  # days


def moon_phase_fraction(jd: float) -> float:
    """
    Return the moon's phase as a fraction 0.0–1.0.
    0 = new moon, 0.25 = first quarter, 0.5 = full, 0.75 = last quarter.
    """
    # Known new moon: 2000-01-06 18:14 UTC → JD 2451549.757
    known_new_moon_jd = 2451549.757
    elapsed = jd - known_new_moon_jd
    phase = (elapsed % SYNODIC_MONTH) / SYNODIC_MONTH
    if phase < 0:
        phase += 1.0
    return phase


def illumination_fraction(phase_fraction: float) -> float:
    """Return the illuminated fraction (0–1) of the moon's disk."""
    return (1 - math.cos(2 * math.pi * phase_fraction)) / 2


def phase_name_and_emoji(phase_fraction: float) -> tuple:
    """Return (name, emoji) for a given phase fraction."""
    p = phase_fraction
    if p < 0.0208 or p >= 0.9792:
        return "New Moon", "🌑"
    elif p < 0.2292:
        return "Waxing Crescent", "🌒"
    elif p < 0.2708:
        return "First Quarter", "🌓"
    elif p < 0.4792:
        return "Waxing Gibbous", "🌔"
    elif p < 0.5208:
        return "Full Moon", "🌕"
    elif p < 0.7292:
        return "Waning Gibbous", "🌖"
    elif p < 0.7708:
        return "Last Quarter", "🌗"
    else:
        return "Waning Crescent", "🌘"


# ---------------------------------------------------------------------------
# Next milestone finder
# ---------------------------------------------------------------------------

TARGET_PHASES = {
    "New Moon":      (0.0,  "🌑"),
    "First Quarter": (0.25, "🌓"),
    "Full Moon":     (0.50, "🌕"),
    "Last Quarter":  (0.75, "🌗"),
}


def next_phase_date(jd_now: float, target_fraction: float) -> datetime:
    """
    Find the next date when the moon reaches a target phase fraction.
    Searches forward in 30-minute steps within ±3 days of estimate.
    """
    current = moon_phase_fraction(jd_now)
    diff = (target_fraction - current) % 1.0
    if diff < 0.005:
        diff += 1.0
    estimate_jd = jd_now + diff * SYNODIC_MONTH

    step = 30 / 1440.0
    search_start = estimate_jd - 3
    search_end = estimate_jd + 3

    best_jd = estimate_jd
    best_diff = 1.0
    jd = search_start
    while jd <= search_end:
        pf = moon_phase_fraction(jd)
        d = abs(pf - target_fraction)
        if d > 0.5:
            d = 1.0 - d
        if d < best_diff:
            best_diff = d
            best_jd = jd
        jd += step

    return jd_to_datetime(best_jd)


def get_upcoming_phases(jd_now: float) -> list:
    """Return the next 4 milestone phases sorted by date."""
    results = []
    for name, (fraction, emoji) in TARGET_PHASES.items():
        dt = next_phase_date(jd_now, fraction)
        results.append({
            "name": name,
            "emoji": emoji,
            "date": dt.strftime("%B %-d, %Y"),
            "iso": dt.strftime("%Y-%m-%d"),
            "time_utc": dt.strftime("%H:%M UTC"),
        })
    results.sort(key=lambda x: x["iso"])
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def moon_info(date_str: Optional[str] = None) -> dict:
    if date_str:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    jd = to_jd(dt)
    phase_frac = moon_phase_fraction(jd)
    illum = illumination_fraction(phase_frac)
    name, emoji = phase_name_and_emoji(phase_frac)

    if 0.0208 <= phase_frac < 0.4792:
        direction = "waxing"
    elif 0.4792 <= phase_frac <= 0.5208:
        direction = "at peak"
    elif 0.9792 <= phase_frac or phase_frac < 0.0208:
        direction = "new"
    else:
        direction = "waning"

    phase_age_days = phase_frac * SYNODIC_MONTH
    days_to_next_new = (1.0 - phase_frac) * SYNODIC_MONTH

    upcoming = get_upcoming_phases(jd)

    return {
        "query_date": dt.strftime("%B %-d, %Y"),
        "query_date_iso": dt.strftime("%Y-%m-%d"),
        "phase_name": name,
        "phase_emoji": emoji,
        "phase_fraction": round(phase_frac, 4),
        "illumination_percent": round(illum * 100, 1),
        "direction": direction,
        "age_days": round(phase_age_days, 1),
        "days_to_next_new_moon": round(days_to_next_new, 1),
        "synodic_month_days": SYNODIC_MONTH,
        "upcoming_phases": upcoming,
    }


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = moon_info(date_arg)
    print(json.dumps(result, indent=2))
