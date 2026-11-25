/* thinkNXG Estate - Tenant Self-Service Portal (/tenant-self-service)
   Vanilla JS single-page app. Every value is read from the server API
   (thinknxg_estate.core.tenant_self_service); nothing here is hard-coded tenant data.
   All interpolated values are HTML-escaped by the `html` tag. */
(function () {
  'use strict';

  const T = window.TSS || {};
  const API = '/api/method/thinknxg_estate.core.tenant_self_service.';
  const LOGIN_API = '/api/method/thinknxg_estate.core.tenant_portal_api.';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  /* ------------------------------------------------------------- templating */
  class Raw { constructor(v) { this.v = v; } }
  const raw = (v) => new Raw(v);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  function val(v) {
    if (v instanceof Raw) return v.v;
    if (Array.isArray(v)) return v.map(val).join('');
    if (v == null || v === false) return '';
    return esc(v);
  }
  function html(strings, ...vals) {
    let out = '';
    strings.forEach((s, i) => { out += s; if (i < vals.length) out += val(vals[i]); });
    return new Raw(out);
  }
  const mount = (el, r) => { el.innerHTML = r instanceof Raw ? r.v : String(r); };

  /* ---------------------------------------------------------------- icons */
  const P = {
    home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    building: '<path d="M4 21V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v16M14 9h5a1 1 0 0 1 1 1v11M2 21h20M8 8h2M8 12h2M8 16h2"/>',
    file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    wallet: '<path d="M3 7a2 2 0 0 1 2-2h13v4"/><path d="M3 7v11a2 2 0 0 0 2 2h14a1 1 0 0 0 1-1v-9a1 1 0 0 0-1-1H5a2 2 0 0 1-2-2z"/><circle cx="16.5" cy="14.5" r="1"/>',
    wrench: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18v3h3l6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    folder: '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    clip: '<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4h6v3H9zM9 12h6M9 16h4"/>',
    msg: '<path d="M21 12a8 8 0 0 1-11.5 7.2L3 21l1.8-5.5A8 8 0 1 1 21 12z"/>',
    mega: '<path d="M3 11v2a1 1 0 0 0 1 1h3l8 4V6L7 10H4a1 1 0 0 0-1 1zM19 9a4 4 0 0 1 0 6"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M16 7l3 3M14 9l2 2"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    bell: '<path d="M6 9a6 6 0 0 1 12 0c0 6 2 7 2 8H4c0-1 2-2 2-8zM10 21h4"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.4-1 1-1 1.7M12 17h.01"/>',
    menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
    down: '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    check: '<path d="m5 12 5 5 9-10"/>',
    alert: '<path d="M12 3 2 20h20zM12 10v4M12 17h.01"/>',
    cal: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/>',
    out: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
    insp: '<path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="m9 14 2 2 4-4"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    send: '<path d="m22 2-11 11M22 2l-7 20-4-9-9-4z"/>',
    mail: '<path d="M3 5h18v14H3zM3 6l9 7 9-7"/>',
    phone: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    receipt: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6"/>',
    chev: '<path d="m9 6 6 6-6 6"/>',
    eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    up: '<path d="M12 15V3M7 8l5-5 5 5M4 21h16"/>',
    bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  };
  const ic = (n) => raw(`<svg class="i" viewBox="0 0 24 24" aria-hidden="true">${P[n] || ''}</svg>`);

  /* ------------------------------------------------------------ formatting */
  const S = {
    token: null, lease: null, boot: null, mode: null, route: 'overview', seen: 0, info: null,
    blobs: {}, search: null,
  };
  try { S.token = localStorage.getItem('tss_token'); S.lease = sessionStorage.getItem('tss_lease'); S.seen = +(localStorage.getItem('tss_seen') || 0); } catch (e) { /* storage blocked */ }

  const cur = () => (S.boot && S.boot.currency) || 'AED';
  function money(n, opts) {
    const v = Number(n || 0);
    try { return new Intl.NumberFormat('en-US', Object.assign({ style: 'currency', currency: cur(), currencyDisplay: 'code', minimumFractionDigits: 2 }, opts || {})).format(v); }
    catch (e) { return cur() + ' ' + v.toFixed(2); }
  }
  const parseDate = (d) => (d ? new Date(String(d).replace(' ', 'T').slice(0, 19)) : null);
  const fmtDate = (d) => { const x = parseDate(d); return x && !isNaN(x) ? x.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '-'; };
  const fmtDT = (d) => { const x = parseDate(d); return x && !isNaN(x) ? x.toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-'; };
  const rel = (days) => (days === 0 ? 'today' : days > 0 ? `in ${days} day${days === 1 ? '' : 's'}` : `${-days} day${days === -1 ? '' : 's'} ago`);
  const initials = (n) => String(n || '?').split(/\s+/).slice(0, 2).map((x) => x[0]).join('').toUpperCase();

  const TONES = {
    Paid: 'good', Completed: 'good', Approved: 'good', Cleared: 'good', Held: 'good', Active: 'good', Good: 'good', Refunded: 'good', valid: 'good',
    Overdue: 'bad', Bounced: 'bad', Rejected: 'bad', Damaged: 'bad', Missing: 'bad', Expired: 'bad', expired: 'bad', Forfeited: 'bad', Emergency: 'bad',
    'Partially Paid': 'warn', 'On Hold': 'warn', Expiring: 'warn', Fair: 'warn', expiring: 'warn', soon: 'warn', High: 'warn', 'Partially Refunded': 'warn',
    Pending: 'info', Invoiced: 'info', 'In Progress': 'info', 'In Review': 'info', Open: 'info', Submitted: 'info', Assigned: 'info', Received: 'info', Deposited: 'info', Medium: 'info',
  };
  const pill = (s, label) => html`<span class="pill ${TONES[s] || ''}">${label || s || '-'}</span>`;

  /* ------------------------------------------------------------------- API */
  const LEASE_AWARE = new Set(['bootstrap', 'overview', 'my_property', 'lease_detail', 'payments', 'documents', 'inspections', 'notifications']);

  function friendly(data, status) {
    try {
      if (data && data._server_messages) {
        const m = JSON.parse(data._server_messages).map((x) => JSON.parse(x).message);
        if (m.length) return m.join(' ').replace(/<[^>]+>/g, '');
      }
    } catch (e) { /* fall through */ }
    if (data && data.exception) return String(data.exception).split(': ').slice(1).join(': ').replace(/<[^>]+>/g, '') || 'Something went wrong.';
    return status === 429 ? 'Too many requests. Please wait a moment and try again.' : 'Something went wrong. Please try again.';
  }
  class ApiError extends Error { constructor(msg, status) { super(msg); this.status = status; } }

  async function call(base, method, params, post, extra) {
    const headers = Object.assign({ Accept: 'application/json' }, extra || {});
    if (S.token && base === API) headers['X-Tenant-Token'] = S.token;
    params = Object.assign({}, params || {});
    if (base === API && S.lease && LEASE_AWARE.has(method) && !params.lease) params.lease = S.lease;
    let url = base + method;
    const init = { method: post ? 'POST' : 'GET', headers, credentials: 'same-origin' };
    if (post) {
      headers['Content-Type'] = 'application/json';
      if (T.csrf) headers['X-Frappe-CSRF-Token'] = T.csrf;
      init.body = JSON.stringify(params);
    } else {
      const q = new URLSearchParams();
      Object.keys(params).forEach((k) => { if (params[k] != null && params[k] !== '') q.set(k, params[k]); });
      if ([...q].length) url += '?' + q.toString();
    }
    const res = await fetch(url, init);
    let data = null;
    try { data = await res.json(); } catch (e) { /* binary or empty */ }
    if (!res.ok) throw new ApiError(friendly(data, res.status), res.status);
    return data ? data.message : null;
  }
  const api = (m, p) => call(API, m, p, false);
  const apiPost = (m, p) => call(API, m, p, true);

  async function fetchBlob(kind, ref) {
    const key = kind + '|' + ref;
    if (S.blobs[key]) return S.blobs[key];
    const q = new URLSearchParams({ kind, ref });
    const headers = {};
    if (S.token) headers['X-Tenant-Token'] = S.token;
    const res = await fetch(API + 'download?' + q.toString(), { headers, credentials: 'same-origin' });
    if (!res.ok) { let d = null; try { d = await res.json(); } catch (e) { /* ignore */ } throw new ApiError(friendly(d, res.status), res.status); }
    const blob = await res.blob();
    const disp = res.headers.get('Content-Disposition') || '';
    const m = disp.match(/filename\*?=(?:UTF-8'')?"?([^";]+)/i);
    const out = { url: URL.createObjectURL(blob), type: blob.type, name: m ? decodeURIComponent(m[1]) : ref.split('/').pop() };
    S.blobs[key] = out;
    return out;
  }
  async function saveDoc(kind, ref, btn) {
    try {
      busy(btn, true);
      const b = await fetchBlob(kind, ref);
      const a = document.createElement('a');
      a.href = b.url; a.download = b.name; document.body.appendChild(a); a.click(); a.remove();
    } catch (e) { toast(e.message, 'bad'); } finally { busy(btn, false); }
  }
  const isPublic = (u) => u && !String(u).startsWith('/private/');
  async function previewDoc(kind, ref, title) {
    const dlg = openDialog({ title: title || 'Preview', body: html`<div class="skel" style="height:320px"></div>`, wide: true, actions: [] });
    try {
      const b = await fetchBlob(kind, ref);
      const body = $('.dlg-b', dlg);
      if ((b.type || '').startsWith('image/')) mount(body, html`<img src="${b.url}" alt="" style="max-width:100%;border-radius:10px">`);
      else if (b.type === 'application/pdf') mount(body, html`<iframe src="${b.url}" title="${title || 'Document'}" style="width:100%;height:70vh;border:0;border-radius:10px"></iframe>`);
      else mount(body, html`<p>This file type cannot be previewed.</p>`);
      const f = $('.dlg-f', dlg); mount(f, html`<button class="btn" data-close>Close</button><a class="btn primary" href="${b.url}" download="${b.name}">${ic('down')} Download</a>`);
      $('[data-close]', dlg).onclick = () => dlg.close();
    } catch (e) { mount($('.dlg-b', dlg), html`<div class="banner bad"><div class="grow">${e.message}</div></div>`); }
  }
  /* loads private images lazily through the secure gateway */
  function hydrateImages(root) {
    $$('img[data-priv]', root).forEach(async (img) => {
      try { const b = await fetchBlob('file', img.dataset.priv); img.src = b.url; img.removeAttribute('data-priv'); } catch (e) { img.alt = 'Unavailable'; }
    });
  }
  const imgTag = (u, alt, cls) => (isPublic(u) ? html`<img src="${u}" alt="${alt || ''}" class="${cls || ''}" loading="lazy">` : html`<img data-priv="${u}" alt="${alt || ''}" class="${cls || ''}" src="data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==">`);

  /* -------------------------------------------------------------- UI utils */
  function toast(msg, tone) {
    const el = document.createElement('div');
    el.className = 'toast ' + (tone || ''); el.textContent = msg;
    $('#toasts').appendChild(el); setTimeout(() => el.remove(), tone === 'bad' ? 6000 : 3500);
  }
  function busy(btn, on) {
    if (!btn) return;
    if (on) { btn.dataset.l = btn.innerHTML; btn.disabled = true; btn.innerHTML = '<span class="spin"></span>'; }
    else if (btn.dataset.l != null) { btn.disabled = false; btn.innerHTML = btn.dataset.l; }
  }
  function openDialog({ title, body, actions, wide, onSubmit }) {
    const dlg = document.createElement('dialog');
    dlg.className = 'dlg'; if (wide) dlg.style.width = 'min(860px, calc(100vw - 24px))';
    dlg.setAttribute('aria-label', title);
    mount(dlg, html`<form method="dialog" novalidate><div class="dlg-h"><h3>${title}</h3><button type="button" class="icon-btn" data-close aria-label="Close">${ic('x')}</button></div><div class="dlg-b">${body}</div><div class="dlg-f">${(actions || []).map((a) => html`<button type="${a.primary ? 'submit' : 'button'}" class="btn ${a.primary ? 'primary' : ''} ${a.danger ? 'danger' : ''}" data-act="${a.id || ''}">${a.label}</button>`)}</div></form>`);
    document.body.appendChild(dlg);
    dlg.querySelector('[data-close]').onclick = () => dlg.close();
    dlg.addEventListener('close', () => dlg.remove());
    const f = $('form', dlg);
    f.onsubmit = async (e) => {
      e.preventDefault();
      if (!onSubmit) return;
      const btn = $('button[type=submit]', dlg);
      try { busy(btn, true); const keep = await onSubmit(f, dlg); if (keep !== false) dlg.close(); }
      catch (err) { const ex = $('.field-error.top', dlg); if (ex) ex.remove(); $('.dlg-b', dlg).insertAdjacentHTML('afterbegin', `<div class="banner bad field-error top" role="alert"><div class="grow">${esc(err.message)}</div></div>`); }
      finally { busy(btn, false); }
    };
    $$('button[data-act=cancel]', dlg).forEach((b) => { b.onclick = () => dlg.close(); });
    dlg.showModal();
    return dlg;
  }
  const confirmDlg = (title, text, label) => new Promise((resolve) => {
    let done = false;
    const d = openDialog({ title, body: html`<p>${text}</p>`, actions: [{ id: 'cancel', label: 'Cancel' }, { id: 'ok', label: label || 'Confirm', primary: true }], onSubmit: () => { done = true; resolve(true); } });
    d.addEventListener('close', () => { if (!done) resolve(false); });
  });
  const skeleton = () => html`<div class="grid g-metrics">${[1, 2, 3, 4].map(() => html`<div class="card"><div class="metric"><div class="skel" style="height:14px;width:60%"></div><div class="skel" style="height:28px;width:80%;margin-top:8px"></div></div></div>`)}</div><div class="card"><div class="card-b"><div class="skel" style="height:14px;width:40%"></div><div class="skel" style="height:90px;margin-top:14px"></div></div></div>`;
  const empty = (icon, title, text, action) => html`<div class="empty"><div class="ico">${ic(icon)}</div><b>${title}</b><div>${text || ''}</div>${action ? html`<div style="margin-top:14px">${action}</div>` : ''}</div>`;
  const metric = (icon, k, v, s, tone, extra) => html`<div class="card metric ${tone || ''}"><div class="k">${ic(icon)}${k}</div><div class="v num">${v}</div><div class="s">${s || ''}</div>${extra || ''}</div>`;
  const head = (title, sub, actions, crumb) => html`<div class="crumbs">Home <span aria-hidden="true">/</span> ${crumb || title}</div><div class="page-head"><div><h1>${title}</h1>${sub ? html`<p>${sub}</p>` : ''}</div><div class="page-actions">${actions || ''}</div></div>`;

  function donut(parts, centerLabel, centerVal) {
    const total = parts.reduce((a, p) => a + p.v, 0) || 1;
    let off = 0; const r = 52, c = 2 * Math.PI * r;
    const arcs = parts.filter((p) => p.v > 0).map((p) => { const len = (p.v / total) * c; const a = `<circle cx="70" cy="70" r="${r}" fill="none" stroke="${p.c}" stroke-width="16" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-off}" transform="rotate(-90 70 70)"/>`; off += len; return a; }).join('');
    return html`<div class="donut-wrap"><svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label="${centerLabel}: ${centerVal}"><circle cx="70" cy="70" r="${r}" fill="none" stroke="#eef2f7" stroke-width="16"/>${raw(arcs)}<text x="70" y="66" text-anchor="middle" font-size="11" fill="#64748b">${centerLabel}</text><text x="70" y="86" text-anchor="middle" font-size="16" font-weight="700" fill="#0f172a">${centerVal}</text></svg><div class="legend">${parts.map((p) => html`<span><i style="background:${p.c}"></i>${p.l}<b class="num" style="margin-inline-start:auto">${money(p.v)}</b></span>`)}</div></div>`;
  }

  /* -------------------------------------------------------- file attachments */
  function attachWidget(root, max) {
    const state = { ids: [], busy: 0 };
    const zone = $('[data-attach]', root); if (!zone) return state;
    const input = $('input[type=file]', zone), list = $('.files', zone);
    const draw = () => mount(list, html`${state.ids.map((f, i) => html`<span class="chip">${f.name}<button type="button" data-rm="${i}" aria-label="Remove ${f.name}">${ic('x')}</button></span>`)}`);
    zone.addEventListener('click', (e) => {
      const rm = e.target.closest('[data-rm]');
      if (rm) { state.ids.splice(+rm.dataset.rm, 1); draw(); return; }
      if (e.target.closest('.drop')) input.click();
    });
    input.addEventListener('change', async () => {
      for (const f of Array.from(input.files)) {
        if (state.ids.length >= (max || 4)) { toast('You can attach up to ' + (max || 4) + ' files.', 'bad'); break; }
        if (f.size > 8 * 1024 * 1024) { toast(f.name + ' is larger than 8 MB.', 'bad'); continue; }
        try { state.busy++; const r = await uploadFile(f); state.ids.push({ id: r.id, name: f.name }); draw(); }
        catch (e) { toast(e.message, 'bad'); } finally { state.busy--; }
      }
      input.value = '';
    });
    return state;
  }
  async function uploadFile(file, purpose) {
    const fd = new FormData(); fd.append('file', file); if (purpose) fd.append('purpose', purpose);
    const headers = {}; if (S.token) headers['X-Tenant-Token'] = S.token; if (T.csrf) headers['X-Frappe-CSRF-Token'] = T.csrf;
    const res = await fetch(API + 'upload', { method: 'POST', headers, body: fd, credentials: 'same-origin' });
    let d = null; try { d = await res.json(); } catch (e) { /* ignore */ }
    if (!res.ok) throw new ApiError(friendly(d, res.status), res.status);
    return d.message;
  }
  const attachHtml = html`<div class="field" data-attach><label>Photos or documents <span class="hint">(optional, JPG / PNG / PDF, up to 8 MB)</span></label><div class="drop" tabindex="0" role="button">${ic('up')} Click to add files</div><input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" multiple hidden><div class="files"></div></div>`;

  /* ------------------------------------------------------------ app shell */
  const NAV = [
    ['overview', 'Overview', 'home'], ['property', 'My Property', 'building'], ['lease', 'My Lease', 'file'],
    ['payments', 'Rent & Payments', 'wallet'], ['maintenance', 'Maintenance', 'wrench'], ['documents', 'Documents', 'folder'],
    ['requests', 'Service Requests', 'clip'], ['messages', 'Messages', 'msg'], ['announcements', 'Announcements', 'mega'],
    ['moves', 'Move-in / Move-out', 'insp'], ['profile', 'Profile & Settings', 'user'],
  ];
  const TAB = ['overview', 'payments', 'maintenance', 'documents', 'profile'];
  const app = () => $('#app');

  function renderShell() {
    const b = S.boot, t = b.tenant;
    mount(app(), html`
      <div class="shell">
        <header class="topbar">
          <button class="icon-btn menu-toggle" id="menu-btn" aria-label="Open navigation">${ic('menu')}</button>
          <a class="logo" href="#/overview"><img src="${T.logo}" alt=""><span>${T.title || 'thinkNXG Estate'}<small>Tenant portal</small></span></a>
          <div class="top-grow">
            ${b.leases.length > 1 ? html`<select class="select lease-select" id="lease-sel" aria-label="Property">${b.leases.map((l) => html`<option value="${l.name}" ${l.name === b.current_lease ? raw('selected') : ''}>${l.label}</option>`)}</select>` : ''}
            <div class="search"><span>${ic('search')}</span><input class="input" id="gsearch" type="search" placeholder="Search pages, documents, requests" aria-label="Search" autocomplete="off"><div class="search-pop" id="spop" hidden></div></div>
          </div>
          <div class="top-actions">
            <div class="menu-wrap"><button class="icon-btn" id="bell" aria-label="Notifications" aria-haspopup="true">${ic('bell')}<span class="dot" id="bell-dot" hidden></span></button><div class="pop" id="bell-pop" hidden></div></div>
            <div class="menu-wrap"><button class="icon-btn" id="help-btn" aria-label="Help and support" aria-haspopup="true">${ic('help')}</button><div class="pop" id="help-pop" hidden></div></div>
            <div class="menu-wrap"><button class="user-btn" id="user-btn" aria-haspopup="true"><span class="avatar">${initials(t.tenant_name)}</span><span class="uname">${t.tenant_name}</span></button>
              <div class="pop pop-menu" id="user-pop" hidden style="width:240px"><div class="pop-head"><div><b>${t.tenant_name}</b><br><small style="color:var(--muted);font-weight:400">${t.email || t.mobile || ''}</small></div></div><a href="#/profile">${ic('user')} Profile & settings</a><button id="signout">${ic('out')} Sign out</button></div></div>
          </div>
        </header>
        <aside class="sidebar" id="sidebar"><nav class="nav" aria-label="Tenant portal">${NAV.map(([id, label, icon]) => html`<a href="#/${id}" data-r="${id}">${ic(icon)}<span>${label}</span>${id === 'maintenance' && b.counters.open_maintenance ? html`<span class="badge">${b.counters.open_maintenance}</span>` : ''}${id === 'requests' && b.counters.open_requests ? html`<span class="badge">${b.counters.open_requests}</span>` : ''}</a>`)}</nav>
          <div class="side-foot"><b>Need a hand?</b>Message the property management team from <a href="#/messages">Messages</a>${b.contact.whatsapp ? html` or reach us on <a href="https://wa.me/${String(b.contact.whatsapp).replace(/\D/g, '')}" target="_blank" rel="noopener">WhatsApp</a>` : ''}.</div></aside>
        <main class="main" id="main" tabindex="-1"></main>
      </div>
      <div class="scrim" id="scrim"></div>
      <nav class="tabbar" aria-label="Quick navigation">${TAB.map((id) => { const n = NAV.find((x) => x[0] === id); return html`<a href="#/${id}" data-r="${id}">${ic(n[2])}<span>${n[1].split(' ')[0].replace('&', '')}</span></a>`; })}</nav>`);
    wireShell();
  }

  function popToggle(btnSel, popSel, onOpen) {
    const btn = $(btnSel), pop = $(popSel);
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const was = !pop.hidden;
      $$('.pop').forEach((p) => { p.hidden = true; });
      pop.hidden = was; if (!was && onOpen) onOpen(pop);
    });
  }
  function wireShell() {
    $('#menu-btn').onclick = () => document.body.classList.toggle('nav-open');
    $('#scrim').onclick = () => document.body.classList.remove('nav-open');
    document.addEventListener('click', (e) => { if (!e.target.closest('.menu-wrap')) $$('.pop').forEach((p) => { p.hidden = true; }); if (!e.target.closest('.search')) { const sp = $('#spop'); if (sp) sp.hidden = true; } });
    const sel = $('#lease-sel');
    if (sel) sel.onchange = () => { S.lease = sel.value; try { sessionStorage.setItem('tss_lease', S.lease); } catch (e) { /* ignore */ } S.search = null; route(); };
    $('#signout').onclick = signOut;
    popToggle('#user-btn', '#user-pop');
    popToggle('#bell', '#bell-pop', loadBell);
    popToggle('#help-btn', '#help-pop', drawHelp);
    wireSearch(); refreshBellDot();
  }
  async function refreshBellDot() {
    try {
      const n = await api('notifications');
      const fresh = n.items.filter((i) => +new Date(String(i.when).replace(' ', 'T')) > S.seen).length;
      const d = $('#bell-dot'); if (d) { d.hidden = !fresh; d.textContent = fresh; }
      S.notes = n.items;
    } catch (e) { /* non-critical */ }
  }
  async function loadBell(pop) {
    mount(pop, html`<div class="pop-head">Notifications</div><div class="pop-body"><div class="skel" style="height:60px;margin:12px"></div></div>`);
    try {
      const n = await api('notifications'); S.notes = n.items;
      mount(pop, html`<div class="pop-head">Notifications<small style="color:var(--muted);font-weight:400">${n.items.length} recent</small></div><div class="pop-body">${n.items.length ? n.items.map((i) => html`<a class="pop-item" href="#/${i.route}"><span class="ico ${i.tone === 'neutral' ? '' : i.tone}">${ic(i.tone === 'bad' ? 'alert' : i.tone === 'warn' ? 'cal' : 'bell')}</span><span><b>${i.title}</b><small>${i.detail}</small></span></a>`) : empty('check', 'You are all caught up', 'Nothing needs your attention.')}</div>`);
      S.seen = Date.now(); try { localStorage.setItem('tss_seen', String(S.seen)); } catch (e) { /* ignore */ }
      const d = $('#bell-dot'); if (d) d.hidden = true;
    } catch (e) { mount(pop, html`<div class="pop-head">Notifications</div><div class="pop-body"><div class="empty">${e.message}</div></div>`); }
  }
  function drawHelp(pop) {
    const c = S.boot.contact;
    mount(pop, html`<div class="pop-head">Help &amp; support</div><div class="pop-menu"><a href="#/messages" data-new-msg>${ic('msg')} Send a message to management</a>${c.whatsapp ? html`<a href="https://wa.me/${String(c.whatsapp).replace(/\D/g, '')}" target="_blank" rel="noopener">${ic('phone')} WhatsApp ${c.whatsapp}</a>` : ''}${c.email ? html`<a href="mailto:${c.email}">${ic('mail')} ${c.email}</a>` : ''}<a href="#/maintenance">${ic('wrench')} Report a maintenance issue</a></div>`);
  }
  function wireSearch() {
    const input = $('#gsearch'), pop = $('#spop');
    if (!input) return;
    const load = async () => {
      if (S.search) return S.search;
      const [d, m, r] = await Promise.all([api('documents').catch(() => ({ documents: [] })), api('maintenance').catch(() => ({ requests: [] })), api('service_requests').catch(() => ({ requests: [] }))]);
      S.search = [
        ...NAV.map(([id, l]) => ({ t: l, s: 'Page', go: '#/' + id })),
        ...d.documents.map((x) => ({ t: x.title, s: x.category, go: '#/documents' })),
        ...m.requests.map((x) => ({ t: `${x.name} - ${x.category || 'Maintenance'}`, s: x.stage, go: '#/maintenance' })),
        ...r.requests.map((x) => ({ t: `${x.name} - ${x.subject}`, s: x.status, go: '#/requests' })),
      ];
      return S.search;
    };
    input.addEventListener('focus', () => { load(); });
    input.addEventListener('input', async () => {
      const q = input.value.trim().toLowerCase();
      if (!q) { pop.hidden = true; return; }
      const idx = await load();
      const hits = idx.filter((x) => (x.t + ' ' + x.s).toLowerCase().includes(q)).slice(0, 8);
      mount(pop, hits.length ? html`${hits.map((h) => html`<a href="${h.go}"><span>${h.t}</span><small>${h.s}</small></a>`)}` : html`<div class="empty" style="padding:16px">No matches</div>`);
      pop.hidden = false;
    });
    pop.addEventListener('click', () => { pop.hidden = true; input.value = ''; });
  }

  /* --------------------------------------------------------------- routing */
  const PAGES = {};
  async function route() {
    const id = (location.hash.replace(/^#\//, '') || 'overview').split('?')[0];
    S.route = PAGES[id] ? id : 'overview';
    document.body.classList.remove('nav-open');
    $$('[data-r]').forEach((a) => { a.classList.toggle('on', a.dataset.r === S.route); if (a.dataset.r === S.route) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    const main = $('#main'); if (!main) return;
    mount(main, skeleton());
    document.title = (NAV.find((n) => n[0] === S.route) || [0, 'My Tenancy'])[1] + ' · ' + (T.title || 'thinkNXG Estate');
    try {
      await PAGES[S.route](main);
      hydrateImages(main);
      main.focus({ preventScroll: true }); window.scrollTo(0, 0);
    } catch (e) {
      if (e.status === 401) return showSignIn('Your session has ended. Please sign in again.');
      mount(main, html`<div class="card"><div class="card-b">${empty('alert', 'We could not load this page', e.message, html`<button class="btn primary" id="retry">Try again</button>`)}</div></div>`);
      const r = $('#retry'); if (r) r.onclick = route;
    }
  }
  window.addEventListener('hashchange', () => { if (S.boot) route(); });

  /* ----------------------------------------------------------------- pages */
  PAGES.overview = async (el) => {
    const o = await api('overview');
    if (!o.has_lease) {
      mount(el, html`${head('Welcome', 'Your tenancy at a glance')}<div class="card"><div class="card-b">${empty('building', 'No active lease on your account yet', 'Once the leasing team submits your lease, your rent, documents and requests will appear here.', html`<a class="btn primary" href="#/messages">Message the leasing team</a>`)}</div></div>`);
      return;
    }
    const m = o.metrics, L = o.lease, due = m.next_due;
    const total = m.paid_to_date + m.remaining_contract_balance;
    const upcomingOnly = Math.max(m.remaining_contract_balance - m.outstanding_balance, 0);
    mount(el, html`
      <div class="card welcome"><div><h1>Welcome back, ${(o.tenant.tenant_name || '').split(' ')[0]}</h1><p>${new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p>
        <div class="chips"><span class="chip">${ic('building')} ${L.property_name || 'Property'}</span><span class="chip">${ic('key')} Unit ${L.unit_no || '-'}${L.unit_type ? ' · ' + L.unit_type : ''}</span><span class="chip">${pill(L.status)}</span></div></div>
        <div class="page-actions"><button class="btn primary" data-q="maintenance">${ic('plus')} New maintenance request</button><a class="btn" href="#/payments">${ic('wallet')} Rent & payments</a></div></div>
      ${m.overdue_count ? html`<div class="banner bad" role="alert">${ic('alert')}<div class="grow"><b>${money(m.overdue_amount)} overdue</b> across ${m.overdue_count} instalment${m.overdue_count > 1 ? 's' : ''}. Please arrange payment with your property manager.</div><a class="btn sm" href="#/payments">View ledger</a></div>` : ''}
      <div class="grid g-metrics six">
        ${metric('wallet', 'Monthly rent', money(m.monthly_rent), 'Contract average · ' + (L.payment_frequency || ''))}
        ${metric('cal', 'Next rent due', due ? money(due.amount) : 'Nothing due', due ? `${fmtDate(due.due_date)} · ${rel(due.days)}` : 'You are fully paid up', due && due.status === 'Overdue' ? 'bad' : due && due.days <= 7 ? 'warn' : '')}
        ${metric('alert', 'Outstanding balance', money(m.outstanding_balance), m.outstanding_balance ? 'Due now' : 'Nothing overdue', m.outstanding_balance ? 'bad' : 'good')}
        ${metric('file', 'Lease expiry', fmtDate(L.end_date), L.days_left >= 0 ? `${L.days_left} days left` : 'Expired', L.days_left <= 60 ? 'warn' : '', html`<div class="bar" aria-hidden="true"><i style="width:${L.progress}%"></i></div>`)}
        ${metric('wrench', 'Open maintenance', m.open_maintenance, m.open_maintenance ? 'In progress with our team' : 'No open requests')}
        ${metric('shield', 'Security deposit', money(m.deposit.amount), m.deposit.status ? `${m.deposit.status}` : 'Not yet recorded')}
      </div>
      <div class="grid g-main">
        <div class="stack">
          <div class="card"><div class="card-h"><h3>Rent overview</h3><a href="#/payments">Full ledger ${ic('chev')}</a></div><div class="card-b">
            ${donut([{ l: 'Paid', v: m.paid_to_date, c: '#34d399' }, { l: 'Due now', v: m.outstanding_balance, c: '#f87171' }, { l: 'Upcoming', v: upcomingOnly, c: '#818cf8' }], 'Contract', new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(total))}
            <div class="list" style="margin-top:18px">${o.upcoming.length ? o.upcoming.map((i) => html`<div class="li"><span class="ico ${TONES[i.status] || ''}">${ic('cal')}</span><div class="grow"><div class="t">Instalment ${i.installment_no || ''} · ${fmtDate(i.due_date)}</div><div class="d">${money(i.outstanding)} outstanding of ${money(i.amount)}</div></div>${pill(i.status)}</div>`) : html`<div class="d" style="color:var(--muted)">No upcoming instalments.</div>`}</div></div></div>
          <div class="card"><div class="card-h"><h3>Maintenance</h3><a href="#/maintenance">All requests ${ic('chev')}</a></div><div class="card-b">${o.maintenance.length ? html`<div class="list">${o.maintenance.slice(0, 4).map((r) => html`<div class="li"><span class="ico info">${ic('wrench')}</span><div class="grow"><div class="t">${r.category || 'Maintenance'} <span class="num" style="color:var(--muted);font-weight:400">${r.name}</span></div><div class="d">${(r.description || '').slice(0, 80)}</div></div>${pill(r.stage)}</div>`)}</div>` : empty('wrench', 'No maintenance requests', 'Report an issue and track it here.')}</div></div>
        </div>
        <div class="stack">
          <div class="card"><div class="card-h"><h3>Quick actions</h3></div><div class="card-b"><div class="quick">
            <button data-q="maintenance"><span class="q-i">${ic('wrench')}</span>Report an issue</button>
            <button data-q="renewal"><span class="q-i">${ic('file')}</span>Request renewal</button>
            <button data-q="message"><span class="q-i">${ic('msg')}</span>Message management</button>
            <button data-q="parking"><span class="q-i">${ic('key')}</span>Access card / parking</button></div></div></div>
          <div class="card"><div class="card-h"><h3>Lease</h3></div><div class="card-b"><dl class="kv"><dt>Contract</dt><dd>${L.name}</dd><dt>Term</dt><dd>${fmtDate(L.start_date)} - ${fmtDate(L.end_date)}</dd><dt>Contract value</dt><dd class="num">${money(L.total_contract_value)}</dd><dt>Renewal</dt><dd>${L.auto_renew ? 'Auto-renews' : 'Manual · ' + (L.notice_period_days || 0) + ' days notice'}</dd></dl><div class="progress" style="margin-top:14px"><i style="width:${L.progress}%"></i></div></div></div>
          <div class="card"><div class="card-h"><h3>Recent activity</h3></div><div class="card-b">${o.activity.length ? html`<div class="timeline">${o.activity.map((a) => html`<div class="tl"><i></i><div><b>${a.title}</b><small>${fmtDate(a.when)} · ${a.detail || ''}</small></div></div>`)}</div>` : empty('bell', 'No activity yet')}</div></div>
          <div class="card"><div class="card-h"><h3>Announcements</h3><a href="#/announcements">All ${ic('chev')}</a></div><div class="card-b">${o.announcements.length ? html`<div class="list">${o.announcements.map((a) => html`<div class="li"><span class="ico">${ic('mega')}</span><div class="grow"><div class="t">${a.title}</div><div class="d">${a.category}</div></div></div>`)}</div>` : empty('mega', 'No announcements', 'Notices from management will appear here.')}</div></div>
        </div>
      </div>`);
    el.onclick = (e) => {
      const q = e.target.closest('[data-q]'); if (!q) return;
      ({ maintenance: () => newMaintenance(), renewal: () => newRequest('Renewal Request'), message: () => newMessage(), parking: () => newRequest('Key / Access Card Request') })[q.dataset.q]();
    };
  };

  PAGES.property = async (el) => {
    const p = await api('my_property');
    if (!p.has_lease) { mount(el, html`${head('My Property')}<div class="card"><div class="card-b">${empty('building', 'No property linked yet')}</div></div>`); return; }
    const u = p.unit || {}, pr = p.property || {};
    const imgs = [pr.cover_image, ...p.photos.map((x) => x.image)].filter(Boolean);
    mount(el, html`${head(pr.property_name || 'My Property', [pr.area, pr.city, pr.country].filter(Boolean).join(', '), '', 'My Property')}
      <div class="grid g-main"><div class="stack">
        <div class="card"><div class="card-h"><h3>Photos</h3></div><div class="card-b">${imgs.length ? html`<div class="gallery">${[...new Set(imgs)].slice(0, 9).map((u2) => html`<div class="ph">${imgTag(u2, 'Property photo')}</div>`)}</div>` : empty('building', 'No photos have been added yet')}</div></div>
        <div class="card"><div class="card-h"><h3>Amenities & facilities</h3></div><div class="card-b">${p.amenities.length ? html`<div class="amen">${p.amenities.map((a) => html`<span class="chip">${ic('check')} ${a}</span>`)}</div>` : html`<span style="color:var(--muted)">No amenities recorded for this property.</span>`}</div></div>
        <div class="card"><div class="card-h"><h3>Utility accounts</h3></div>${p.utilities.length ? html`<div class="tbl-wrap"><table class="t rs"><thead><tr><th>Utility</th><th>Provider</th><th>Account</th><th>Meter</th></tr></thead><tbody>${p.utilities.map((x) => html`<tr><td data-l="Utility">${x.utility_type}</td><td data-l="Provider">${x.provider || '-'}</td><td data-l="Account" class="num">${x.account_number}</td><td data-l="Meter">${x.meter_number || '-'}</td></tr>`)}</tbody></table></div>` : html`<div class="card-b" style="color:var(--muted)">No utility accounts are linked to your unit.</div>`}</div>
      </div><div class="stack">
        <div class="card"><div class="card-h"><h3>Your unit</h3></div><div class="card-b"><dl class="kv"><dt>Unit</dt><dd>${u.unit_no}${u.unit_title ? ' · ' + u.unit_title : ''}</dd><dt>Type</dt><dd>${u.unit_type || '-'}</dd><dt>Floor</dt><dd>${u.floor || '-'}</dd><dt>Usage</dt><dd>${u.usage || '-'}</dd><dt>Area</dt><dd>${u.area_sqm ? u.area_sqm + ' m²' : '-'}</dd><dt>Bedrooms / baths</dt><dd>${u.bedrooms || 0} / ${u.bathrooms || 0}</dd><dt>Furnishing</dt><dd>${u.furnishing || '-'}</dd><dt>Parking</dt><dd>${u.parking_slots || 0} bay(s)</dd></dl></div></div>
        <div class="card"><div class="card-h"><h3>Property</h3></div><div class="card-b"><dl class="kv"><dt>Type</dt><dd>${pr.property_type || '-'}</dd><dt>Address</dt><dd>${pr.address_line || '-'}</dd><dt>Area</dt><dd>${[pr.area, pr.city].filter(Boolean).join(', ') || '-'}</dd><dt>Floors</dt><dd>${pr.no_of_floors || '-'}</dd></dl></div></div>
        <div class="card"><div class="card-h"><h3>Property management</h3></div><div class="card-b"><div class="list">${p.management.email ? html`<div class="li"><span class="ico">${ic('mail')}</span><div class="grow"><a href="mailto:${p.management.email}">${p.management.email}</a></div></div>` : ''}${p.management.whatsapp ? html`<div class="li"><span class="ico">${ic('phone')}</span><div class="grow"><a href="https://wa.me/${String(p.management.whatsapp).replace(/\D/g, '')}" target="_blank" rel="noopener">WhatsApp ${p.management.whatsapp}</a></div></div>` : ''}<div class="li"><span class="ico">${ic('msg')}</span><div class="grow"><a href="#/messages">Send a message</a></div></div></div></div></div>
      </div></div>`);
  };

  PAGES.lease = async (el) => {
    const d = await api('lease_detail');
    if (!d.has_lease) { mount(el, html`${head('My Lease')}<div class="card"><div class="card-b">${empty('file', 'No lease found')}</div></div>`); return; }
    const L = d.lease, dep = d.deposit, live = L.status === 'Active' || L.status === 'Expiring';
    mount(el, html`${head('My Lease', `${L.name} · ${L.status}`, live ? html`<button class="btn" data-q="Extension Request">${ic('cal')} Request extension</button><button class="btn primary" data-q="Renewal Request">${ic('file')} Request renewal</button>` : '', 'My Lease')}
      ${d.renewal_window_open ? html`<div class="banner warn">${ic('cal')}<div class="grow"><b>Your lease ends in ${d.days_left} days.</b> You can ask management to renew or extend it below. Terms are confirmed by the leasing team.</div></div>` : ''}
      <div class="grid g-main"><div class="stack">
        <div class="card"><div class="card-h"><h3>Contract terms</h3>${pill(L.status)}</div><div class="card-b"><dl class="kv"><dt>Contract</dt><dd>${L.name}</dd><dt>Start</dt><dd>${fmtDate(L.start_date)}</dd><dt>End</dt><dd>${fmtDate(L.end_date)} (${d.days_left >= 0 ? d.days_left + ' days left' : 'ended'})</dd><dt>Duration</dt><dd>${L.duration_months || '-'} months</dd><dt>Total rent</dt><dd class="num">${money(L.total_contract_value, { maximumFractionDigits: 2 })}</dd><dt>Payment frequency</dt><dd>${L.payment_frequency}</dd><dt>Notice period</dt><dd>${L.notice_period_days || 0} days</dd><dt>Auto renew</dt><dd>${L.auto_renew ? 'Yes' : 'No'}</dd>${L.ejari_contract_no ? html`<dt>Ejari / registry no.</dt><dd>${L.ejari_contract_no}</dd>` : ''}</dl></div></div>
        ${d.charges.length ? html`<div class="card"><div class="card-h"><h3>Charges</h3></div><div class="tbl-wrap"><table class="t rs"><thead><tr><th>Charge</th><th>Description</th><th class="r">Amount</th></tr></thead><tbody>${d.charges.map((c) => html`<tr><td data-l="Charge">${c.charge_type}</td><td data-l="Description">${c.description || '-'}</td><td class="r num" data-l="Amount">${money(c.amount)}</td></tr>`)}</tbody></table></div></div>` : ''}
        ${d.terms ? html`<div class="card"><div class="card-h"><h3>Terms & conditions</h3></div><div class="card-b" style="white-space:pre-wrap;color:var(--ink-2)">${d.terms}</div></div>` : ''}
        <div class="card"><div class="card-h"><h3>Lease history</h3></div><div class="tbl-wrap"><table class="t rs"><thead><tr><th>Contract</th><th>Period</th><th class="r">Value</th><th>Status</th></tr></thead><tbody>${d.history.map((h) => html`<tr><td data-l="Contract">${h.name}</td><td data-l="Period">${fmtDate(h.start_date)} - ${fmtDate(h.end_date)}</td><td class="r num" data-l="Value">${money(h.total_contract_value)}</td><td data-l="Status">${pill(h.status)}</td></tr>`)}</tbody></table></div></div>
      </div><div class="stack">
        <div class="card"><div class="card-h"><h3>Security deposit</h3>${dep.status ? pill(dep.status) : ''}</div><div class="card-b"><dl class="kv"><dt>Amount</dt><dd class="num">${money(dep.amount)}</dd><dt>Held</dt><dd class="num">${money(dep.held)}</dd>${dep.deducted ? html`<dt>Deductions</dt><dd class="num">${money(dep.deducted)}</dd><dt>Reason</dt><dd>${dep.deduction_reason || '-'}</dd>` : ''}${dep.refunded ? html`<dt>Refunded</dt><dd class="num">${money(dep.refunded)}</dd>` : ''}${dep.received_date ? html`<dt>Received</dt><dd>${fmtDate(dep.received_date)}</dd>` : ''}</dl></div></div>
        <div class="card"><div class="card-h"><h3>Lease documents</h3></div><div class="card-b">${d.documents.length ? html`<div class="list">${d.documents.map((x) => html`<div class="li"><span class="ico">${ic('file')}</span><div class="grow t">${x.title}</div><button class="btn sm" data-view="${x.url}" data-t="${x.title}">${ic('eye')}</button><button class="btn sm" data-dl="${x.url}">${ic('down')}</button></div>`)}</div>` : html`<span style="color:var(--muted)">No signed documents have been uploaded yet.</span>`}</div></div>
        <div class="card"><div class="card-h"><h3>Your lease requests</h3></div><div class="card-b">${d.requests.length ? html`<div class="list">${d.requests.map((r) => html`<div class="li"><div class="grow"><div class="t">${r.request_type}</div><div class="d">${r.name} · ${fmtDate(r.creation)}${r.requested_date ? ' · for ' + fmtDate(r.requested_date) : ''}</div>${r.management_response ? html`<div class="d" style="color:var(--ink-2)">${r.management_response}</div>` : ''}</div>${pill(r.status)}</div>`)}</div>` : html`<span style="color:var(--muted)">You have not made any renewal, extension or termination requests.</span>`}${live ? html`<div style="margin-top:14px"><button class="btn danger sm" data-q="Termination Request">Request early termination</button><div class="hint" style="margin-top:6px">Management reviews every request. Your lease stays in force until you receive written confirmation.</div></div>` : ''}</div></div>
      </div></div>`);
    el.onclick = (e) => {
      const q = e.target.closest('[data-q]'); if (q) return newRequest(q.dataset.q, { lease: L.name });
      const v = e.target.closest('[data-view]'); if (v) return previewDoc('file', v.dataset.view, v.dataset.t);
      const dl = e.target.closest('[data-dl]'); if (dl) return saveDoc('file', dl.dataset.dl, dl);
    };
  };

  PAGES.payments = async (el) => {
    const d = await api('payments');
    if (!d.has_lease) { mount(el, html`${head('Rent & Payments')}<div class="card"><div class="card-b">${empty('wallet', 'No rent schedule yet')}</div></div>`); return; }
    const s = d.summary, ins = d.instalments || d.installments;
    const next = ins.findIndex((i) => i.effective_status !== 'Paid' && i.effective_status !== 'Cancelled');
    let tab = 'ledger';
    const drawTab = () => {
      const box = $('#pay-body', el);
      const T2 = {
        ledger: () => ins.length ? html`<div class="tbl-wrap"><table class="t rs"><thead><tr><th>#</th><th>Due date</th><th class="r">Amount</th><th class="r">Paid</th><th class="r">Outstanding</th><th>Status</th><th>Cheque</th><th></th></tr></thead><tbody>${ins.map((i) => html`<tr><td data-l="#">${i.installment_no}</td><td data-l="Due date">${fmtDate(i.due_date)}<div class="d" style="color:var(--muted);font-size:12px">${i.effective_status === 'Paid' ? '' : rel(i.days_to_due)}</div></td><td class="r num" data-l="Amount">${money(i.amount)}</td><td class="r num" data-l="Paid">${money(i.paid_amount)}</td><td class="r num" data-l="Outstanding"><b>${money(i.outstanding_amount)}</b></td><td data-l="Status">${pill(i.effective_status)}</td><td data-l="Cheque">${i.pdc_no || '-'}</td><td class="act">${i.invoice_available ? html`<button class="btn sm" data-inv="${i.sales_invoice}" title="Download invoice" aria-label="Download invoice">${ic('down')}</button>` : ''}</td></tr>`)}</tbody></table></div>` : empty('wallet', 'No instalments yet'),
        payments: () => d.payments.length ? html`<div class="tbl-wrap"><table class="t rs"><thead><tr><th>Date</th><th>Receipt</th><th>Method</th><th>Reference</th><th class="r">Amount</th><th></th></tr></thead><tbody>${d.payments.map((p) => html`<tr><td data-l="Date">${fmtDate(p.posting_date)}</td><td data-l="Receipt">${p.name}</td><td data-l="Method">${p.mode_of_payment || '-'}</td><td data-l="Reference">${p.reference_no || '-'}</td><td class="r num" data-l="Amount"><b>${money(p.paid_amount)}</b></td><td class="act"><button class="btn sm" data-rec="${p.name}">${ic('down')} Receipt</button></td></tr>`)}</tbody></table></div>` : empty('receipt', 'No payments recorded yet', 'Receipts appear here once the leasing team records your payments.'),
        cheques: () => d.cheques.length ? html`<div class="tbl-wrap"><table class="t rs"><thead><tr><th>Cheque no.</th><th>Bank</th><th>Cheque date</th><th class="r">Amount</th><th>Status</th><th>Cleared</th></tr></thead><tbody>${d.cheques.map((c) => html`<tr><td data-l="Cheque no.">${c.cheque_no}</td><td data-l="Bank">${c.bank}</td><td data-l="Cheque date">${fmtDate(c.cheque_date)}</td><td class="r num" data-l="Amount">${money(c.amount)}</td><td data-l="Status">${pill(c.status)}</td><td data-l="Cleared">${c.clearance_date ? fmtDate(c.clearance_date) : '-'}</td></tr>`)}</tbody></table></div>` : empty('receipt', 'No post-dated cheques on file'),
        deposit: () => html`<div class="card-b"><dl class="kv"><dt>Deposit</dt><dd class="num">${money(d.deposit.amount)}</dd><dt>Status</dt><dd>${d.deposit.status ? pill(d.deposit.status) : 'Not recorded'}</dd><dt>Currently held</dt><dd class="num">${money(d.deposit.held)}</dd><dt>Deductions</dt><dd class="num">${money(d.deposit.deducted)}</dd><dt>Refunded</dt><dd class="num">${money(d.deposit.refunded)}</dd><dt>Credit balance</dt><dd class="num">${money(s.credit_balance)}</dd></dl>${d.credits.length ? html`<h4 style="margin:18px 0 8px">Credit balances</h4><div class="list">${d.credits.map((c) => html`<div class="li"><div class="grow"><div class="t">${c.name}</div><div class="d">${fmtDate(c.creation)} · ${c.status}</div></div><b class="num">${money(c.amount - c.amount_used)}</b></div>`)}</div>` : ''}</div>`,
      };
      mount(box, T2[tab]());
      $$('.tabs button', el).forEach((b) => b.classList.toggle('on', b.dataset.t === tab));
    };
    const ib = d.instructions.bank;
    mount(el, html`${head('Rent & Payments', 'Your rent ledger, invoices and receipts', html`<button class="btn" id="csv">${ic('down')} Statement (CSV)</button>`, 'Rent & Payments')}
      ${s.overdue > 0 ? html`<div class="banner bad" role="alert">${ic('alert')}<div class="grow"><b>${money(s.overdue)} is overdue.</b> Please pay by bank transfer or cheque and quote your unit number. Your balance updates once the leasing team records the payment.</div></div>` : ''}
      <div class="grid g-metrics">
        ${metric('wallet', 'Total rent', money(s.total), 'Whole lease')}
        ${metric('check', 'Paid to date', money(s.paid), `${Math.round((s.paid / (s.total || 1)) * 100)}% of contract`, 'good')}
        ${metric('alert', 'Due now', money(s.outstanding_due), s.outstanding_due ? 'Please pay promptly' : 'Nothing due', s.outstanding_due ? 'bad' : '')}
        ${metric('cal', 'Upcoming', money(s.upcoming), 'Not yet due')}
        ${metric('receipt', 'Credit balance', money(s.credit_balance), 'Held in your favour')}
      </div>
      <div class="grid g-main"><div class="card"><div class="card-b" style="padding-bottom:0"><div class="tabs" role="tablist">${[['ledger', 'Rent ledger'], ['payments', 'Payment history'], ['cheques', 'Cheques'], ['deposit', 'Deposit & credit']].map(([k, l]) => html`<button role="tab" data-t="${k}">${l}</button>`)}</div></div><div id="pay-body"></div></div>
      <div class="stack"><div class="card"><div class="card-h"><h3>Progress</h3></div><div class="card-b">${donut([{ l: 'Paid', v: s.paid, c: '#34d399' }, { l: 'Due now', v: s.outstanding_due, c: '#f87171' }, { l: 'Upcoming', v: s.upcoming, c: '#818cf8' }], 'Paid', Math.round((s.paid / (s.total || 1)) * 100) + '%')}
        <div class="strip" aria-hidden="true" title="One block per instalment">${ins.filter((i) => i.status !== 'Cancelled').map((i, k) => html`<i class="${i.effective_status === 'Paid' ? 'paid' : i.effective_status === 'Overdue' ? 'over' : i.effective_status === 'Partially Paid' ? 'part' : k === next ? 'next' : ''}"></i>`)}</div></div></div>
      <div class="card"><div class="card-h"><h3>How to pay</h3></div><div class="card-b">${ib ? html`<dl class="kv"><dt>Account name</dt><dd>${ib.account_name || '-'}</dd><dt>Bank</dt><dd>${ib.bank || '-'}</dd><dt>IBAN</dt><dd class="num">${ib.iban || '-'}</dd></dl>` : ''}<p style="color:var(--muted);margin-top:${ib ? 12 : 0}px">${d.instructions.note}</p></div></div></div></div>`);
    drawTab();
    el.onclick = (e) => {
      const t = e.target.closest('.tabs button'); if (t) { tab = t.dataset.t; return drawTab(); }
      const inv = e.target.closest('[data-inv]'); if (inv) return saveDoc('invoice', inv.dataset.inv, inv);
      const rec = e.target.closest('[data-rec]'); if (rec) return saveDoc('receipt', rec.dataset.rec, rec);
      if (e.target.closest('#csv')) return statementCsv(d, ins);
    };
  };
  function statementCsv(d, ins) {
    const q = (v) => '"' + String(v == null ? '' : v).replace(/"/g, '""') + '"';
    const rows = [['Instalment', 'Due date', 'Amount', 'Paid', 'Outstanding', 'Status', 'Invoice', 'Cheque'], ...ins.filter((i) => i.status !== 'Cancelled').map((i) => [i.installment_no, i.due_date, i.amount, i.paid_amount, i.outstanding_amount, i.effective_status, i.sales_invoice || '', i.pdc_no || ''])];
    const csv = '﻿' + rows.map((r) => r.map(q).join(',')).join('\r\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `account-statement-${d.lease}.csv`; document.body.appendChild(a); a.click(); a.remove();
  }

  const STAGES = ['Submitted', 'Assigned', 'In Progress', 'Completed'];
  PAGES.maintenance = async (el) => {
    const d = await api('maintenance');
    let tab = 'open';
    const draw = () => {
      const list = d.requests.filter((r) => (tab === 'open' ? ['Open', 'In Progress', 'On Hold'].includes(r.status) : !['Open', 'In Progress', 'On Hold'].includes(r.status)));
      mount($('#m-body', el), list.length ? html`<div class="grid">${list.map((r) => {
        const idx = STAGES.indexOf(r.stage);
        return html`<div class="card"><div class="card-b">
          <div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap"><div><b>${r.category || 'Maintenance'}</b> <span class="num" style="color:var(--muted)">${r.name}</span><div class="d" style="color:var(--muted)">Submitted ${fmtDate(r.creation)} · Priority ${r.priority || '-'}</div></div><div>${pill(r.stage)}</div></div>
          <p style="margin:10px 0;white-space:pre-wrap">${r.description}</p>
          ${idx >= 0 ? html`<div class="strip" aria-label="Progress">${STAGES.map((s, k) => html`<i class="${k <= idx ? 'paid' : ''}" title="${s}"></i>`)}</div><div class="d" style="display:flex;justify-content:space-between;color:var(--muted);font-size:11.5px;margin-top:4px">${STAGES.map((s) => html`<span>${s}</span>`)}</div>` : ''}
          ${r.job && r.job.assigned_to ? html`<div class="chip" style="margin-top:10px">${ic('user')} Assigned to ${r.job.assigned_to}${r.job.scheduled_date ? ' · visit ' + fmtDate(r.job.scheduled_date) : ''}</div>` : ''}
          ${r.photos.length ? html`<div class="gallery" style="margin-top:12px">${r.photos.slice(0, 4).map((u) => html`<div class="ph">${imgTag(u, 'Attached photo')}</div>`)}</div>` : ''}
          ${r.resolution_notes ? html`<div class="banner good" style="margin:12px 0 0">${ic('check')}<div class="grow"><b>Resolution</b><br>${r.resolution_notes}</div></div>` : ''}
          <details style="margin-top:10px"><summary style="cursor:pointer;color:var(--brand)">Updates</summary><div class="timeline" style="margin-top:10px">${r.timeline.map((t) => html`<div class="tl"><i></i><div><b>${t.title}</b><small>${fmtDT(t.when)}</small></div></div>`)}</div></details>
          <div class="page-actions" style="margin-top:12px">${r.status === 'Completed' ? html`<button class="btn sm primary" data-fb="confirm" data-n="${r.name}">${ic('check')} Confirm completed</button><button class="btn sm" data-fb="reopen" data-n="${r.name}">Still needs help</button>` : ''}${['Open', 'In Progress', 'On Hold'].includes(r.status) ? html`<button class="btn sm" data-fb="note" data-n="${r.name}">${ic('msg')} Add a note</button>` : ''}</div>
        </div></div>`;
      })}</div>` : html`<div class="card"><div class="card-b">${empty('wrench', tab === 'open' ? 'No open requests' : 'No past requests', 'Report an issue and we will get it fixed.', html`<button class="btn primary" data-new>${ic('plus')} New request</button>`)}</div></div>`);
      hydrateImages(el);
      $$('.tabs button', el).forEach((b) => b.classList.toggle('on', b.dataset.t === tab));
    };
    mount(el, html`${head('Maintenance', 'Report problems and follow them to completion', html`<button class="btn primary" data-new>${ic('plus')} New request</button>`)}<div class="tabs"><button data-t="open">Open (${d.requests.filter((r) => ['Open', 'In Progress', 'On Hold'].includes(r.status)).length})</button><button data-t="past">Completed & closed</button></div><div id="m-body"></div>`);
    draw();
    el.onclick = async (e) => {
      const t = e.target.closest('.tabs button'); if (t) { tab = t.dataset.t; return draw(); }
      if (e.target.closest('[data-new]')) return newMaintenance(d);
      const fb = e.target.closest('[data-fb]');
      if (fb) {
        const a = fb.dataset.fb, n = fb.dataset.n;
        if (a === 'confirm') { try { await apiPost('maintenance_feedback', { name: n, action: a }); toast('Thanks for confirming.', 'good'); route(); } catch (err) { toast(err.message, 'bad'); } return; }
        openDialog({ title: a === 'reopen' ? 'What still needs attention?' : 'Add a note', body: html`<div class="field"><label>Message</label><textarea class="textarea" name="note" maxlength="500" required></textarea></div>`, actions: [{ id: 'cancel', label: 'Cancel' }, { primary: true, label: 'Send' }], onSubmit: async (f) => { const note = f.note.value.trim(); if (!note) throw new Error('Please add a message.'); await apiPost('maintenance_feedback', { name: n, action: a, note }); toast('Sent to the leasing team.', 'good'); route(); } });
      }
    };
  };

  async function newMaintenance(d) {
    d = d || await api('maintenance');
    const body = html`<div class="row2"><div class="field"><label>Issue category</label><select class="select" name="category" required><option value="">Select…</option>${d.categories.map((c) => html`<option>${c}</option>`)}</select></div><div class="field"><label>Priority</label><select class="select" name="priority">${d.priorities.map((p) => html`<option ${p === 'Medium' ? raw('selected') : ''}>${p}</option>`)}</select></div></div>
      ${d.units.length > 1 ? html`<div class="field"><label>Unit</label><select class="select" name="unit">${d.units.map((u) => html`<option value="${u.unit}">${u.label}</option>`)}</select></div>` : ''}
      <div class="field"><label>Describe the problem</label><textarea class="textarea" name="description" maxlength="2000" placeholder="What is happening, where, and since when?" required></textarea></div>
      <div class="field"><label>Preferred access times</label><input class="input" name="preferred_access" maxlength="200" placeholder="e.g. Weekdays after 5 pm"></div>${attachHtml}
      <div class="hint">For gas leaks, fire or flooding call the emergency number for your building first.</div>`;
    let att;
    const dlg = openDialog({ title: 'New maintenance request', body, actions: [{ id: 'cancel', label: 'Cancel' }, { primary: true, label: 'Submit request' }], onSubmit: async (f) => {
      if (att.busy) throw new Error('Please wait for the uploads to finish.');
      if (!f.category.value) throw new Error('Please choose an issue category.');
      const r = await apiPost('create_maintenance', { category: f.category.value, priority: f.priority.value, unit: f.unit ? f.unit.value : '', description: f.description.value, preferred_access: f.preferred_access.value, file_ids: JSON.stringify(att.ids.map((x) => x.id)) });
      toast('Request ' + r.name + ' submitted.', 'good'); S.boot.counters.open_maintenance++; if (S.route === 'maintenance' || S.route === 'overview') route();
    } });
    att = attachWidget(dlg);
  }
  async function newRequest(type, extra) {
    const types = ['Renewal Request', 'Extension Request', 'Termination Request', 'Move-out Inspection Request', 'Damage Report', 'Key / Access Card Request', 'Parking Request', 'Address Change', 'Occupant Update', 'Facility Access', 'Profile Correction'];
    const needDate = ['Extension Request', 'Termination Request', 'Move-out Inspection Request'];
    const body = html`<div class="field"><label>Request type</label><select class="select" name="request_type">${types.map((t) => html`<option ${t === type ? raw('selected') : ''}>${t}</option>`)}</select></div>
      <div class="field" id="rq-date" ${needDate.includes(type) ? '' : raw('hidden')}><label id="rq-date-l">Date</label><input class="input" type="date" name="requested_date" min="${new Date().toISOString().slice(0, 10)}"><div class="hint" id="rq-date-h"></div></div>
      <div class="field"><label>Subject</label><input class="input" name="subject" maxlength="140" required placeholder="Short summary"></div>
      <div class="field"><label>Details</label><textarea class="textarea" name="details" maxlength="2000" placeholder="Anything management should know"></textarea></div>${attachHtml}
      <div class="hint">Requests are reviewed by the leasing team. Nothing changes on your lease until management confirms.</div>`;
    let att;
    const labels = { 'Extension Request': ['Requested new end date', 'The date you would like your lease to run until.'], 'Termination Request': ['Requested termination date', 'Subject to your notice period and management approval.'], 'Move-out Inspection Request': ['Preferred move-out date', 'We will schedule your inspection around this date.'] };
    const dlg = openDialog({ title: 'New service request', body, actions: [{ id: 'cancel', label: 'Cancel' }, { primary: true, label: 'Submit request' }], onSubmit: async (f) => {
      if (att.busy) throw new Error('Please wait for the uploads to finish.');
      if (f.request_type.value === 'Termination Request' && !(await confirmDlg('Request early termination?', 'This sends a termination request to management. Your lease remains in force until it is approved in writing.', 'Send request'))) return false;
      const r = await apiPost('create_service_request', { request_type: f.request_type.value, subject: f.subject.value, details: f.details.value, requested_date: f.requested_date.value, lease: (extra && extra.lease) || S.lease || '', file_ids: JSON.stringify(att.ids.map((x) => x.id)) });
      toast('Request ' + r.name + ' sent.', 'good'); if (['requests', 'lease', 'moves', 'overview'].includes(S.route)) route();
    } });
    att = attachWidget(dlg);
    const sync = () => { const f = $('form', dlg), t = f.request_type.value, wrap = $('#rq-date', dlg); wrap.hidden = !needDate.includes(t); if (labels[t]) { $('#rq-date-l', dlg).textContent = labels[t][0]; $('#rq-date-h', dlg).textContent = labels[t][1]; } if (!f.subject.value || types.includes(f.subject.dataset.auto)) { f.subject.value = t; f.subject.dataset.auto = t; } };
    $('select[name=request_type]', dlg).addEventListener('change', sync); sync();
  }
  function newMessage(thread, subject) {
    openDialog({ title: thread ? 'Reply' : 'Message management', body: html`${thread ? '' : html`<div class="field"><label>Subject</label><input class="input" name="subject" maxlength="140" required></div>`}<div class="field"><label>Message</label><textarea class="textarea" name="message" maxlength="1500" required></textarea></div>`, actions: [{ id: 'cancel', label: 'Cancel' }, { primary: true, label: 'Send' }], onSubmit: async (f) => {
      if (!f.message.value.trim()) throw new Error('Please type a message.');
      await apiPost('send_message', { message: f.message.value, subject: f.subject ? f.subject.value : '', thread: thread || '' }); toast('Message sent.', 'good'); if (S.route === 'messages') route();
    } });
  }

  PAGES.documents = async (el) => {
    const d = await api('documents');
    let q = '', cat = '';
    const draw = () => {
      const rows = d.documents.filter((x) => (!cat || x.category === cat) && (!q || (x.title + ' ' + x.category).toLowerCase().includes(q)));
      mount($('#doc-body', el), rows.length ? html`<div class="tbl-wrap"><table class="t rs"><thead><tr><th>Document</th><th>Category</th><th>Date</th><th>Expiry</th><th></th></tr></thead><tbody>${rows.map((x, i) => html`<tr><td data-l="Document"><b>${x.title}</b></td><td data-l="Category">${x.category}</td><td data-l="Date">${x.date ? fmtDate(x.date) : '-'}</td><td data-l="Expiry">${x.expiry ? html`${fmtDate(x.expiry)} ${pill(x.expiry_state)}` : '-'}</td><td class="act"><button class="btn sm" data-view="${i}" title="Preview">${ic('eye')}</button> <button class="btn sm" data-get="${i}">${ic('down')}</button></td></tr>`)}</tbody></table></div>` : empty('folder', 'No documents found', q || cat ? 'Try a different search or category.' : 'Your lease, invoices and receipts will appear here.'));
    };
    mount(el, html`${head('Documents', 'Lease, invoices, receipts, inspection reports and your own uploads', html`<button class="btn primary" id="up-doc">${ic('up')} Upload a document</button><input type="file" id="up-file" accept="image/jpeg,image/png,image/webp,application/pdf" hidden>`)}
      <div class="filters"><input class="input" id="dq" type="search" placeholder="Search documents" aria-label="Search documents"><select class="select" id="dc" aria-label="Category"><option value="">All categories</option>${d.categories.map((c) => html`<option>${c}</option>`)}</select></div><div class="card" id="doc-body"></div>`);
    draw();
    $('#dq', el).oninput = (e) => { q = e.target.value.trim().toLowerCase(); draw(); };
    $('#dc', el).onchange = (e) => { cat = e.target.value; draw(); };
    $('#up-doc', el).onclick = () => $('#up-file', el).click();
    $('#up-file', el).onchange = async (e) => { const f = e.target.files[0]; if (!f) return; try { await uploadFile(f, 'document'); toast('Document uploaded.', 'good'); route(); } catch (err) { toast(err.message, 'bad'); } };
    el.addEventListener('click', (e) => {
      const v = e.target.closest('[data-view]'), g = e.target.closest('[data-get]');
      const pick = (b) => d.documents.filter((x) => (!cat || x.category === cat) && (!q || (x.title + ' ' + x.category).toLowerCase().includes(q)))[+b];
      if (v) { const x = pick(v.dataset.view); previewDoc(x.kind, x.ref, x.title); }
      if (g) { const x = pick(g.dataset.get); saveDoc(x.kind, x.ref, g); }
    });
  };

  PAGES.requests = async (el) => {
    const d = await api('service_requests');
    mount(el, html`${head('Service Requests', 'Renewals, parking, access cards, address changes and more', html`<button class="btn primary" id="nr">${ic('plus')} New request</button>`)}
      ${d.requests.length ? html`<div class="grid">${d.requests.map((r) => html`<div class="card"><div class="card-b"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap"><div><b>${r.subject}</b><div class="d" style="color:var(--muted)">${r.request_type} · <span class="num">${r.name}</span> · ${fmtDate(r.creation)}${r.requested_date ? ' · for ' + fmtDate(r.requested_date) : ''}</div></div>${pill(r.status)}</div>
        ${r.management_response ? html`<div class="banner info" style="margin:12px 0 0">${ic('msg')}<div class="grow"><b>Management response</b><br>${r.management_response}</div></div>` : ''}
        <details style="margin-top:10px"><summary style="cursor:pointer;color:var(--brand)">Conversation (${r.messages.length})</summary><div class="thread" style="margin-top:10px">${r.messages.map((m) => html`<div class="bubble ${m.sender_type === 'Tenant' ? 'me' : ''}">${m.message}<small>${m.sender_type === 'Tenant' ? 'You' : 'Management'} · ${fmtDT(m.posted_on)}</small></div>`)}</div></details>
        <div class="page-actions" style="margin-top:12px">${!['Cancelled', 'Rejected', 'Completed'].includes(r.status) ? html`<button class="btn sm" data-reply="${r.name}">${ic('send')} Reply</button>` : ''}${r.status === 'Open' ? html`<button class="btn sm danger" data-cancel="${r.name}">Cancel request</button>` : ''}</div></div></div>`)}</div>` : html`<div class="card"><div class="card-b">${empty('clip', 'No service requests yet', 'Ask for a renewal, extra parking, a new access card or update your details.', html`<button class="btn primary" id="nr2">${ic('plus')} New request</button>`)}</div></div>`}`);
    el.onclick = async (e) => {
      if (e.target.closest('#nr') || e.target.closest('#nr2')) return newRequest('Parking Request');
      const rp = e.target.closest('[data-reply]'); if (rp) return newMessage(rp.dataset.reply);
      const cn = e.target.closest('[data-cancel]');
      if (cn && (await confirmDlg('Cancel this request?', 'The leasing team will no longer act on it.', 'Cancel request'))) { try { await apiPost('cancel_service_request', { name: cn.dataset.cancel }); toast('Request cancelled.'); route(); } catch (err) { toast(err.message, 'bad'); } }
    };
  };

  PAGES.messages = async (el) => {
    const [d, c] = await Promise.all([api('service_requests', { kind: 'messages' }), api('communications')]);
    let tab = 'conv', sel = d.requests[0] && d.requests[0].name;
    const draw = () => {
      const body = $('#msg-body', el);
      if (tab === 'conv') {
        const t = d.requests.find((x) => x.name === sel);
        mount(body, d.requests.length ? html`<div class="grid g-main" style="grid-template-columns:minmax(0,1fr) minmax(0,1.6fr)"><div class="card"><div class="card-b"><div class="list">${d.requests.map((x) => html`<button class="li" data-th="${x.name}" style="background:${x.name === sel ? 'var(--brand-soft)' : 'none'};border:0;border-radius:10px;padding:10px;text-align:start;cursor:pointer;width:100%"><span class="ico">${ic('msg')}</span><div class="grow"><div class="t">${x.subject}</div><div class="d">${fmtDate(x.modified)} · ${x.messages.length} message${x.messages.length === 1 ? '' : 's'}</div></div>${pill(x.status)}</button>`)}</div></div></div>
          <div class="card"><div class="card-h"><h3>${t.subject}</h3><small>${t.name}</small></div><div class="card-b"><div class="thread">${t.messages.map((m) => html`<div class="bubble ${m.sender_type === 'Tenant' ? 'me' : ''}">${m.message}<small>${m.sender_type === 'Tenant' ? 'You' : 'Management'} · ${fmtDT(m.posted_on)}</small></div>`)}</div>${t.management_response ? html`<div class="banner info" style="margin-top:14px">${ic('msg')}<div class="grow">${t.management_response}</div></div>` : ''}<div style="margin-top:14px"><button class="btn primary" data-reply="${t.name}">${ic('send')} Reply</button></div></div></div></div>` : html`<div class="card"><div class="card-b">${empty('msg', 'No conversations yet', 'Send a message to the property management team.', html`<button class="btn primary" data-new>${ic('plus')} New message</button>`)}</div></div>`);
      } else {
        mount(body, html`<div class="card"><div class="card-b">${c.notifications.length ? html`<div class="list">${c.notifications.map((n) => html`<div class="li"><span class="ico info">${ic('bolt')}</span><div class="grow"><div class="t">${n.message}</div><div class="d">Automated notification · ${fmtDT(n.when)}</div></div>${pill(n.status === 'Sent' ? 'Completed' : n.status, n.status)}</div>`)}</div>` : empty('bolt', 'No automated notifications', 'Reminders and updates sent to your phone appear here.')}</div></div>`);
      }
      $$('.tabs button', el).forEach((b) => b.classList.toggle('on', b.dataset.t === tab));
    };
    mount(el, html`${head('Messages', 'Direct conversations with management and automated notifications', html`<button class="btn primary" data-new>${ic('plus')} New message</button>`)}<div class="tabs"><button data-t="conv">Conversations</button><button data-t="auto">Automated notifications</button></div><div id="msg-body"></div>`);
    draw();
    el.onclick = (e) => {
      const t = e.target.closest('.tabs button'); if (t) { tab = t.dataset.t; return draw(); }
      const th = e.target.closest('[data-th]'); if (th) { sel = th.dataset.th; return draw(); }
      if (e.target.closest('[data-new]')) return newMessage();
      const rp = e.target.closest('[data-reply]'); if (rp) return newMessage(rp.dataset.reply);
    };
  };

  PAGES.announcements = async (el) => {
    const a = await api('announcements');
    const TONE = { Emergency: 'bad', Maintenance: 'warn', 'Building Rules': 'info', Community: 'good', Notice: '' };
    mount(el, html`${head('Announcements', 'Notices from property management')}${a.length ? html`<div class="grid">${a.map((x) => html`<div class="card"><div class="card-b"><div style="display:flex;justify-content:space-between;gap:10px"><b style="font-size:15px">${x.title}</b><span class="pill ${TONE[x.category] || ''}">${x.category}</span></div><div class="d" style="color:var(--muted);margin:2px 0 10px">${fmtDate(x.publish_from || x.creation)}</div><div style="color:var(--ink-2)">${raw(x.body || '')}</div></div></div>`)}</div>` : html`<div class="card"><div class="card-b">${empty('mega', 'No announcements', 'Building notices, scheduled maintenance and community updates will appear here.')}</div></div>`}`);
  };

  PAGES.moves = async (el) => {
    const d = await api('inspections');
    mount(el, html`${head('Move-in / Move-out', 'Inspection records, damage reports and final settlement', html`<button class="btn" data-q="Damage Report">${ic('alert')} Report damage</button><button class="btn" data-q="Key / Access Card Request">${ic('key')} Key / access card</button><button class="btn primary" data-q="Move-out Inspection Request">${ic('insp')} Request move-out inspection</button>`)}
      <div class="grid g-main"><div class="stack">${d.inspections.length ? d.inspections.map((i) => html`<div class="card"><div class="card-h"><h3>${i.inspection_type} inspection · ${fmtDate(i.inspection_date)}</h3><span class="num" style="color:var(--muted)">${i.name}</span></div><div class="card-b">
          ${i.summary ? html`<p style="margin-bottom:12px">${i.summary}</p>` : ''}
          ${i.items.length ? html`<div class="tbl-wrap"><table class="t rs"><thead><tr><th>Room</th><th>Item</th><th>Condition</th><th>Remarks</th><th>Photo</th></tr></thead><tbody>${i.items.map((x) => html`<tr><td data-l="Room">${x.room || '-'}</td><td data-l="Item">${x.item || '-'}</td><td data-l="Condition">${x.condition ? pill(x.condition) : '-'}</td><td data-l="Remarks">${x.remarks || '-'}</td><td data-l="Photo">${x.photo ? html`<button class="btn sm" data-view="${x.photo}">${ic('eye')}</button>` : '-'}</td></tr>`)}</tbody></table></div>` : html`<span style="color:var(--muted)">No checklist items were recorded.</span>`}
          ${i.estimated_damage_cost ? html`<div class="banner warn" style="margin:12px 0 0">${ic('alert')}<div class="grow">Estimated damage cost: <b>${money(i.estimated_damage_cost)}</b></div></div>` : ''}
          <div class="page-actions" style="margin-top:14px">${i.docstatus === 1 ? html`<button class="btn sm" data-rep="${i.name}">${ic('down')} Download report</button>` : ''}${i.acknowledged_on ? html`<span class="pill good">Acknowledged ${fmtDate(i.acknowledged_on)}</span>` : html`<button class="btn sm primary" data-ack="${i.name}">${ic('check')} I acknowledge this condition report</button>`}</div></div></div>`) : html`<div class="card"><div class="card-b">${empty('insp', 'No inspection records yet', 'Your move-in and move-out condition reports will appear here once the leasing team completes them.')}</div></div>`}
        <div class="card"><div class="card-h"><h3>Your requests</h3></div><div class="card-b">${d.requests.length ? html`<div class="list">${d.requests.map((r) => html`<div class="li"><div class="grow"><div class="t">${r.request_type}</div><div class="d">${r.name} · ${fmtDate(r.creation)}${r.requested_date ? ' · for ' + fmtDate(r.requested_date) : ''}</div>${r.management_response ? html`<div class="d" style="color:var(--ink-2)">${r.management_response}</div>` : ''}</div>${pill(r.status)}</div>`)}</div>` : html`<span style="color:var(--muted)">No move-out, damage or key requests yet.</span>`}</div></div>
      </div><div class="stack"><div class="card"><div class="card-h"><h3>Final settlement</h3>${d.deposit && d.deposit.status ? pill(d.deposit.status) : ''}</div><div class="card-b">${d.deposit ? html`<dl class="kv"><dt>Lease</dt><dd>${d.lease} · ${d.lease_status}</dd><dt>Deposit</dt><dd class="num">${money(d.deposit.amount)}</dd><dt>Deductions</dt><dd class="num">${money(d.deposit.deducted)}</dd>${d.deposit.deduction_reason ? html`<dt>Reason</dt><dd>${d.deposit.deduction_reason}</dd>` : ''}<dt>Refunded</dt><dd class="num">${money(d.deposit.refunded)}</dd><dt>Still held</dt><dd class="num">${money(d.deposit.held)}</dd></dl><p class="hint" style="margin-top:12px">Your deposit is settled after the move-out inspection and clearance of final dues.</p>` : html`<span style="color:var(--muted)">No deposit on record.</span>`}</div></div></div></div>`);
    el.onclick = async (e) => {
      const q = e.target.closest('[data-q]'); if (q) return newRequest(q.dataset.q);
      const v = e.target.closest('[data-view]'); if (v) return previewDoc('file', v.dataset.view, 'Inspection photo');
      const r = e.target.closest('[data-rep]'); if (r) return saveDoc('inspection', r.dataset.rep, r);
      const a = e.target.closest('[data-ack]');
      if (a && (await confirmDlg('Acknowledge condition report', 'By acknowledging you confirm you have reviewed the recorded condition of the property. You can still raise a damage report if something is missing.', 'Acknowledge'))) { try { await apiPost('acknowledge_inspection', { name: a.dataset.ack }); toast('Acknowledged.', 'good'); route(); } catch (err) { toast(err.message, 'bad'); } }
    };
  };

  PAGES.profile = async (el) => {
    const p = await api('profile'), t = p.tenant;
    mount(el, html`${head('Profile & Settings', 'Your details and account security', '', 'Profile')}
      <div class="grid g-2" style="align-items:start"><div class="stack">
        <div class="card"><div class="card-h"><h3>Personal details</h3></div><div class="card-b"><dl class="kv"><dt>Name</dt><dd>${t.tenant_name}</dd><dt>Type</dt><dd>${t.tenant_type || '-'}</dd><dt>Nationality</dt><dd>${t.nationality || '-'}</dd><dt>Mobile (sign-in)</dt><dd>${t.mobile}</dd><dt>Email</dt><dd>${t.email || '-'}</dd></dl><div class="hint" style="margin-top:12px">Name, mobile, email and identity details are verified by the leasing office. <a href="#" id="corr">Request a correction</a></div></div></div>
        <div class="card"><div class="card-h"><h3>Contact preferences</h3></div><div class="card-b"><form id="pf" novalidate><div class="field"><label>WhatsApp number</label><input class="input" name="whatsapp_number" value="${t.whatsapp_number || ''}" inputmode="tel" placeholder="+971 5x xxx xxxx"></div><div class="field"><label>Emergency contact name</label><input class="input" name="emergency_contact_name" value="${t.emergency_contact_name || ''}" maxlength="140"></div><div class="field"><label>Emergency contact number</label><input class="input" name="emergency_contact_mobile" value="${t.emergency_contact_mobile || ''}" inputmode="tel"></div><button class="btn primary" type="submit">Save changes</button></form></div></div>
      </div><div class="stack">
        <div class="card"><div class="card-h"><h3>Identity documents</h3></div><div class="card-b">${p.kyc.length ? html`<div class="list">${p.kyc.map((k) => html`<div class="li"><span class="ico">${ic('shield')}</span><div class="grow"><div class="t">${k.id_type || 'Document'}</div><div class="d">${k.id_number || ''}${k.expiry_date ? ' · expires ' + fmtDate(k.expiry_date) : ''}</div></div>${pill(k.state)}</div>`)}</div><p class="hint" style="margin-top:12px">ID numbers are masked. Files are available under Documents.</p>` : html`<span style="color:var(--muted)">No identity documents on file.</span>`}</div></div>
        <div class="card"><div class="card-h"><h3>Account security</h3></div><div class="card-b"><dl class="kv"><dt>Sign-in method</dt><dd>${p.mode === 'access_code' ? 'Mobile number + access code' : 'Website account'}</dd>${p.login_email ? html`<dt>Login</dt><dd>${p.login_email}</dd>` : ''}${p.mode === 'access_code' ? html`<dt>Active sessions</dt><dd>${p.active_sessions.length}</dd>` : ''}</dl>${p.mode === 'access_code' ? html`<button class="btn" id="so-all" style="margin-top:12px">${ic('out')} Sign out of all devices</button>` : html`<p class="hint" style="margin-top:12px">Manage your password from the website sign-in page.</p>`}</div></div>
      </div></div>`);
    $('#pf', el).onsubmit = async (e) => {
      e.preventDefault(); const f = e.target, b = $('button', f);
      try { busy(b, true); await apiPost('update_profile', { whatsapp_number: f.whatsapp_number.value, emergency_contact_name: f.emergency_contact_name.value, emergency_contact_mobile: f.emergency_contact_mobile.value }); toast('Details saved.', 'good'); } catch (err) { toast(err.message, 'bad'); } finally { busy(b, false); }
    };
    $('#corr', el).onclick = (e) => { e.preventDefault(); newRequest('Profile Correction'); };
    const so = $('#so-all', el); if (so) so.onclick = async () => { if (await confirmDlg('Sign out everywhere?', 'You will need your access code to sign in again.', 'Sign out')) { await apiPost('sign_out_everywhere'); clearAuth(); location.reload(); } };
  };

  /* ------------------------------------------------------- auth + startup */
  function clearAuth() { S.token = null; S.boot = null; S.blobs = {}; S.search = null; try { localStorage.removeItem('tss_token'); sessionStorage.removeItem('tss_lease'); } catch (e) { /* ignore */ } }
  async function signOut() {
    try {
      if (S.token) await call(LOGIN_API, 'tenant_portal_logout', { token: S.token }, true);
      else await fetch('/api/method/logout', { method: 'POST', headers: { 'X-Frappe-CSRF-Token': T.csrf || '' }, credentials: 'same-origin' });
    } catch (e) { /* best effort */ }
    clearAuth(); location.hash = ''; location.reload();
  }
  function showSignIn(msg) {
    clearAuth();
    const codeOn = S.info && S.info.access_code_enabled;
    const next = encodeURIComponent('/tenant-self-service');
    mount(app(), html`<div class="auth"><section class="auth-hero"><div class="brand"><img src="${T.logo}" alt="">${T.title || 'thinkNXG Estate'}</div>
      <div><h1>Your home, in one place.</h1><p>Pay and track rent, request repairs, access your lease and documents, and talk to your property team.</p><div class="auth-points"><div>${ic('wallet')}<span>Rent ledger, invoices and receipts</span></div><div>${ic('wrench')}<span>Maintenance requests with live status</span></div><div>${ic('folder')}<span>Lease and documents, always to hand</span></div></div></div><small>Secure tenant portal</small></section>
      <section class="auth-panel"><div class="auth-card"><h2>Sign in</h2><p class="sub">Access your tenancy.</p>
        ${msg ? html`<div class="banner warn" role="alert"><div class="grow">${msg}</div></div>` : ''}
        <a class="btn primary block" href="/login?redirect-to=${next}">Sign in with your account</a>
        ${codeOn ? html`<div class="auth-divider">or use your access code</div><form id="code-form" novalidate><div class="field"><label for="mob">Mobile number</label><input class="input" id="mob" name="mobile" inputmode="tel" autocomplete="tel" placeholder="+971 5x xxx xxxx" required></div><div class="field"><label for="acode">Access code</label><input class="input" id="acode" name="code" type="password" autocomplete="one-time-code" required></div><div class="field-error" id="code-err" role="alert" hidden></div><button class="btn block" type="submit">Sign in with access code</button></form>` : html`<p class="auth-note">Your property manager provides your login. If you cannot sign in, contact the leasing office.</p>`}
      </div></section></div>`);
    const f = $('#code-form');
    if (f) f.onsubmit = async (e) => {
      e.preventDefault(); const b = $('button', f), er = $('#code-err');
      er.hidden = true;
      try {
        busy(b, true);
        const r = await call(LOGIN_API, 'tenant_portal_login', { mobile: f.mobile.value.trim(), access_code: f.code.value }, true);
        S.token = r.token; try { localStorage.setItem('tss_token', r.token); } catch (x) { /* ignore */ }
        await start();
      } catch (err) { er.textContent = err.message; er.hidden = false; busy(b, false); }
    };
  }
  async function start() {
    mount(app(), html`<div style="padding:40px"><div class="skel" style="height:24px;width:220px"></div></div>`);
    try {
      S.info = await api("session_info");
      if (!S.info.authenticated) return showSignIn();
      S.mode = S.info.mode;
      S.boot = await api('bootstrap');
      S.lease = S.boot.current_lease; try { if (S.lease) sessionStorage.setItem('tss_lease', S.lease); } catch (e) { /* ignore */ }
      renderShell(); await route();
    } catch (e) {
      if (e.status === 401) return showSignIn(S.token ? 'Your session has ended. Please sign in again.' : '');
      if (e.status === 403) {
        mount(app(), html`<div class="auth-panel" style="min-height:100vh"><div class="auth-card"><h2>No tenancy found</h2><p class="sub">${e.message}</p><button class="btn block" id="so">Sign out</button></div></div>`);
        $('#so').onclick = signOut; return;
      }
      mount(app(), html`<div class="auth-panel" style="min-height:100vh"><div class="auth-card"><h2>Something went wrong</h2><p class="sub">${e.message}</p><button class="btn primary block" onclick="location.reload()">Try again</button></div></div>`);
    }
  }

  (async function init() {
    try { S.info = await api('session_info'); } catch (e) { S.info = { access_code_enabled: false, authenticated: false }; if (e.status === 401) clearAuth(); }
    if (S.info.authenticated) await start(); else showSignIn(S.token ? 'Your session has ended. Please sign in again.' : '');
  }());
}());
