(function(){
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];

/* header glass */
const bar = $('#bar');
const onScroll = () => bar.classList.toggle('solid', scrollY > 40);
addEventListener('scroll', onScroll, {passive:true}); onScroll();

/* hide stale "next performance" */
const nx = $('.next[data-date]');
if (nx && new Date(nx.dataset.date + 'T23:59:59') < new Date()) nx.classList.add('past');

/* menu */
const menu = $('#menu'), mb = $('#menuBtn');
const closeMenu = () => { menu.hidden = true; mb.setAttribute('aria-expanded','false'); mb.focus(); };
mb.addEventListener('click', () => { menu.hidden = false; mb.setAttribute('aria-expanded','true'); $('#menuClose').focus(); });
$('#menuClose').addEventListener('click', closeMenu);
menu.addEventListener('click', ev => { if (ev.target.closest('nav a')) { menu.hidden = true; mb.setAttribute('aria-expanded','false'); } });
addEventListener('keydown', ev => { if (ev.key === 'Escape' && !menu.hidden) closeMenu(); });

/* sticky bar: hide on scroll down, while invite form visible, while typing */
const sticky = $('#sticky');
let lastY = scrollY, formVisible = false, typing = false, heroVisible = true;
const updSticky = () => sticky.classList.toggle('off', formVisible || typing || hideByScroll || heroVisible);
let hideByScroll = false;
addEventListener('scroll', () => { const y = scrollY; hideByScroll = y > lastY && y > 300; lastY = y; updSticky(); }, {passive:true});
new IntersectionObserver(en => { formVisible = en[0].isIntersecting; updSticky(); }, {threshold:.05}).observe($('#invite'));
new IntersectionObserver(en => { heroVisible = en[0].isIntersecting; updSticky(); }).observe($('.actions'));
addEventListener('focusin', ev => { if (ev.target.matches('input,textarea')) { typing = true; updSticky(); } });
addEventListener('focusout', () => { typing = false; updSticky(); });

/* video facades */
function ytSrc(id, start, end){
  let u = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0&playsinline=1';
  if (start) u += '&start=' + start; if (end) u += '&end=' + end; return u;
}
function stopAll(except){
  $$('.facade iframe, .facade video').forEach(n => { if (!except || !except.contains(n)) n.remove(); });
}
$$('.facade').forEach(f => f.addEventListener('click', () => {
  if (f.querySelector('iframe,video')) return;
  stopAll(f);
  let el;
  if (f.dataset.yt) { el = document.createElement('iframe'); el.src = ytSrc(f.dataset.yt, f.dataset.start, f.dataset.end);
    el.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen'; el.allowFullscreen = true; el.title = f.getAttribute('aria-label'); }
  else { el = document.createElement('video'); el.src = f.dataset.mp4; el.controls = true; el.autoplay = true; el.playsInline = true; }
  f.appendChild(el);
}));

/* concerts: show 6 then "show all" */
const grid = $('#concert-grid'), sa = $('#showall');
if (grid) { const cards = [...grid.children]; if (cards.length > 6) { cards.slice(6).forEach(c => c.classList.add('hide')); sa.hidden = false;
  sa.addEventListener('click', () => { cards.forEach(c => c.classList.remove('hide')); sa.hidden = true; cards[6].querySelector('button,div').focus?.(); }); } }

/* lightbox */
const G = JSON.parse($('#galleries').textContent);
const lb = $('#lightbox'), track = $('#lbTrack'), cap = $('#lbCap'), count = $('#lbCount');
let cur = [], idx = 0, opener = null, meta = {};
function render(i){
  const s = cur[i], slide = track.children[i];
  if (!slide || slide.dataset.done) return;
  slide.dataset.done = 1;
  if (s.t === 'img') { const im = new Image(); im.src = s.src; im.alt = s.cap || ''; im.decoding = 'async'; slide.appendChild(im); }
  else if (s.t === 'mp4') { const v = document.createElement('video'); v.src = s.src; v.controls = true; v.preload = 'none'; v.playsInline = true; if (s.poster) v.poster = s.poster; slide.appendChild(v); }
  else if (s.t === 'yt') { const w = document.createElement('div'); w.className = 'yt'; const b = document.createElement('button'); b.className = 'facade';
    b.setAttribute('aria-label','Play video'); b.innerHTML = '<img src="https://i.ytimg.com/vi/'+s.id+'/hqdefault.jpg" alt="" onerror="this.remove()"><span class="play">▶</span>';
    b.addEventListener('click', () => { const f = document.createElement('iframe'); f.src = ytSrc(s.id, s.start, s.end); f.allow='autoplay; encrypted-media; fullscreen'; f.allowFullscreen = true; b.replaceWith(f); });
    w.appendChild(b); slide.appendChild(w); }
}
function show(i){
  idx = Math.max(0, Math.min(cur.length - 1, i));
  [idx-1, idx, idx+1].forEach(render);
  cap.innerHTML = ''; if (idx === 0 && meta.desc) { const d = document.createElement('span'); d.className='lb-desc'; d.textContent = meta.desc; cap.appendChild(d); } cap.appendChild(document.createTextNode(cur[idx].cap || '')); count.textContent = (idx+1) + ' / ' + cur.length;
}
function go(i){ track.children[i]?.scrollIntoView({behavior: reduce ? 'auto' : 'smooth', inline:'center', block:'nearest'}); }
let scrollT;
track.addEventListener('scroll', () => { clearTimeout(scrollT); scrollT = setTimeout(() => {
  const i = Math.round(track.scrollLeft / track.clientWidth);
  if (i !== idx) { track.querySelectorAll('iframe,video').forEach(n => { if (n.tagName === 'VIDEO') n.pause(); else n.remove(); }); show(i); } }, 80); }, {passive:true});
function open(id, btn){
  meta = G[id] || {}; cur = meta.s || []; if (!cur.length) return;
  opener = btn; track.innerHTML = '';
  cur.forEach(() => { const d = document.createElement('div'); d.className = 'lb-slide'; track.appendChild(d); });
  lb.showModal(); history.pushState({lb:1}, '');
  track.scrollLeft = 0; show(0);
}
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
form.addEventListener('submit', ev => {
  ev.preventDefault();
  const how = ev.submitter?.dataset.send || 'fb';
  const f = new FormData(form), v = k => (f.get(k) || '').toString().trim();
  if (!v('name') || !v('phone')) { $('#formErr').hidden = false; (v('name') ? form.phone : form.name).focus(); return; }
  $('#formErr').hidden = true;
  const lines = ['Invitation for Chathurya Sandabarana', '', 'Name: ' + v('name')];
  if (v('event')) lines.push('Organisation / event: ' + v('event'));
  if (v('date')) lines.push('Date: ' + v('date'));
  if (v('town')) lines.push('Town: ' + v('town'));
  lines.push('Phone / WhatsApp: ' + v('phone'));
  if (v('msg')) lines.push('', v('msg'));
  const text = lines.join('\n').slice(0, 1500);
  const done = $('#formDone');
  if (how === 'wa' && form.dataset.wa) { location.href = 'https://wa.me/' + form.dataset.wa + '?text=' + encodeURIComponent(text); done.textContent = 'Your message is ready in WhatsApp. Press send there.'; }
  else if (how === 'mail' && form.dataset.mail) { location.href = 'mailto:' + form.dataset.mail + '?subject=' + encodeURIComponent('Invitation to perform') + '&body=' + encodeURIComponent(text.replace(/\n/g, '\r\n')); done.textContent = 'Your message is ready in your email app. Press send there.'; }
  else { navigator.clipboard?.writeText(text).catch(()=>{}); window.open(form.dataset.fb, '_blank', 'noopener'); done.textContent = 'Your message has been copied. Paste it into the Messenger chat that opened, then press send.'; }
  done.hidden = false;
});

/* hero waves: only on capable devices, pause when off screen */
const c = $('#waves'), g = c.getContext('2d');
const lowEnd = (navigator.connection && navigator.connection.saveData) || (navigator.hardwareConcurrency || 8) <= 4;
let W, H, mx=0, my=0, tx=0, ty=0, run = false, last = 0;
function size(){ const d = Math.min(devicePixelRatio||1, 2); W = c.clientWidth; H = c.clientHeight; c.width = W*d; c.height = H*d; g.setTransform(d,0,0,d,0,0); draw(0); }
addEventListener('pointermove', e => { tx = e.clientX/innerWidth - .5; ty = e.clientY/innerHeight - .5; }, {passive:true});
function draw(t){
  t *= .00045; mx += (tx-mx)*.04; my += (ty-my)*.04; g.clearRect(0,0,W,H);
  const R = W < 700 ? 16 : 24, N = W < 700 ? 60 : 90;
  const f = Math.min(W,H)*1.1, cx = W*(.62+mx*.05), hz = H*(.42+my*.04);
  for (let r = R-1; r >= 0; r--){ const z = 1.2 + r*.42*24/R, dp = 1 - r/R; g.beginPath();
    for (let i = 0; i <= N; i++){ const wx = (i/N*2-1)*9, amp = .5+.35*Math.sin(r*.35+t*2);
      const wy = Math.sin(wx*.55+t*3+r*.28)*amp*.6 + Math.sin(wx*1.3-t*2.2+r*.5)*.22 + Math.cos(wx*.25+r*.15-t)*.35;
      const px = cx + (wx+mx*2)/z*f*.42, py = hz + (1.6-wy)/z*f*.32; i ? g.lineTo(px,py) : g.moveTo(px,py); }
    g.strokeStyle = `rgba(${212+(1-dp)*20|0},${165+(1-dp)*40|0},${58+(1-dp)*60|0},${.05+dp*dp*.38})`; g.lineWidth = .6+dp*1.1; g.stroke(); }
}
function loop(ts){ if (!run) return; if (ts - last > 33) { draw(ts); last = ts; } requestAnimationFrame(loop); }
addEventListener('resize', size); size();
if (!reduce && !lowEnd) {
  new IntersectionObserver(en => { const was = run; run = en[0].isIntersecting && !document.hidden; if (run && !was) requestAnimationFrame(loop); }).observe(c);
  document.addEventListener('visibilitychange', () => { run = !document.hidden && c.getBoundingClientRect().bottom > 0; if (run) requestAnimationFrame(loop); });
}
})();
