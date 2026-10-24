'use strict';

// Ambient leaves use compositor transforms only, behind all interactive content.
if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const layer = document.createElement('div');
  layer.className = 'ambient-leaves';
  layer.setAttribute('aria-hidden', 'true');
  for (let n = 0; n < 7; n++) {
    const leaf = document.createElement('div');
    leaf.className = 'leaf-fall';
    leaf.style.cssText = `--left:${6 + n * 14}%;--fall:${29 + Math.random()*18}s;--delay:${-Math.random()*45}s;--sway:${6 + Math.random()*5}s;--drift:${35 + Math.random()*55}px;--size:${[20,35,24,46,28,39,22][n] + Math.random()*4}px;--tint:${['#d8a13b','#ce7136','#b94e3d'][n%3]}`;
    const sway = document.createElement('span'); sway.className = 'leaf-sway';
    const blade = document.createElement('span'); blade.className = 'leaf-blade';
    // Recognizable maple silhouette rather than rounded petal shapes.
    blade.innerHTML = `<svg viewBox="0 0 64 80" aria-hidden="true"><defs><linearGradient id="leaf-light-${n}" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#efd078"/><stop offset=".5" stop-color="${['#d8a13b','#ce7136','#b94e3d'][n%3]}"/><stop offset="1" stop-color="#713321"/></linearGradient></defs><path d="M32 2 38 19 44 12 43 30 58 24 54 37 63 40 47 51 51 60 36 57 34 67 29 67 28 57 12 61 16 51 1 40 12 37 7 24 23 30 21 12 28 20Z" fill="url(#leaf-light-${n})"/><path d="m32 20 0 45-3 12M32 46 14 36m18 16 15-12M32 35l7-12m-7 13-7-12" fill="none" stroke="#efd098" stroke-opacity=".65" stroke-width="1" stroke-linecap="round"/></svg>`;
    sway.append(blade); leaf.append(sway); layer.append(leaf);
  }
  document.body.prepend(layer);
}

let progressBusy = false;
let progressSignature = '';
function progressChart(data) {
  const W=760,H=285,L=62,R=22,T=22,B=58;
  const maxCount=Math.max(1,...data.points.map(p=>p.applications));
  const step=Math.max(1,Math.ceil(maxCount/4)); const top=step*4;
  const x=n=>L+n/100*(W-L-R),y=n=>H-B-n/top*(H-T-B);
  const grid=Array.from({length:5},(_,n)=>{const v=n*step;return `<line x1="${L}" x2="${W-R}" y1="${y(v)}" y2="${y(v)}" class="chart-grid"/><text x="${L-12}" y="${y(v)+4}" text-anchor="end">${v}</text>`;}).join('');
  const ticks=Array.from({length:11},(_,n)=>`<text x="${x(n*10)}" y="${H-B+22}" text-anchor="middle">${n*10}%</text>`).join('');
  const points=data.points.map(p=>`${x(p.match_percent)},${y(p.applications)}`).join(' ');
  const dots=data.points.filter(p=>p.applications).map(p=>`<circle cx="${x(p.match_percent)}" cy="${y(p.applications)}" r="4" class="chart-dot" tabindex="0" role="img" aria-label="${p.match_percent}% match: ${p.applications} applications, ${p.interviews} interviews or offers"><title>${p.match_percent}% match · ${p.applications} applications · ${p.interviews} interviews/offers</title></circle>`).join('');
  return `<svg class="progress-chart" viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="progress-title progress-description"><title id="progress-title">Applications by profile match percentage</title><desc id="progress-description">X-axis: match percentage, rounded to the nearest whole percent. Y-axis: confirmed application count at each percentage. ${data.submitted} confirmed applications; ${data.unscored} have no recorded score.</desc><rect x="${x(80)}" y="${T}" width="${x(100)-x(80)}" height="${H-T-B}" class="chart-qualified"/>${grid}<line x1="${x(80)}" x2="${x(80)}" y1="${T}" y2="${H-B}" class="chart-threshold"/>${ticks}<line x1="${L}" x2="${W-R}" y1="${H-B}" y2="${H-B}" class="chart-axis"/>${data.submitted>data.unscored?`<polyline points="${points}" class="chart-line" pathLength="1"/>${dots}`:''}<text x="${(L+W-R)/2}" y="${H-8}" text-anchor="middle" class="chart-axis-title">Profile match (%)</text><text transform="translate(16 ${(T+H-B)/2}) rotate(-90)" text-anchor="middle" class="chart-axis-title">Jobs applied</text></svg>`;
}

async function refreshApplicationProgress() {
  const panel=document.querySelector('#application-progress');
  if (!panel || progressBusy) return;
  progressBusy=true;
  try {
    const data=await api('/api/applications/progress');
    if(!panel.isConnected) return;
    const signature=JSON.stringify({...data,updated_at:undefined});
    if(panel.dataset.ready && signature===progressSignature) return;
    progressSignature=signature; panel.dataset.ready='true';
    const rate=v=>v===null?'—':`${v}%`;
    panel.innerHTML=`<div class="row spread"><div><h2>Application success</h2><p class="muted">Confirmed applications by profile match percentage</p></div><span class="badge">Updates every 15s</span></div><div class="metrics progress-metrics"><div class="metric"><b>${data.submitted}</b>Jobs applied</div><div class="metric"><b>${rate(data.interview_rate)}</b>Interview success rate</div><div class="metric"><b>${rate(data.response_rate)}</b>Response rate</div></div><div class="progress-plot">${progressChart(data)}${data.submitted===0?'<p class="chart-empty">Your line will appear after the first confirmed application.</p>':''}</div><p class="chart-note">Interview success = applications with an interview or offer ÷ confirmed applications. Responses include rejections. Shaded area: your ≥80% match criterion. ${data.unscored?`${data.unscored} unscored application(s) excluded from the line. `:''}${data.legacy_current_scores?`${data.legacy_current_scores} older application(s) use current scores. `:''}New submissions keep their score at submission.</p>`;
  } catch(e) {
    if(panel.isConnected && !panel.dataset.ready) panel.innerHTML='<h2>Application success</h2><p class="muted">Unable to load progress. It will retry automatically.</p>';
  } finally { progressBusy=false; }
}
setInterval(()=>{if(document.body.dataset.screen==='applications' && !document.hidden) refreshApplicationProgress();},15000);
