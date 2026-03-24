# Moon Phase Calculation — Developer Reference

This document explains the `calculate_moon_phase()` function in [app.py](../app.py), how it works internally, and how the rest of the project consumes its output.

---

## Overview

`calculate_moon_phase(year, month, day)` takes a calendar date and returns a dictionary describing the Moon's state on that day. It uses no external libraries — only Python's built-in `math` module. The algorithm is a simplified Julian Date approach accurate to within roughly ±1 day.

---

## The Algorithm

### Step 1 — Normalize January and February

```python
if month < 3:
    year -= 1
    month += 12
```

The Julian Date formula treats January and February as months 13 and 14 of the previous year. This normalization step adjusts the input before the calculation.

### Step 2 — Compute a Simplified Julian Day Number

```python
c = 365.25 * year
e = 30.6 * month
jd = c + e + day - 694039.09
```

This produces an offset Julian Day Number — a continuous count of days anchored to a known new moon (`694039.09`). The constants `365.25` (average days in a year) and `30.6` (average days in a month in this approximation) come from the standard simplified JD formula.

### Step 3 — Extract the Fractional Phase

```python
total_phase = jd / 29.5305882
phase = total_phase - math.floor(total_phase)
```

Dividing the JD offset by the synodic month (29.5305882 days) gives the total number of lunar cycles elapsed. Subtracting the integer part leaves a value between `0.0` and `1.0` representing where the Moon sits in its current cycle:

| `phase` value | Position in cycle |
|---|---|
| `0.0` | New Moon |
| `0.25` | First Quarter |
| `0.5` | Full Moon |
| `0.75` | Last Quarter |
| `1.0` | New Moon (next cycle) |

### Step 4 — Derive Moon Age and Illumination

```python
age = phase * 29.53
illumination = (1 - math.cos(2 * math.pi * phase)) / 2 * 100
```

- **Age** is simply the phase fraction scaled to the 29.53-day synodic month.
- **Illumination** uses the cosine formula `(1 - cos(2π × phase)) / 2`, which produces 0% at new moon, 50% at quarter phases, and 100% at full moon — matching observed illumination accurately.

### Step 5 — Map Phase to a Named Stage

The `phase` value is divided into 8 equal segments of 0.125 (one-eighth of the cycle each). The boundaries are centred on each named phase:

```
0.0000 – 0.0625  →  New Moon          🌑
0.0625 – 0.1875  →  Waxing Crescent   🌒
0.1875 – 0.3125  →  First Quarter     🌓
0.3125 – 0.4375  →  Waxing Gibbous    🌔
0.4375 – 0.5625  →  Full Moon         🌕
0.5625 – 0.6875  →  Waning Gibbous    🌖
0.6875 – 0.8125  →  Last Quarter      🌗
0.8125 – 0.9375  →  Waning Crescent   🌘
0.9375 – 1.0000  →  New Moon          🌑  (wraps)
```

New Moon wraps at both ends of the range (`phase < 0.0625 or phase > 0.9375`).

### Step 6 — Days Until Next Full Moon

```python
days_to_full = ((0.5 - phase + 1) % 1) * 29.53
```

`0.5` is full moon in normalised phase units. The expression `(0.5 - phase + 1) % 1` computes the forward distance from the current phase to `0.5`, wrapping correctly through the cycle boundary. Multiplying by `29.53` converts to days.

Examples:
- New Moon (`phase = 0.0`) → `(0.5) % 1 × 29.53 = 14.8 days`
- Full Moon (`phase = 0.5`) → `(1.0) % 1 × 29.53 = 0.0 days`
- Waning Gibbous (`phase = 0.6`) → `(0.9) % 1 × 29.53 = 26.6 days`

---

## Return Value

```python
{
    "phase":        float,  # 0.0–1.0, position in lunar cycle
    "illumination": float,  # 0.0–100.0, percentage of visible face lit
    "age":          float,  # days since last new moon (0–29.53)
    "phase_name":   str,    # one of the 8 named phases
    "emoji":        str,    # corresponding moon emoji
    "days_to_full": float,  # days until next full moon
}
```

All floats are rounded: `phase` to 4 decimal places, all others to 1.

---

## How the Project Uses It

### Server-Side Rendering (`/`)

```python
moon_data = calculate_moon_phase(today.year, today.month, today.day)
lesson = PHASE_LESSONS.get(moon_data["phase_name"], {})
return render_template("index.html", moon=moon_data, lesson=lesson, ...)
```

The index route calls `calculate_moon_phase` for today's date and passes the result directly to the Jinja template. The template uses `moon.phase_name`, `moon.illumination`, `moon.age`, `moon.emoji`, and `moon.days_to_full` to render the hero section, lesson cards, and cycle diagram. The `phase` value is stored in a `data-phase` attribute on `#moon-sphere` and read by JavaScript to render the shadow overlay.

### JSON API (`/api/moon`)

```python
moon_data = calculate_moon_phase(d.year, d.month, d.day)
lesson = PHASE_LESSONS.get(moon_data["phase_name"], {})
moon_data["lesson"] = lesson
moon_data["date"] = date_str
return jsonify(moon_data)
```

The API route accepts any date via `?date=YYYY-MM-DD`, runs the same calculation, appends the matching `PHASE_LESSONS` entry, and returns the combined object as JSON. The Date Explorer on the frontend calls this endpoint on demand and renders the result without a page reload.

### Frontend Moon Visual (`main.js`)

```js
const moonSphere = document.getElementById('moon-sphere');
initMoonVisual(parseFloat(moonSphere.dataset.phase));
```

`initMoonVisual(phase)` positions a dark overlay element over the moon sphere CSS graphic to simulate the correct shadow shape:

- **Waxing (`phase ≤ 0.5`)** — the overlay slides rightward, revealing the lit surface from the left.
- **Waning (`phase > 0.5`)** — the overlay grows from the right, covering the lit surface.

---

## Static Content

`calculate_moon_phase` only produces the numeric/named phase data. Two static dictionaries in `app.py` provide the educational content:

- **`PHASE_LESSONS`** — keyed by `phase_name`, contains `description`, `visibility`, `science`, and `cultural_note` for each of the 8 phases.
- **`MOON_FACTS`** — a list of standalone fact objects (`title` + `fact`) rendered in the facts grid.

Both are injected into templates at render time and returned inside the `/api/moon` response.

---

## Accuracy and Limitations

The algorithm is a well-known simplified approximation. It does not account for:

- The Moon's elliptical orbit (varies actual illumination slightly from the cosine model)
- Time of day (treats each date as a single point rather than a moment in time)
- Time zones (calculations are date-based, not timestamp-based)

For educational purposes these differences are negligible. For astronomical precision, use a library such as [ephem](https://rhodesmill.org/pyephem/) or [astropy](https://www.astropy.org/).
