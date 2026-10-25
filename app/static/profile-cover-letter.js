// Keep optional supporting documents separate from the master resume.
(() => {
  async function mount() {
    const form = document.getElementById('upload');
    if (!form || document.getElementById('cover-letter-upload') || !location.hash.startsWith('#/profile')) return;
    const resumeCard = form.closest('section');
    if (!resumeCard) return;
    const card = document.createElement('section');
    card.className = 'card stack profile-card';
    card.id = 'cover-letter-upload';
    card.innerHTML = '<h2 class="profile-section-title">Cover letter <span class="muted optional-label">Optional</span></h2><p class="muted">Loading…</p>';
    resumeCard.after(card);
    try {
      const docs = await api('/api/documents');
      if (!card.isConnected) return;
      const letter = docs.filter(d => d.kind === 'cover_letter' && d.source === 'upload').sort((a,b) => b.id-a.id)[0];
      card.innerHTML = `<h2 class="profile-section-title">Cover letter <span class="muted optional-label">Optional</span></h2>
        ${letter ? `<p><a href="/api/documents/${letter.id}/file" target="_blank" rel="noopener">${esc(letter.filename)}</a> <span class="badge good">Uploaded</span></p>` : '<p class="muted">Add a cover letter for applications that accept one.</p>'}
        <form class="stack profile-upload-form"><label>Choose cover letter<input type="file" name="file" accept=".pdf,.docx" required></label>
        <p class="muted">PDF or DOCX · up to 10 MB. Your resume stays separate.</p>
        <button type="submit">${letter ? 'Replace cover letter' : 'Upload cover letter'}</button></form>`;
      card.querySelector('form').onsubmit = async e => {
        e.preventDefault();
        const button = e.target.querySelector('button'); button.disabled = true;
        const data = new FormData(e.target); data.set('kind','cover_letter'); data.set('is_master','false');
        try { await api('/api/documents',{method:'POST',body:data}); toast('Cover letter uploaded'); await route(); }
        catch(err) { toast(err.message); button.disabled = false; }
      };
    } catch(e) {card.innerHTML = `<p role="alert">${esc(e.message)}</p>`;}
  }
  new MutationObserver(mount).observe(document.getElementById('view'),{childList:true});
  mount();
})();
