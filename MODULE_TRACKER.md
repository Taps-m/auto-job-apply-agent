# Personal Job Assistant — Module Tracker

## Background correction — V 0.3.3
- [x] Strengthen reference-inspired violet/cyan lighting and diagonal texture
- [x] Verify rendered jobs page and locally loaded Inter font
- [x] Verify desktop/mobile layout has no horizontal overflow


Current release: **V 0.3.3** (Python/FastAPI + SQLite). Check an item only after implementation and verification.

## Reference background and typography — V 0.3.2
- [x] Verify locally hosted Inter font loads and specified type scale (browser computed styles)
- [x] Verify diagonal blue/purple/turquoise background and glass surfaces (desktop/mobile screenshots)

## Frontend refinement — V 0.3.1
- [x] Verify compact 170px home empty state
- [x] Verify concise chat welcome, bottom composer and disconnected setup state
- [x] Verify contextual chat prompts and retain existing module navigation
- [x] Verify compact job cards and computed-only fit scores (browser-only fixtures, no saved sample jobs)
- [x] Verify ambient lighting at desktop and mobile sizes; no horizontal overflow
- [x] JavaScript syntax check and all 33 current backend tests pass

## Platform
- [x] FastAPI backend, localhost only, host/origin checks, strict CSP
- [x] SQLite schema following the FRS table design (PostgreSQL-ready)
- [x] One-time import of earlier `data/state.json` preferences
- [x] Windows launcher with first-run setup
- [x] One module per function; `main.py` only registers modules listed in `config/app.json`
- [x] All settings, defaults, rules and prompts in `config/*.json`
- [x] Automated tests (scoring, API workflow, agent controller, structure)
- [ ] Optional desktop shortcut and launch at sign-in

## M01 Home dashboard
- [x] FR-101 greeting · FR-102 top 3 · FR-103 score · FR-104 summary · FR-105 open job · FR-106 see all · FR-107 edit preferences
- [ ] FR-108 fetch new listings (needs discovery sources)

## M02 Job search & matches
- [x] FR-201 natural-language search (rule-based; Gemini via assistant)
- [x] FR-202–206 keyword, location/remote, salary, seniority, company include/exclude filters
- [x] FR-208 duplicate detection and merge · FR-209 transparent weighted ranking · FR-210 shortlist
- [x] FR-211 posted/retrieved/verified dates · FR-212 link status check
- [ ] FR-207 multi-source discovery: HiringCafe, Welcome to the Jungle, Himalayas, Work at a Startup, Glassdoor, LinkedIn, ZipRecruiter — verify permitted access per site first

## M03 Job details & fit
- [x] FR-301–305 overview, responsibilities, skills, fit breakdown, skills gap
- [x] FR-307 source link · FR-308 send job context to Gemini · FR-309 start application
- [ ] FR-303 AI extraction of skills from description (currently keyword detection, marked as estimate)
- [x] FR-306 career relevance via assistant

## M04 Gemini agent
- [x] FR-401–405 conversation, job and profile context, recommendations, comparison
- [x] FR-406–408 resume suggestions, interview questions, skill-gap guidance (by prompt)
- [x] FR-409 contextual suggestions · FR-410 history · FR-411 validated tool calling
- [x] FR-412 rate-limit/key/model error handling · FR-413 approval for changes · FR-414 verified vs recommendation labelling
- [ ] Streaming responses

## M05 Applications
- [x] FR-501–504 start, readiness, preview, explicit approval
- [x] FR-505 open employer page (not counted as submission)
- [x] FR-506–510 status tracking, timeline, duplicate warning, follow-ups, confirmation capture
- [ ] Automatic submission through verified, permitted portal routes
- [ ] Screening-answer fact store reused across applications

## M06 Resume & documents
- [x] FR-601 PDF/DOCX upload with content check · FR-603 master resume · FR-608 preview
- [ ] FR-602 parsing · FR-604 tailored resume · FR-605 ATS checks · FR-606 cover letter generation
- [ ] FR-607 per-job versions · FR-609 PDF/DOCX export · FR-610 automated fact validation

## M07 Profile & preferences
- [x] FR-701–708 profile, work history, skills, roles, ranked cities, salary rules, industries, exclusions
- [x] FR-710 completeness
- [ ] FR-709 AI-suggested profile updates for approval

## M08 Settings & integrations
- [x] FR-801 key via `.env` only · FR-802 model selection · FR-807 automation level · FR-808 usage and failures
- [x] FR-806 delete all data
- [~] FR-803 source list (display only) · FR-804 search frequency (saved, not scheduled yet)
- [ ] FR-805 notifications · FR-809 accounts (single local user for now)
- [ ] Gmail OAuth with minimal scopes for recruiter-response tracking
