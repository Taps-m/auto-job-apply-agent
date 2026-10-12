# Personal Job Assistant — V 0.1.0

Double-click **Start Assistant.cmd**, or run `npm start`, then open http://127.0.0.1:8765. Keep the terminal open while using the app. Requires Node.js 18 or later. All state is stored locally in `data/state.json`.

This standalone foundation supports saved user preferences, configurable local review intervals, job entry with duplicate URL prevention, salary screening, confirmed application records, outcome/call notes, activity history, and downloadable period reports. Undisclosed salaries are allowed for subsequent matching checks. Reports count confirmed submissions and outcomes from the same submission cohort.

## Integration status

Portal search and automatic submission are **not implemented** in this version. Local scheduled reviews do not access portals. No AI matching or automatic CV generation runs yet. Gemini is intentionally deferred. Gmail is not connected; future integration requires explicit OAuth authorization. Actual submission requires a verified supported portal route, complete screening answers and durable confirmation of success. Unknown required facts must ask the user rather than fabricate answers.

## Release numbering

Every release uses **V x.y.z**. V 0.1.0 is the standalone tracker foundation. Future integrations and CV workflows will increment the version. Maintain CHANGELOG.md with each release.

## Data

Data is stored in plaintext locally. Do not publish `data/`, CVs, credentials, or OAuth tokens to GitHub. No desktop files or scheduled Windows tasks are installed by this version. No cloud credentials are needed. Backup `data/state.json` while the application is stopped.
