from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from datetime import datetime, date
import os
import re
import json
import subprocess
import anthropic

app = Flask(__name__)

CALCULATOR = os.path.join(os.path.dirname(__file__), "scripts", "moon_calculator.py")

# Load the moon-phase skill instructions at startup
_skill_path = os.path.join(os.path.dirname(__file__), ".claude", "skills", "moon-phase", "SKILL.md")
with open(_skill_path) as _f:
    _skill_raw = _f.read()
# Strip YAML frontmatter
_skill_instructions = re.sub(r"^---.*?---\s*", "", _skill_raw, flags=re.DOTALL).strip()

SYSTEM_PROMPT_BASE = (
    _skill_instructions
    + "\n\n## Topic Scope\n\n"
    "You are Moon Classroom's AI lunar guide. Only discuss topics related to the moon, "
    "lunar phases, astronomy, space, tides, night sky observation, and related subjects. "
    "If the user asks about anything unrelated, warmly let them know that Moon Classroom "
    "focuses on lunar and space topics, and invite them to ask a moon-related question instead."
    "\n\n## Live Moon Data\n\n"
    "Today's moon data has been pre-fetched — you do not need to run the calculator script. "
    "Use the data below directly:\n\n"
)


def get_moon_data(year, month, day):
    """Return moon phase data for the given date using the moon-phase skill calculator."""
    result = subprocess.run(
        ["python3", CALCULATOR, f"{year}-{month:02d}-{day:02d}"],
        capture_output=True, text=True, check=True
    )
    info = json.loads(result.stdout)

    if info["phase_name"] == "Full Moon":
        days_to_full = 0
    else:
        query_date = date(year, month, day)
        days_to_full = 0
        for p in info["upcoming_phases"]:
            if p["name"] == "Full Moon":
                days_to_full = (date.fromisoformat(p["iso"]) - query_date).days
                break

    return {
        "phase":            info["phase_fraction"],
        "illumination":     info["illumination_percent"],
        "age":              info["age_days"],
        "phase_name":       info["phase_name"],
        "emoji":            info["phase_emoji"],
        "days_to_full":     days_to_full,
        "upcoming_phases":  info["upcoming_phases"],
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
    moon_data = get_moon_data(today.year, today.month, today.day)
    lesson = PHASE_LESSONS.get(moon_data["phase_name"], {})
    return render_template("index.html", moon=moon_data, lesson=lesson, facts=MOON_FACTS, today=today.isoformat())


@app.route("/api/moon")
def moon_api():
    date_str = request.args.get("date", date.today().isoformat())
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    moon_data = get_moon_data(d.year, d.month, d.day)
    lesson = PHASE_LESSONS.get(moon_data["phase_name"], {})
    moon_data["lesson"] = lesson
    moon_data["date"] = date_str
    return jsonify(moon_data)


@app.route("/ask")
def ask():
    return render_template("ask.html")


@app.route("/api/ask", methods=["POST"])
def ask_api():
    data = request.get_json()
    question = data.get("question", "").strip()
    history = data.get("history", [])

    if not question:
        return jsonify({"error": "No question provided."}), 400

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY is not configured on the server."}), 500

    moon_result = subprocess.run(
        ["python3", CALCULATOR], capture_output=True, text=True, check=True
    )
    system = SYSTEM_PROMPT_BASE + f"```json\n{moon_result.stdout}\n```"
    messages = history + [{"role": "user", "content": question}]

    def generate():
        client = anthropic.Anthropic(api_key=api_key)
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "False") == "True", port=5050)
