/**
 * Chathurya website server: enquiries + visitor analytics + private dashboard.
 * Google Apps Script bound to a Google Sheet, running under the site owner's Google account.
 *
 * Deploy twice from the same project (Deploy > New deployment > Web app):
 *   1. Execute as: Me. Who has access: Anyone.        -> COLLECTOR url (the website posts here)
 *   2. Execute as: Me. Who has access: Only myself.    -> DASHBOARD url (open it in a browser, signed in)
 * Script properties (Project Settings > Script properties):
 *   OWNER_EMAIL   inbox for enquiries (also the only account allowed to view the dashboard)
 *   ALERTS        CallMeBot pairs, e.g. 447700900123:1234567,447700900456:7654321   (optional)
 */

var FIELDS = { name: 80, phone: 20, email: 120, event: 150, date: 80, msg: 1500, page: 200, botcheck: 5 };
var REQUIRED = ['name', 'phone', 'event', 'date', 'msg'];
var EVENT_NAMES = ['Page view', 'Section viewed', 'Tab opened', 'Video played', 'Gallery opened', 'Navigation', 'Education chip',
  'Email link', 'Phone call link', 'WhatsApp link', 'YouTube link', 'Instagram link', 'Outbound link',
  'Invite: form started', 'Invite: send pressed', 'Invite: error shown', 'Invite: sent successfully', 'Invite: send another', 'Time on page'];

function doPost(e) {
  try {
    var body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (body.kind === 'events') return handleEvents_(body);
    return handleEnquiry_(body);
  } catch (err) { console.error(err); return reply_(500, 'Something went wrong. Please try again or email us.'); }
}

function doGet(e) {
  var me = (Session.getActiveUser().getEmail() || '').toLowerCase();
  var owner = (prop_('OWNER_EMAIL') || Session.getEffectiveUser().getEmail() || '').toLowerCase();
  if (!me || me !== owner) return ContentService.createTextOutput('Chathurya site collector is running.');
  var days = Math.min(365, Math.max(1, Number((e && e.parameter && e.parameter.days) || 30)));
  var t = HtmlService.createTemplateFromFile('dashboard');
  t.stats = JSON.stringify(stats_(days)); t.days = days;
  return t.evaluate().setTitle('Chathurya site: visitors').addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/* ---------------- analytics ---------------- */
function handleEvents_(b) {
  var evs = Array.isArray(b.events) ? b.events.slice(0, 40) : [];
  var sid = String(b.sid || '').replace(/[^a-z0-9]/gi, '').slice(0, 24) || 'anon';
  var ctx = { path: s_(b.path, 80), source: s_(b.source, 60), tz: s_(b.tz, 40), lang: s_(b.lang, 10),
    device: s_(b.device, 10), returning: b.returning ? 1 : 0, width: Number(b.width) || 0 };
  var cache = CacheService.getScriptCache(), k = 'ev:' + sid, n = Number(cache.get(k) || 0);
  if (n > 400) return reply_(200, 'ok');
  cache.put(k, String(n + evs.length), 21600);
  var rows = [], now = new Date();
  evs.forEach(function (ev) {
    var name = s_(ev.n, 40); if (EVENT_NAMES.indexOf(name) < 0) return;
    var data = {}; if (ev.d && typeof ev.d === 'object') Object.keys(ev.d).slice(0, 6).forEach(function (kk) { data[s_(kk, 20)] = s_(ev.d[kk], 80); });
    rows.push([now, sid, name, JSON.stringify(data), ctx.path, ctx.source, ctx.tz, ctx.lang, ctx.device, ctx.returning, ctx.width]);
  });
  if (rows.length) {
    var lock = LockService.getScriptLock(); lock.waitLock(5000);
    try { var sh = sheet_('Events', ['Time', 'Session', 'Event', 'Data', 'Page', 'Source', 'Timezone', 'Language', 'Device', 'Returning', 'Width']);
      sh.getRange(sh.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows); } finally { lock.releaseLock(); }
  }
  return reply_(200, 'ok');
}

function stats_(days) {
  var sh = sheet_('Events', []), last = sh.getLastRow(); if (last < 2) return empty_(days);
  var since = Date.now() - days * 864e5, chunk = 2000, rows = [], r = last;
  while (r > 1) { var from = Math.max(2, r - chunk + 1), vals = sh.getRange(from, 1, r - from + 1, 11).getValues();
    var stop = false; for (var i = vals.length - 1; i >= 0; i--) { if (new Date(vals[i][0]).getTime() < since) { stop = true; break; } rows.push(vals[i]); }
    if (stop) break; r = from - 1; }
  var S = empty_(days), sessions = {}, byDay = {};
  function inc(o, k, w) { if (k === undefined || k === null || k === '') k = '(none)'; o[k] = (o[k] || 0) + (w || 1); }
  rows.forEach(function (v) {
    var ts = new Date(v[0]), sid = v[1], ev = v[2], d = {}; try { d = JSON.parse(v[3] || '{}'); } catch (e) {}
    var day = Utilities.formatDate(ts, 'UTC', 'yyyy-MM-dd');
    if (!sessions[sid]) { sessions[sid] = { source: v[5], tz: v[6], device: v[8], ret: v[9], secs: 0 }; byDay[day] = byDay[day] || {}; byDay[day][sid] = 1; }
    var se = sessions[sid];
    if (ev === 'Page view') { inc(S.pages, v[4]); S.pageviews++; }
    else if (ev === 'Section viewed') inc(S.sections, d.section);
    else if (ev === 'Tab opened') inc(S.tabs, d.tab);
    else if (ev === 'Video played') inc(S.videos, d.video);
    else if (ev === 'Gallery opened') inc(S.galleries, d.gallery);
    else if (ev === 'Time on page') se.secs = Math.max(se.secs, Number(d.seconds) || 0);
    else if (/^Invite: /.test(ev)) { inc(S.invite, ev.replace('Invite: ', '')); if (ev === 'Invite: error shown') inc(S.errors, d.message); }
    else if (/ link$/.test(ev)) inc(S.links, ev.replace(' link', ''));
    else if (ev === 'Navigation') inc(S.nav, d.label || d.to);
    else if (ev === 'Education chip') inc(S.nav, 'Education chip');
  });
  var ids = Object.keys(sessions); S.visitors = ids.length;
  var times = [], retn = 0;
  ids.forEach(function (id) { var se = sessions[id]; inc(S.sources, src_(se.source)); inc(S.regions, region_(se.tz)); inc(S.devices, se.device || 'unknown');
    if (se.ret) retn++; if (se.secs) times.push(se.secs); });
  S.returning = retn; S.medianSeconds = times.length ? times.sort(function (a, b) { return a - b; })[Math.floor(times.length / 2)] : 0;
  for (var i = days - 1; i >= 0; i--) { var dd = Utilities.formatDate(new Date(Date.now() - i * 864e5), 'UTC', 'yyyy-MM-dd'); S.daily.push([dd.slice(5), Object.keys(byDay[dd] || {}).length]); }
  var is = {}; rows.forEach(function (v) { if (/^Invite: /.test(v[2])) { var k = v[2].replace('Invite: ', ''); is[k] = is[k] || {}; is[k][v[1]] = 1; } });
  Object.keys(is).forEach(function (k) { S.inviteSessions[k] = Object.keys(is[k]).length; });
  S.enquiries = Math.max(0, sheet_('Enquiries', []).getLastRow() - 1);
  return S;
}
function empty_(days) { return { days: days, visitors: 0, pageviews: 0, returning: 0, medianSeconds: 0, daily: [], pages: {}, sources: {}, regions: {}, devices: {}, sections: {}, tabs: {}, videos: {}, galleries: {}, invite: {}, inviteSessions: {}, errors: {}, links: {}, nav: {}, enquiries: 0 }; }
function src_(s) { s = String(s || '').toLowerCase(); if (!s || s === 'direct') return 'Direct, typed or WhatsApp';
  if (/facebook|fb\.|m\.me/.test(s)) return 'Facebook'; if (/instagram/.test(s)) return 'Instagram'; if (/google/.test(s)) return 'Google';
  if (/youtube|youtu\.be/.test(s)) return 'YouTube'; if (/tiktok/.test(s)) return 'TikTok'; if (/whatsapp/.test(s)) return 'WhatsApp'; if (/t\.co|twitter|x\.com/.test(s)) return 'X'; if (/linkedin/.test(s)) return 'LinkedIn'; return s; }
function region_(tz) { tz = String(tz || ''); var m = { 'Asia/Colombo': 'Sri Lanka', 'Europe/London': 'UK', 'Asia/Dubai': 'UAE', 'Asia/Qatar': 'Qatar', 'Asia/Riyadh': 'Saudi Arabia', 'Australia/Sydney': 'Australia', 'Australia/Melbourne': 'Australia', 'Asia/Kolkata': 'India', 'Asia/Singapore': 'Singapore', 'Europe/Paris': 'France', 'Europe/Rome': 'Italy', 'Europe/Berlin': 'Germany', 'America/New_York': 'USA (East)', 'America/Los_Angeles': 'USA (West)', 'America/Toronto': 'Canada', 'Asia/Seoul': 'South Korea', 'Asia/Tokyo': 'Japan', 'Asia/Kuala_Lumpur': 'Malaysia', 'Asia/Kuwait': 'Kuwait', 'Asia/Muscat': 'Oman', 'Asia/Bahrain': 'Bahrain', 'Europe/Dublin': 'Ireland', 'Pacific/Auckland': 'New Zealand' };
  return m[tz] || (tz.split('/')[0] || 'Unknown'); }

/* ---------------- enquiries ---------------- */
function handleEnquiry_(body) {
  var clean = validate_(body); if (clean.error) return reply_(400, clean.error);
  if (clean.data.botcheck) return reply_(200, 'ok');
  var limited = rateLimit_(clean.data.phone); if (limited) return reply_(429, limited);
  var d = clean.data;
  var text = ['New enquiry from ' + d.name + ', ' + d.phone, '', 'Name: ' + d.name, 'Phone / WhatsApp: ' + d.phone, d.email ? 'Email: ' + d.email : '', '',
    'Event: ' + d.event, 'Possible date: ' + d.date, '', 'Description: ' + d.msg, '', 'Sent from Chathurya website']
    .filter(function (l, i, a) { return !(l === '' && a[i - 1] === ''); }).join('\n');
  sendWhatsApp_(text); sendEmails_(d, text);
  var sh = sheet_('Enquiries', ['Received', 'Name', 'Phone', 'Email', 'Event', 'Possible date', 'Description', 'Status', 'Notes']);
  sh.appendRow([new Date(), d.name, "'" + d.phone, d.email || '', d.event, d.date, d.msg, 'New', '']);
  return reply_(200, 'ok');
}
function validate_(b) {
  if (typeof b !== 'object' || b === null || Array.isArray(b)) return { error: 'Invalid request.' };
  var out = {};
  for (var k in b) { if (k === 'kind') continue; if (!FIELDS.hasOwnProperty(k)) return { error: 'Unknown field: ' + k };
    var v = b[k]; if (typeof v !== 'string') return { error: 'Invalid value for ' + k };
    v = v.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '').trim(); if (v.length > FIELDS[k]) return { error: 'Too long: ' + k }; out[k] = v; }
  for (var i = 0; i < REQUIRED.length; i++) if (!out[REQUIRED[i]]) return { error: 'Missing: ' + REQUIRED[i] };
  out.phone = out.phone.replace(/[\s()-]/g, ''); if (!/^\+?\d{7,15}$/.test(out.phone)) return { error: 'Please check the phone number.' };
  if (out.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(out.email)) return { error: 'Please check the email address.' };
  return { data: out };
}
function rateLimit_(phone) {
  var cache = CacheService.getScriptCache(), hour = Utilities.formatDate(new Date(), 'UTC', 'yyyyMMddHH');
  var kp = 'p:' + phone + ':' + hour, kt = 't:' + hour, np = Number(cache.get(kp) || 0), nt = Number(cache.get(kt) || 0);
  if (np >= 3) return 'You have already sent a few messages. Please wait an hour, or email us.';
  if (nt >= 30) return 'We are receiving a lot of messages right now. Please try again later or email us.';
  cache.put(kp, String(np + 1), 3600); cache.put(kt, String(nt + 1), 3600); return '';
}
function sendWhatsApp_(text) {
  (prop_('ALERTS') || '').split(',').forEach(function (pair, i) { var p = pair.trim().split(':'); if (p.length !== 2) return; if (i) Utilities.sleep(2500);
    try { UrlFetchApp.fetch('https://api.callmebot.com/whatsapp.php?phone=' + encodeURIComponent(p[0]) + '&apikey=' + encodeURIComponent(p[1]) + '&text=' + encodeURIComponent(text), { muteHttpExceptions: true }); }
    catch (e) { console.error('WhatsApp ' + p[0] + ': ' + e); } });
}
function sendEmails_(d, text) {
  var owner = prop_('OWNER_EMAIL');
  if (owner) MailApp.sendEmail({ to: owner, subject: 'New enquiry: ' + d.event + ' (' + d.name + ')', body: text, replyTo: d.email || owner });
  if (d.email) MailApp.sendEmail({ to: d.email, subject: 'Thank you for contacting Chathurya Sandabarana',
    body: 'Dear ' + d.name + ',\n\nThank you for your message. We have received it and will get back to you on WhatsApp at ' + d.phone + ' as soon as possible.\n\nYour message:\nEvent: ' + d.event + '\nPossible date: ' + d.date + '\n\n' + d.msg + '\n\nChathurya Sandabarana' });
}

/* ---------------- helpers ---------------- */
function sheet_(name, header) { var ss = SpreadsheetApp.getActiveSpreadsheet(), sh = ss.getSheetByName(name) || ss.insertSheet(name);
  if (sh.getLastRow() === 0 && header.length) { sh.appendRow(header); sh.setFrozenRows(1); } return sh; }
function prop_(k) { return PropertiesService.getScriptProperties().getProperty(k); }
function s_(v, n) { return String(v === undefined || v === null ? '' : v).replace(/[\u0000-\u001F]/g, '').slice(0, n); }
function reply_(code, message) { return ContentService.createTextOutput(JSON.stringify({ ok: code === 200, code: code, message: message })).setMimeType(ContentService.MimeType.JSON); }
function testEnquiry() { console.log(doPost({ postData: { contents: JSON.stringify({ name: 'Test', phone: '+94771234567', event: 'Test concert', date: 'Test date', msg: 'Test message' }) } }).getContent()); }
