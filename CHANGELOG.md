# Changelog

## V 0.4.4
- Record the user's weekly application-report preference. Automated report generation and delivery remain pending.

## V 0.4.3
- Record daily search with manual runs, match threshold ≥80%, and no daily application cap in application_policy.json.
- Keep required screening answers, matching preferences, permitted routes and duplicate checks as submission conditions. Connector execution remains pending.

## V 0.4.2
- Remove the conversation selector and New button from Gemini; retain the active chat and backend conversation storage.

## V 0.4.1
- Display the Gemini panel and mobile Assistant toggle on Home only.
- Let other pages use the freed horizontal space; contextual assistant actions open Home while retaining the original request context.

## V 0.4.0
- Simplify Profile & resume to resume upload/replacement, optional photo and professional links only.
- Preserve existing profile facts and matching preferences; saving links cannot erase career data.
- Move search preferences to Settings; retain existing resume/document backend workflows.
- Store normalized profile photos locally with file validation and removal controls; privacy deletion also removes photos and links.

## V 0.3.3
- Correct the overly muted background with more visible blue/violet ribbons, lower-left purple and upper-right turquoise lighting, and subtle texture.
- Reduce panel opacity so ambient colors remain visible through glass surfaces; preserve Inter typography and compact layouts.
- Version the background URL as well as stylesheet/script URLs to avoid cached styling.

## V 0.3.2
- Apply the user-specified Inter typography scale with a locally hosted variable font and its SIL Open Font License.
- Add a lightweight original SVG background with deep blue base, diagonal purple/cyan ribbons, ambient glows and subtle star texture.
- Adjust glass panel gradients, headings and chat typography while retaining compact cards and the 170px empty state.
- Use the supplied midnight navy palette, component gradients, 16px glass blur, lower-left violet and upper-right turquoise lighting, restrained borders and selective cyan highlights.

## V 0.3.1
- Refine the current Python frontend with a dark navy theme, controlled central purple glow and subtle turquoise lighting behind Gemini.
- Limit the home empty state to 170px and use compact reusable vacancy cards with one View Details action.
- Show fit scores only when computed; keep detailed source, eligibility and application controls in job details.
- Use a short conversational welcome, bottom composer and explicit disconnected Gemini setup state.
- Disable chat and contextual prompts until a key is configured; preserve conversation history and approved-action controls.
- Keep navigation actions in their existing modules and version frontend asset URLs to refresh cached files.

## V 0.3.0
- Rebuild as a single Python app (FastAPI + SQLite) implementing the first slice of FRS v1.0; remove the Node.js server and the separate `dashboard.html` prototype.
- Transparent weighted match scoring with per-factor reasons, data coverage, exclusions and skills gaps; salary rules carried over.
- Natural-language and filtered job search, duplicate merging across sources, shortlist and link status checks.
- Application workflow: draft, readiness, preview, explicit approval, employer page, confirmed submission, outcomes, follow-ups and timeline.
- Gemini assistant with validated tool calling, context-aware suggestions, conversation history, usage tracking and approval-gated proposals. No submission tool.
- Profile, work history, preferences, resume upload, settings and delete-all-data.
- One module per function (`app/modules/<name>/router.py` + `service.py`), registered by `main.py` from `config/app.json`; settings, defaults, rules and prompts live in `config/*.json`.
- 28 automated tests, including a check that `main.py` holds no routes or settings.

## V 0.2.2
- Remove duplicate Tapomoy avatar/name from the top-right header; keep the main greeting.

## V 0.2.1
- Match reference layout proportions: full-width header, left sidebar, central jobs area and taller right-side assistant panel.
- Remove extra homepage metrics, status banner and activity panel from the reference layout; retain reports in Applications and controls in Settings.
- Preserve real-data job rendering without sample cards. Discovery integration remains pending.

## V 0.2.0
- Redesign active dashboard using the user's neon glass reference: dark navy background, cyan/purple borders, sidebar, job cards, metrics and Gemini panel.
- Responsive desktop, tablet and mobile layout with local job search and functional navigation.
- Preserve job entry, outcome tracking, schedules, local reviews and downloadable reports.
- Show real tracked jobs and honest empty states; no fabricated listings or match percentages.
- Add outcome dialog with CV version and notes; website and GitHub remain prominent in preferences.
- Gemini panel runs local helper actions and clearly states AI is disconnected.
- Browser verification and test execution pending due to tool process-launch failure.

## V 0.1.2
- Save personal website and recruiter-facing showcase preference.
- Display website and GitHub links together in the dashboard.
- Document website inclusion in future CV and application workflows.

## V 0.1.1
- Salary screening uses ₹20 LPA total CTC for Google, Microsoft, Meta, Amazon, Apple and Netflix; other employers retain ₹25 LPA.
- Save GitHub profile and project showcase preference for future CV/application integrations.
- Add salary boundary and employer-name test. Execution pending due to tool process-launch failure.

## V 0.1.0
- Standalone local Windows dashboard and launcher.
- Saved role, salary, location, seniority and notice preferences.
- Configurable local review interval and report window.
- Job tracking, confirmed submission/outcome recording and response metrics.
- Explicit integration status; Gemini deferred, Gmail and portal connectors pending.
