const $ = s => document.querySelector(s);
const FIELDS = [...document.querySelectorAll('[data-f]')];
let design = localStorage.getItem('design') || 'classic';

const data = () => {
  const o = {design, copies: Math.max(1, parseInt($('#copies').value) || 1)};
  FIELDS.forEach(i => o[i.dataset.f] = i.value.trim() || null);
  return o;
};
const show = (el, text, cls) => { el.hidden = !text; el.textContent = text || ''; el.className = 'msg ' + (cls || ''); };

/* ---- preview ---- */
let timer, seq = 0;
function schedulePreview() { clearTimeout(timer); timer = setTimeout(updatePreview, 250); }
async function updatePreview() {
  const my = ++seq;
  const r = await fetch('/api/preview', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data())});
  if (!r.ok || my !== seq) return;
  const url = URL.createObjectURL(await r.blob());
  const img = $('#preview'); const old = img.src; img.src = url; if (old.startsWith('blob:')) URL.revokeObjectURL(old);
}
FIELDS.forEach(i => i.addEventListener('input', schedulePreview));

/* ---- designs ---- */
async function loadDesigns() {
  const j = await (await fetch('/api/designs')).json();
  if (!j.designs.some(d => d.id === design)) design = j.designs[0].id;
  $('#seal_date').value = j.today;
  const box = $('#designs'); box.innerHTML = '';
  j.designs.forEach(d => {
    const l = document.createElement('label');
    l.innerHTML = `<input type="radio" name="design" value="${d.id}"> ${d.name}`;
    const r = l.firstChild; r.checked = d.id === design; l.classList.toggle('on', r.checked);
    r.onchange = () => { design = d.id; localStorage.setItem('design', d.id);
      box.querySelectorAll('label').forEach(x => x.classList.remove('on')); l.classList.add('on'); updatePreview(); };
    box.appendChild(l);
  });
  updatePreview();
}

/* ---- extraction ---- */
async function errMsg(r, fallback) {
  try {
    const j = await r.json();
    const d = j.error || j.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map(x => x.msg || JSON.stringify(x)).join('; ');
    if (d) return JSON.stringify(d);
  } catch (e) {}
  return `${fallback} (HTTP ${r.status})`;
}
let extracting = false;
const extractInputs = () => ['#url', '#url-go', '#file', '#cam'].map($);
async function extract(req) {
  if (extracting) return;
  extracting = true;
  show($('#extract-msg'), '');
  $('#busy').hidden = false;
  extractInputs().forEach(el => el.disabled = true);
  $('#drop').classList.add('disabled');
  try {
    const r = await req();
    if (!r.ok) throw new Error(await errMsg(r, 'Extraction failed'));
    const j = await r.json();
    FIELDS.forEach(i => { const k = i.dataset.f; if (k in j && k !== 'dose' && k !== 'seal_date') i.value = j[k] || ''; });
    const n = Object.entries(j).filter(([k, v]) => v && k !== 'source_url').length;
    show($('#extract-msg'), `Filled ${n} field(s). Check them before printing.`, 'ok');
    updatePreview();
  } catch (e) {
    show($('#extract-msg'), `${e.message}. You can still fill the fields in by hand.`, 'err');
  } finally {
    extracting = false; $('#busy').hidden = true;
    extractInputs().forEach(el => el.disabled = false); $('#drop').classList.remove('disabled');
  }
}
const doUrl = () => { const u = $('#url').value.trim(); if (u && !extracting) extract(() => fetch('/api/extract/url', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({url: u})})); };
const doFile = f => { if (!f || extracting) return; const fd = new FormData(); fd.append('file', f); extract(() => fetch('/api/extract/image', {method: 'POST', body: fd})); };
$('#url-go').onclick = doUrl;
$('#url').addEventListener('keydown', e => e.key === 'Enter' && doUrl());
$('#file').onchange = e => { doFile(e.target.files[0]); e.target.value = ''; };
const drop = $('#drop');
['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', e => doFile(e.dataTransfer.files[0]));
window.addEventListener('dragover', e => e.preventDefault());
window.addEventListener('drop', e => e.preventDefault());

/* ---- printer status ---- */
async function refreshStatus() {
  const el = $('#status'), t = $('#status-text');
  try {
    const s = await (await fetch('/api/status')).json();
    if (s.busy) { el.className = 'status warn'; t.textContent = 'Printer busy printing'; return; }
    if (!s.connected) { el.className = 'status bad'; t.textContent = s.error || 'Printer not connected'; return; }
    const bits = ['Connected'];
    bits.push(s.low_battery ? 'battery LOW' : s.battery != null ? `battery ${s.battery}%` : 'battery ?');
    bits.push(s.paper === false ? 'NO PAPER' : s.paper ? 'paper OK' : 'paper ?');
    if (s.hot) bits.push('head too hot');
    el.className = 'status ' + (s.paper === false || s.low_battery || s.hot ? 'warn' : 'ok');
    t.textContent = bits.join(' · ');
  } catch (e) { el.className = 'status bad'; t.textContent = 'Server unreachable'; }
}
$('#status-refresh').onclick = () => { $('#status-text').textContent = 'Checking printer...'; refreshStatus(); };
setInterval(() => { if (!document.hidden && !printing) refreshStatus(); }, 20000);

/* ---- print ---- */
let printing = false;
$('#print').onclick = async () => {
  const d = data(), msg = $('#print-msg');
  if (!(parseFloat(d.dose) > 0)) { show(msg, 'Enter the dose in grams first.', 'err'); $('#dose').focus(); return; }
  printing = true; $('#print').disabled = true;
  show(msg, `Printing ${d.copies} label(s)...`, 'info');
  const poll = setInterval(async () => { try { const p = await (await fetch('/api/print/progress')).json();
    if (p.state === 'connecting' || p.state === 'printing') show(msg, `${p.message} (${p.done}/${p.total} done)`, 'info'); } catch (e) {} }, 700);
  try {
    const r = await fetch('/api/print', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(d)});
    if (!r.ok) throw new Error(await errMsg(r, 'Print failed'));
    const j = await r.json();
    show(msg, `Printed ${j.printed} label(s). Change the dose to print another batch.`, 'ok');
  } catch (e) { show(msg, e.message, 'err'); }
  finally { clearInterval(poll); printing = false; $('#print').disabled = false; refreshStatus(); }
};

loadDesigns(); refreshStatus();
