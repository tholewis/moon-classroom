from flask import Flask, render_template, jsonify, request
from datetime import datetime, date
import math

app = Flask(__name__)


def calculate_moon_phase(year, month, day):
    """Calculate moon phase data for a given date.
    Returns phase (0-1), illumination (0-100), age in days, phase name, and days to next full moon.
    """
    if month < 3:
        year -= 1
        month += 12

    c = 365.25 * year
    e = 30.6 * month
    jd = c + e + day - 694039.09
    total_phase = jd / 29.5305882
    phase = total_phase - math.floor(total_phase)

    age = phase * 29.53
    illumination = abs(math.sin(math.pi * phase) * 100)

    if phase < 0.0625 or phase > 0.9375:
        phase_name = "New Moon"
        emoji = "🌑"
    elif phase < 0.1875:
        phase_name = "Waxing Crescent"
        emoji = "🌒"
    elif phase < 0.3125:
        phase_name = "First Quarter"
        emoji = "🌓"
    elif phase < 0.4375:
        phase_name = "Waxing Gibbous"
        emoji = "🌔"
    elif phase < 0.5625:
        phase_name = "Full Moon"
        emoji = "🌕"
    elif phase < 0.6875:
        phase_name = "Waning Gibbous"
        emoji = "🌖"
    elif phase < 0.8125:
        phase_name = "Last Quarter"
        emoji = "🌗"
    else:
        phase_name = "Waning Crescent"
        emoji = "🌘"

    days_to_full = ((0.5 - phase + 1) % 1) * 29.53

    return {
        "phase": round(phase, 4),
        "illumination": round(illumination, 1),
        "age": round(age, 1),
        "phase_name": phase_name,
        "emoji": emoji,
        "days_to_full": round(days_to_full, 1),
    }


MOON_FACTS = [
    {"title": "Distance from Earth", "fact": "The Moon is about 384,400 km (238,855 miles) from Earth on average — about 30 Earths lined up side by side."},
    {"title": "Lunar Month", "fact": "A complete lunar cycle (new moon to new moon) takes about 29.5 days, known as a synodic month."},
    {"title": "Tidal Locking", "fact": "The Moon is tidally locked to Earth — we always see the same side because it rotates once per orbit."},
    {"title": "Surface Temperature", "fact": "The Moon's surface ranges from -173°C (-280°F) at night to 127°C (260°F) during the day."},
    {"title": "Moonquakes", "fact": "The Moon experiences moonquakes caused by tidal stresses from Earth's gravity and cooling of the lunar interior."},
    {"title": "No Atmosphere", "fact": "The Moon has virtually no atmosphere, which is why the sky is always black from its surface."},
    {"title": "Origin Theory", "fact": "The leading theory for the Moon's origin is the 'Giant Impact Hypothesis' — a Mars-sized body collided with early Earth."},
    {"title": "Effect on Tides", "fact": "The Moon's gravity is the primary cause of Earth's ocean tides, creating two tidal bulges as Earth rotates."},
]

PHASE_LESSONS = {
    "New Moon": {
        "description": "The Moon is between Earth and the Sun. The illuminated side faces away from us — we see the dark side.",
        "visibility": "Not visible in the night sky.",
        "cultural_note": "Many cultures use the new moon to mark the beginning of a lunar month.",
        "science": "Solar and lunar tides align during new moon, creating stronger 'spring tides'.",
    },
    "Waxing Crescent": {
        "description": "A small sliver of the Moon's right side becomes visible as it moves away from the Sun.",
        "visibility": "Visible low in the western sky just after sunset.",
        "cultural_note": "The crescent moon is a symbol used in many world religions and national flags.",
        "science": "The lit portion grows (waxes) each night as the Moon moves around Earth.",
    },
    "First Quarter": {
        "description": "The Moon has completed one quarter of its orbit. Exactly half of the visible face is lit.",
        "visibility": "High in the sky at sunset, sets around midnight.",
        "cultural_note": "Called 'first quarter' because the Moon has traveled one quarter of its orbit.",
        "science": "The terminator — the line between light and dark — is straight, and lunar craters are most visible here.",
    },
    "Waxing Gibbous": {
        "description": "More than half the Moon is lit and the illuminated area continues to grow.",
        "visibility": "Rises in the afternoon, visible for most of the night.",
        "cultural_note": "'Gibbous' comes from Latin 'gibbosus' meaning hump-backed.",
        "science": "Shadows are shorter near the terminator, making the surface look smoother than at quarter phases.",
    },
    "Full Moon": {
        "description": "Earth is between the Sun and Moon — the entire Earth-facing side is illuminated.",
        "visibility": "Rises at sunset, visible all night long, sets at sunrise.",
        "cultural_note": "Full moons have names in many traditions: Harvest Moon, Wolf Moon, Strawberry Moon, and more.",
        "science": "During a full moon, lunar opposition surge makes the Moon appear extra bright due to retroreflection.",
    },
    "Waning Gibbous": {
        "description": "Past full moon, the lit portion begins to shrink from the right side.",
        "visibility": "Rises after sunset, visible through the late night and into the morning.",
        "cultural_note": "Many farmers historically used the waning moon as a signal for harvesting crops.",
        "science": "Waning means the illuminated fraction is decreasing each night.",
    },
    "Last Quarter": {
        "description": "The Moon has completed three quarters of its orbit. The left half is now lit.",
        "visibility": "Rises around midnight, visible through the morning.",
        "cultural_note": "Also called the 'third quarter' moon — three-quarters of the orbit is complete.",
        "science": "The terminator is again straight, but now the opposite side is lit compared to First Quarter.",
    },
    "Waning Crescent": {
        "description": "A thin crescent remains as the Moon approaches new moon and the start of a new cycle.",
        "visibility": "Visible low in the eastern sky just before sunrise.",
        "cultural_note": "Called the 'old moon' or 'balsamic moon' in some traditions — a time of rest and reflection.",
        "science": "The Moon is moving back toward alignment with the Sun, completing its 29.5-day synodic cycle.",
    },
}


@app.route("/")
def index():
    today = date.today()
    moon_data = calculate_moon_phase(today.year, today.month, today.day)
    lesson = PHASE_LESSONS.get(moon_data["phase_name"], {})
    return render_template("index.html", moon=moon_data, lesson=lesson, facts=MOON_FACTS, today=today.isoformat())


@app.route("/api/moon")
def moon_api():
    date_str = request.args.get("date", date.today().isoformat())
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    moon_data = calculate_moon_phase(d.year, d.month, d.day)
    lesson = PHASE_LESSONS.get(moon_data["phase_name"], {})
    moon_data["lesson"] = lesson
    moon_data["date"] = date_str
    return jsonify(moon_data)


if __name__ == "__main__":
    app.run(debug=True, port=5050)
