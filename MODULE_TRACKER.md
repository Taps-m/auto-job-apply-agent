# Personal Job Assistant — Module Tracker

Current release: **V 0.1.0**

Check an item only after implementation and relevant verification. Update this tracker with each change and commit it with the related work. Portal submission must remain disabled until a permitted route is verified.

## 1. Standalone application
- [x] Local Node.js server and browser dashboard
- [x] Windows launch script
- [x] Bind server to localhost
- [x] Persistent local state with atomic file replacement
- [ ] Browser visual and end-to-end verification
- [ ] Optional desktop shortcut installation
- [ ] Optional automatic launch at Windows sign-in

## 2. Candidate profile and matching
- [x] Read supplied CV for qualifications and experience
- [x] Record user-approved role areas, equal priorities and seniority
- [x] Record India metros, all work arrangements, two-month notice
- [x] Record ₹25 LPA minimum total CTC; allow undisclosed salaries
- [x] Basic salary screening
- [ ] Store structured, verified CV facts locally
- [ ] Clarify work authorization when an application requires it
- [ ] Role, experience, location and seniority matching
- [ ] Explain match scores and unmet requirements

## 3. Discovery connectors
- [ ] HiringCafe: verify permitted access, implement and test
- [ ] Welcome to the Jungle: verify permitted access, implement and test
- [ ] Himalayas: verify permitted access, implement and test
- [ ] Y Combinator Work at a Startup: verify permitted access, implement and test
- [ ] Glassdoor: verify permitted access, implement and test
- [ ] LinkedIn: supported discovery/manual application workflow
- [ ] ZipRecruiter: verify permitted access, implement and test
- [x] Prevent duplicate tracked job URLs
- [ ] Detect duplicate vacancies across portals
- [ ] Handle expired jobs, pagination, retries and rate limits

## 4. CV tailoring and Gemini — integration deferred by user
- [x] Record authorization to reword/reorder verified CV content
- [ ] Secure Gemini credential configuration
- [ ] Model selection and usage/budget controls
- [ ] Generate job-specific CVs using only verified facts
- [ ] Preserve original CV and record changes
- [ ] Version and render tailored CV files
- [ ] Validate factual consistency and document layout
- [ ] Suggest improvements from recorded outcomes without inventing causation

## 5. Applications
- [x] Manual job queue
- [x] Record actual submissions with confirmation
- [x] Maintain outcome history and optional CV version field
- [ ] Verify portal-specific permitted submission routes
- [ ] Screening-answer fact store
- [ ] Ask user about unknown required answers
- [ ] Automatic submission for eligible, supported routes
- [ ] Save submission receipt and exact CV used
- [ ] Prevent repeat submissions and ambiguous retry duplicates
- [ ] Daily limits, pause/resume and emergency stop

## 6. Gmail and recruiter calls
- [x] Record requested Gmail account: tapomoy400@gmail.com
- [x] Manual outcome/call notes
- [ ] Gmail OAuth with minimal required scopes
- [ ] Secure token storage and disconnect/revocation
- [ ] Link recruiter messages to the correct application
- [ ] Handle uncertain classifications through review
- [ ] Track response/interview dates and call counts separately

## 7. Schedule and reports
- [x] User-editable local check interval
- [x] Local review timer while app is running
- [x] User-editable report period
- [x] Downloadable JSON period report
- [x] Confirmed-submission, response and interview metrics
- [x] Response rate excludes unconfirmed submissions
- [ ] Scheduled portal discovery
- [ ] Automatic periodic report generation and notification
- [ ] Windows scheduled task and missed-run handling
- [ ] Conversion comparison by portal, role and CV version

## 8. Verification and release management
- [x] Use V x.y.z release numbering
- [x] Maintain changelog
- [x] Three unit tests pass: conversion counting and salary screening
- [x] Initialize local Git repository
- [x] Ignore personal data, logs and secrets in Git
- [ ] Commit V 0.1.0 source and tracker
- [ ] Connect GitHub repository under Taps-m
- [ ] Push commits to GitHub
- [ ] Integration and persistence tests
- [ ] Security review before external account connections

## Open setup decisions
- GitHub repository name and public/private visibility
- Gmail OAuth setup
- Gemini integration deferred until standalone validation
- Supported access and application capability of each portal

## Known limits of V 0.1.0
No portal search, automatic applications, AI CV tailoring or Gmail reading is operational yet. Scheduled local reviews only log that connectors are unavailable. Outcome reports rely on manually recorded data. This is a standalone foundation, not the completed agent.
