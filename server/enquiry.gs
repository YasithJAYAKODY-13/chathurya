/**
 * Chathurya website: enquiry handler (Google Apps Script web app).
 * Runs on Google's servers under sandabarana@gmail.com, so no keys ever reach the browser.
 *
 * What it does for every enquiry:
 *   1. Validates the fields (strict list, length limits, unknown fields rejected).
 *   2. Rate limits (per phone number and overall).
 *   3. Sends a WhatsApp alert to every number in ALERTS (CallMeBot).
 *   4. Emails the enquiry to OWNER_EMAIL, and a confirmation to the sender if they gave an email.
 *   5. Logs it as a new row in the "Enquiries" sheet.
 *
 * Keys live in Project Settings > Script properties, never in this file:
 *   ALERTS       e.g.  447700900123:1234567,447700900456:7654321  (number:apikey pairs)
 *   OWNER_EMAIL  the inbox that receives enquiries
 */

var FIELDS = { name: 80, phone: 20, email: 120, event: 150, date: 80, msg: 1500, page: 200, botcheck: 5 };
var REQUIRED = ['name', 'phone', 'event', 'date', 'msg'];
var LIMIT_PER_PHONE_PER_HOUR = 3;
var LIMIT_TOTAL_PER_HOUR = 30;

function doPost(e) {
  try {
    var body = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    var clean = validate_(body);
    if (clean.error) return reply_(400, clean.error);
    if (clean.data.botcheck) return reply_(200, 'ok');           // honeypot: pretend success, do nothing
    var limited = rateLimit_(clean.data.phone);
    if (limited) return reply_(429, limited);

    var d = clean.data;
    var text = ['New enquiry from ' + d.name + ', ' + d.phone, '',
      'Name: ' + d.name, 'Phone / WhatsApp: ' + d.phone, d.email ? 'Email: ' + d.email : '', '',
      'Event: ' + d.event, 'Possible date: ' + d.date, '', 'Description: ' + d.msg, '', 'Sent from Chathurya website']
      .filter(function (l, i, a) { return !(l === '' && a[i - 1] === ''); }).join('\n');

    sendWhatsApp_(text);
    sendEmails_(d, text);
    logRow_(d);
    return reply_(200, 'ok');
  } catch (err) {
    console.error(err);
    return reply_(500, 'Something went wrong. Please try again or email us.');
  }
}

function validate_(b) {
  if (typeof b !== 'object' || b === null || Array.isArray(b)) return { error: 'Invalid request.' };
  var out = {};
  for (var k in b) {
    if (!FIELDS.hasOwnProperty(k)) return { error: 'Unknown field: ' + k };
    var v = b[k];
    if (typeof v !== 'string') return { error: 'Invalid value for ' + k };
    v = v.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, '').trim();
    if (v.length > FIELDS[k]) return { error: 'Too long: ' + k };
    out[k] = v;
  }
  for (var i = 0; i < REQUIRED.length; i++) if (!out[REQUIRED[i]]) return { error: 'Missing: ' + REQUIRED[i] };
  if (!/^\+?\d{7,15}$/.test(out.phone.replace(/[\s()-]/g, ''))) return { error: 'Please check the phone number.' };
  out.phone = out.phone.replace(/[\s()-]/g, '');
  if (out.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(out.email)) return { error: 'Please check the email address.' };
  return { data: out };
}

function rateLimit_(phone) {
  var cache = CacheService.getScriptCache();
  var hour = Utilities.formatDate(new Date(), 'UTC', 'yyyyMMddHH');
  var kp = 'p:' + phone + ':' + hour, kt = 't:' + hour;
  var np = Number(cache.get(kp) || 0), nt = Number(cache.get(kt) || 0);
  if (np >= LIMIT_PER_PHONE_PER_HOUR) return 'You have already sent a few messages. Please wait an hour, or email us.';
  if (nt >= LIMIT_TOTAL_PER_HOUR) return 'We are receiving a lot of messages right now. Please try again later or email us.';
  cache.put(kp, String(np + 1), 3600); cache.put(kt, String(nt + 1), 3600);
  return '';
}

function sendWhatsApp_(text) {
  var alerts = (PropertiesService.getScriptProperties().getProperty('ALERTS') || '').split(',');
  alerts.forEach(function (pair, i) {
    var p = pair.trim().split(':'); if (p.length !== 2) return;
    if (i) Utilities.sleep(2500);
    try {
      UrlFetchApp.fetch('https://api.callmebot.com/whatsapp.php?phone=' + encodeURIComponent(p[0]) +
        '&apikey=' + encodeURIComponent(p[1]) + '&text=' + encodeURIComponent(text), { muteHttpExceptions: true });
    } catch (e) { console.error('WhatsApp ' + p[0] + ': ' + e); }
  });
}

function sendEmails_(d, text) {
  var owner = PropertiesService.getScriptProperties().getProperty('OWNER_EMAIL');
  if (owner) MailApp.sendEmail({ to: owner, subject: 'New enquiry: ' + d.event + ' (' + d.name + ')', body: text, replyTo: d.email || owner });
  if (d.email) MailApp.sendEmail({ to: d.email, subject: 'Thank you for contacting Chathurya Sandabarana',
    body: 'Dear ' + d.name + ',\n\nThank you for your message. We have received it and will get back to you on WhatsApp at ' + d.phone +
      ' as soon as possible.\n\nYour message:\nEvent: ' + d.event + '\nPossible date: ' + d.date + '\n\n' + d.msg + '\n\nChathurya Sandabarana' });
}

function logRow_(d) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('Enquiries') || ss.insertSheet('Enquiries');
  if (sh.getLastRow() === 0) sh.appendRow(['Received', 'Name', 'Phone', 'Email', 'Event', 'Possible date', 'Description', 'Status', 'Notes']);
  sh.appendRow([new Date(), d.name, "'" + d.phone, d.email || '', d.event, d.date, d.msg, 'New', '']);
}

function reply_(code, message) {
  return ContentService.createTextOutput(JSON.stringify({ ok: code === 200, code: code, message: message }))
    .setMimeType(ContentService.MimeType.JSON);
}

/** Run once from the editor to check WhatsApp + email + sheet without the website. */
function testEnquiry() {
  var r = doPost({ postData: { contents: JSON.stringify({ name: 'Test', phone: '+94771234567', event: 'Test concert', date: 'Test date', msg: 'Test message' }) } });
  console.log(r.getContent());
}
