# Moon Phase — Developer Reference

This document covers two related but independent components:

1. **The `moon-phase` Claude skill** — a bundled skill file that gives Claude the ability to answer lunar questions using a precise astronomical calculator.
2. **The Moon Classroom app calculator** — a lightweight implementation inside `app.py` that powers the web interface.

---

## 1. The `moon-phase` Skill

### What it is

The skill is a `.skill` file (a ZIP archive) located at:

```
~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/
  └── <session-id>/
        └── <plugin-id>/
              └── skills/skill-creator/moon-phase.skill
```

It contains two files:

```
moon-phase/
├── SKILL.md                      # Skill definition — triggers, workflow, formatting rules
└── scripts/moon_calculator.py    # Python calculator script
```

### SKILL.md

`SKILL.md` is the skill's instruction file. It tells Claude:

- **When to activate** — any message containing words like "moon", "lunar", "full moon", "new moon", "moonrise", "tides", or requests about night sky visibility.
- **What to do** — run `moon_calculator.py` via the Bash tool to get real data before responding, then build a response that includes the current phase, upcoming milestone dates, illumination percentage, and contextual information based on what the user asked.
- **How to format** — lead with the phase emoji and name, keep a warm tone, include an upcoming phases table.
- **Phase boundary rule** — always use `phase_name` from the script output directly; never infer phase from illumination alone (e.g. 43% illumination the day before First Quarter is still "Waxing Crescent").

### moon_calculator.py

The script implements the algorithm from Jean Meeus' *Astronomical Algorithms* (2nd ed., Chapter 49). It is significantly more precise than the simplified approach used in `app.py`.

**Usage:**

```bash
# Today
python3 moon_calculator.py

# Specific date
python3 moon_calculator.py 2025-07-04
```

**Output (JSON):**

```json
{
  "query_date": "March 24, 2026",
  "query_date_iso": "2026-03-24",
  "phase_name": "Waxing Crescent",
  "phase_emoji": "🌒",
  "phase_fraction": 0.1732,
  "illumination_percent": 30.4,
  "direction": "waxing",
  "age_days": 5.5,
  "days_to_next_new_moon": 24.0,
  "synodic_month_days": 29.530588853,
  "upcoming_phases": [
    { "name": "First Quarter", "emoji": "🌓", "date": "March 30, 2026", "iso": "2026-03-30", "time_utc": "02:17 UTC" },
    { "name": "Full Moon",     "emoji": "🌕", "date": "April 6, 2026",  "iso": "2026-04-06", "time_utc": "18:00 UTC" },
    { "name": "Last Quarter",  "emoji": "🌗", "date": "April 13, 2026", "iso": "2026-04-13", "time_utc": "10:52 UTC" },
    { "name": "New Moon",      "emoji": "🌑", "date": "April 20, 2026", "iso": "2026-04-20", "time_utc": "00:11 UTC" }
  ]
}
```

**How the calculator works:**

| Step | What it does |
|---|---|
| `to_jd(dt)` | Converts the input date to a Julian Date — a continuous day count used in astronomy |
| `moon_phase_fraction(jd)` | Measures elapsed days since a known new moon (2000-01-06 18:14 UTC, JD 2451549.757) and divides by the synodic month (29.5306 days) to get a 0.0–1.0 fraction |
| `illumination_fraction(phase)` | Applies `(1 − cos(2π × phase)) / 2` — gives 0% at new moon, 50% at quarters, 100% at full moon |
| `phase_name_and_emoji(phase)` | Maps the fraction to one of 8 named phases using tighter boundaries than the app (e.g. First Quarter spans 0.2292–0.2708 rather than equal eighths) |
| `next_phase_date(jd, target)` | Estimates when the next milestone (new/quarter/full) occurs, then refines it by scanning in 30-minute steps over a ±3-day window |
| `get_upcoming_phases(jd)` | Calls `next_phase_date` for all four milestones and returns them sorted by date |

---

## 2. The Moon Classroom App Calculator

`calculate_moon_phase(year, month, day)` in [app.py](../app.py) is a self-contained implementation that powers both the web page and the `/api/moon` endpoint. It uses no external libraries.

**Algorithm summary:**

```python
# Normalize Jan/Feb as months 13–14 of the prior year
if month < 3:
    year -= 1
    month += 12

# Compute a simplified Julian Day offset anchored to a known new moon
jd = 365.25 * year + 30.6 * month + day - 694039.09

# Extract fractional cycle position (0.0–1.0)
phase = (jd / 29.5305882) % 1

# Illumination and age
illumination = (1 - cos(2π × phase)) / 2 × 100
age = phase × 29.53

# Days until next full moon (phase 0.5), wrapping correctly
days_to_full = ((0.5 - phase + 1) % 1) * 29.53
```

**Return value:**

```python
{
    "phase":        float,   # 0.0–1.0
    "illumination": float,   # 0–100%
    "age":          float,   # days since new moon
    "phase_name":   str,     # one of 8 named phases
    "emoji":        str,
    "days_to_full": float,
}
```

---

## 3. How They Differ

| | Skill (`moon_calculator.py`) | App (`app.py`) |
|---|---|---|
| **Algorithm basis** | Jean Meeus *Astronomical Algorithms* | Simplified Julian Date approximation |
| **Phase anchor** | Verified new moon (Jan 6, 2000 18:14 UTC) | Empirical constant (694039.09) |
| **Synodic month** | 29.530588853 days | 29.5305882 days |
| **Phase boundaries** | Astronomically proportioned (wider for crescents, narrower for quarters) | Equal eighths (0.125 each) |
| **Upcoming milestones** | Yes — next 4 milestone dates with UTC times | No |
| **Wax/wane direction** | Yes (`direction` field) | No |
| **Date/time aware** | Full UTC datetime | Date only |
| **Output format** | JSON to stdout | Python dict |
| **Dependencies** | Python stdlib only | Python stdlib only |

Both use the same illumination formula: `(1 − cos(2π × phase)) / 2`.

---

## 4. How the App Uses the Skill's Output Indirectly

The app does not call `moon_calculator.py` at runtime. However, the skill and the app share the same data model — both produce a `phase_name` that maps to entries in `PHASE_LESSONS` in `app.py`. If you wanted to replace the app's calculator with the skill's more precise version, the integration would be:

```python
import subprocess, json

def calculate_moon_phase(year, month, day):
    result = subprocess.run(
        ["python3", "/path/to/moon_calculator.py", f"{year}-{month:02d}-{day:02d}"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    return {
        "phase":        data["phase_fraction"],
        "illumination": data["illumination_percent"],
        "age":          data["age_days"],
        "phase_name":   data["phase_name"],
        "emoji":        data["phase_emoji"],
        "days_to_full": next(
            (p for p in data["upcoming_phases"] if p["name"] == "Full Moon"), {}
        ).get("iso", ""),
    }
```

This would add upcoming milestone dates and UTC-accurate phase boundaries to the app while keeping the existing template and API interface unchanged.
