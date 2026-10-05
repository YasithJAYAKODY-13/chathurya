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
function fromHash(){ const t = document.getElementById('t-' + location.hash.slice(1));
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
function open(id, btn){ meta = G[id] || {}; cur = meta.s || []; if (!cur.length) return; opener = btn; track.innerHTML = '';
  cur.forEach(() => { const d = document.createElement('div'); d.className = 'lb-slide'; track.appendChild(d); });
  stopAll(); lb.showModal(); history.pushState({lb:1}, ''); track.scrollLeft = 0; show(0); }
function close(){ if (!lb.open) return; track.innerHTML = ''; lb.close(); opener?.focus(); }
$$('[data-gallery]').forEach(b => b.addEventListener('click', ev => { ev.preventDefault(); open(b.dataset.gallery, b); }));
$('#lbClose').addEventListener('click', () => history.state?.lb ? history.back() : close());
$('#lbPrev').addEventListener('click', () => go(idx-1));
$('#lbNext').addEventListener('click', () => go(idx+1));
lb.addEventListener('cancel', ev => { ev.preventDefault(); history.state?.lb ? history.back() : close(); });
lb.addEventListener('keydown', ev => { if (ev.key === 'ArrowRight') go(idx+1); if (ev.key === 'ArrowLeft') go(idx-1); });
addEventListener('popstate', () => close());

/* invite form */
const form = $('#inviteForm');
if (form) form.addEventListener('submit', ev => { ev.preventDefault();
  const how = ev.submitter?.dataset.send || ''; const f = new FormData(form), v = k => (f.get(k) || '').toString().trim();
  if (!v('name') || !v('phone')) { $('#formErr').hidden = false; (v('name') ? form.phone : form.name).focus(); return; }
  $('#formErr').hidden = true;
  const lines = ['Invitation for Chathurya Sandabarana', '', 'Name: ' + v('name')];
  if (v('event')) lines.push('Organisation / event: ' + v('event')); if (v('date')) lines.push('Date: ' + v('date'));
  if (v('town')) lines.push('Town: ' + v('town')); lines.push('Phone / WhatsApp: ' + v('phone')); if (v('msg')) lines.push('', v('msg'));
  const text = lines.join('\n').slice(0, 1500); const done = $('#formDone');
  if (how === 'wa' && form.dataset.wa) { location.href = 'https://wa.me/' + form.dataset.wa + '?text=' + encodeURIComponent(text); done.textContent = 'Your message is ready in WhatsApp. Press send there.'; }
  else if (how === 'mail' && form.dataset.mail) { location.href = 'mailto:' + form.dataset.mail + '?subject=' + encodeURIComponent('Invitation to perform') + '&body=' + encodeURIComponent(text.replace(/\n/g, '\r\n')); done.textContent = 'Your message is ready in your email app. Press send there.'; }
  done.hidden = false; });

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
document.querySelectorAll('.divider, h2.reveal, .hl-tile').forEach(el=>io.observe(el));
})();
