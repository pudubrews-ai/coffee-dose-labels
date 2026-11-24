const $ = s => document.querySelector(s);
const FIELDS = [...document.querySelectorAll('[data-f]')];
let design = localStorage.getItem('design') || 'classic';

const data = () => {
  const o = {design, copies: Math.max(1, parseInt($('#copies').value) || 1)};
  FIELDS.forEach(i => o[i.dataset.f] = i.value.trim() || null);
  if (o.dose) o.dose = o.dose.replace(',', '.');   // '17,5' -> '17.5' (a number input would read it as 175)
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
/* ---- persisted form state (no messages, no in-flight extraction) ---- */
const KEY = 'labelForm';
let sealEdited = false;
const saved = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } })();
function save() {
  const o = {copies: $('#copies').value, sealEdited};
  FIELDS.forEach(i => { if (i.dataset.f !== 'seal_date' || sealEdited) o[i.dataset.f] = i.value; });
  localStorage.setItem(KEY, JSON.stringify(o));
}
FIELDS.forEach(i => { const k = i.dataset.f; if (k in saved && k !== 'seal_date') i.value = saved[k] || ''; });
if (saved.copies) $('#copies').value = saved.copies;
if (saved.sealEdited && saved.seal_date) { $('#seal_date').value = saved.seal_date; sealEdited = true; }
FIELDS.forEach(i => i.addEventListener('input', () => { if (i.dataset.f === 'seal_date') sealEdited = true; save(); schedulePreview(); }));
$('#copies').addEventListener('input', () => { save(); schedulePreview(); });
$('#clear').onclick = () => {
  FIELDS.forEach(i => { if (i.dataset.f !== 'seal_date') i.value = ''; });
  save(); updatePreview();
};

/* ---- designs ---- */
async function loadDesigns() {
  const j = await (await fetch('/api/designs')).json();
  if (!j.designs.some(d => d.id === design)) design = j.designs[0].id;
  if (!sealEdited) $('#seal_date').value = j.today;
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
const extractInputs = () => ['#url', '#url-go', '#file'].map($).filter(Boolean);
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
    save(); updatePreview();
  } catch (e) {
    show($('#extract-msg'), `${e.message.replace(/[.\s]+$/, '')}. You can still fill the fields in by hand.`, 'err');
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

/* ---- capabilities (is Claude-based auto-fill available?) ---- */
async function loadCaps() {
  let ok = true;
  try { const r = await fetch('/api/capabilities'); if (r.ok) ok = !!(await r.json()).extract; } catch (e) {}
  $('#extract-box').hidden = !ok; $('#extract-off').hidden = ok;
}

/* ---- printer picker ---- */
const sel = $('#printer-sel'), pmsg = (t, ok) => { $('#picker-msg').textContent = t || ''; $('#picker-msg').className = 'picker-msg' + (ok ? ' ok' : ''); };
let known = [];
function renderPrinters(list, selectedId) {
  const keep = list.slice();
  const cur = (() => { try { return JSON.parse(localStorage.getItem('printer')); } catch (e) { return null; } })();
  if (selectedId && !keep.some(p => p.id === selectedId) && cur && cur.id === selectedId) keep.push({id: cur.id, name: cur.name || 'Saved printer', missing: true});
  sel.innerHTML = '';
  if (!keep.length) sel.add(new Option('No printer found', ''));
  else if (!selectedId) sel.add(new Option('Choose a printer...', ''));
  keep.forEach(p => sel.add(new Option(p.name + (p.missing ? ' (not found)' : ''), p.id)));
  sel.value = selectedId || '';
}
async function choose(id, name) {
  const r = await fetch('/api/printer/select', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, name})});
  if (!r.ok) { pmsg(await errMsg(r, 'Could not select printer')); return false; }
  if (id) localStorage.setItem('printer', JSON.stringify({id, name})); else localStorage.removeItem('printer');
  return true;
}
async function scan(auto) {
  $('#scan').disabled = true; pmsg('Scanning for printers... (about 6 s)', true);
  try {
    const r = await fetch('/api/printers');
    if (!r.ok) { pmsg(await errMsg(r, 'Scan failed')); return; }
    const j = await r.json(); known = j.printers;
    let selId = j.selected;
    if (selId && !known.some(p => p.id === selId)) {
      pmsg('Your saved printer was not found. Switch it on, then press Scan again, or pick another.');
    } else if (!selId && known.length === 1) {
      if (await choose(known[0].id, known[0].name)) { selId = known[0].id; pmsg('Printer selected automatically.', true); }
    } else if (!known.length) {
      pmsg('No Phomemo printers found. Switch it on, keep it close, then press Scan.');
    } else if (!selId) pmsg('Several printers found. Choose yours.', true);
    else pmsg('', true);
    renderPrinters(known, selId);
  } catch (e) { pmsg('Scan failed. Is the server running?'); }
  finally { $('#scan').disabled = false; refreshStatus(); }
}
$('#scan').onclick = () => scan(false);
sel.onchange = async () => {
  const p = known.find(x => x.id === sel.value);
  if (await choose(sel.value || null, p ? p.name : null)) { pmsg('', true); $('#status-text').textContent = 'Checking printer...'; refreshStatus(); }
};
async function initPrinter() {
  let cur = null; try { cur = JSON.parse(localStorage.getItem('printer')); } catch (e) {}
  try {
    const srv = await (await fetch('/api/printer')).json();
    if (cur && cur.id && cur.id !== srv.id) await choose(cur.id, cur.name);   // browser memory wins; restores the server
    else if (srv.id && !cur) localStorage.setItem('printer', JSON.stringify({id: srv.id, name: srv.name}));
    const id = (cur && cur.id) || srv.id;
    if (id) renderPrinters([{id, name: (cur && cur.name) || srv.name || 'Saved printer'}], id);
  } catch (e) {}
  scan(true);
}

/* ---- printer status ---- */
async function refreshStatus() {
  const el = $('#status'), t = $('#status-text');
  try {
    const s = await (await fetch('/api/status')).json();
    if (s.busy) { el.className = 'status warn'; t.textContent = 'Printer busy printing'; return; }
    if (!s.selected && !s.connected) { el.className = 'status bad'; t.textContent = 'No printer selected'; return; }
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
  const g = Number(d.dose), n = Number($('#copies').value);
  if (!d.dose || !(g > 0 && g <= 1000)) {
    show(msg, d.dose ? 'The dose must be a number of grams above 0 and up to 1000.' : 'Enter the dose in grams first.', 'err');
    $('#dose').focus(); return;
  }
  if (!Number.isInteger(n) || n < 1 || n > 50) { show(msg, 'Copies must be a whole number from 1 to 50.', 'err'); $('#copies').focus(); return; }
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

loadDesigns(); loadCaps(); initPrinter();
