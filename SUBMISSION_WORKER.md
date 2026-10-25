# Submission worker — V 0.6.3

This is an initial implementation, not a verified seven-portal auto-apply release.

- [x] Persistent submission queue with 80% match and preference checks.
- [x] Duplicate protection and uncertain-result states.
- [x] CV-first upload; optional fields and cover letters skipped.
- [x] Home metric changed to confirmed jobs applied.
- [ ] Verify Dover autofill completion and required-field mappings live.
- [ ] Verify employer submission confirmation end to end.
- [ ] Add and validate remaining employer/portal adapters.
- [x] Integrate queue controls and worker lifecycle into the dashboard.

The optional worker uses Microsoft Edge with a dedicated local profile under
ignored `data/application-browser`. It does not import passwords or sessions
from your usual browser. Login is required once in that profile.

The worker waits for native CV autofill and checks required text against saved answers. It does not
claim that upload, a draft, or clicking Apply is a successful submission.
Agreements, verification challenges, missing answers and unknown forms need
attention. Interrupted attempts must be checked at the employer before retrying.

Developer entry point: `python -m app.modules.applications.worker` after
installing `requirements-worker.txt`. An operating-system lock prevents simultaneous workers.
This prototype is not enabled automatically by the application scheduler.

## Use

Open Applications to start or stop the worker. Open an application detail to queue its verified Dover employer URL. Save answers using the exact field labels (for example `First Name`) in the existing application editor. The worker opens Edge; attention items stay visible until you resolve or close that tab. Stop takes effect between operations and before submit.

Eight isolated queue/worker tests pass. Live autofill, employer submission and other portal adapters remain unverified; no real applications were sent during this build.
