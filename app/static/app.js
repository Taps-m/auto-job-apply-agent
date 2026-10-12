'use strict';

// ---------- helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);
const view = () => $('#view');
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const lpa = (v) => (v === null || v === undefined ? 'Salary not disclosed' : `₹${v} LPA`);
const date = (v) => (v ? new Date(v).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '—');
const safeUrl = (u) => (/^https?:\/\//i.test(u || '') ? u : '#');
const STATUS_LABEL = { draft: 'Draft', approved: 'Approved', awaiting_confirmation: 'Awaiting confirmation', submitted: 'Submitted', interview: 'Interview', offer: 'Offer', rejected: 'Rejected', withdrawn: 'Withdrawn' };
let SENIORITY = []; // Loaded from the matching module's configured levels.

async function api(path, opts = {}) {
  const init = { method: opts.method || 'GET', headers: {} };
  if (opts.body instanceof FormData) init.body = opts.body;
  else if (opts.body !== undefined) { init.body = JSON.stringify(opts.body); init.headers['Content-Type'] = 'application/json'; }
  const res = await fetch(path, init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { const err = new Error(data.error || data.detail?.[0]?.msg || `Request failed (${res.status})`); err.data = data; err.status = res.status; throw err; }
  return data;
}

function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(toast.timer); toast.timer = setTimeout(() => t.classList.remove('show'), 3500);
}

function formData(form) {
  const out = {};
  for (const el of form.elements) {
    if (!el.name) continue;
    if (el.type === 'checkbox') {
      if (el.dataset.group) { (out[el.dataset.group] ||= []); if (el.checked) out[el.dataset.group].push(el.value); }
      else out[el.name] = el.checked;
    } else out[el.name] = el.value;
  }
  return out;
}

function scoreBadge(m) {
  if (!m || m.score === null || m.score === undefined) return '<span class="badge">Not enough data</span>';
  const cls = !m.eligible ? 'bad' : m.score >= 75 ? 'good' : m.score >= 50 ? '' : 'warn';
  return `<span class="badge ${cls}" title="Estimated profile compatibility based on ${m.coverage}% of the scoring weight">${m.score}% fit${m.coverage < 100 ? ` · ${m.coverage}% data` : ''}</span>`;
}

function jobCard(j) {
  const m = j.match || {};
  return `<div class="card">
    <div class="row spread"><div><h3><a href="#/job/${j.id}">${esc(j.title)}</a></h3>
      <div>${esc(j.company)} · ${esc(j.location || 'Location not stated')}${j.work_arrangement ? ` · ${esc(j.work_arrangement)}` : ''}</div></div>
      <div>${scoreBadge(m)}</div></div>
    <div class="row muted">${esc(lpa(j.salary_lpa))} · Source: <a href="${esc(safeUrl(j.source_url))}" target="_blank" rel="noopener noreferrer">${esc(j.source_name)}</a> · retrieved ${date(j.retrieved_at)}
      ${j.status !== 'open' ? `<span class="badge warn">${esc(j.status)}</span>` : ''}${j.saved ? '<span class="badge">Saved</span>' : ''}
      ${j.application ? `<span class="badge">${esc(STATUS_LABEL[j.application.status])}</span>` : ''}</div>
    ${!m.eligible && m.blockers?.length ? `<div class="muted">Not eligible: ${esc(m.blockers.join('; '))}</div>` : ''}
    <div class="row" style="margin-top:8px"><a class="button ghost small" href="#/job/${j.id}">View details</a></div>
  </div>`;
}

// ---------- state ----------
const state = { screen: 'home', jobId: null, applicationId: null, sessionId: null };

// ---------- router ----------
const routes = {
  home: renderHome, jobs: renderJobs, job: renderJob, applications: renderApplications,
  application: renderApplication, profile: renderProfile, settings: renderSettings,
};

async function route() {
  const [, name = 'home', id] = location.hash.split('?')[0].split('/');
  const render = routes[name] || renderHome;
  state.screen = name in routes ? name : 'home';
  state.jobId = name === 'job' ? Number(id) : null;
  state.applicationId = name === 'application' ? Number(id) : null;
  const nav = { job: 'jobs', application: 'applications' }[state.screen] || state.screen;
  document.querySelectorAll('[data-nav]').forEach((a) => a.classList.toggle('active', a.dataset.nav === nav));
  view().innerHTML = '<p class="muted">Loading…</p>';
  try { await render(id); } catch (e) { view().innerHTML = `<div class="notice">${esc(e.message)}</div>`; }
  loadSuggestions();
}

// ---------- M01 Home ----------
async function renderHome() {
  const d = await api('/api/home');
  $('#version').textContent = d.version;
  const c = d.completeness;
  view().innerHTML = `
    <div class="row spread"><div><h1>${d.preferred_name ? `Hello, ${esc(d.preferred_name)}` : 'Welcome'}</h1>
      <div class="muted">Your job search at a glance</div></div>
      <a class="button ghost" href="#/profile">Edit preferences</a></div>
    ${c.percent < 100 ? `<div class="notice">Profile ${c.percent}% complete. Missing: ${esc(c.missing.join(', '))}. <a href="#/profile">Complete profile</a> for better matches.</div>` : ''}
    ${d.follow_ups_due ? `<div class="notice">${d.follow_ups_due} application follow-up(s) due. <a href="#/applications">Review</a></div>` : ''}
    <h2>Top matches</h2>
    ${d.top_matches.length ? d.top_matches.map(jobCard).join('') : '<div class="empty">No eligible matches yet. Add vacancies you find on job sites and they will be ranked against your profile.</div>'}
    <div class="row"><a class="button" href="#/jobs">See all jobs</a><a class="button ghost" href="#/jobs/add">Add a job</a></div>
    <h2>Applications</h2>
    <div class="metrics">
      <div class="card metric"><b>${d.metrics.submitted}</b>Confirmed submissions</div>
      <div class="card metric"><b>${d.metrics.interviews}</b>Interviews or offers</div>
      <div class="card metric"><b>${d.metrics.response_rate ?? '—'}${d.metrics.response_rate !== null ? '%' : ''}</b>Response rate</div>
    </div>`;
}

// ---------- M02 Jobs ----------
const JOB_FORM = `
  <form id="add-job" class="card stack">
    <h2 style="margin-top:0">Add a vacancy</h2>
    <p class="muted">Paste details from the original posting. Every job needs its source link so facts can be verified.</p>
    <div class="grid">
      <label>Job title *<input name="title" required maxlength="200"></label>
      <label>Company *<input name="company" required maxlength="200"></label>
      <label>Source link *<input name="source_url" type="url" required placeholder="https://"></label>
      <label>Source name<input name="source_name" placeholder="e.g. LinkedIn"></label>
      <label>Location<input name="location" placeholder="e.g. Pune"></label>
      <label>Work arrangement<select name="work_arrangement"><option value="">Unknown</option><option>remote</option><option>hybrid</option><option>on-site</option></select></label>
      <label>Salary (₹ LPA, total CTC)<input name="salary_lpa" type="number" min="0" step="0.1" placeholder="Leave empty if not disclosed"></label>
      <label>Employment type<input name="employment_type" placeholder="Full-time"></label>
      <label>Posted on<input name="posted_at" type="date"></label>
    </div>
    <label>Description<textarea name="description" rows="6"></textarea></label>
    <label>Responsibilities<textarea name="responsibilities" rows="3"></textarea></label>
    <div class="grid">
      <label>Required skills (comma separated)<input name="required_skills"></label>
      <label>Preferred skills (comma separated)<input name="preferred_skills"></label>
    </div>
    <div class="row"><button type="submit">Save vacancy</button><a class="button ghost" href="#/jobs">Cancel</a></div>
  </form>`;

async function renderJobs(sub) {
  const params = new URLSearchParams(location.hash.split('?')[1] || '');
  const q = Object.fromEntries(params);
  const res = await api('/api/jobs?' + params.toString());
  view().innerHTML = `
    <div class="row spread"><h1>Jobs &amp; matches</h1>
      <div class="row"><button type="button" class="ghost" id="rescore">Refresh scores</button><a class="button" href="#/jobs/add">Add a job</a></div></div>
    ${sub && sub.startsWith('add') ? JOB_FORM : ''}
    <form id="job-filters" class="card grid">
      <label>Search<input name="q" value="${esc(q.q || '')}" placeholder="credit risk jobs in Kolkata"></label>
      <label>Location<input name="location" value="${esc(q.location || '')}"></label>
      <label>Minimum salary (LPA)<input name="min_salary" type="number" min="0" value="${esc(q.min_salary || '')}"></label>
      <label>Company<input name="company" value="${esc(q.company || '')}"></label>
      <label>Exclude company<input name="exclude_company" value="${esc(q.exclude_company || '')}"></label>
      <label>Seniority<select name="seniority"><option value="">Any</option>${SENIORITY.map((s) => `<option ${q.seniority === s ? 'selected' : ''}>${s}</option>`).join('')}</select></label>
      <label class="check"><input type="checkbox" name="remote" ${q.remote === 'true' ? 'checked' : ''}> Remote only</label>
      <label class="check"><input type="checkbox" name="saved_only" ${q.saved_only === 'true' ? 'checked' : ''}> Saved only</label>
      <label class="check"><input type="checkbox" name="hide_ineligible" ${q.include_ineligible === 'false' ? 'checked' : ''}> Hide ineligible</label>
      <div class="row"><button type="submit">Apply filters</button><a class="button ghost" href="#/jobs">Clear</a></div>
    </form>
    ${res.interpreted.keywords || res.interpreted.location || res.interpreted.min_salary ? `<p class="muted">Interpreted as: ${esc([res.interpreted.keywords && `keywords “${res.interpreted.keywords}”`, res.interpreted.location && `in ${res.interpreted.location}`, res.interpreted.remote && 'remote', res.interpreted.min_salary && `≥ ₹${res.interpreted.min_salary} LPA`].filter(Boolean).join(', '))}</p>` : ''}
    <p class="muted">${res.jobs.length} vacancies, ranked by estimated fit. Automatic discovery from job sites is not connected yet; add vacancies manually.</p>
    ${res.jobs.length ? res.jobs.map(jobCard).join('') : '<div class="empty">No vacancies match.</div>'}`;
  $('#job-filters').addEventListener('submit', (e) => {
    e.preventDefault();
    const f = formData(e.target); const p = new URLSearchParams();
    for (const k of ['q', 'location', 'min_salary', 'company', 'exclude_company', 'seniority']) if (f[k]) p.set(k, f[k]);
    if (f.remote) p.set('remote', 'true');
    if (f.saved_only) p.set('saved_only', 'true');
    if (f.hide_ineligible) p.set('include_ineligible', 'false');
    location.hash = '#/jobs' + (p.toString() ? '?' + p : '');
  });
  $('#rescore').addEventListener('click', async () => { await api('/api/matching/rescore', { method: 'POST' }); toast('Scores recalculated from your current profile'); route(); });
  const form = $('#add-job');
  if (form) form.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      const r = await api('/api/jobs', { method: 'POST', body: formData(form) });
      toast(r.merged_with_existing ? 'Same vacancy already saved from another source; missing details were merged' : 'Vacancy saved and scored');
      location.hash = `#/job/${r.job.id}`;
    } catch (err) {
      if (err.data?.job_id) { toast(err.message); location.hash = `#/job/${err.data.job_id}`; } else toast(err.message);
    }
  });
}

// ---------- M03 Job details ----------
async function renderJob(id) {
  const j = await api(`/api/jobs/${id}`);
  const m = j.match || {};
  view().innerHTML = `
    <p><a href="#/jobs">← All jobs</a></p>
    <div class="card">
      <div class="row spread"><div><h1>${esc(j.title)}</h1><div>${esc(j.company)}</div></div><div class="score">${scoreBadge(m)}</div></div>
      <table style="margin-top:12px">
        <tr><th>Location</th><td>${esc(j.location || 'Not stated')}${j.work_arrangement ? ` · ${esc(j.work_arrangement)}` : ''}</td></tr>
        <tr><th>Salary</th><td>${esc(lpa(j.salary_lpa))}</td></tr>
        <tr><th>Employment type</th><td>${esc(j.employment_type || 'Not stated')}</td></tr>
        <tr><th>Source</th><td><a href="${esc(safeUrl(j.source_url))}" target="_blank" rel="noopener noreferrer">Original vacancy (${esc(j.source_name)})</a></td></tr>
        <tr><th>Posted</th><td>${esc(j.posted_at ? date(j.posted_at) : 'Unknown')}</td></tr>
        <tr><th>Retrieved</th><td>${date(j.retrieved_at)} · link ${j.verified_at ? `verified ${date(j.verified_at)}` : 'not yet checked'} · status <span class="badge ${j.status === 'open' ? 'good' : 'warn'}">${esc(j.status)}</span></td></tr>
      </table>
      <div class="row" style="margin-top:12px">
        ${j.application ? `<a class="button" href="#/application/${j.application.id}">Open application (${esc(STATUS_LABEL[j.application.status])})</a>` : '<button type="button" id="start-app">Start application</button>'}
        <button type="button" class="ghost" id="save">${j.saved ? 'Remove from shortlist' : 'Save to shortlist'}</button>
        <button type="button" class="ghost" id="check">Check link</button>
        <button type="button" class="ghost" id="explain">Ask assistant about this job</button>
        <button type="button" class="ghost" id="delete">Delete</button>
      </div>
    </div>
    <h2>Fit breakdown</h2>
    <div class="card">
      <p class="muted">${esc(m.note || '')}</p>
      ${m.blockers?.length ? `<div class="notice">Not eligible: ${esc(m.blockers.join('; '))}</div>` : ''}
      <table><tr><th>Factor</th><th>Weight</th><th>Score</th><th>Why</th></tr>
      ${(m.components || []).map((c) => `<tr><td>${esc(c.name)}</td><td>${c.weight}</td><td>${c.score === null ? 'Unknown' : c.score + '%'}</td><td>${esc(c.reason)}</td></tr>`).join('')}</table>
    </div>
    <h2>Skills</h2>
    <div class="card">
      <p><b>Required:</b> ${esc(j.required_skills.join(', ') || 'Not listed')}<br><b>Preferred:</b> ${esc(j.preferred_skills.join(', ') || 'Not listed')}</p>
      <p><b>Possible gaps:</b> ${!m.skills_gap ? 'Add your skills in <a href="#/profile">Profile</a> to see gaps' : (m.skills_gap.required.length || m.skills_gap.preferred.length)
        ? esc([...m.skills_gap.required.map((s) => `${s} (required)`), ...m.skills_gap.preferred.map((s) => `${s} (preferred)`)].join(', '))
        : 'None found against your profile skills'}</p>
    </div>
    <h2>From the vacancy <span class="badge good">Verified source text</span></h2>
    <div class="card">${j.responsibilities ? `<h3>Responsibilities</h3><pre class="text">${esc(j.responsibilities)}</pre>` : ''}
      <pre class="text">${esc(j.description || 'No description saved.')}</pre></div>`;
  $('#save').addEventListener('click', async () => { await api(`/api/jobs/${id}/save`, { method: 'POST', body: { saved: !j.saved } }); route(); });
  $('#check').addEventListener('click', async () => { const r = await api(`/api/jobs/${id}/check`, { method: 'POST' }); toast(`Link check: ${r.status} (${r.detail})`); route(); });
  $('#explain').addEventListener('click', () => askAssistant(`Explain how well ${j.title} at ${j.company} fits my profile, and what I would need to improve.`));
  $('#delete').addEventListener('click', async () => {
    if (!confirm('Delete this vacancy and any draft application for it?')) return;
    try { await api(`/api/jobs/${id}`, { method: 'DELETE' }); location.hash = '#/jobs'; } catch (e) { toast(e.message); }
  });
  $('#start-app')?.addEventListener('click', () => startApplication(id));
}

async function startApplication(jobId, force = false) {
  try {
    const a = await api('/api/applications', { method: 'POST', body: { job_id: jobId, force } });
    location.hash = `#/application/${a.id}`;
  } catch (e) {
    if (e.status === 409 && confirm(`${e.message}. Open the existing application? (Cancel starts another one.)`)) location.hash = `#/application/${e.data.application_id}`;
    else if (e.status === 409) startApplication(jobId, true);
    else toast(e.message);
  }
}

// ---------- M05 Applications ----------
async function renderApplications() {
  const d = await api('/api/applications');
  const due = new Set(d.follow_ups_due);
  view().innerHTML = `
    <h1>Applications</h1>
    <div class="metrics">
      <div class="card metric"><b>${d.metrics.submitted}</b>Confirmed submissions</div>
      <div class="card metric"><b>${d.metrics.interviews}</b>Interviews or offers</div>
      <div class="card metric"><b>${d.metrics.response_rate ?? '—'}${d.metrics.response_rate !== null ? '%' : ''}</b>Response rate</div>
      <div class="card metric"><b>${due.size}</b>Follow-ups due</div>
    </div>
    ${d.applications.length ? `<div class="card"><table><tr><th>Job</th><th>Status</th><th>Updated</th><th>Follow-up</th></tr>
      ${d.applications.map((a) => `<tr><td><a href="#/application/${a.id}">${esc(a.job.title)}</a><div class="muted">${esc(a.job.company)}</div></td>
        <td><span class="badge">${esc(STATUS_LABEL[a.status])}</span></td><td>${date(a.updated_at)}</td>
        <td>${a.follow_up_on ? `${due.has(a.id) ? '<span class="badge warn">Due</span> ' : ''}${esc(a.follow_up_on)}` : '—'}</td></tr>`).join('')}</table></div>`
      : '<div class="empty">No applications yet. Open a job and choose “Start application”.</div>'}`;
}

async function renderApplication(id) {
  const [a, docs] = await Promise.all([api(`/api/applications/${id}`), api('/api/documents')]);
  const draft = a.status === 'draft';
  const r = a.readiness;
  const answers = Object.entries(a.answers).map(([k, v]) => `${k}: ${v}`).join('\n');
  view().innerHTML = `
    <p><a href="#/applications">← Applications</a></p>
    <div class="card"><div class="row spread"><div><h1>${esc(a.job.title)}</h1><div>${esc(a.job.company)} · <a href="#/job/${a.job.id}">job details</a></div></div>
      <span class="badge">${esc(STATUS_LABEL[a.status])}</span></div></div>
    <h2>1. Readiness</h2>
    <div class="card"><ul>${r.checks.map((c) => `<li>${c.ok ? '✅' : '❌'} ${esc(c.item)}</li>`).join('')}</ul>
      ${r.warnings.map((w) => `<div class="notice">${esc(w)}</div>`).join('')}
      ${!r.checks[0].ok ? '<p class="muted">Upload a resume under <a href="#/profile">Profile &amp; resume</a>.</p>' : ''}</div>
    <h2>2. Preview and edit</h2>
    <form id="draft" class="card stack">
      <label>Resume<select name="resume_document_id" ${draft ? '' : 'disabled'}><option value="">None</option>
        ${docs.map((d) => `<option value="${d.id}" ${d.id === a.resume_document_id ? 'selected' : ''}>${esc(d.filename)}${d.is_master ? ' (master)' : ''}</option>`).join('')}</select></label>
      ${a.resume ? `<a href="/api/documents/${a.resume.id}/file" target="_blank">Preview resume</a>` : ''}
      <label>Cover letter<textarea name="cover_letter" rows="8" ${draft ? '' : 'disabled'} placeholder="Write or paste a cover letter. Ask the assistant for a draft based on your verified profile.">${esc(a.cover_letter)}</textarea></label>
      <label>Proposed answers to application questions (one per line, “Question: answer”)<textarea name="answers" rows="4" ${draft ? '' : 'disabled'}>${esc(answers)}</textarea></label>
      ${draft ? '<div class="row"><button type="submit">Save draft</button></div>' : '<p class="muted">Withdraw approval to edit.</p>'}
    </form>
    <h2>3. Approve and submit</h2>
    <div class="card stack">
      ${draft ? `<p>Approving confirms you have reviewed the resume, cover letter and answers above.</p>
        <button type="button" id="approve" ${r.ready ? '' : 'disabled'}>I approve this application</button>` : ''}
      ${['approved', 'awaiting_confirmation'].includes(a.status) ? `
        <p>Open the employer's page and submit there. Opening the page does <b>not</b> count as a submission.</p>
        <div class="row"><button type="button" id="open">Open employer application page</button><button type="button" class="ghost" id="unapprove">Withdraw approval</button></div>
        <form id="confirm" class="row"><input name="confirmation" placeholder="Confirmation reference, email subject, or “manual”" required style="flex:1"><button type="submit">Mark as submitted</button></form>` : ''}
      ${a.submitted_at ? `<p>Submitted ${date(a.submitted_at)} · confirmation: ${esc(a.confirmation)}</p>
        <div class="row">${['interview', 'offer', 'rejected', 'withdrawn'].map((s) => `<button type="button" class="ghost small" data-outcome="${s}">${STATUS_LABEL[s]}</button>`).join('')}</div>` : ''}
    </div>
    <h2>Follow-up</h2>
    <form id="follow" class="card row"><input type="date" name="follow_up_on" value="${esc(a.follow_up_on || '')}" style="width:auto">
      <input name="follow_up_note" value="${esc(a.follow_up_note)}" placeholder="What to do" style="flex:1"><button type="submit">Save</button></form>
    <h2>Timeline</h2>
    <div class="card"><ul class="timeline">${a.events.slice().reverse().map((e) => `<li><b>${esc(e.kind.replace(/_/g, ' '))}</b> <span class="muted">${new Date(e.at).toLocaleString()}</span><div>${esc(e.detail)}</div></li>`).join('')}</ul></div>`;

  $('#draft').addEventListener('submit', async (e) => {
    e.preventDefault(); const f = formData(e.target); const ans = {};
    for (const line of f.answers.split('\n')) { const i = line.indexOf(':'); if (i > 0) ans[line.slice(0, i).trim()] = line.slice(i + 1).trim(); }
    try { await api(`/api/applications/${id}`, { method: 'PUT', body: { cover_letter: f.cover_letter, answers: ans, resume_document_id: f.resume_document_id ? Number(f.resume_document_id) : null } }); toast('Draft saved'); route(); } catch (err) { toast(err.message); }
  });
  $('#approve')?.addEventListener('click', async () => { try { await api(`/api/applications/${id}/approve`, { method: 'POST' }); route(); } catch (e) { toast(e.message); } });
  $('#unapprove')?.addEventListener('click', async () => { await api(`/api/applications/${id}/withdraw-approval`, { method: 'POST' }); route(); });
  $('#open')?.addEventListener('click', async () => { const res = await api(`/api/applications/${id}/open`, { method: 'POST' }); window.open(safeUrl(res.url), '_blank', 'noopener'); route(); });
  $('#confirm')?.addEventListener('submit', async (e) => { e.preventDefault(); try { await api(`/api/applications/${id}/confirm`, { method: 'POST', body: formData(e.target) }); route(); } catch (err) { toast(err.message); } });
  view().querySelectorAll('[data-outcome]').forEach((b) => b.addEventListener('click', async () => {
    const note = prompt(`Note for “${STATUS_LABEL[b.dataset.outcome]}” (optional)`); if (note === null) return;
    try { await api(`/api/applications/${id}/outcome`, { method: 'POST', body: { status: b.dataset.outcome, note } }); route(); } catch (e) { toast(e.message); }
  }));
  $('#follow').addEventListener('submit', async (e) => { e.preventDefault(); await api(`/api/applications/${id}/follow-up`, { method: 'PUT', body: formData(e.target) }); toast('Follow-up saved'); route(); });
}

// ---------- M06/M07 Profile, preferences, documents ----------
async function renderProfile() {
  const [b, docs] = await Promise.all([api('/api/profile'), api('/api/documents')]);
  const p = b.profile, pr = b.preferences;
  const list = (v) => esc((v || []).join(', '));
  view().innerHTML = `
    <h1>Profile &amp; resume</h1>
    <div class="notice">Profile ${b.completeness.percent}% complete${b.completeness.missing.length ? ` · missing: ${esc(b.completeness.missing.join(', '))}` : ''}.
      These are your verified facts: the assistant may reword them but never adds to them.</div>
    <h2>Career profile</h2>
    <form id="profile" class="card stack">
      <div class="grid">
        <label>Preferred name<input name="preferred_name" value="${esc(p.preferred_name)}"></label>
        <label>Headline<input name="headline" value="${esc(p.headline)}" placeholder="e.g. Credit risk analyst"></label>
        <label>Years of experience<input name="years_experience" type="number" min="0" max="60" step="0.5" value="${esc(p.years_experience ?? '')}"></label>
        <label>Notice period (months)<input name="notice_months" type="number" min="0" max="12" value="${esc(p.notice_months ?? '')}"></label>
        <label>GitHub<input name="github_url" value="${esc(p.github_url)}"></label>
        <label>Website<input name="website_url" value="${esc(p.website_url)}"></label>
        <label>Work authorization<input name="work_authorization" value="${esc(p.work_authorization)}"></label>
      </div>
      <label>Skills (comma separated)<textarea name="skills" rows="2">${list(p.skills)}</textarea></label>
      <label>Summary<textarea name="summary" rows="3">${esc(p.summary)}</textarea></label>
      <label>Career goals<textarea name="career_goals" rows="2">${esc(p.career_goals)}</textarea></label>
      <div><button type="submit">Save profile</button></div>
    </form>
    <h2>Work history</h2>
    <div class="card">
      ${b.experiences.length ? `<table>${b.experiences.map((e) => `<tr><td><b>${esc(e.role)}</b>, ${esc(e.employer)}<div class="muted">${esc(e.start_date)} – ${esc(e.end_date || 'present')}</div><pre class="text">${esc(e.achievements)}</pre></td><td><button type="button" class="ghost small" data-del-exp="${e.id}">Remove</button></td></tr>`).join('')}</table>` : '<p class="muted">No roles added.</p>'}
      <form id="exp" class="stack" style="margin-top:12px"><div class="grid">
        <label>Employer<input name="employer" required></label><label>Role<input name="role" required></label>
        <label>Start<input name="start_date" type="month"></label><label>End (empty if current)<input name="end_date" type="month"></label></div>
        <label>Achievements (facts only)<textarea name="achievements" rows="3"></textarea></label>
        <div><button type="submit">Add role</button></div></form>
    </div>
    <h2>Resume</h2>
    <div class="card stack">
      ${docs.length ? `<table>${docs.map((d) => `<tr><td><a href="/api/documents/${d.id}/file" target="_blank">${esc(d.filename)}</a> ${d.is_master ? '<span class="badge good">Master</span>' : ''}</td><td class="muted">${date(d.uploaded_at)}</td><td>${d.is_master ? '' : `<button type="button" class="ghost small" data-master="${d.id}">Make master</button>`}</td></tr>`).join('')}</table>` : '<p class="muted">No resume uploaded.</p>'}
      <form id="upload" class="row"><input type="file" name="file" accept=".pdf,.docx" required style="flex:1"><button type="submit">Upload as master</button></form>
      <p class="muted">PDF or DOCX, up to 10 MB, stored only on this computer. Automatic resume parsing and tailored resume export arrive in a later version.</p>
    </div>
    <h2>Job preferences</h2>
    <form id="prefs" class="card stack">
      <label>Target roles (comma separated)<input name="roles" value="${list(pr.roles)}"></label>
      <label>Industries<input name="industries" value="${list(pr.industries)}"></label>
      <label>Preferred cities, most preferred first<input name="cities" value="${list(pr.cities)}"></label>
      <div class="row">${['remote', 'hybrid', 'on-site'].map((a) => `<label class="check"><input type="checkbox" data-group="arrangements" name="arr_${a}" value="${a}" ${pr.arrangements.includes(a) ? 'checked' : ''}> ${a}</label>`).join('')}</div>
      <div class="grid">
        <label>Minimum salary (₹ LPA)<input name="min_salary_lpa" type="number" min="0" step="0.5" value="${pr.min_salary_lpa}"></label>
        <label>Minimum for premium employers<input name="premium_min_salary_lpa" type="number" min="0" step="0.5" value="${pr.premium_min_salary_lpa}"></label>
        <label>Seniority from<select name="seniority_min">${SENIORITY.map((s, i) => `<option value="${i}" ${pr.seniority_min === i ? 'selected' : ''}>${s}</option>`).join('')}</select></label>
        <label>Seniority to<select name="seniority_max">${SENIORITY.map((s, i) => `<option value="${i}" ${pr.seniority_max === i ? 'selected' : ''}>${s}</option>`).join('')}</select></label>
      </div>
      <label class="check"><input type="checkbox" name="allow_unknown_salary" ${pr.allow_unknown_salary ? 'checked' : ''}> Include jobs that do not disclose salary</label>
      <label>Premium employers (exact names)<input name="premium_employers" value="${list(pr.premium_employers)}"></label>
      <h3>Exclusions</h3>
      <div class="grid">
        <label>Companies<input name="excluded_companies" value="${list(pr.excluded_companies)}"></label>
        <label>Locations<input name="excluded_locations" value="${list(pr.excluded_locations)}"></label>
        <label>Keywords<input name="excluded_keywords" value="${list(pr.excluded_keywords)}"></label>
      </div>
      <h3>Scoring weights</h3>
      <div class="grid">${Object.entries(pr.weights).map(([k, v]) => `<label>${esc(k)}<input name="w_${k}" type="number" min="0" max="100" value="${v}"></label>`).join('')}</div>
      <div><button type="submit">Save preferences</button></div>
    </form>`;

  const save = async (path, body, method = 'PUT') => { try { await api(path, { method, body }); toast('Saved'); route(); } catch (e) { toast(e.message); } };
  $('#profile').addEventListener('submit', (e) => { e.preventDefault(); save('/api/profile', formData(e.target)); });
  $('#exp').addEventListener('submit', (e) => { e.preventDefault(); save('/api/profile/experiences', formData(e.target), 'POST'); });
  view().querySelectorAll('[data-del-exp]').forEach((b) => b.addEventListener('click', () => save(`/api/profile/experiences/${b.dataset.delExp}`, undefined, 'DELETE')));
  view().querySelectorAll('[data-master]').forEach((b) => b.addEventListener('click', () => save(`/api/documents/${b.dataset.master}/master`, undefined, 'POST')));
  $('#upload').addEventListener('submit', async (e) => {
    e.preventDefault(); const fd = new FormData(e.target); fd.set('is_master', 'true');
    try { await api('/api/documents', { method: 'POST', body: fd }); toast('Resume uploaded'); route(); } catch (err) { toast(err.message); }
  });
  $('#prefs').addEventListener('submit', (e) => {
    e.preventDefault(); const f = formData(e.target); const weights = {};
    for (const k of Object.keys(pr.weights)) weights[k] = Number(f[`w_${k}`]);
    save('/api/preferences', {
      roles: f.roles, industries: f.industries, cities: f.cities, arrangements: f.arrangements || [],
      min_salary_lpa: f.min_salary_lpa, premium_min_salary_lpa: f.premium_min_salary_lpa,
      seniority_min: Number(f.seniority_min), seniority_max: Number(f.seniority_max),
      allow_unknown_salary: f.allow_unknown_salary, premium_employers: f.premium_employers,
      excluded_companies: f.excluded_companies, excluded_locations: f.excluded_locations, excluded_keywords: f.excluded_keywords, weights,
    });
  });
}

// ---------- M08 Settings ----------
async function renderSettings() {
  const s = await api('/api/settings');
  const u = s.usage;
  view().innerHTML = `
    <h1>Settings</h1>
    <h2>Gemini</h2>
    <div class="card stack">
      <p>Status: ${s.gemini_connected ? '<span class="badge good">API key configured</span>' : '<span class="badge warn">Not connected</span>'}</p>
      ${s.gemini_connected ? '' : '<p class="muted">Create a key in Google AI Studio, then add <code>GEMINI_API_KEY=your-key</code> to the <code>.env</code> file in the app folder and restart. The key stays on this computer and is never shown in the browser.</p>'}
      <form id="model" class="row"><label style="flex:1">Model<input name="gemini_model" list="model-list" value="${esc(s.gemini_model)}"></label>
        <datalist id="model-list"></datalist><button type="button" class="ghost" id="load-models" ${s.gemini_connected ? '' : 'disabled'}>Load available models</button><button type="submit">Save</button></form>
    </div>
    <h2>API usage</h2>
    <div class="card"><div class="metrics">
      <div class="metric"><b>${u.requests}</b>Requests</div><div class="metric"><b>${u.failures}</b>Failures</div>
      <div class="metric"><b>${u.input_tokens.toLocaleString()}</b>Input tokens</div><div class="metric"><b>${u.output_tokens.toLocaleString()}</b>Output tokens</div></div>
      <p class="muted">${esc(u.cost_note)}</p>
      ${u.recent_failures.length ? `<h3>Recent failures</h3><ul>${u.recent_failures.map((f) => `<li>${new Date(f.at).toLocaleString()} — ${esc(f.error)}</li>`).join('')}</ul>` : ''}</div>
    <h2>Automation</h2>
    <form id="automation" class="card stack">
      <label>Automation level<select name="automation_level">
        <option value="manual" ${s.automation_level === 'manual' ? 'selected' : ''}>Manual — the assistant only answers questions</option>
        <option value="assisted" ${s.automation_level === 'assisted' ? 'selected' : ''}>Assisted — the assistant may propose actions for your approval</option>
        <option value="approved_automation" ${s.automation_level === 'approved_automation' ? 'selected' : ''}>Approved automation — reserved for supported portals (not available yet)</option></select></label>
      <label>Job search frequency<select name="search_frequency">
        ${['manual', 'daily', 'weekly'].map((f) => `<option ${s.search_frequency === f ? 'selected' : ''}>${f}</option>`).join('')}</select></label>
      <p class="muted">Applications are never submitted without your explicit approval, at any level.</p>
      <div><button type="submit">Save</button></div>
    </form>
    <h2>Job sources</h2>
    <div class="card"><table>${s.sources.map((x) => `<tr><td>${esc(x.name)}</td><td><span class="badge ${x.status === 'Enabled' ? 'good' : ''}">${esc(x.status)}</span></td></tr>`).join('')}</table>
      <p class="muted">Each site will be connected only through an access route it permits.</p></div>
    <h2>Privacy</h2>
    <div class="card stack"><p>All data is stored in the <code>data</code> folder on this computer. Gemini receives only the job and profile details needed for each question.</p>
      <form id="delete-all" class="row"><input name="confirm" placeholder="Type DELETE" style="width:auto"><button type="submit" class="danger">Delete all my data</button></form></div>`;

  $('#model').addEventListener('submit', async (e) => { e.preventDefault(); try { await api('/api/settings', { method: 'PUT', body: formData(e.target) }); toast('Model saved'); } catch (err) { toast(err.message); } });
  $('#load-models').addEventListener('click', async () => {
    try { const r = await api('/api/settings/models'); $('#model-list').innerHTML = r.models.map((m) => `<option value="${esc(m)}">`).join(''); toast(`${r.models.length} models available`); } catch (e) { toast(e.message); }
  });
  $('#automation').addEventListener('submit', async (e) => { e.preventDefault(); try { await api('/api/settings', { method: 'PUT', body: formData(e.target) }); toast('Saved'); } catch (err) { toast(err.message); } });
  $('#delete-all').addEventListener('submit', async (e) => {
    e.preventDefault(); if (!confirm('Permanently delete your profile, jobs, applications, documents and conversations?')) return;
    try { await api('/api/privacy/delete-all', { method: 'POST', body: formData(e.target) }); state.sessionId = null; toast('All data deleted'); loadSessions(); location.hash = '#/home'; } catch (err) { toast(err.message); }
  });
}

// ---------- M04 Assistant panel ----------
function formatReply(text) {
  return esc(text)
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/^\s*[-*] (.*)$/gm, '• $1')
    .replace(/\n/g, '<br>');
}

function appendMessage(role, content, tools) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = role === 'user' ? esc(content).replace(/\n/g, '<br>') : formatReply(content);
  if (tools?.length) div.insertAdjacentHTML('beforeend', `<div class="tools">Looked up: ${esc([...new Set(tools)].join(', ').replace(/_/g, ' '))}</div>`);
  $('#chat-log').append(div);
  $('#chat-log').scrollTop = $('#chat-log').scrollHeight;
}

async function loadSessions() {
  const sessions = await api('/api/chat/sessions');
  $('#chat-sessions').innerHTML = '<option value="">New conversation</option>' + sessions.map((s) => `<option value="${s.id}" ${s.id === state.sessionId ? 'selected' : ''}>${esc(s.title)}</option>`).join('');
}

async function openSession(id) {
  state.sessionId = id;
  $('#chat-log').innerHTML = '';
  if (!id) return;
  for (const m of await api(`/api/chat/sessions/${id}`)) appendMessage(m.role, m.content);
}

async function loadSuggestions() {
  const qs = new URLSearchParams({ screen: state.screen });
  if (state.jobId) qs.set('job_id', state.jobId);
  try {
    const list = await api('/api/chat/suggestions?' + qs);
    $('#chat-suggestions').innerHTML = list.map((s) => `<button type="button" data-suggest="${esc(s)}">${esc(s)}</button>`).join('');
  } catch { $('#chat-suggestions').innerHTML = ''; }
}

async function loadActions() {
  const acts = await api('/api/actions');
  $('#chat-actions').innerHTML = acts.map((a) => `<div class="card"><b>Assistant proposes:</b> ${a.tool === 'propose_save_job' ? 'save' : 'start an application draft for'} job #${a.arguments.job_id}
    ${a.arguments.reason ? `<div class="muted">${esc(a.arguments.reason)}</div>` : ''}
    <div class="row" style="margin-top:6px"><a href="#/job/${a.arguments.job_id}">View job</a><button type="button" class="small" data-act="${a.id}" data-approve="1">Approve</button><button type="button" class="ghost small" data-act="${a.id}" data-approve="">Decline</button></div></div>`).join('');
}

async function sendMessage(text) {
  text = text.trim(); if (!text) return;
  appendMessage('user', text);
  const btn = $('#chat-form button'); btn.disabled = true; btn.textContent = '…';
  try {
    const r = await api('/api/chat', { method: 'POST', body: { message: text, session_id: state.sessionId, context: { screen: state.screen, job_id: state.jobId, application_id: state.applicationId } } });
    const isNew = !state.sessionId; state.sessionId = r.session_id;
    appendMessage(r.role, r.reply, r.tools_used);
    if (isNew) loadSessions();
    loadActions();
  } catch (e) { appendMessage('error', e.message); }
  finally { btn.disabled = false; btn.textContent = 'Send'; }
}

function askAssistant(text) { $('#chat').classList.add('open'); sendMessage(text); }

async function initChat() {
  const s = await api('/api/settings');
  $('#version').textContent = s.version;
  $('#chat-status').innerHTML = s.gemini_connected ? '' : '<div class="notice">Gemini is not connected. <a href="#/settings">Set it up</a>.</div>';
  await loadSessions(); loadActions();
  $('#chat-sessions').addEventListener('change', (e) => openSession(e.target.value ? Number(e.target.value) : null));
  $('#chat-new').addEventListener('click', () => { $('#chat-sessions').value = ''; openSession(null); });
  $('#chat-form').addEventListener('submit', (e) => { e.preventDefault(); const t = e.target.message; sendMessage(t.value); t.value = ''; });
  $('#chat-form textarea').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); $('#chat-form').requestSubmit(); } });
  $('#chat-suggestions').addEventListener('click', (e) => { const b = e.target.closest('[data-suggest]'); if (b) sendMessage(b.dataset.suggest); });
  $('#chat-actions').addEventListener('click', async (e) => {
    const b = e.target.closest('[data-act]'); if (!b) return;
    try {
      const r = await api(`/api/actions/${b.dataset.act}`, { method: 'POST', body: { approve: Boolean(b.dataset.approve) } });
      toast(r.status === 'executed' ? 'Done' : r.status === 'failed' ? r.result.error : 'Declined');
      if (r.result.application_id) location.hash = `#/application/${r.result.application_id}`; else route();
      loadActions();
    } catch (err) { toast(err.message); }
  });
  $('#chat-toggle').addEventListener('click', () => $('#chat').classList.toggle('open'));
}

// ---------- boot ----------
$('#global-search').addEventListener('submit', (e) => {
  e.preventDefault(); const q = e.target.q.value.trim();
  location.hash = '#/jobs' + (q ? '?' + new URLSearchParams({ q }) : '');
});
window.addEventListener('hashchange', route);
initChat().catch((e) => { $('#chat-status').innerHTML = `<div class="notice">${esc(e.message)}</div>`; });
api('/api/matching/seniority-levels')
  .then((levels) => { SENIORITY = levels.map((l) => l.label); })
  .catch(() => {})
  .finally(route);
