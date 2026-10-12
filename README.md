# Personal Job Assistant — V 0.3.0

A local, single-user job-search agent: it ranks vacancies against your verified career profile, explains each match, walks every application through review and approval, and offers a Gemini assistant that can look things up and propose actions but never submit anything on its own.

Principles: minimal interface, maximum personalisation, controlled automation.

## Run

Double-click **Start Assistant.cmd**. The first run creates `.venv` and installs dependencies; the browser then opens http://127.0.0.1:8765.

Or manually (Python 3.12+):

```
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m app.main
```

Tests: `.venv\Scripts\python -m pytest`

### Gemini

Copy `.env.example` to `.env` and set `GEMINI_API_KEY` (from Google AI Studio). Restart, then choose a model in **Settings**. Without a key everything except the assistant works.

## What it does

| Module | V 0.3.0 |
|---|---|
| Home | Greeting, top 3 eligible matches, application metrics, profile gaps, follow-ups due |
| Jobs & matches | Manual vacancy entry with mandatory source link, natural-language and filtered search, duplicate merging across sources, shortlist, link status check |
| Job details | Source facts, transparent weighted fit score with a reason per factor, skills gap |
| Assistant | Gemini with tool calling over your jobs, profile and applications; context-aware suggested prompts; conversation history; proposals need your approval |
| Applications | Draft → readiness check → preview → your approval → open employer page → confirmed submission → outcome; follow-ups; full timeline; duplicate warning |
| Resume | PDF/DOCX upload, master resume, attach to applications |
| Profile & preferences | Career profile, work history, skills, target roles, ranked cities, salary rules, seniority range, exclusions, scoring weights |
| Settings | Gemini model, API usage, automation level, search frequency, job sources, delete all data |

### Rules built in

- ₹25 LPA total CTC minimum; ₹20 LPA for Google, Microsoft, Meta, Amazon, Apple and Netflix (exact names only). Undisclosed salaries stay eligible unless you turn that off.
- Every job keeps its source link and retrieval time. No sample or invented listings.
- The match score estimates profile compatibility. It is not a chance of selection. Unknown factors are left out and shown as reduced data coverage.
- Opening an employer's page is not a submission. An application is marked submitted only when you confirm it with a reference.
- The assistant gets only the selected job and your approved profile facts, has no submission tool, and every change it proposes waits for your click.

## Not yet built

Automatic discovery from job sites, resume parsing, tailored resume/cover-letter generation and export, Gmail tracking, scheduled searches and notifications. See [MODULE_TRACKER.md](MODULE_TRACKER.md).

## Data

Everything is stored locally in `data/` (SQLite database `assistant.db` and uploaded documents). `data/` and `.env` are ignored by Git. Preferences saved by earlier releases in `data/state.json` are imported once on first start.

## Project layout

```
app/
  main.py            loads config, prepares storage, registers the modules listed in config/app.json
  config.py          reads config/*.json and .env
  core/              db (SQLite schema), security (local-only middleware), errors, text, settings_store
  modules/           one package per function, each with router.py (HTTP) and service.py (logic)
    home/            M01 dashboard
    jobs/            M02 search, vacancies, duplicates, link checks
    matching/        M03 scoring and fit breakdown
    agent/           M04 Gemini: tools.py, gemini.py, chat.py
    applications/    M05 application workflow
    documents/       M06 resumes
    profile/         M07 profile and preferences
    settings/        M08 settings, usage, privacy
    ui/              serves app/static
  static/            single-page interface
config/
  app.json           name, version, host/port, CSP, upload limits, Gemini limits, job sources, enabled modules
  preferences.json   default job preferences (roles, cities, salary rules, weights)
  matching.json      seniority rules, city aliases, skill vocabulary, scoring constants
  agent.json         system prompt, tool schemas, suggested prompts, error messages
tests/
```

To add a module: create `app/modules/<name>/router.py` exposing `router`, then add `<name>` to `modules` in `config/app.json`.
