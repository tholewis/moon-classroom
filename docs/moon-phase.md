---
title: Moon Phase — Developer Reference
description: Architecture, calculator output schema, field mapping, and route reference for the moon-phase Claude Code skill and the Moon Classroom Flask app.
category: reference
version: "1.0"
last_updated: 2026-03-30
audience: developers
---

# Moon Phase — Developer Reference

This document covers two related but distinct components:

1. **The `moon-phase` Claude Code skill** — a project-scoped skill that gives Claude lunar knowledge and a precise calculator during development sessions.
2. **The Moon Classroom app** — a Flask web app that calls the same calculator script as a CLI subprocess to power its interface.

---

## 1. The `moon-phase` Skill

### What it is

The skill lives at `.claude/skills/moon-phase/` in the project root — the standard location for project-scoped Claude Code skills. Claude Code loads it automatically at session start and invokes it whenever a moon-related question arises, or when you invoke it directly with `/moon-phase`.

```
.claude/skills/moon-phase/
├── SKILL.md                   # Skill definition: triggers, workflow, formatting
└── scripts/
    └── moon_calculator.py     # Calculator script Claude runs via Bash tool
```

### SKILL.md

The `SKILL.md` frontmatter tells Claude when and how to use the skill:

```yaml
---
name: moon-phase
description: >
  Provides detailed moon phase information... Use this skill whenever the user
  asks anything about the moon — current phase, upcoming full moon, tides...
---
```

When invoked, the skill instructs Claude to:
1. Run `moon_calculator.py` via the Bash tool to get live data
2. Use `phase_name` directly from the JSON output (never infer it from illumination)
3. Build a response with current phase, upcoming milestones, illumination, and contextual notes

### moon_calculator.py

The skill's calculator is based on Jean Meeus' *Astronomical Algorithms* (2nd ed., Chapter 49). Claude runs it as a shell command:

```bash
# Today
python3 "scripts/moon_calculator.py"

# Specific date
python3 "scripts/moon_calculator.py" "2025-07-04"
```

Output:

```json
{
  "query_date": "March 24, 2026",
  "query_date_iso": "2026-03-24",
  "phase_name": "Waxing Crescent",
  "phase_emoji": "🌒",
  "phase_fraction": 0.1975,
  "illumination_percent": 33.8,
  "direction": "waxing",
  "age_days": 5.8,
  "days_to_next_new_moon": 23.7,
  "synodic_month_days": 29.530588853,
  "upcoming_phases": [
    { "name": "First Quarter", "emoji": "🌓", "date": "March 25, 2026", "iso": "2026-03-25", "time_utc": "13:12 UTC" },
    { "name": "Full Moon",     "emoji": "🌕", "date": "April 1, 2026",  "iso": "2026-04-01", "time_utc": "22:23 UTC" },
    { "name": "Last Quarter",  "emoji": "🌗", "date": "April 9, 2026",  "iso": "2026-04-09", "time_utc": "07:34 UTC" },
    { "name": "New Moon",      "emoji": "🌑", "date": "April 16, 2026", "iso": "2026-04-16", "time_utc": "16:45 UTC" }
  ]
}
```

---

## 2. The Moon Classroom App

### How it uses the calculator

The app calls `scripts/moon_calculator.py` as a CLI subprocess — the interface the script is designed for. This is independent of the skill mechanism; the skill is Claude's tool, not the app's library.

`get_moon_data()` in [app.py](../app.py):

```python
CALCULATOR = os.path.join(os.path.dirname(__file__), "scripts", "moon_calculator.py")

def get_moon_data(year, month, day):
    result = subprocess.run(
        ["python3", CALCULATOR, f"{year}-{month:02d}-{day:02d}"],
        capture_output=True, text=True, check=True
    )
    info = json.loads(result.stdout)
    ...
```

It maps the script's output to the fields the templates and API expect:

| Script field | App field | Notes |
|---|---|---|
| `phase_fraction` | `phase` | 0.0–1.0 |
| `illumination_percent` | `illumination` | 0–100% |
| `age_days` | `age` | days since new moon |
| `phase_name` | `phase_name` | one of 8 named phases |
| `phase_emoji` | `emoji` | moon emoji |
| derived from `upcoming_phases` | `days_to_full` | whole days to next full moon |
| `upcoming_phases` | `upcoming_phases` | next 4 milestone dates with UTC times |

`days_to_full` is derived by finding the Full Moon entry in `upcoming_phases` and computing the difference from the query date:

```python
if info["phase_name"] == "Full Moon":
    days_to_full = 0
else:
    query_date = date(year, month, day)
    for p in info["upcoming_phases"]:
        if p["name"] == "Full Moon":
            days_to_full = (date.fromisoformat(p["iso"]) - query_date).days
            break
```

### Routes

**`GET /`** — renders the homepage for today's date. Passes `moon`, `lesson`, `facts`, and `today` to `index.html`.

**`GET /learn`** — renders the long-form educational article. Passes `moon` and `today` to `learn.html`. The live moon data is embedded in the Moon Phases section as a callout card.

**`GET /api/moon?date=YYYY-MM-DD`** — returns full moon data as JSON, including the `lesson` from `PHASE_LESSONS` and all `upcoming_phases`. Defaults to today if no date is provided. Returns `400` for invalid date formats.

### Static content

Two dictionaries in `app.py` provide educational content keyed by `phase_name`:

- **`PHASE_LESSONS`** — `description`, `visibility`, `science`, and `cultural_note` for each of the 8 phases. Injected into templates at render time and included in the API response.
- **`MOON_FACTS`** — a list of standalone fact objects (`title` + `fact`) shown in the facts grid.

---

## 3. Project structure

```
Moon-Classroom/
├── app.py                          # Flask app — routes and static content
├── scripts/
│   └── moon_calculator.py          # Calculator script (used by app via subprocess)
├── templates/
│   ├── index.html                  # Homepage Jinja2 template
│   └── learn.html                  # Long-form education article template
├── static/
│   ├── css/style.css
│   └── js/main.js
├── .claude/
│   └── skills/
│       └── moon-phase/
│           ├── SKILL.md            # Claude Code skill definition
│           └── scripts/
│               └── moon_calculator.py  # Calculator script (used by Claude via Bash)
├── docs/
│   ├── moon-phase.md               # This document
│   ├── ai_friendly_docs.md         # Documentation standards for this project
│   ├── screenshot.png              # Homepage screenshot
│   └── screenshot-learn.png        # Learn page screenshot
├── Dockerfile                      # Cloud Run container definition
├── .dockerignore
├── CLAUDE.md                       # Claude Code project guidance
├── llms.txt                        # AI-optimized project summary
└── requirements.txt
```

> **Note:** `moon_calculator.py` exists in two locations intentionally. The copy in `scripts/` is the app's CLI dependency. The copy in `.claude/skills/moon-phase/scripts/` is the skill's resource — what Claude runs when the skill is invoked. Keeping them separate means the app and the skill can evolve independently.

---

## 4. Accuracy and limitations

`moon_calculator.py` anchors its calculation to a verified new moon (2000-01-06 18:14 UTC, JD 2451549.757) and uses the precise synodic month (29.530588853 days). It does not account for:

- The Moon's elliptical orbit (minor effect on exact phase timing)
- Time zones (upcoming phase times are UTC only)

For higher-precision applications, see [ephem](https://rhodesmill.org/pyephem/) or [astropy](https://www.astropy.org/).
