# Personal Job Assistant — Workflow

Release: **V 0.3.0**. Dashed steps are planned; see the [module tracker](MODULE_TRACKER.md).

```mermaid
flowchart TD
    A["You maintain profile, resume and preferences"] --> B["Add vacancy with source link"]
    B -.-> B2["Planned: discovery from permitted job sources"]
    B --> C["Merge duplicates across sources"]
    B2 -.-> C
    C --> D["Transparent scoring service:<br/>role, skills, experience, location, compensation"]
    D --> E{"Eligible?<br/>exclusions and salary rules"}
    E -->|No| F["Shown as not eligible, with reasons"]
    E -->|Yes| G["Ranked matches and top 3 on Home"]
    G --> H["Job details and fit breakdown"]
    H --> I["Start application draft"]
    I --> J{"Ready?<br/>resume, profile, link"}
    J -->|No| K["Fix missing items"] --> J
    J -->|Yes| L["You review and approve"]
    L --> M["Open employer page"]
    M --> N{"You confirm submission<br/>with a reference?"}
    N -->|No| M
    N -->|Yes| O["Submitted"]
    O --> P["Interview / offer / rejected / withdrawn<br/>follow-ups and timeline"]

    Q["Gemini assistant"] -->|"read-only tools"| D
    Q -->|"propose save / draft"| R{"You approve?"}
    R -->|Yes| I
```

## Gemini controller

Gemini interprets the question and picks tools. The backend validates every argument, scopes data to the local user, and turns any change into a pending action you approve. Tools: `search_jobs`, `get_job_details`, `get_user_profile`, `calculate_job_match`, `compare_jobs`, `analyze_skill_gaps`, `list_applications`, `get_application_status`, `propose_save_job`, `propose_application_draft`. There is no submission tool.

## Operating rules

- Equal priority for credit risk, market risk, investment banking, AI/software and fintech roles; Global Capability Centres included.
- Mid-level to AVP; Indian metros including Bengaluru and Pune; remote, hybrid or on-site.
- ₹25 LPA total CTC minimum; ₹20 LPA for Google, Microsoft, Meta, Amazon, Apple and Netflix by exact name. Undisclosed salaries remain eligible.
- Showcase https://github.com/Taps-m and https://dastapomoy.com/ in tailored materials; never invent links or project claims.
- Reword and reorder verified facts only; ask before adding any new factual claim.
- Two-month notice. Clarify work authorization when an application requires it.
- Record a submission only after confirmation.
- Keep personal records, resumes and credentials out of Git.
- Number every release **V x.y.z** and update the tracker and changelog with it.
