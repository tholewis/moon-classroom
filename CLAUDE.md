# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project overview

Moon Classroom is a Flask web app that teaches users about lunar phases. All moon data comes from a pure-Python calculator script (`scripts/moon_calculator.py`) that implements Jean Meeus' *Astronomical Algorithms*. The calculator is also exposed as a Claude Code skill at `.claude/skills/moon-phase/`.

## Repository layout

```
Moon-Classroom/
├── app.py                              # Flask routes and static educational content
├── scripts/
│   └── moon_calculator.py             # Moon phase calculator (used by the app via subprocess)
├── templates/
│   ├── index.html                     # Homepage (Tonight's Moon, Explorer, Lesson, Facts)
│   └── learn.html                     # Long-form lunar education article
├── static/
│   ├── css/style.css
│   └── js/main.js
├── .claude/
│   └── skills/
│       └── moon-phase/
│           ├── SKILL.md               # Claude Code skill definition
│           └── scripts/
│               └── moon_calculator.py # Skill's own copy of the calculator
├── docs/
│   ├── moon-phase.md                  # Developer reference for the skill and app
│   ├── ai_friendly_docs.md            # Documentation standards for this project
│   └── screenshot*.png
├── Dockerfile                         # For Google Cloud Run deployment
├── .dockerignore
├── requirements.txt                   # flask==3.1.3
└── llms.txt                           # AI-optimized project summary
```

## Running the app

**Prerequisites:** Python 3.9 or later, pip.

```bash
pip install -r requirements.txt
python app.py
# App listens on http://localhost:5050
```

## Key conventions

- The calculator script is the single source of truth for all moon data. Do not hardcode phase names or illumination values.
- `get_moon_data()` in `app.py` is the only place the calculator is called from within the app. All three routes use it.
- `PHASE_LESSONS` and `MOON_FACTS` in `app.py` are the only locations for educational text content. If you add or edit lesson text, do it there — templates receive it via Jinja2 context.
- The calculator exists in two locations intentionally — one for the app (`scripts/`), one for the Claude skill (`.claude/skills/moon-phase/scripts/`). Keep them in sync when making algorithm changes.
- The app runs on port 5050 locally and port 8080 in the Docker container (Cloud Run).

## Documentation standards

All documentation in this project follows the standards in `docs/ai_friendly_docs.md`. When creating or editing docs:
- Use YAML frontmatter with `title`, `description`, `category`, `version`, and `last_updated`
- Define acronyms inline
- Label all code blocks with a language tag
- Show both request and response for API examples
- Be explicit about prerequisites and environment assumptions
