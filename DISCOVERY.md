# Job discovery — V 0.6.0

Home and Jobs now offer **Search now**, progress counts and a Manual/Daily/Weekly schedule. Daily is the saved user preference. Scheduling runs only while the local app is running; closing the browser is fine, stopping the Python server pauses it. After restarting, an overdue search starts within about 30 seconds. Manual disables scheduled searches.

## Connected source

**Himalayas**, through its [official public API](https://himalayas.app/api). No portal login or Gemini request is needed. Searches use the saved role categories, India country filter, and local verification of country/timezone restrictions. GCC is included when selected as an industry. Other portals remain unconnected.

Each search reads up to three recent-results pages per query, round-robin across role areas. This is a disclosed discovery window, not an application cap or a claim to have found every vacancy. Configure terms and page depth in `config/discovery.json`. The connector spaces requests and stops on source rate limits; jobs already saved survive an interrupted search.

Results are deduplicated by source identity and existing vacancy rules, saved locally, and passed to the current deterministic matching engine. A match percentage estimates profile compatibility. It does not prove all employer requirements are satisfied. Feed categories are not invented as required skills.

Advertised pay is retained with currency and pay period in the description. The app's salary field means INR total CTC; foreign or unverified pay is not silently converted to total CTC. Unknown CTC follows the user's existing preference. Before future automatic submission, disclosed pay and all required answers must be resolved where necessary.

The original application link is preserved, and cards link to Himalayas for attribution. Expired imported jobs disappear from discovery results while application history remains. The next search refreshes returned records. A job may close earlier than its advertised expiry; check the current employer posting before applying.

## Still pending

- Supported connections for HiringCafe, Welcome to the Jungle, YC Work at a Startup, Glassdoor, LinkedIn and ZipRecruiter.
- Browser sign-in/session management for portals that need it.
- Permitted automatic submissions at ≥80%, with required answers, eligibility checks, duplicate protection and genuine confirmation receipts.
- Gmail response tracking and weekly report delivery.

No application is submitted by discovery. No portal password or private CV is sent to the public jobs API. Job records and run history stay under the ignored local data directory.
