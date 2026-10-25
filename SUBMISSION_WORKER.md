# Application prototype — V 0.6.4

## Verified

- [x] Persistent queue, eligibility >=80%, duplicate protection and crash recovery.
- [x] Start/Stop controls on Applications, using a local Edge profile.
- [x] CV-first upload, required text and radio answers, optional fields skipped.
- [x] Dover label discovery checked against the live IOMETE form.
- [x] Actual worker started from dashboard and prepared IOMETE through terms review.
- [x] Default preparation mode cannot click Apply.
- [ ] Confirm a real employer submission.
- [ ] Validate other portals and employer form adapters.

## Current operation

The dashboard worker is preparation-only. It uploads the CV, fills required fields
from verified application answers, and leaves the employer page open for review.
It never clicks Apply in this mode. The final agreement and submission remain
with the user. It can observe a confirmation on the same employer URL after
manual submission and then update the application count.

Open http://127.0.0.1:8765/#/applications to view queue status. Start worker opens
Edge with its own local profile. Existing Firefox and in-app-browser sessions
are not copied. Stop is checked between operations and before submission.
A blocked page stays open; close it to move to the next queued job.

On 25 October 2026, the running worker reached IOMETE's terms-review state after
CV attachment and required-field completion. No confirmed submission has been
recorded. Thirteen isolated tests cover matching, duplicates, crash recovery,
required answers, single CV upload, optional-field skipping, confirmation handling,
and the default no-submission behavior. These tests are not a claim that all
portals work. Private answers, browser sessions and evidence remain under ignored
data/ and tmp/ directories.
