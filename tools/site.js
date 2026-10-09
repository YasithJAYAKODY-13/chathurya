(function(){
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];

const bar = $('#bar');
const onScroll = () => bar.classList.toggle('solid', scrollY > 40);
addEventListener('scroll', onScroll, {passive:true}); onScroll();

const nx = $('.next[data-date]');
if (nx && new Date(nx.dataset.date + 'T23:59:59') < new Date()) nx.classList.add('past');

/* video facades */
function ytSrc(id, start, end){ let u = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0&playsinline=1';
  if (start) u += '&start=' + start; if (end) u += '&end=' + end; return u; }
function stopAll(except){ $$('.facade iframe, .facade video').forEach(n => { if (!except || !except.contains(n)) n.remove(); }); }
function bindFacade(f){ f.addEventListener('click', () => {
  if (f.querySelector('iframe,video')) return; stopAll(f); let el;
  if (f.dataset.yt) { el = document.createElement('iframe'); el.src = ytSrc(f.dataset.yt, f.dataset.start, f.dataset.end);
    el.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen'; el.allowFullscreen = true; el.title = f.getAttribute('aria-label'); }
  else { el = document.createElement('video'); el.src = f.dataset.mp4; el.controls = true; el.autoplay = true; el.playsInline = true; }
  f.appendChild(el); }); }
$$('.facade').forEach(bindFacade);

/* tabs */
const tabs = $$('[role="tab"]');
function select(tab, focus){
  tabs.forEach(t => { const on = t === tab; t.setAttribute('aria-selected', on); t.tabIndex = on ? 0 : -1;
    const p = document.getElementById(t.getAttribute('aria-controls')); p.hidden = !on;
    if (on) { p.classList.remove('enter'); void p.offsetWidth; p.classList.add('enter'); } });
  stopAll(); if (focus) tab.focus();
  tab.scrollIntoView({block:'nearest', inline:'nearest'});
}
tabs.forEach((t,i) => {
  t.addEventListener('click', () => { select(t); history.replaceState(null, '', '#' + t.id.slice(2)); });
  t.addEventListener('keydown', e => { let j = null;
    if (e.key === 'ArrowRight') j = (i+1) % tabs.length; if (e.key === 'ArrowLeft') j = (i-1+tabs.length) % tabs.length;
    if (e.key === 'Home') j = 0; if (e.key === 'End') j = tabs.length-1;
    if (j !== null) { e.preventDefault(); select(tabs[j], true); } });
});
function fromHash(){ const t = document.getElementById('t-' + (location.hash.slice(1) === 'singing' ? 'concerts' : location.hash.slice(1)));
  if (t) { select(t); $('#performances').scrollIntoView({behavior: reduce ? 'auto' : 'smooth'}); } }
addEventListener('hashchange', fromHash); fromHash();
$$('[data-tab]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); const t = document.getElementById(a.dataset.tab); if (t) { select(t); history.replaceState(null,'','#'+t.id.slice(2)); } }));

/* lightbox */
const G = JSON.parse($('#galleries').textContent);
const lb = $('#lightbox'), track = $('#lbTrack'), cap = $('#lbCap'), count = $('#lbCount');
let cur = [], idx = 0, opener = null, meta = {};
function render(i){ const s = cur[i], slide = track.children[i]; if (!slide || slide.dataset.done) return; slide.dataset.done = 1;
  if (s.t === 'img') { const im = new Image(); im.src = s.src; im.alt = s.cap || ''; im.decoding = 'async'; slide.appendChild(im); }
  else if (s.t === 'mp4') { const v = document.createElement('video'); v.src = s.src; v.controls = true; v.preload = 'none'; v.playsInline = true; if (s.poster) v.poster = s.poster; slide.appendChild(v); }
  else if (s.t === 'yt') { const w = document.createElement('div'); w.className = 'yt'; const b = document.createElement('button'); b.className = 'facade';
    b.dataset.yt = s.id; if (s.start) b.dataset.start = s.start; if (s.end) b.dataset.end = s.end; b.setAttribute('aria-label','Play video');
    b.innerHTML = '<img src="https://i.ytimg.com/vi/'+s.id+'/hqdefault.jpg" alt="" onerror="this.remove()"><span class="play"><svg viewBox="0 0 24 24" width="28" height="28"><path d="M8 5v14l11-7z" fill="currentColor"/></svg></span>';
    bindFacade(b); w.appendChild(b); slide.appendChild(w); } }
function show(i){ idx = Math.max(0, Math.min(cur.length-1, i)); [idx-1, idx, idx+1].forEach(render);
  cap.innerHTML = ''; const d = document.createElement('span'); d.className = 'lb-desc';
  d.textContent = idx === 0 && meta.desc ? (meta.title + '. ' + meta.desc) : (meta.title || ''); cap.appendChild(d);
  cap.appendChild(document.createTextNode(cur[idx].cap || '')); count.textContent = (idx+1) + ' / ' + cur.length; }
function go(i){ track.children[i]?.scrollIntoView({behavior: reduce ? 'auto' : 'smooth', inline:'center', block:'nearest'}); }
let scrollT;
track.addEventListener('scroll', () => { clearTimeout(scrollT); scrollT = setTimeout(() => {
  const i = Math.round(track.scrollLeft / track.clientWidth);
  if (i !== idx) { track.querySelectorAll('video').forEach(v => v.pause()); track.querySelectorAll('iframe').forEach(f => f.remove()); show(i); } }, 80); }, {passive:true});
function open(id, btn, start = 0){ meta = G[id] || {}; cur = meta.s || []; if (!cur.length) return; opener = btn; track.innerHTML = '';
  cur.forEach(() => { const d = document.createElement('div'); d.className = 'lb-slide'; track.appendChild(d); });
  stopAll(); lb.showModal(); history.pushState({lb:1}, ''); start = Math.min(start, cur.length-1); track.scrollLeft = start * track.clientWidth; show(start); }
function close(){ if (!lb.open) return; track.innerHTML = ''; lb.close(); opener?.focus(); }
$$('[data-gallery]').forEach(b => b.addEventListener('click', ev => { ev.preventDefault(); open(b.dataset.gallery, b, +b.dataset.index || 0); }));
$('#lbClose').addEventListener('click', () => history.state?.lb ? history.back() : close());
$('#lbPrev').addEventListener('click', () => go(idx-1));
$('#lbNext').addEventListener('click', () => go(idx+1));
lb.addEventListener('cancel', ev => { ev.preventDefault(); history.state?.lb ? history.back() : close(); });
lb.addEventListener('keydown', ev => { if (ev.key === 'ArrowRight') go(idx+1); if (ev.key === 'ArrowLeft') go(idx-1); });
addEventListener('popstate', () => close());

/* invite form: WhatsApp to the bookings contact, plus an email copy when a key is set */
const form = $('#inviteForm');
if (form) form.addEventListener('submit', async ev => { ev.preventDefault();
  const f = new FormData(form), v = k => (f.get(k) || '').toString().trim();
  const need = ['name','phone','event','date','msg'].find(k => !v(k)); if (need) { $('#formErr').hidden = false; form[need].focus(); return; }
  let phone = v('phone').replace(/[^\d+]/g, ''); if (!phone.startsWith('+')) phone = v('cc') + phone.replace(/^0+/, '');
  const err = $('#formErr'), say = m => { err.textContent = m; err.hidden = false; };
  if (!/^\+\d{7,15}$/.test(phone)) { say('Please check your phone number.'); form.phone.focus(); return; }
  if (v('email') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v('email'))) { say('Please check your email address.'); form.email.focus(); return; }
  let last = 0; try { last = +localStorage.getItem('cs_sent') || 0; } catch (e) {}
  if (Date.now() - last < 60000) { say('Your message was just sent. Please wait a minute before sending another.'); return; }
  err.hidden = true;
  const lines = ['New enquiry from ' + v('name') + ', ' + phone, '', 'Name: ' + v('name'), 'Phone / WhatsApp: ' + phone, '', 'Event: ' + v('event')];
  lines.push('Possible date: ' + v('date'), '', 'Description: ' + v('msg'));
  lines.push('', 'Sent from Chathurya website');
  const text = lines.join('\n').slice(0, 1500); const done = $('#formDone'); const btn = form.querySelector('[data-send]');
  btn.disabled = true;
  if (f.get('botcheck')) { btn.disabled = false; return; }
  if (form.dataset.endpoint) {
    let res = null;
    try { const r = await fetch(form.dataset.endpoint, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({ name: v('name'), phone, email: v('email'), event: v('event'), date: v('date'), msg: v('msg'), page: location.href }) });
      res = await r.json(); } catch (e) { res = null; }
    if (!res || !res.ok) { btn.disabled = false; say((res && res.message) || 'Sorry, the message could not be sent. Please try again, or email ' + (form.dataset.mail || 'us') + '.'); return; }
  } else {
    try { JSON.parse(form.dataset.alerts || '[]').forEach(([ph, k], i) => setTimeout(() => {
      const u = 'https://api.callmebot.com/whatsapp.php?phone=' + ph.replace(/\D/g, '') + '&apikey=' + encodeURIComponent(k) + '&text=' + encodeURIComponent(text);
      (window.__beacons = window.__beacons || []).push(Object.assign(new Image(), { src: u })); }, i * 2500)); } catch (e) {}
    if (form.dataset.mail) {
      try { await fetch('https://formsubmit.co/ajax/' + form.dataset.mail, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ _subject: 'New enquiry: ' + v('event') + ' (' + v('name') + ')', _template: 'table', _captcha: 'false', _autoresponse: 'Thank you for contacting Chathurya Sandabarana. We have received your message and will get back to you on WhatsApp as soon as possible.',
          Name: v('name'), Phone: phone, email: v('email'), Event: v('event'), 'Possible date': v('date'), Description: v('msg'), Page: location.href }) }); } catch (e) {}
    }
  }
  try { localStorage.setItem('cs_sent', Date.now()); } catch (e) {}
  btn.disabled = false;
  if (form.dataset.wa) { window.open('https://wa.me/' + form.dataset.wa + '?text=' + encodeURIComponent(text), '_blank', 'noopener');
    done.textContent = 'Thank you. WhatsApp has opened with your message ready. Press send there and we will reply on WhatsApp.'; }
  else {
    const cf = $('#formConfirm'), dl = $('#cfList'); dl.innerHTML = '';
    [['Name', v('name')], ['Phone / WhatsApp', phone], ['Event', v('event')], ['Possible date', v('date')], ['Description', v('msg')]].forEach(([k, val]) => {
      const dt = document.createElement('dt'), dd = document.createElement('dd'); dt.textContent = k; dd.textContent = val; dl.append(dt, dd); });
    $('#cfTitle').textContent = 'Thank you, ' + v('name') + '. Your message has been sent.';
    $('#cfLead').textContent = 'We will contact you on WhatsApp at ' + phone + ' as soon as possible. Here is what you sent:';
    $('#cfNote').textContent = v('email') ? 'A confirmation copy is also on its way to ' + v('email') + '.' : 'Please keep WhatsApp open on this number so we can reach you.';
    form.hidden = true; cf.hidden = false; cf.focus(); cf.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' }); form.reset(); return; }
  done.hidden = false; done.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'nearest' }); });
const again = $('#cfAgain'); if (again) again.addEventListener('click', () => { $('#formConfirm').hidden = true; form.hidden = false; form.name.focus(); });

/* portrait tilt */
const portrait = $('.portrait');
if (portrait && !reduce && matchMedia('(pointer:fine)').matches) {
  addEventListener('pointermove', e => { const x = e.clientX/innerWidth - .5, y = e.clientY/innerHeight - .5;
    portrait.style.transform = `rotateY(${x*-10}deg) rotateX(${y*6}deg)`; }, {passive:true}); }

/* hero waves */
const c = $('#waves'), g = c.getContext('2d');
const lowEnd = (navigator.connection && navigator.connection.saveData) || (navigator.hardwareConcurrency || 8) <= 4;
let W, H, mx=0, my=0, tx=0, ty=0, run = false, last = 0;
function size(){ const d = Math.min(devicePixelRatio||1, 2); W = c.clientWidth; H = c.clientHeight; c.width = W*d; c.height = H*d; g.setTransform(d,0,0,d,0,0); draw(0); }
addEventListener('pointermove', e => { tx = e.clientX/innerWidth - .5; ty = e.clientY/innerHeight - .5; }, {passive:true});
function draw(t){ t *= .00045; mx += (tx-mx)*.04; my += (ty-my)*.04; g.clearRect(0,0,W,H);
  const R = W < 700 ? 16 : 26, N = W < 700 ? 60 : 90, f = Math.min(W,H)*1.1, cx = W*(.62+mx*.05), hz = H*(.42+my*.04);
  for (let r = R-1; r >= 0; r--){ const z = 1.2 + r*.42*26/R, dp = 1 - r/R; g.beginPath();
    for (let i = 0; i <= N; i++){ const wx = (i/N*2-1)*9, amp = .5+.35*Math.sin(r*.35+t*2);
      const wy = Math.sin(wx*.55+t*3+r*.28)*amp*.6 + Math.sin(wx*1.3-t*2.2+r*.5)*.22 + Math.cos(wx*.25+r*.15-t)*.35;
      const px = cx + (wx+mx*2)/z*f*.42, py = hz + (1.6-wy)/z*f*.32; i ? g.lineTo(px,py) : g.moveTo(px,py); }
    g.strokeStyle = `rgba(${212+(1-dp)*20|0},${165+(1-dp)*40|0},${58+(1-dp)*60|0},${.05+dp*dp*.38})`; g.lineWidth = .6+dp*1.1; g.stroke(); } }
function loop(ts){ if (!run) return; if (ts - last > 33) { draw(ts); last = ts; } requestAnimationFrame(loop); }
addEventListener('resize', size); size();
if (!reduce && !lowEnd) {
  new IntersectionObserver(en => { const was = run; run = en[0].isIntersecting && !document.hidden; if (run && !was) requestAnimationFrame(loop); }).observe(c);
  document.addEventListener('visibilitychange', () => { run = !document.hidden && c.getBoundingClientRect().bottom > 0; if (run) requestAnimationFrame(loop); }); }
})();
(function(){
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
/* background darkens from forest green to near-black as you scroll */
const from=[14,44,37], to=[5,15,12], root=document.documentElement;
function bg(){ const max=Math.max(1,document.body.scrollHeight-innerHeight); const t=Math.min(1,scrollY/max);
  const c=from.map((v,i)=>Math.round(v+(to[i]-v)*t)); root.style.setProperty('--bg',`rgb(${c})`); }
addEventListener('scroll',bg,{passive:true}); addEventListener('resize',bg); bg();
/* reveal gold accents when they come into view */
document.querySelectorAll('main h2').forEach(h=>h.classList.add('reveal'));
const io=new IntersectionObserver(es=>es.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target);
  const n=e.target.querySelector('.num[data-count]'); if(n && !reduce){ const end=+n.dataset.count; let k=0; const st=performance.now();
    (function tick(ts){ k=Math.min(1,(ts-st)/1200); n.textContent=Math.round(end*(1-Math.pow(1-k,3))); if(k<1) requestAnimationFrame(tick); })(st); } } }),{threshold:.35});
document.querySelectorAll('.divider, h2.reveal, .hl-tile, .ms, .medal').forEach(el=>io.observe(el));
/* 3D tilt for milestone cards */
const fine=matchMedia('(pointer:fine)').matches;
document.querySelectorAll('.ms').forEach(card=>{ if(reduce) return;
  if(fine){ card.addEventListener('pointermove',ev=>{ const r=card.getBoundingClientRect(), x=(ev.clientX-r.left)/r.width, y=(ev.clientY-r.top)/r.height;
      card.classList.add('live'); card.style.setProperty('--ry',((x-.5)*16).toFixed(2)+'deg'); card.style.setProperty('--rx',((.5-y)*12).toFixed(2)+'deg');
      card.style.setProperty('--gx',(x*100).toFixed(0)+'%'); card.style.setProperty('--gy',(y*100).toFixed(0)+'%'); });
    card.addEventListener('pointerleave',()=>{ card.style.setProperty('--rx','0deg'); card.style.setProperty('--ry','0deg'); }); } });
if(!reduce && !fine){ const cards=[...document.querySelectorAll('.ms')];
  const tilt=()=>cards.forEach(c=>{ const r=c.getBoundingClientRect(); const t=((r.top+r.height/2)/innerHeight-.5); c.classList.add('live');
    c.style.setProperty('--rx',(t*-14).toFixed(2)+'deg'); c.style.setProperty('--gy',(50+t*80).toFixed(0)+'%'); });
  addEventListener('scroll',()=>requestAnimationFrame(tilt),{passive:true}); }
/* 3D gold wave ribbons, same language as the hero waves */
const lowEnd=(navigator.connection&&navigator.connection.saveData)||(navigator.hardwareConcurrency||8)<=4;
const ribs=[...document.querySelectorAll('.divider canvas')].map((cv,k)=>({cv,g:cv.getContext('2d'),gem:cv.parentNode.querySelector('.gem'),k,on:false,W:0,H:0}));
function rsize(r){ const d=Math.min(devicePixelRatio||1,2); r.W=r.cv.clientWidth; r.H=r.cv.clientHeight; r.cv.width=r.W*d; r.cv.height=r.H*d; r.g.setTransform(d,0,0,d,0,0); }
function rdraw(r,t){ const {g,W,H,k}=r; g.clearRect(0,0,W,H); t*=.00035; const L=W<700?11:16, N=W<700?70:120, ph=k*1.7;
  for(let j=L-1;j>=0;j--){ const z=1+j*.16, dp=1-j/L; g.beginPath();
    for(let i=0;i<=N;i++){ const u=i/N, x=(u*2-1)*6;
      const h=Math.sin(x*.62+t*2.4+j*.32+ph)*.55+Math.sin(x*1.45-t*1.7+j*.55)*.22+Math.cos(x*.3+j*.2-t+ph)*.3;
      const env=Math.sin(Math.PI*u);
      const px=W/2+(u-.5)*W*(1.08/(.85+.15*z)), py=H*.5+(j-L/2)*H*.03/z-h*env*H*.2/z;
      i?g.lineTo(px,py):g.moveTo(px,py); if(j===0&&i===N/2&&r.gem) r.gem.style.top=py+'px'; }
    g.strokeStyle=`rgba(${212+(1-dp)*24|0},${165+(1-dp)*45|0},${58+(1-dp)*70|0},${.06+dp*dp*.55})`; g.lineWidth=.5+dp*1.2; g.stroke(); } }
ribs.forEach(r=>{ rsize(r); rdraw(r,0); });
addEventListener('resize',()=>ribs.forEach(r=>{ rsize(r); rdraw(r,performance.now()); }));
if(!reduce&&!lowEnd&&ribs.length){ let last=0;
  const vio=new IntersectionObserver(es=>es.forEach(e=>{ ribs.find(r=>r.cv===e.target).on=e.isIntersecting; }));
  ribs.forEach(r=>vio.observe(r.cv));
  (function loop(ts){ if(ts-last>33&&!document.hidden){ last=ts; ribs.forEach(r=>r.on&&rdraw(r,ts)); } requestAnimationFrame(loop); })(0); }
})();

/* ---- visitor analytics: our own, cookieless. Events go to the site's Google Apps Script collector. ---- */
(function(){
const ep = (document.querySelector('meta[name="site-collector"]') || {}).content; if (!ep) return;
let sid = ''; try { sid = sessionStorage.getItem('cs_sid'); if (!sid) { sid = Math.random().toString(36).slice(2, 12) + Date.now().toString(36); sessionStorage.setItem('cs_sid', sid); } } catch (e) { sid = 'x' + Date.now().toString(36); }
let returning = false; try { returning = !!localStorage.getItem('cs_seen'); localStorage.setItem('cs_seen', '1'); } catch (e) {}
let src = 'direct'; try { const r = document.referrer && new URL(document.referrer); if (r && r.hostname !== location.hostname) src = r.hostname.replace(/^www\./, ''); } catch (e) {}
const u = new URLSearchParams(location.search); if (u.get('utm_source') || u.get('src')) src = u.get('utm_source') || u.get('src');
const ctx = { kind: 'events', sid, path: location.pathname + (location.hash || ''), source: src, tz: (Intl.DateTimeFormat().resolvedOptions().timeZone || ''), lang: navigator.language || '',
  device: matchMedia('(max-width: 700px)').matches ? 'phone' : matchMedia('(max-width: 1100px)').matches ? 'tablet' : 'computer', returning, width: innerWidth };
let q = [], timer = null;
function flush(beacon) { if (!q.length) return; const body = JSON.stringify(Object.assign({}, ctx, { events: q.splice(0, 40) }));
  if (beacon && navigator.sendBeacon) { navigator.sendBeacon(ep, new Blob([body], { type: 'text/plain' })); return; }
  fetch(ep, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' }, body, keepalive: true }).catch(() => {}); }
const T = (n, d) => { q.push({ n, d: d || {} }); clearTimeout(timer); timer = setTimeout(() => flush(false), 2500); if (q.length >= 20) flush(false); };
window.__track = T;
T('Page view');
const t0 = Date.now(); let lastSent = 0;
const tick = () => { const s = Math.round((Date.now() - t0) / 1000); if (s - lastSent >= 30) { lastSent = s; T('Time on page', { seconds: s }); } };
setInterval(tick, 30000);
addEventListener('pagehide', () => { const s = Math.round((Date.now() - t0) / 1000); q.push({ n: 'Time on page', d: { seconds: s } }); flush(true); });
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flush(true); });
const label = el => (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
document.addEventListener('click', ev => {
  const el = ev.target.closest('a, button'); if (!el) return;
  const where = el.closest('section, header, footer, dialog'); const sec = where ? (where.id || where.className.split(' ')[0] || where.tagName.toLowerCase()) : 'page';
  if (el.matches('.tab')) return T('Tab opened', { tab: label(el) });
  if (el.matches('.facade, .tvclip')) return T('Video played', { video: label(el), section: sec });
  if (el.dataset.gallery) return T('Gallery opened', { gallery: el.dataset.gallery, section: sec });
  if (el.matches('[data-send]')) return T('Invite: send pressed');
  if (el.matches('#cfAgain')) return T('Invite: send another');
  if (el.matches('.edu-chip')) return T('Education chip');
  const href = el.getAttribute('href') || '';
  if (href.startsWith('mailto:')) return T('Email link', { section: sec });
  if (href.startsWith('tel:')) return T('Phone call link', { section: sec });
  if (/wa\.me|whatsapp/.test(href)) return T('WhatsApp link', { section: sec });
  if (/youtube\.com|youtu\.be/.test(href)) return T('YouTube link', { section: sec });
  if (/instagram\.com/.test(href)) return T('Instagram link', { section: sec });
  if (href.startsWith('#') || href.includes('.html')) return T('Navigation', { to: href, from: sec, label: label(el) });
  if (el.matches('a[href^="http"]')) return T('Outbound link', { url: href.slice(0, 80) });
}, { capture: true });
const form = document.getElementById('inviteForm');
if (form) {
  let started = false;
  form.addEventListener('input', () => { if (!started) { started = true; T('Invite: form started'); } });
  const cf = document.getElementById('formConfirm');
  if (cf) new MutationObserver(() => { if (!cf.hidden) T('Invite: sent successfully'); }).observe(cf, { attributes: true, attributeFilter: ['hidden'] });
  const err = document.getElementById('formErr');
  if (err) new MutationObserver(() => { if (!err.hidden) T('Invite: error shown', { message: err.textContent.slice(0, 60) }); }).observe(err, { attributes: true, childList: true });
}
const seen = new Set();
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting && !seen.has(e.target.id)) { seen.add(e.target.id); T('Section viewed', { section: e.target.id }); } }), { threshold: .4 });
document.querySelectorAll('main section[id]').forEach(s => io.observe(s));
})();
