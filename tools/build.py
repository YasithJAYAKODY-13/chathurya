#!/usr/bin/env python3
"""Build the site from content/.

Reads content/site.json and content/<category>/items.json, writes index.html,
phone-sized image variants under assets/img/, sitemap.xml and robots.txt.
Only an allowlist of fields is ever rendered, so internal notes in the JSON
(needs, note, omitted_on_purpose, publish_ok, inbox/...) never reach the page.

Run from the repo root:  python3 tools/build.py
"""
import datetime as dt
import html
import json
import os
import sys
from urllib.parse import quote

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "content")
OUT_IMG = os.path.join(ROOT, "assets", "img")
TODAY = dt.date.today()
os.makedirs(os.path.join(ROOT, "assets", "img"), exist_ok=True)
used_media = set()
errors = []


def load(cat):
    with open(os.path.join(C, cat, "items.json"), encoding="utf-8") as f:
        return json.load(f)["items"]


def e(s):
    return html.escape(str(s or ""), quote=True)


MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def parse_date(s):
    """Return (sort_key, pretty) for 'YYYY', 'YYYY-MM' or 'YYYY-MM-DD'."""
    s = str(s or "")
    parts = s.split("-")
    try:
        y = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        d = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return None, ""
    if d:
        return (y, m, d), f"{d} {MONTHS[m-1]} {y}"
    if m:
        return (y, m, 0), f"{MONTHS[m-1]} {y}"
    return (y, 0, 0), str(y)


def date_obj(s):
    k, _ = parse_date(s)
    if not k or not k[2]:
        return None
    return dt.date(*k)


# ---------------------------------------------------------------- images
def variants(rel, widths=(480, 960, 1440)):
    """rel: path relative to repo root. Returns (src, srcset, w, h)."""
    src_path = os.path.join(ROOT, rel)
    if not os.path.exists(src_path):
        errors.append(f"missing image: {rel}")
        return rel, "", 0, 0
    used_media.add(os.path.normpath(rel))
    im = Image.open(src_path)
    W, H = im.size
    base = os.path.splitext(rel.replace("content/", "").replace("/", "__"))[0]
    out = []
    for w in widths:
        if w >= W and out:
            break
        tw = min(w, W)
        name = f"{base}-{tw}.webp"
        dest = os.path.join(OUT_IMG, name)
        if not os.path.exists(dest) or os.path.getmtime(dest) < os.path.getmtime(src_path):
            r = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").resize((tw, round(H * tw / W)), Image.LANCZOS)
            r.save(dest, quality=72, method=6)
        out.append((f"assets/img/{name}", tw))
    srcset = ", ".join(f"{u} {w}w" for u, w in out)
    small = out[0][0]
    return small, srcset, W, H


def img_tag(rel, alt, sizes="(max-width: 700px) 50vw, 360px", cls="", eager=False):
    small, srcset, W, H = variants(rel)
    lazy = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return (f'<img src="{e(small)}" srcset="{e(srcset)}" sizes="{sizes}" width="{W}" height="{H}" '
            f'alt="{e(alt)}" class="{cls}" {lazy}>')


def large(rel):
    """Largest variant URL for lightbox use."""
    small, srcset, W, H = variants(rel)
    return srcset.split(", ")[-1].split(" ")[0] if srcset else rel


# ---------------------------------------------------------------- data
site = json.load(open(os.path.join(C, "site.json"), encoding="utf-8"))
voice = {i["id"]: i for i in load("the-voice")}
concerts = load("concerts-and-events")
singing = load("singing")
film = load("film")
education = load("education")
press = load("press")
gallery_items = load("gallery")

galleries = {}  # id -> list of slides


def slides_for(item, folder):
    out = []
    caps = item.get("image_captions", {})
    for rel in item.get("images", []):
        path = f"content/{folder}/{rel}"
        out.append({"t": "img", "src": large(path), "cap": caps.get(rel, item.get("title", ""))})
    for v in item.get("videos", []):
        p = f"content/{folder}/{v['file']}"
        if os.path.exists(os.path.join(ROOT, p)):
            used_media.add(os.path.normpath(p))
            if v.get("poster"):
                used_media.add(os.path.normpath(f"content/{folder}/{v['poster']}"))
            out.append({"t": "mp4", "src": p, "poster": f"content/{folder}/{v.get('poster','')}",
                        "cap": v.get("caption", "")})
        else:
            errors.append(f"missing video: {p}")
    for v in item.get("videos_youtube", []):
        out.append({"t": "yt", "id": v["id"], "cap": v.get("title", "")})
    return out


# ---------------------------------------------------------------- icons
ICONS = {
    "chair": '<path d="M7 3h10v9H7zM5 12h14v3H5zM7 15v6M17 15v6"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "mic": '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8"/>',
    "pin": '<path d="M12 21s7-6 7-11a7 7 0 0 0-14 0c0 5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "play": '<path d="M8 5v14l11-7z" fill="currentColor" stroke="none"/>',
    "wa": '<path d="M4 20l1.3-4A8 8 0 1 1 8 19z"/><path d="M9 9c0 3 3 6 6 6l1-1.5-2-1-1 1c-1 0-3-2-3-3l1-1-1-2z" fill="currentColor" stroke="none"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    "fb": '<path d="M14 8h3V4h-3a4 4 0 0 0-4 4v3H7v4h3v6h4v-6h3l1-4h-4V8z"/>',
    "yt": '<rect x="2" y="5" width="20" height="14" rx="4"/><path d="M10 9v6l5-3z" fill="currentColor" stroke="none"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8 12l3 3 5-6"/>',
    "satellite": '<path d="M13 7l4 4-6 6-4-4z"/><path d="M15 5l2-2 4 4-2 2M5 15l-2 2 4 4 2-2M17 13a4 4 0 0 0 4 4"/>',
    "engine": '<circle cx="12" cy="12" r="8"/><path d="M12 4v16M4 12h16M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "film": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
}


def icon(n, cls="ico"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[n]}</svg>')


def yt_thumb(vid):
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"


# ---------------------------------------------------------------- sections
contact = site["contact"]
whatsapp = "".join(ch for ch in contact.get("whatsapp", "") if ch.isdigit())
email = contact.get("email", "").strip()


def section_hero():
    portrait = img_tag("assets/chathurya-stage.webp", "Chathurya Sandabarana singing on stage in a green gown",
                       sizes="(max-width: 860px) 88vw, 520px", cls="portrait", eager=True)
    return f'''
<section class="hero" id="top" aria-label="Introduction">
  <canvas id="waves" aria-hidden="true"></canvas>
  <div class="wrap hero-grid">
    <div class="intro">
      <h1 class="name"><span>Chathurya</span><span>Sandabarana</span></h1>
      <p class="lede">{e(site["tagline"])}</p>
      <p class="also">{e(site["secondary"])}</p>
      <div class="actions">
        <a class="btn primary" href="#watch">{icon("play")}Watch her sing</a>
        <a class="btn ghost" href="#invite">Invite to perform</a>
      </div>
    </div>
    <div class="stage">{portrait}</div>
  </div>
</section>'''


def section_proof():
    items = "".join(f'<li>{icon(p["icon"])}<span>{e(p["text"])}</span></li>' for p in site["proof"])
    return f'<section class="proof" aria-label="Highlights"><div class="wrap"><ul>{items}</ul></div></section>'


def section_press_card():
    out = []
    for p in press:
        if not p.get("featured_on_home"):
            continue
        rel = f"content/press/{p['images'][0]}"
        gid = "press-" + p["id"]
        galleries[gid] = {"title": p["outlet"], "desc": p.get("summary", ""), "s": slides_for(p, "press")}
        _, pretty = parse_date(p["date"])
        quotes = "".join(f'<li><span lang="si">{e(si)}</span><em>{e(en)}</em></li>'
                         for si, en in zip(p.get("pull_quotes_sinhala", []), p.get("pull_quotes_english", [])))
        out.append(f'''
<section class="press" aria-labelledby="press-title"><div class="wrap">
  <article class="press-card">
    <button class="press-img" data-gallery="{gid}" aria-label="Open the newspaper page">{img_tag(rel, "Silumina Rasaduna feature page about Chathurya", sizes="(max-width: 700px) 40vw, 260px")}</button>
    <div>
      <p class="kicker">As featured in {e(p["outlet"])}, {e(p["section"])}, {e(pretty)}</p>
      <h2 id="press-title" class="h3"><span lang="si">{e(p["headline_sinhala"])}</span></h2>
      <p class="tr">{e(p["headline_english"])}</p>
      <ul class="pull">{quotes}</ul>
      <button class="link" data-gallery="{gid}">Read the article</button>
    </div>
  </article>
</div></section>''')
    return "".join(out)


def video_facade(v, cls="vcard"):
    if v["type"] == "youtube":
        thumb = yt_thumb(v["id"])
        data = f'data-yt="{e(v["id"])}" data-start="{v.get("start", "")}" data-end="{v.get("end", "")}"'
    else:
        used_media.add(os.path.normpath(v["src"]))
        used_media.add(os.path.normpath(v["poster"]))
        thumb = v["poster"]
        data = f'data-mp4="{e(v["src"])}"'
    return f'''<figure class="{cls}">
  <button class="facade" {data} aria-label="Play {e(v["title"])}, {e(v["label"])}">
    <img src="{e(thumb)}" alt="" loading="lazy" decoding="async" onerror="this.remove()">
    <span class="play">{icon("play")}</span>
  </button>
  <figcaption><strong>{e(v["title"])}</strong><span>{e(v["label"])}</span></figcaption>
</figure>'''


def section_watch():
    cards = "".join(video_facade(v) for v in site["watch"])
    n = len(site["watch"])
    return f'''
<section class="watch" id="watch" aria-labelledby="watch-title"><div class="wrap">
  <h2 id="watch-title">Watch and listen</h2>
  <p class="sub">Swipe to see more. Videos load only when you tap play.</p>
  <div class="row" tabindex="0" aria-label="Videos, {n} items">{cards}</div>
</div></section>'''


def upcoming():
    ups = []
    for c in concerts:
        d = date_obj(c.get("date"))
        if d and d >= TODAY:
            ups.append((d, c))
    return sorted(ups, key=lambda x: x[0])


def section_next():
    ups = upcoming()
    if not ups:
        return '<section class="next" aria-label="Invitations"><div class="wrap"><div class="card"><div><span class="label">Invitations</span><h3>Now accepting invitations for upcoming concerts and events</h3></div><a class="btn ghost" href="#invite">Invite to perform</a></div></div></section>'
    d, c = ups[0]
    where = ", ".join(x for x in [c.get("venue"), c.get("city")] if x)
    return f'''
<section class="next" aria-label="Next performance" data-date="{d.isoformat()}"><div class="wrap"><div class="card">
  <div class="date" aria-hidden="true"><b>{MONTHS[d.month-1][:3].upper()}</b><span>{d.day}</span></div>
  <div><span class="label">Next performance</span><h3>{e(c["title"])}</h3>
  <p>{icon("pin")}{e(where)}. {d.strftime("%A")} {d.day} {MONTHS[d.month-1]} {d.year}</p></div>
</div></div></section>'''


VOICE_ORDER = ["blind-audition", "best-of-the-week", "battles", "knockouts", "road-to-lives", "live-shows"]


def section_voice():
    rows = []
    for vid in VOICE_ORDER:
        it = voice.get(vid)
        if not it:
            continue
        _, pretty = parse_date(it.get("date"))
        song = "Hithala Wanniye" if vid == "best-of-the-week" else (it.get("song") or it.get("title"))
        meta = []
        if vid == "blind-audition":
            meta.append(f'Season {it.get("season", 1)}. Three chairs turned; joined Team {e(it.get("coach", ""))}')
        if vid == "best-of-the-week":
            meta.append("Chosen to represent Sri Lanka in The Voice's international highlights")
        if vid == "battles":
            meta.append(f'Won her battle against {e(it.get("opponent", ""))}')
        if vid == "knockouts" and it.get("original_artist"):
            meta.append(f'Original by {e(it["original_artist"])}')
        if vid == "road-to-lives":
            meta.append("Showcase programme before the Live Shows")
        if vid == "live-shows":
            meta.append("Reached the Live Shows")
        if pretty:
            meta.append(pretty)
        gid = "voice-" + vid
        sl = slides_for(it, "the-voice")
        if it.get("youtube"):
            sl = [{"t": "yt", "id": it["youtube"], "start": it.get("start", ""), "end": it.get("end", ""),
                   "cap": f'{it["round"]}: {song}'}] + sl
        galleries[gid] = {"title": f'{it["round"]}: {song}', "desc": " ".join(meta), "s": sl}
        if it.get("images"):
            thumb = img_tag(f'content/the-voice/{it["images"][0]}', f'{it["round"]}', sizes="96px", cls="tthumb")
        elif it.get("youtube"):
            thumb = f'<img class="tthumb" src="{yt_thumb(it["youtube"])}" alt="" loading="lazy" width="480" height="360" onerror="this.remove()">'
        else:
            thumb = ""
        badge = []
        if it.get("youtube"):
            badge.append("video")
        if it.get("images"):
            n = len(it["images"])
            badge.append(f"{n} photo" + ("s" if n > 1 else ""))
        extra = ""
        if vid == "best-of-the-week" and it.get("quote"):
            extra = f'<blockquote class="quote">"{e(it["quote"])}"<cite>Chathurya</cite></blockquote>'
        rows.append(f'''<li class="step{' hl' if it.get('highlight') else ''}">
  <button class="tcard" data-gallery="{gid}" aria-label="Open {e(it['round'])}">
    {thumb}
    <span class="ttext"><span class="round">{e(it['round'])}</span><strong lang="si-Latn">{e(song)}</strong>
    <span class="meta">{"<br>".join(meta)}</span><span class="badge">{" + ".join(badge)}</span></span>
  </button>{extra}
</li>''')
    coach = voice.get("coach-reaction-adam-baruell")
    coach_html = ""
    if coach:
        qs = "".join(f"<li>\"{e(q)}\"</li>" for q in coach.get("quotes", [])[:3])
        coach_html = f'''<aside class="coach"><h3>A vocal coach's view</h3><p>{e(coach.get("description", ""))}</p>
<ul>{qs}</ul><p class="cite">Adam Baruell, vocal coach, on her Blind Audition</p></aside>'''
    return f'''
<section class="voice" id="voice" aria-labelledby="voice-title"><div class="wrap">
  <h2 id="voice-title">The Voice Sri Lanka</h2>
  <p class="sub">Season 1 on Sirasa TV, round by round. Tap a round for photos and video.</p>
  <ol class="timeline">{"".join(rows)}</ol>
  {coach_html}
</div></section>'''


def concert_card(c, big=False):
    gid = "concert-" + c["id"]
    _, pretty = parse_date(c.get("date"))
    galleries[gid] = {"title": c["title"], "desc": " ".join(x for x in [pretty, c.get("description", "")] if x), "s": slides_for(c, "concerts-and-events")}
    where = c.get("city") or c.get("venue") or ""
    n_img = len(c.get("images", []))
    n_vid = len(c.get("videos", [])) + len(c.get("videos_youtube", []))
    badges = []
    if n_vid:
        badges.append(f"▶ {n_vid} video" + ("s" if n_vid > 1 else ""))
    if n_img:
        badges.append(f"{n_img} photo" + ("s" if n_img > 1 else ""))
    d = date_obj(c.get("date"))
    up = d and d >= TODAY
    if n_img:
        cover = img_tag(f'content/concerts-and-events/{c["images"][0]}', c["title"],
                        sizes="(max-width: 700px) 46vw, 260px", cls="cover")
    else:
        cover = f'<span class="cover blank">{icon("mic")}</span>'
    clickable = bool(galleries[gid]["s"])
    tag = "button" if clickable else "div"
    attr = f'data-gallery="{gid}" aria-label="Open {e(c["title"])}"' if clickable else ""
    return f'''<li class="ccard{' up' if up else ''}"><{tag} class="cbtn" {attr}>
  {cover}<span class="cinfo"><strong>{e(c["title"])}</strong><span>{e(pretty)}{(" · " + e(where)) if where else ""}</span>
  {('<span class="upcoming">Upcoming</span>' if up else '')}<span class="badge">{" · ".join(badges)}</span></span>
</{tag}></li>'''


def section_concerts():
    real = [c for c in concerts if parse_date(c.get("date"))[0]]
    hand = sorted([c for c in real if c.get("series") == "Handawaka"], key=lambda c: parse_date(c["date"])[0], reverse=True)
    rest = sorted([c for c in real if c.get("series") != "Handawaka"], key=lambda c: parse_date(c["date"])[0], reverse=True)
    hand_cards = "".join(concert_card(c) for c in hand)
    rest_cards = "".join(concert_card(c) for c in rest)
    cover_src = next((c for c in hand if c.get("images")), None)
    hcover = img_tag(f'content/concerts-and-events/{cover_src["images"][0]}', "Chathurya at Handawaka",
                     sizes="(max-width: 700px) 92vw, 560px", cls="hcover") if cover_src else ""
    total = len(real)
    return f'''
<section class="concerts" id="concerts" aria-labelledby="concerts-title"><div class="wrap">
  <h2 id="concerts-title">Concerts and events</h2>
  <p class="sub">{total} concerts and events since 2022, newest first. Tap any poster for photos and videos.</p>
  <details class="hgroup" open>
    <summary>{hcover}<span class="hlabel"><span class="kicker">A returning voice</span><strong>Handawaka</strong><span>{len(hand)} shows across Colombo, Kandy, Galle and Anuradhapura</span></span></summary>
    <ul class="grid">{hand_cards}</ul>
  </details>
  <ul class="grid more" id="concert-grid">{rest_cards}</ul>
  <button class="btn ghost showall" id="showall" hidden>Show all {len(rest)} concerts</button>
</div></section>'''


def section_repertoire():
    songs = []
    for vid in VOICE_ORDER:
        it = voice.get(vid)
        if it and vid != "best-of-the-week":
            t = it.get("song") or it.get("title")
            if t:
                songs.append((t, f'The Voice Sri Lanka, {it["round"]}', "voice-" + vid if it.get("youtube") else ""))
    for sg in singing:
        gid = ""
        if sg.get("youtube"):
            gid = "song-" + sg["id"]
            galleries[gid] = {"title": sg["title"], "desc": " ".join(x for x in [sg.get("description", ""), ("With " + sg["with"] + ".") if sg.get("with") else "", (sg["credits"] + ".") if sg.get("credits") else ""] if x),
                              "s": [{"t": "yt", "id": sg["youtube"], "cap": sg["title"] + ", " + sg.get("type", "")}]}
        songs.append((sg["title"], sg.get("type", ""), gid))
    for c in concerts:
        if c.get("song"):
            songs.append((c["song"], c["title"], "concert-" + c["id"]))
    seen, uniq = set(), []
    for t, w, g in songs:
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append((t, w, g))
    def li(t, w, g):
        inner = f'<strong>{e(t)}</strong><span>{e(w)}</span>'
        if g:
            return f'<li><button class="songbtn" data-gallery="{g}" aria-label="Play {e(t)}">{icon("play")}<span>{inner}</span></button></li>'
        return f'<li><span class="nob">{icon("mic")}<span>{inner}</span></span></li>'
    lis = "".join(li(*x) for x in uniq)
    fm = "".join(f"<li>{e(f)}</li>" for f in site.get("formats", []))
    return f'''
<section class="rep" id="songs" aria-labelledby="rep-title"><div class="wrap rep-grid">
  <div><h2 id="rep-title">What she sings</h2><p class="sub">Songs Chathurya has performed on stage and on television.</p>
  <ul class="songs">{lis}</ul></div>
  <aside class="formats"><h3>Performance formats</h3><ul>{fm}</ul><p>{e(site.get("availability", ""))}</p>
  <a class="btn primary" href="#invite">Invite to perform</a></aside>
</div></section>'''


def section_about():
    f = film[0] if film else None
    ed = education[0] if education else None
    film_html = ""
    if f:
        gid = "film"
        galleries[gid] = {"title": f["title"], "desc": "", "s": slides_for(f, "film")}
        cover = img_tag(f'content/film/{f["images"][0]}', "Man Hoyanne Premayak poster", sizes="120px", cls="fcover") if f.get("images") else ""
        film_html = f'''<article class="mini"><button class="mini-img" data-gallery="{gid}" aria-label="Open film poster">{cover}</button>
<div><span class="kicker">Screen debut, {e(f.get("year", ""))}</span><h3 lang="si-Latn">{e(f["title"])}</h3>
<p>Sinhala feature film directed by {e(f.get("director", ""))}, produced by {e(f.get("producer", ""))}.</p>
<a class="link" href="{e(contact["imdb"])}" target="_blank" rel="noopener">{icon("film")}Her profile on IMDb</a></div></article>'''
    ed_html = ""
    if ed:
        gid = "education"
        galleries[gid] = {"title": ed["title"], "desc": "", "s": slides_for(ed, "education")}
        photo = img_tag(f'content/education/{ed["images"][0]}', "Chathurya at her graduation", sizes="(max-width: 700px) 40vw, 220px", cls="grad") if ed.get("images") else ""
        why = "".join(f'<li>{icon(w["icon"])}<div><strong>{e(w["title"])}</strong><p>{e(w["text"])}</p></div></li>' for w in ed.get("why_it_matters", []))
        areas = "".join(f"<li>{e(a)}</li>" for a in ed.get("research_areas", []))
        ed_html = f'''<article class="edu">
<svg class="edu-bg" viewBox="0 0 600 300" aria-hidden="true"><defs><linearGradient id="trail" x1="0" x2="1"><stop offset="0" stop-color="#D4A53A" stop-opacity="0"/><stop offset="1" stop-color="#ECCF85" stop-opacity=".5"/></linearGradient></defs>
<path d="M-20 260 C 200 230, 380 150, 470 90" stroke="url(#trail)" stroke-width="26" fill="none" stroke-linecap="round"/>
<path d="M455 70 l40 -18 q22 22 8 52 l-40 10z" fill="#ECCF85" fill-opacity=".35"/>
<circle cx="470" cy="90" r="46" fill="none" stroke="#D4A53A" stroke-opacity=".25"/>
<path d="M0 290 Q 300 200 600 230" stroke="#D4A53A" stroke-opacity=".15" fill="none"/></svg>
<div class="edu-in">
<button class="mini-img" data-gallery="{gid}" aria-label="Open graduation photo">{photo}</button>
<div><span class="kicker">Education</span><h3>{e(ed["title"])}</h3>
<p class="cls">{e(ed.get("classification", ""))}, {e(ed.get("institution", ""))}, {e(ed.get("year", ""))}</p>
<p>{e(ed.get("plain_language", ""))}</p>
<details class="why"><summary>Why her work matters to everyone</summary><ul>{why}</ul>
<p class="areas-h">Research areas</p><ul class="areas">{areas}</ul></details></div></div></article>'''
    return f'''
<section class="about" id="about" aria-labelledby="about-title"><div class="wrap">
  <h2 id="about-title">About Chathurya</h2>
  <div class="bio"><p>Chathurya Sandabarana is a singer from Tangalle, on Sri Lanka's southern coast. She came to national attention on The Voice Sri Lanka, Season 1, where three coaches turned for her Blind Audition and her performance was chosen for The Voice Global's "Best of the Week". She went on to the Live Shows.</p>
  <p>Since then she has sung at concerts across Sri Lanka and in Dubai, including the Handawaka series, released her single <em>Sayam Heene</em>, and made her screen debut in a Sinhala feature film. Alongside music, she is an aerospace engineering graduate, a balance the Sunday Silumina featured in October 2026.</p></div>
  {film_html}
  {ed_html}
</div></section>'''


def section_gallery():
    if not gallery_items:
        return ""
    return ""


def section_invite():
    btns = []
    if whatsapp:
        btns.append(f'<button type="submit" class="btn primary" data-send="wa">{icon("wa")}Send via WhatsApp</button>')
    if email:
        btns.append(f'<button type="submit" class="btn {"ghost" if whatsapp else "primary"}" data-send="mail">{icon("mail")}Send via email</button>')
    if not btns:
        btns.append(f'<button type="submit" class="btn primary" data-send="fb">{icon("fb")}Send via Facebook Messenger</button>')
    direct = []
    if whatsapp:
        direct.append(f'<a href="https://wa.me/{whatsapp}">{icon("wa")}WhatsApp +{whatsapp}</a>')
    if email:
        direct.append(f'<a href="mailto:{e(email)}">{icon("mail")}{e(email)}</a>')
    direct.append(f'<a href="{e(contact["facebook"])}" target="_blank" rel="noopener">{icon("fb")}Facebook</a>')
    direct.append(f'<a href="{e(contact["youtube"])}" target="_blank" rel="noopener">{icon("yt")}YouTube</a>')
    person = f'<p class="person">Enquiries handled by {e(contact["contact_person"])}</p>' if contact.get("contact_person") else ""
    return f'''
<section class="invite" id="invite" aria-labelledby="invite-title"><div class="wrap"><div class="icard">
  <h2 id="invite-title">Invite to perform</h2>
  <p class="si" lang="si">වැඩසටහනකට ආරාධනා කරන්න</p>
  <p>For concerts, musical shows, school and community events, television and media, in Sri Lanka or overseas. Fill in what you know and your message will be ready to send.</p>
  <form id="inviteForm" novalidate data-wa="{whatsapp}" data-mail="{e(email)}" data-fb="{e(contact.get("messenger", ""))}">
    <label><span class="lt">Your name <span class="req">required</span></span><input name="name" autocomplete="name" required></label>
    <label><span class="lt">Organisation or event</span><input name="event" autocomplete="organization"></label>
    <div class="two"><label><span class="lt">Date</span><input name="date" type="date"></label><label><span class="lt">Town or city</span><input name="town" autocomplete="address-level2"></label></div>
    <label><span class="lt">Your phone or WhatsApp <span class="req">required</span></span><input name="phone" type="tel" inputmode="tel" autocomplete="tel" required></label>
    <label><span class="lt">Message <span class="opt">optional</span></span><textarea name="msg" rows="3"></textarea></label>
    <p class="err" id="formErr" role="alert" hidden>Please add your name and a phone number so she can reply.</p>
    <div class="send">{"".join(btns)}</div>
    <p class="done" id="formDone" role="status" hidden></p>
  </form>
  {person}
  <div class="direct">{"".join(direct)}</div>
</div></div></section>'''


# ---------------------------------------------------------------- page
CSS = open(os.path.join(ROOT, "tools", "site.css"), encoding="utf-8").read()
JS = open(os.path.join(ROOT, "tools", "site.js"), encoding="utf-8").read()

hero = section_hero()
body = "".join([hero, section_proof(), section_press_card(), section_watch(), section_next(), section_voice(),
                section_concerts(), section_repertoire(), section_about(), section_gallery(), section_invite()])

# structured data
person = {"@context": "https://schema.org", "@type": "Person", "name": site["name"], "url": site["url"],
          "jobTitle": "Singer", "homeLocation": {"@type": "Place", "name": site["hometown"]},
          "alumniOf": {"@type": "CollegeOrUniversity", "name": "Kingston University London"},
          "sameAs": [contact["facebook"], contact["youtube"], contact["imdb"]],
          "image": site["url"] + "assets/share.jpg"}
ld = [person]
for d, c in upcoming():
    if c.get("venue") and c.get("city"):
        ld.append({"@context": "https://schema.org", "@type": "MusicEvent", "name": c["title"],
                   "startDate": d.isoformat(), "eventStatus": "https://schema.org/EventScheduled",
                   "location": {"@type": "Place", "name": c["venue"], "address": {"@type": "PostalAddress", "addressLocality": c["city"], "addressCountry": "LK"}},
                   "performer": {"@type": "Person", "name": site["name"], "url": site["url"]}})

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(site["name"])} | Singer, The Voice Sri Lanka</title>
<meta name="description" content="{e(site["description"])}">
<link rel="canonical" href="{site["url"]}">
<meta property="og:type" content="website">
<meta property="og:url" content="{site["url"]}">
<meta property="og:title" content="{e(site["name"])} | Singer">
<meta property="og:description" content="{e(site["description"])}">
<meta property="og:image" content="{site["url"]}assets/share.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0C241F">
<link rel="icon" href="assets/icon.png">
<link rel="preload" href="assets/fonts/rozha-one-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/hanken-grotesk-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<a class="skip" href="#watch">Skip to videos</a>
<header class="bar" id="bar"><div class="wrap">
  <a class="mark" href="#top">Chathurya</a>
  <nav class="desk" aria-label="Main"><a href="#watch">Watch</a><a href="#voice">The Voice</a><a href="#concerts">Concerts</a><a href="#about">About</a><a href="#invite" class="cta">Invite to perform</a></nav>
  <button class="menu-btn" id="menuBtn" aria-expanded="false" aria-controls="menu">{icon("menu")}<span>Menu</span></button>
</div></header>
<div class="menu" id="menu" hidden>
  <button class="menu-close" id="menuClose" aria-label="Close menu">{icon("close")}</button>
  <nav aria-label="Menu"><a href="#watch">Watch</a><a href="#voice">The Voice</a><a href="#concerts">Concerts</a><a href="#songs">What she sings</a><a href="#about">About</a><a href="#invite">Invite to perform</a></nav>
  <div class="menu-foot">{''.join(x for x in [f'<a href="https://wa.me/{whatsapp}">{icon("wa")}WhatsApp</a>' if whatsapp else '', f'<a href="mailto:{e(email)}">{icon("mail")}Email</a>' if email else '', f'<a href="{e(contact["facebook"])}" target="_blank" rel="noopener">{icon("fb")}Facebook</a>'])}</div>
</div>
<main>{body}</main>
<footer><div class="wrap"><span>&copy; <span id="yr">{TODAY.year}</span> {e(site["name"])}</span><span>Photographs credited to their photographers.</span><a href="#top">Back to top</a></div></footer>
<div class="sticky" id="sticky"><a class="btn primary" href="#invite">Invite to perform</a>{f'<a class="wa" href="https://wa.me/{whatsapp}" aria-label="WhatsApp">{icon("wa")}</a>' if whatsapp else ''}</div>
<dialog id="lightbox" aria-label="Gallery">
  <div class="lb-top"><span id="lbCount" aria-live="polite"></span><button id="lbClose" aria-label="Close gallery">{icon("close")}</button></div>
  <div class="lb-track" id="lbTrack"></div>
  <p class="lb-cap" id="lbCap"></p>
  <button class="lb-nav prev" id="lbPrev" aria-label="Previous">‹</button><button class="lb-nav next" id="lbNext" aria-label="Next">›</button>
</dialog>
<script id="galleries" type="application/json">{json.dumps(galleries, ensure_ascii=False)}</script>
<script>{JS}</script>
</body>
</html>
'''

os.makedirs(OUT_IMG, exist_ok=True)
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(page)

with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
    f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{site["url"]}</loc><lastmod>{TODAY.isoformat()}</lastmod></url></urlset>\n')
with open(os.path.join(ROOT, "robots.txt"), "w") as f:
    f.write(f"User-agent: *\nAllow: /\nDisallow: /content/inbox/\nDisallow: /tools/\nSitemap: {site['url']}sitemap.xml\n")

# report media in content/ that the page does not use
all_media = []
for dp, _, fs in os.walk(C):
    if "inbox" in dp or "sources" in dp:
        continue
    for fn in fs:
        if fn.endswith((".webp", ".jpg", ".png", ".mp4")):
            all_media.append(os.path.normpath(os.path.relpath(os.path.join(dp, fn), ROOT)))
unused = [m for m in all_media if m not in used_media]
print(f"index.html: {len(page)//1024} KB, galleries: {len(galleries)}, media used: {len(used_media)}")
print("UNUSED:", unused if unused else "none")
if errors:
    print("ERRORS:", *errors, sep="\n  ")
    sys.exit(1)
