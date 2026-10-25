/* Local queue controls; never present queued work as submitted. */
(() => {
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const request = async (path, body) => {
    const response = await fetch('/api/applications' + path, body === undefined ? {} : {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed');
    return data;
  };
  async function update(panel) {
    try {
      const [worker, queue] = await Promise.all([request('/worker'), request('/queue')]);
      if (!panel.isConnected) return;
      panel.querySelector('[data-worker-state]').textContent = worker.running ? 'Worker running' : 'Worker stopped';
      panel.querySelector('[data-queue-list]').innerHTML = queue.items.length ? queue.items.map(item =>
        `<li><a href="#/application/${item.application_id}">${escape(item.company)} — ${escape(item.title)}</a>: ${escape(item.state.replaceAll('_',' '))}${item.detail ? `<p>${escape(item.detail)}</p>` : ''}${item.state === 'queued' ? ` <button type="button" data-cancel="${item.application_id}">Remove</button>` : ''}</li>`).join('') : '<li>No queued applications.</li>';
    } catch (error) { panel.querySelector('[data-worker-state]').textContent = error.message; }
  }
  function mount() {
    const view = document.querySelector('#view');
    if (!view || view.querySelector('#submission-controls') || !/^#\/(applications|application\/\d+)$/.test(location.hash) || !view.querySelector('h1')) return;
    const id = location.hash.match(/^#\/application\/(\d+)$/)?.[1];
    const panel = document.createElement('section');
    panel.id = 'submission-controls'; panel.className = 'card';
    panel.innerHTML = `<h2>Application worker</h2><p data-worker-state role="status">Loading…</p>
      <p>Dover forms only · Live submission validation pending. Uses a separate local browser login.</p>
      <div class="row"><button type="button" data-start>Start worker</button><button type="button" class="ghost" data-stop>Stop worker</button><button type="button" class="ghost" data-refresh>Refresh</button></div>
      ${id ? '<form data-queue-form><label>Employer application URL<input name="employer_url" type="url" required placeholder="https://app.dover.com/apply/company/job"></label><button type="submit">Queue this application</button></form>' : ''}
      <ul data-queue-list></ul>`;
    view.append(panel);
    panel.addEventListener('click', async event => {
      const button = event.target.closest('button'); if (!button) return;
      let path;
      if (button.hasAttribute('data-start')) path='/worker/start';
      if (button.hasAttribute('data-stop')) path='/worker/stop';
      if (button.dataset.cancel) path=`/${button.dataset.cancel}/queue/cancel`;
      try { if (path) await request(path, {}); await update(panel); }
      catch (error) { panel.querySelector('[data-worker-state]').textContent=error.message; }
    });
    panel.querySelector('form')?.addEventListener('submit', async event => {
      event.preventDefault();
      try { await request(`/${id}/queue`,Object.fromEntries(new FormData(event.target))); await update(panel); }
      catch(error) { panel.querySelector('[data-worker-state]').textContent=error.message; }
    });
    update(panel);
  }
  new MutationObserver(mount).observe(document.querySelector('#view'),{childList:true});
  window.addEventListener('hashchange',mount);
  mount();
})();
