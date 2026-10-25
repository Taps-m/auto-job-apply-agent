(() => {
  let lastFinished = null;
  async function refresh() {
    const panel = document.getElementById('discovery-panel');
    const nav = document.getElementById('discovery-nav-run');
    if (!panel && !nav) return;
    try {
      const s = await api('/api/discovery');
      const r = s.last_run;
      if (nav) {
        const last = r?.finished_at || r?.started_at;
        nav.textContent = s.running ? 'Searching…' : last ? `Last run: ${new Date(last).toLocaleString(undefined,{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})}` : 'Search now';
        nav.disabled = s.running;
        nav.title = 'Search for jobs now';
        nav.onclick = async () => {nav.disabled = true; try {await api('/api/discovery/run',{method:'POST'}); await refresh();} catch(e) {toast(e.message);nav.disabled = false;}};
      }
      if (!panel?.isConnected) return;
      panel.innerHTML = `<div class="row spread"><div><h2>Find new jobs</h2>
        <p class="muted">India-compatible remote vacancies from <a href="https://himalayas.app" target="_blank" rel="noopener noreferrer">Himalayas</a>.</p></div>
        <button type="button" id="discover-now" ${s.running ? 'disabled' : ''}>${s.running ? 'Searching…' : 'Search now'}</button></div>
        <div class="row"><label>Search schedule <select id="discovery-frequency">
          ${['manual','daily','weekly'].map(f => `<option value="${f}" ${s.frequency === f ? 'selected' : ''}>${f[0].toUpperCase()+f.slice(1)}</option>`).join('')}</select></label></div>
        ${r?.status === 'failed' && !s.running ? '<p role="alert">Search could not finish. Please try again later.</p>' : ''}
`;
      panel.querySelector('#discover-now').onclick = async () => {
        const button = panel.querySelector('#discover-now'); button.disabled = true;
        try { await api('/api/discovery/run', {method:'POST'}); await refresh(); }
        catch(e) { toast(e.message); button.disabled = false; }
      };
      panel.querySelector('#discovery-frequency').onchange = async e => {
        try { await api('/api/settings', {method:'PUT',body:{search_frequency:e.target.value}}); toast('Search schedule saved'); }
        catch(err) { toast(err.message); await refresh(); }
      };
      const finished = r?.finished_at;
      if (finished && lastFinished && finished !== lastFinished) {
        lastFinished = finished; await route();
      } else if (finished) lastFinished = finished;
      else if (s.running) lastFinished = 'running';
    } catch(e) {
      if (panel?.isConnected) panel.textContent = 'Job discovery unavailable. Restart the app after updating, then refresh.';
    }
  }
  function mount() {
    const navigation = document.querySelector('.top-navigation');
    if (navigation && !document.getElementById('discovery-nav-run')) {
      const nav = document.createElement('button'); nav.id = 'discovery-nav-run'; nav.type = 'button'; nav.className = 'ghost small'; nav.textContent = 'Search now';
      navigation.append(nav); refresh();
    }
    const screen = location.hash.split('/')[1]?.split('?')[0] || 'home';
    const view = document.getElementById('view');
    if (!view || !['home','jobs'].includes(screen) || document.getElementById('discovery-panel') || !view.children.length) return;
    const panel = document.createElement('section');
    panel.id = 'discovery-panel'; panel.className = 'card discovery-panel';
    panel.setAttribute('aria-label','Job discovery');
    view.prepend(panel); refresh();
  }
  new MutationObserver(mount).observe(document.getElementById('view'), {childList:true});
  setInterval(() => {if (!document.hidden) refresh();}, 5000);
  mount();
})();
