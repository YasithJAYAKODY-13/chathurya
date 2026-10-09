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
import re
import os
import sys
from urllib.parse import quote

from PIL import Image
from edu_art import journey_html, medal

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
            if out[-1][1] < W:
                w = W
            else:
                break
        tw = min(w, W)
        name = f"{base}-{tw}.webp"
        dest = os.path.join(OUT_IMG, name)
        if not os.path.exists(dest) or os.path.getmtime(dest) < os.path.getmtime(src_path):
            r = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB").resize((tw, round(H * tw / W)), Image.LANCZOS)
            r.save(dest, quality=88 if "stage" in rel else 72, method=6)
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
modelling = load("modelling")
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
    "cap": '<path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c3 2.5 9 2.5 12 0v-5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M21 9v6" stroke="currentColor" stroke-width="1.8"/>',
    "phone": '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    "trophy": '<path d="M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4M12 14v4M8 21h8M9 18h6"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
}


def icon(n, cls="ico"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[n]}</svg>')


def yt_thumb(vid):
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"


# ---------------------------------------------------------------- sections
contact = site["contact"]
_pp = os.path.join(C, "private.json")
private = json.load(open(_pp, encoding="utf-8")) if os.path.exists(_pp) else {}
contact = {**contact, "whatsapp_alerts": private.get("whatsapp_alerts", []), "form_to": contact.get("form_to", "")}
people = contact.get("people", [])
form_person = next((p for p in people if p["id"] == contact.get("form_to")), None)
whatsapp = "".join(ch for ch in form_person["number"] if ch.isdigit()) if form_person else ""
email = contact.get("enquiry_email", "").strip()


def gal(gid, title, desc, slides):
    galleries[gid] = {"title": title, "desc": desc, "s": slides}
    return gid


def video_facade(vid_type, ref, title, sub, poster=None, start="", end="", cls="video"):
    if vid_type == "youtube":
        thumb = yt_thumb(ref)
        data = f'data-yt="{e(ref)}" data-start="{start}" data-end="{end}"'
    else:
        used_media.add(os.path.normpath(ref))
        if poster:
            used_media.add(os.path.normpath(poster))
        thumb = poster or ""
        data = f'data-mp4="{e(ref)}"'
    return f'''<button class="{cls} facade" {data} aria-label="Play {e(title)}{(', ' + e(sub)) if sub else ''}">
  <img src="{e(thumb)}" alt="" loading="lazy" decoding="async" onerror="this.remove()">
  <span class="play">{icon("play")}</span>{f'<span class="cap">{e(title)}</span>' if cls == "video" else ''}
</button>'''


def upcoming():
    ups = []
    for c in concerts:
        d = date_obj(c.get("date"))
        if d and d >= TODAY:
            ups.append((d, c))
    return sorted(ups, key=lambda x: x[0])


def section_hero():
    portrait = img_tag("assets/chathurya-stage.webp", "Chathurya Sandabarana singing on stage in a green gown",
                       sizes="(max-width: 860px) 92vw, 520px", cls="portrait", eager=True)
    return f'''
<section class="hero" aria-label="Introduction">
  <canvas id="waves" aria-hidden="true"></canvas>
  <div class="wrap hero-grid">
    <div class="intro">
      <h1 class="name"><span>Chathurya</span><span>Sandabarana</span></h1>
      <p class="lede"><strong>{e(site["tagline"])}</strong> {e(site["lede"])}</p>
      <a class="edu-chip" href="education.html">{icon("cap")}<span>{e(site.get("secondary", ""))}</span><b aria-hidden="true">›</b></a>
      <div class="actions">
        <a class="btn primary" href="#performances">Performances</a>
        <a class="btn ghost" href="#invite">Invite to perform</a>
      </div>
    </div>
    <div class="stage">{portrait}</div>
  </div>
</section>'''


def section_next():
    ups = upcoming()
    if not ups:
        return ""
    d, c = ups[0]
    where = ", ".join(x for x in [c.get("venue"), c.get("city")] if x)
    return f'''
<section class="next" aria-label="Next performance" data-date="{d.isoformat()}"><div class="wrap"><div class="card">
  <div class="date" aria-hidden="true"><b>{MONTHS[d.month-1][:3].upper()}</b><span>{d.day}</span></div>
  <div class="ninfo"><span class="label">Next performance</span><h3>{e(c["title"])}</h3>
  <p>{icon("pin")}{e(where)}. {d.strftime("%A")} {d.day} {MONTHS[d.month-1]} {d.year}</p></div>
  <a class="btn ghost" href="#concerts">All concerts</a>
</div></div></section>'''


def divider():
    return '<div class="divider" aria-hidden="true"><canvas></canvas><span class="gem"></span></div>'


def section_highlights():
    past = [c for c in concerts if parse_date(c.get("date"))[0] and not (date_obj(c["date"]) and date_obj(c["date"]) >= TODAY)]
    groups = set()
    n_concerts = 0
    for c in past:
        if c.get("series") == "Handawaka":
            key = (c.get("city"), str(c.get("date"))[:7])
            if key in groups:
                continue
            groups.add(key)
        n_concerts += 1
    n_hand = len(groups)
    aw = site.get("handawaka_award", {})
    n_places = len([p for p in places_list() if p["shows"]])
    tiles = [
        ("trophy", str(n_hand), "Handawaka shows", "Colombo · Kandy · Havelock · Galle", "#concerts"),
        ("pin", str(n_concerts), "Concerts and events", f"{n_places} cities · Sri Lanka and Dubai", "#concerts"),
        ("mic", "Live Shows", "The Voice Sri Lanka", "Season 1 · Team Umaria Sinhawansa", "#voice"),
        ("globe", "Global", "International recognition", "The Voice Global best performances of the week · Live in Dubai", "#voice"),
    ]
    def tile(ic, n, a, s, h):
        num = n.isdigit()
        dc = f' data-count="{n}"' if num else ""
        return (f'<a class="ms" href="{h}"><span class="ms-in"><span class="ms-ico">{icon(ic)}</span>'
                f'<span class="ms-big{" n num" if num else ""}"{dc}>{e(n)}</span><strong>{e(a)}</strong><span class="ms-sub">{e(s)}</span></span></a>')
    t = "".join(tile(*x) for x in tiles)
    award = ""
    if aw.get("text"):
        name = f" ({e(aw['award_name'])})" if aw.get("award_name") else ""
        award = f'<a class="award" href="#concerts">{icon("trophy")}<span><strong>{e(aw["text"])}{name}</strong><span>Chathurya has sung at four Handawaka shows.</span></span></a>'
    return f'''
<section class="highlights" aria-label="Highlights"><div class="wrap"><div class="ms-stage top">{t}</div>{award}</div></section>'''


def places_list():
    """Every town she has performed in, from the concert data. International first, then most shows."""
    seen = {}
    for c in concerts:
        city = c.get("city")
        if not city or not parse_date(c.get("date"))[0]:
            continue
        p = seen.setdefault(city, {"city": city, "country": c.get("country") or "", "shows": 0, "next": False, "handawaka": False})
        d = date_obj(c["date"])
        if d and d >= TODAY:
            p["next"] = True
            continue
        if c.get("series") == "Handawaka":
            p["handawaka"] = True
            if "Day 2" in c.get("title", ""):
                continue
        p["shows"] += 1
    return sorted(seen.values(), key=lambda p: (not p["country"], not p["shows"], -p["shows"], p["city"]))


def section_places():
    ps = places_list()
    if not ps:
        return ""
    items = []
    for p in ps:
        if p["country"]:
            tag, cls = p["country"], "pl intl"
        elif not p["shows"]:
            tag, cls = "Next show", "pl soon"
        else:
            tag, cls = "", "pl"
        items.append(f'<li class="{cls}"><a href="#concerts"><span>{e(p["city"])}</span>{f"<em>{e(tag)}</em>" if tag else ""}</a></li>')
    n_lk = sum(1 for p in ps if not p["country"] and p["shows"])
    return f'''
<section class="places" aria-labelledby="places-title"><div class="wrap">
  <span class="kicker">On stage</span>
  <h2 id="places-title">Where she has performed</h2>
  <p class="sub">{n_lk} towns and cities across Sri Lanka, and overseas in Dubai.</p>
  <ul class="pl-list">{"".join(items)}</ul>
</div></section>'''


def section_music():
    s = next((x for x in singing if x.get("featured")), singing[0])
    return f'''
<section class="music" id="music" aria-labelledby="music-title"><div class="wrap music-grid">
  {video_facade("youtube", s["youtube"], s["title"], s.get("type", ""))}
  <div class="lead">
    <span class="kicker">{e(s.get("type", ""))}</span>
    <h2 id="music-title">{e(s["title"])}</h2>
    <p>{e(s.get("description", ""))}</p>
    <div class="links"><a class="btn primary" href="{e(contact["youtube"])}" target="_blank" rel="noopener">{icon("yt")}YouTube channel</a></div>
  </div>
</div></section>'''


def section_press():
    out = []
    for p in press:
        if not p.get("featured_on_home"):
            continue
        rel = f"content/press/{p['images'][0]}"
        gid = gal("press-" + p["id"], p["outlet"], p.get("summary", ""), slides_for(p, "press"))
        _, pretty = parse_date(p["date"])
        out.append(f'''
<section class="press" aria-labelledby="press-title"><div class="wrap"><article class="press-card">
  <button class="press-img" data-gallery="{gid}" aria-label="Open the newspaper page">{img_tag(rel, "Silumina Rasaduna feature page about Chathurya", sizes="(max-width: 700px) 34vw, 200px")}</button>
  <div>
    <span class="kicker">As featured in {e(p["outlet"])}, {e(p["section"])}, {e(pretty)}</span>
    <h2 id="press-title" class="h3" lang="si">{e(p["headline_sinhala"])}</h2>
    <p class="tr">{e(p["headline_english"])}</p>
    <button class="link" data-gallery="{gid}">Read the article</button>
  </div>
</article></div></section>''')
    return "".join(out)


def section_about():
    return f'''
<section class="about" id="about" aria-labelledby="about-title"><div class="wrap about-grid">
  <h2 id="about-title">About Chathurya</h2>
  <div>
    <p>Chathurya Sandabarana is a singer from Tangalle, on Sri Lanka's southern coast. She came to national attention on The Voice Sri Lanka, Season 1, where she trained under Umaria Sinhawansa and reached the Live Shows. Her Blind Audition then brought her international recognition: The Voice Global chose it among the best performances of the week from Voice shows around the world, representing Sri Lanka.</p>
    <p>Since then she has sung at concerts across Sri Lanka, from Colombo, Kandy and Galle to Ambalantota, Beliatta and Tissamaharama, and overseas in Dubai. She has performed at four Handawaka shows, released her single <em>Sayam Heene</em>, and made her screen debut in a Sinhala feature film. Alongside music, she studied Aerospace Engineering in the United Kingdom and graduated with First Class Honours. <a class="link" href="education.html">Read about her education</a></p>
  </div>
</div></section>'''


# ---------- tab: singing
def tab_singing():
    items = []
    for sg in singing:
        if not sg.get("youtube"):
            continue
        extra = " ".join(x for x in [("With " + sg["with"] + ".") if sg.get("with") else "", (sg["credits"] + ".") if sg.get("credits") else ""] if x)
        items.append(f'''<div class="item"><span class="when">{e(sg.get("type", ""))}</span><h4>{e(sg["title"])}</h4>
{f'<p>{e(extra)}</p>' if extra else ''}{video_facade("youtube", sg["youtube"], sg["title"], sg.get("type", ""), cls="video small")}</div>''')
    for c in concerts:
        for v in c.get("videos_youtube", []):
            if v.get("short"):
                continue
            items.append(f'''<div class="item"><span class="when">Live duet with {e(", ".join(c.get("with", [])))}</span><h4>{e(c.get("song") or v["title"])}</h4>
<p>{e(c["title"])}</p>{video_facade("youtube", v["id"], c.get("song") or v["title"], c["title"], cls="video small")}</div>''')
    songs, seen = [], set()
    for vid in VOICE_ORDER:
        it = voice.get(vid)
        if it and vid != "best-of-the-week":
            t = it.get("song") or it.get("title")
            if t and t.lower() not in seen:
                seen.add(t.lower()); songs.append(t)
    for sg in singing:
        if sg["title"].lower() not in seen:
            seen.add(sg["title"].lower()); songs.append(sg["title"])
    for c in concerts:
        if c.get("song") and c["song"].lower() not in seen:
            seen.add(c["song"].lower()); songs.append(c["song"])
    sl = "".join(f"<li>{e(t)}</li>" for t in songs)
    fm = "".join(f"<li>{e(f)}</li>" for f in site.get("formats", []))
    return f'''<div class="lead slead"><h3>Singing and concerts</h3>
<p>Singing is at the heart of everything Chathurya does: her own releases and duets, and the concert stages, television and community celebrations below.</p>
<div class="rep"><h4>Songs she has performed</h4><ul class="songs">{sl}</ul>
<h4>Performance formats</h4><ul class="songs">{fm}</ul><p class="avail">{e(site.get("availability", ""))}</p></div></div>
<div class="items vgrid">{"".join(items)}</div>'''


# ---------- tab: concerts
def handawaka_steps():
    hand = [c for c in concerts if c.get("series") == "Handawaka" and parse_date(c.get("date"))[0]]
    hand.sort(key=lambda c: parse_date(c["date"])[0])
    past = [c for c in hand if not (date_obj(c["date"]) and date_obj(c["date"]) >= TODAY)]
    up = [c for c in hand if c not in past]
    groups = []
    for c in past:
        key = (c.get("city"), str(c.get("date"))[:7])
        if groups and groups[-1]["key"] == key:
            groups[-1]["items"].append(c)
        else:
            groups.append({"key": key, "items": [c]})
    steps = []
    for n, g in enumerate(groups, 1):
        first = g["items"][0]
        city = first.get("city", "")
        venue = first.get("venue", "")
        _, pretty = parse_date(first["date"])
        slides, descs, nphoto, nvid = [], [], 0, 0
        for c in g["items"]:
            sl = slides_for(c, "concerts-and-events")
            day = ""
            if "Day" in c["title"]:
                day = c["title"][c["title"].index("Day"):].rstrip(")")
                for s in sl:
                    s["cap"] = f'{day}: {s.get("cap", "")}'
            slides += sl
            descs.append(c.get("description", ""))
            nphoto += len(c.get("images", []))
            nvid += len(c.get("videos", [])) + len(c.get("videos_youtube", []))
        nights = len(g["items"])
        place = first["title"].replace("Handawaka, ", "").split(" (")[0]
        title = f"Handawaka {n}, {place}"
        gid = gal(f"handawaka-{n}", title, " ".join([pretty] + descs), slides)
        cover_rel = first["images"][0]
        cover = img_tag(f"content/concerts-and-events/{cover_rel}", f"Chathurya at Handawaka, {city}",
                        sizes="(max-width: 860px) 92vw, 260px", cls="hcover")
        counts = [f"{nphoto} photos"] + ([f"{nvid} video" + ("s" if nvid > 1 else "")] if nvid else [])
        sub = ", ".join(x for x in [venue if venue and venue not in place else (city if city not in place else ""), ("Day 1 and Day 2" if nights == 2 else "")] if x)
        steps.append(f'''<li class="hstep"><button class="hbtn" data-gallery="{gid}" aria-label="Open Handawaka {n}, {e(place)}">
  <span class="hnum">{n}</span>{cover}
  <span class="htext"><strong>{e(place)}</strong><span>{e(pretty)}{(" · " + e(sub)) if sub else ""}</span><span class="badge">{" · ".join(counts)}. View all</span></span>
</button></li>''')
    for c in up:
        d = date_obj(c["date"])
        steps.append(f'''<li class="hstep next-step"><div class="hbtn"><span class="hnum">{icon("pin")}</span>
  <span class="hcover blank"><b>{MONTHS[d.month-1][:3].upper()}</b><span>{d.day}</span></span>
  <span class="htext"><strong>{e(c.get("city", ""))}</strong><span>{d.day} {MONTHS[d.month-1]} {d.year}</span><span class="upcoming">Next show</span></span></div></li>''')
    return len(groups), "".join(steps)


def concert_card(c):
    _, pretty = parse_date(c.get("date"))
    gid = gal("concert-" + c["id"], c["title"], " ".join(x for x in [pretty, c.get("description", "")] if x),
              slides_for(c, "concerts-and-events"))
    venue, city = c.get("venue") or "", c.get("city") or ""
    where = ", ".join(x for x in [venue, city if city and city not in venue else ""] if x)
    n_img = len(c.get("images", []))
    n_vid = len(c.get("videos", [])) + len(c.get("videos_youtube", []))
    badges = []
    if n_img:
        badges.append(f"{n_img} photo" + ("s" if n_img > 1 else ""))
    if n_vid:
        badges.append(f"{n_vid} video" + ("s" if n_vid > 1 else ""))
    cover = (img_tag(f'content/concerts-and-events/{c["images"][0]}', c["title"], sizes="(max-width: 700px) 38vw, 200px", cls="ccover")
             if n_img else f'<span class="ccover blank">{icon("mic")}</span>')
    with_line = ""
    if c.get("with"):
        names = [w.split(" (")[0] for w in c["with"]][:4]
        with_line = f'<p class="with">With {e(", ".join(names))}</p>'
    tag, attr = ("button", f'data-gallery="{gid}" aria-label="Open {e(c["title"])}"') if (n_img or n_vid) else ("div", "")
    return f'''<li><{tag} class="item feature" {attr}>{cover}<span class="ctext">
<span class="when">{e(pretty)}</span><strong>{e(c["title"])}</strong><span class="where">{e(where)}</span>{with_line}
{f'<span class="badge">{" · ".join(badges)}</span>' if badges else ''}</span></{tag}></li>'''


def tab_concerts():
    n, steps = handawaka_steps()
    others = [c for c in concerts if c.get("series") != "Handawaka" and parse_date(c.get("date"))[0]
              and not (date_obj(c["date"]) and date_obj(c["date"]) >= TODAY)]
    others.sort(key=lambda c: parse_date(c["date"])[0], reverse=True)
    cards = "".join(concert_card(c) for c in others)
    return tab_singing() + f'''<div class="wide merged">
<div class="hhead"><h3>Handawaka</h3><p>Chathurya has sung at {n} Handawaka shows. Tap a show to see all its photos and videos.</p>{('<span class="hawards">' + icon("trophy") + e(site["handawaka_award"]["text"]) + '</span>') if site.get("handawaka_award", {}).get("text") else ""}</div>
<ol class="htimeline">{steps}</ol>
<h3 class="sub-h">Concerts and events</h3>
<p class="muted">Shows across Sri Lanka and overseas, newest first. Tap a poster for photos.</p>
<ul class="clist">{cards}</ul></div>'''


# ---------- tab: television
def tab_tv():
    tv_all = load("television")
    vid_html = ""
    for x in [x for x in tv_all if x.get("videos")]:
        gid = gal("tv-" + x["id"], x["title"], x.get("description", ""), slides_for(x, "television"))
        v0 = x["videos"][0]
        poster = f'<img src="content/television/{e(v0["poster"])}" alt="{e(x["title"])} on {e(x.get("channel", ""))}" loading="lazy" decoding="async">'
        vid_html += (f'<div class="item"><span class="when">{e(x.get("channel", ""))}</span><h4>{e(x["title"])}</h4><p>{e(x.get("description", ""))}</p>'
                     f'<button class="tvclip" data-gallery="{gid}" aria-label="Play {e(x["title"])} clips">{poster}<span class="play">{icon("play")}</span>'
                     f'<span class="badge">{len(x["videos"])} clips</span></button></div>')
    tv_items = [x for x in tv_all if x.get("youtube")]
    son_html = vid_html + "".join(
        f'<div class="item"><span class="when">{e(x.get("channel", ""))}</span><h4>{e(x["title"])}</h4><p>{e(x.get("description", ""))}</p>'
        f'{video_facade("youtube", x["youtube"], x["title"], x.get("channel", ""), start=x.get("start", ""), cls="video small")}</div>'
        for x in tv_items)
    return f'''<div class="lead"><h3>Television</h3>
<p>Chathurya first reached audiences across Sri Lanka on The Voice Sri Lanka on Sirasa TV, and her Blind Audition was later featured in The Voice Global's international highlights. She has also sung on television and been a guest on television podcasts.</p>
<a class="link" href="#voice" data-tab="t-voice">See her journey on The Voice</a></div>
<div class="items">
<div class="item"><span class="when">8 January 2021</span><h4>International recognition, The Voice Global</h4><p>Her Blind Audition of Hithala Wanniye, chosen to represent Sri Lanka.</p>
{video_facade("youtube", "JatYDHP0ARc", "Hithala Wanniye", "The Voice Global, best performances of the week", start=211, end=337, cls="video small")}</div>
{son_html}
<div class="item"><h4>Television podcasts</h4><p>Guest appearances, conversation and live singing.</p></div></div>'''


# ---------- tab: the voice
VOICE_ORDER = ["blind-audition", "best-of-the-week", "battles", "knockouts", "road-to-lives", "live-shows"]


def tab_voice():
    rows = []
    for vid in VOICE_ORDER:
        it = voice.get(vid)
        if not it:
            continue
        _, pretty = parse_date(it.get("date"))
        song = "Hithala Wanniye" if vid == "best-of-the-week" else (it.get("song") or it.get("title"))
        meta = {"blind-audition": f'Season {it.get("season", 1)}. Joined Team {it.get("coach", "")}',
                "best-of-the-week": "Selected to represent Sri Lanka in The Voice's international highlights",
                "battles": f'Won her battle against {it.get("opponent", "")}',
                "knockouts": f'Original by {it.get("original_artist", "")}' if it.get("original_artist") else "",
                "road-to-lives": "Showcase programme before the Live Shows",
                "live-shows": "Reached the Live Shows"}.get(vid, "")
        sl = slides_for(it, "the-voice")
        if it.get("youtube"):
            sl = [{"t": "yt", "id": it["youtube"], "start": it.get("start", ""), "end": it.get("end", ""), "cap": f'{it["round"]}: {song}'}] + sl
        gid = gal("voice-" + vid, f'{it["round"]}: {song}', " ".join(x for x in [meta, pretty] if x), sl)
        if it.get("images"):
            thumb = img_tag(f'content/the-voice/{it["images"][0]}', it["round"], sizes="110px", cls="tthumb")
        elif it.get("youtube"):
            thumb = f'<img class="tthumb" src="{yt_thumb(it["youtube"])}" alt="" loading="lazy" width="480" height="360" onerror="this.remove()">'
        else:
            thumb = ""
        thumb = f'<span class="tthumbw">{thumb}</span>'
        badge = (["video"] if it.get("youtube") else []) + ([f'{len(it["images"])} photo' + ("s" if len(it["images"]) > 1 else "")] if it.get("images") else [])
        rows.append(f'''<li class="step{' hl' if it.get('highlight') else ''}"><button class="tcard" data-gallery="{gid}" aria-label="Open {e(it['round'])}">{thumb}
<span class="ttext"><span class="round">{e(it['round'])}{(' · ' + e(pretty)) if pretty else ''}</span><strong>{e(song)}</strong><span class="meta">{e(meta)}</span>
<span class="badge">{" + ".join(badge)}</span></span></button></li>''')
    bw = voice.get("best-of-the-week", {})
    coach = voice.get("coach-reaction-adam-baruell")
    coach_html = ""
    if coach:
        qs = "".join(f"<li>\"{e(q)}\"</li>" for q in coach.get("quotes", [])[:3])
        coach_html = f'''<div class="coach"><h4>A vocal coach's view</h4><p>{e(coach.get("description", ""))}</p><ul>{qs}</ul>
{video_facade("youtube", coach["youtube"], "Vocal coach reaction", "Adam Baruell", cls="video small")}</div>'''
    return f'''<div class="lead"><h3>The Voice Sri Lanka</h3>
<p>On Season 1 of The Voice Sri Lanka on Sirasa TV, Chathurya trained under Umaria Sinhawansa and went through every round to the Live Shows.</p>
<div class="global">{icon("globe")}<p><strong>A proud moment for Sri Lanka.</strong> Her Blind Audition of <em>Hithala Wanniye</em> was chosen by The Voice Global among the best performances of the week from Voice shows around the world, on 8 January 2021, representing Sri Lanka.</p></div>
<blockquote class="quote">"{e(bw.get("quote", ""))}"<cite>Chathurya</cite></blockquote>
{coach_html}</div>
<ol class="timeline">{"".join(rows)}</ol>'''


# ---------- tab: film
def tab_film():
    f = film[0]
    gid = gal("film", f["title"], "", slides_for(f, "film"))
    caps = f.get("image_captions", {})
    lead = img_tag(f'content/film/{f["images"][0]}', caps.get(f["images"][0], f["title"]), sizes="(max-width: 700px) 86vw, 360px", cls="fprofile")
    thumbs = "".join(
        f'<button class="fthumb" data-gallery="{gid}" data-index="{i}" aria-label="Open {e(caps.get(rel, "photo"))}">'
        f'{img_tag(f"content/film/{rel}", caps.get(rel, f["title"]), sizes="(max-width: 700px) 40vw, 170px")}<span>{e("Red carpet" if "red-carpet" in rel else "Official poster" if "poster" in rel else "")}</span></button>'
        for i, rel in enumerate(f["images"]) if i)
    return f'''<div class="lead"><h3>Film</h3><p>Alongside her music, Chathurya made her screen debut in the Sinhala feature film {e(f["title"])}.</p></div>
<div class="items"><div class="item filmcard2">
<button class="fmain" data-gallery="{gid}" data-index="0" aria-label="Open film photos">{lead}</button>
<div class="finfo"><span class="when">Screen debut</span><h4>{e(f["title"])}</h4>
<p>Directed by {e(f.get("director", ""))}, produced by {e(f.get("producer", ""))}.</p>
<div class="fthumbs">{thumbs}</div></div></div></div>'''


# ---------- tab: education
def tab_education():
    ed = education[0]
    gid = gal("education", ed["title"], "", slides_for(ed, "education"))
    photo = img_tag(f'content/education/{ed["images"][0]}', "Chathurya at her graduation", sizes="(max-width: 700px) 60vw, 300px", cls="grad")
    why = "".join(f'<li>{icon(w["icon"])}<div><strong>{e(w["title"])}</strong><p>{e(w["text"])}</p></div></li>' for w in ed.get("why_it_matters", []))
    areas = "".join(f"<li>{e(a)}</li>" for a in ed.get("research_areas", []))
    return f'''<div class="lead edu">
<svg class="edu-bg" viewBox="0 0 600 300" aria-hidden="true"><defs><linearGradient id="trail" x1="0" x2="1"><stop offset="0" stop-color="#D4A53A" stop-opacity="0"/><stop offset="1" stop-color="#ECCF85" stop-opacity=".5"/></linearGradient></defs>
<path d="M-20 260 C 200 230, 380 150, 470 90" stroke="url(#trail)" stroke-width="26" fill="none" stroke-linecap="round"/><path d="M455 70 l40 -18 q22 22 8 52 l-40 10z" fill="#ECCF85" fill-opacity=".35"/>
<circle cx="470" cy="90" r="46" fill="none" stroke="#D4A53A" stroke-opacity=".25"/></svg>
<h3>Education</h3><p class="cls">{e(ed["title"])}<br>{e(ed.get("classification", ""))}, {e(ed.get("institution", ""))}, {e(ed.get("year", ""))}</p>
<p>{e(ed.get("plain_language", ""))}</p><h4>Research areas</h4><ul class="areas">{areas}</ul>
<a class="btn primary" href="education.html">Open her education page</a></div>
<div class="items"><button class="item gradbtn" data-gallery="{gid}" aria-label="Open graduation photo">{photo}</button>
<div class="item"><h4>Why her work matters to everyone</h4><ul class="why">{why}</ul></div></div>'''


def education_body():
    ed = education[0]
    st = ed.get("statement", {})
    rp = ed.get("research_paper", {})
    slides = slides_for(ed, "education")
    gid = gal("education-page", ed["title"], ed.get("intro", ""), slides)
    lead_photo = img_tag(f'content/education/{ed["images"][0]}', "Chathurya at her graduation, Kingston University London",
                         sizes="(max-width: 860px) 80vw, 440px", cls="eportrait", eager=True)
    thumbs = "".join(
        f'<button class="eg-item" data-gallery="{gid}" data-index="{i}" aria-label="Open photo {i + 1}">'
        f'{img_tag(f"content/education/{rel}", ed.get("image_captions", {}).get(rel, ed["title"]), sizes="(max-width: 700px) 46vw, 280px")}</button>'
        for i, rel in enumerate(ed["images"]))
    why = "".join(f'<li>{icon(w["icon"])}<div><strong>{e(w["title"])}</strong><p>{e(w["text"])}</p></div></li>' for w in ed.get("why_it_matters", []))
    areas = "".join(f"<li>{e(a)}</li>" for a in ed.get("research_areas", []))
    medals = [("cap", "First Class", "BSC (HONS) AEROSPACE ENGINEERING · 2026 · ", "Honours degree", "The highest class of degree"),
              ("globe", "UK", "KINGSTON UNIVERSITY LONDON · ENGLAND · ", "Studied in England", ed.get("institution", "")),
              ("shield", "Research", "RE-ENTRY HEAT RESEARCH · PEER REVIEW · ", rp.get("status", ""), "Research paper on re-entry heating")]
    t = "".join(medal(i, icon(ic), big, ring, lab, sub, e) for i, (ic, big, ring, lab, sub) in enumerate(medals))
    return f'''
<section class="hero ehero" aria-label="Education">
  <canvas id="waves" aria-hidden="true"></canvas>
  <div class="wrap hero-grid">
    <div class="intro">
      <span class="kicker">Education</span>
      <h1 class="ename">Aerospace Engineering<span>United Kingdom</span></h1>
      <p class="efirst">First Class Honours</p>
      <p class="lede">{e(ed["title"])}, {e(ed.get("institution", ""))}, {e(ed.get("year", ""))}.</p>
      <div class="actions"><a class="btn primary" href="#words">In her words</a><a class="btn ghost" href="./#performances">Her music</a></div>
    </div>
    <div class="stage"><button class="eframe" data-gallery="{gid}" data-index="0" aria-label="Open graduation photos">{lead_photo}</button></div>
  </div>
</section>
<section class="medals-sec"><div class="wrap"><div class="medals">{t}</div></div></section>
{divider()}
<section class="words" id="words" aria-labelledby="words-title"><div class="wrap">
  <span class="kicker">In her words</span>
  <h2 id="words-title">Music and engineering, side by side</h2>
  <blockquote class="wquote"><p>{e(st.get("english", ""))}</p><cite>Chathurya Sandabarana</cite></blockquote>
  <blockquote class="wquote si-q" lang="si"><p>{e(st.get("sinhala", ""))}</p></blockquote>
</div></section>
{divider()}
<section class="eresearch" aria-labelledby="res-title"><div class="wrap">
  <div class="er-head"><span class="kicker">Her research</span><h2 id="res-title">Bringing spacecraft home safely</h2>
  <p class="er-lede">The most dangerous minutes of any space mission are the last ones. Here is the problem her research works on, in four pictures.</p></div>
  {journey_html(e)}
  <div class="er-grid">
    <div><p class="paper">{icon("shield")}<span><strong>Research paper, {e(rp.get("status", "").lower())}</strong>{e(rp.get("topic", ""))}</span></p>
      <h4>Research areas</h4><ul class="chips">{"".join(f"<li>{e(a)}</li>" for a in ed.get("research_areas", []))}</ul></div>
    <div class="item"><h4>Why her work matters to everyone</h4><ul class="why">{why}</ul></div>
  </div>
</div></section>
{divider()}
<section class="egallery" aria-labelledby="eg-title"><div class="wrap">
  <span class="kicker">Graduation, 2026</span><h2 id="eg-title">Class of 2026</h2>
  <div class="eg-grid">{thumbs}</div>
  <div class="eback"><a class="btn primary" href="./#invite">Invite to perform</a><a class="btn ghost" href="./">Back to the main page</a></div>
</div></section>'''


def tab_modelling():
    rows = ""
    for m in modelling:
        gid = gal("modelling-" + m["id"], m["title"], m.get("credit", ""), slides_for(m, "modelling"))
        thumbs = "".join(f'<button class="eg-item" data-gallery="{gid}" data-index="{i}" aria-label="Open photo {i + 1}">'
                         f'{img_tag(f"content/modelling/{rel}", m["image_captions"].get(rel, m["title"]), sizes="(max-width: 700px) 46vw, 220px")}</button>'
                         for i, rel in enumerate(m["images"]))
        rows += f'<div class="mrow"><h4>{e(m["title"])}</h4><p class="credit">{e(m.get("credit", ""))}</p><div class="eg-grid">{thumbs}</div></div>'
    ag = site.get("agency", {})
    agency = (f'<p class="agency">{icon("globe")}<span>Signed model with <strong>{e(ag["name"])}</strong></span></p>'
              f'<a class="btn ghost agbtn" href="{e(ag["url"])}" target="_blank" rel="noopener">{e(ag.get("label", ag["name"]))}</a>') if ag.get("name") else ""
    return f'''<div class="lead"><h3>Modelling</h3>{agency}<p>Commercial advertising and bridal shoots, taken on selectively. A few examples are shown here.</p></div>
<div class="items mitems">{rows}</div>'''


TABS = [("concerts", "Singing and concerts", tab_concerts), ("tv", "Television", tab_tv),
        ("voice", "The Voice", tab_voice), ("film", "Film", tab_film), ("education", "Education", tab_education), ("modelling", "Modelling", tab_modelling)]


def section_performances():
    btns, panels = [], []
    for i, (key, label, fn) in enumerate(TABS):
        sel = "true" if key == "concerts" else "false"
        btns.append(f'<button class="tab" role="tab" id="t-{key}" aria-controls="p-{key}" aria-selected="{sel}" tabindex="{0 if sel == "true" else -1}">{e(label)}</button>')
        panels.append(f'<div class="panel" role="tabpanel" id="p-{key}" aria-labelledby="t-{key}" tabindex="0"{"" if sel == "true" else " hidden"}>{fn()}</div>')
    return f'''
<section class="perf" id="performances" aria-labelledby="perf-title"><div class="wrap">
  <h2 id="perf-title">Performances</h2>
  <p class="sub">Choose a category to see Chathurya's work.</p>
  <div class="tablist" role="tablist" aria-label="Performance categories">{"".join(btns)}</div>
  {"".join(panels)}
</div></section>'''


def section_invite():
    key = contact.get("web3forms_key", "").strip()
    cards = "".join(f'''<div class="ccard"><span class="crole">{e(p["role"])}</span><span class="crole-si" lang="si">{e(p.get("role_si", ""))}</span>
  {f'<strong>{e(p["name"])}</strong>' if p.get("name") else ""}<span class="cnum">{e(p["display"])}</span>
  <span class="cbtns"><a href="tel:{e(p["number"])}">{icon("phone")}Call</a><a href="https://wa.me/{"".join(ch for ch in p["number"] if ch.isdigit())}" target="_blank" rel="noopener">{icon("wa")}WhatsApp</a></span></div>''' for p in people)
    form_html = f'''  <form id="inviteForm" novalidate data-wa="{whatsapp}" data-to="{e(form_person["name"] if form_person else "")}" data-key="{e(key)}" data-mail="{e(email)}" data-endpoint="{e(private.get("endpoint", ""))}" data-alerts="{e("" if private.get("endpoint") else json.dumps([[a["phone"], a["apikey"]] for a in contact.get("whatsapp_alerts", []) if a.get("apikey")]))}">
    <input type="checkbox" name="botcheck" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
    <label><span class="lt">Your name <span class="req">required</span></span><input name="name" maxlength="80" autocomplete="name" required></label>
    <label><span class="lt">Your phone or WhatsApp <span class="req">required</span></span>
      <span class="phone"><select name="cc" aria-label="Country code"><option value="+94" selected>🇱🇰 +94</option><option value="+44">🇬🇧 +44</option><option value="+971">🇦🇪 +971</option><option value="+61">🇦🇺 +61</option><option value="+1">🇺🇸 +1</option><option value="+91">🇮🇳 +91</option><option value="+65">🇸🇬 +65</option><option value="+974">🇶🇦 +974</option><option value="+966">🇸🇦 +966</option><option value="+33">🇫🇷 +33</option><option value="+49">🇩🇪 +49</option><option value="+39">🇮🇹 +39</option><option value="+82">🇰🇷 +82</option><option value="+81">🇯🇵 +81</option><option value="+60">🇲🇾 +60</option><option value="+">Other</option></select>
      <input name="phone" maxlength="20" type="tel" inputmode="tel" autocomplete="tel-national" placeholder="7X XXX XXXX" required></span></label>
    <label><span class="lt">Your email <span class="opt">optional, for a confirmation copy</span></span><input name="email" maxlength="120" type="email" autocomplete="email" inputmode="email" placeholder="name@example.com"></label>
    <label><span class="lt">Event or organisation <span class="req">required</span></span><input name="event" maxlength="150" autocomplete="organization" placeholder="e.g. Singing at a concert, TV show, talk show programme" required></label>
    <label><span class="lt">Possible date or week <span class="req">required</span></span><input name="date" maxlength="80" placeholder="e.g. 14 December, or the week of 20 January" required></label>
    <label><span class="lt">Short description <span class="req">required</span></span><textarea name="msg" maxlength="1500" rows="5" placeholder="Please share as much information as possible: the event, venue or town, audience, how many songs, timings and any other details." required></textarea></label>
    <p class="err" id="formErr" role="alert" hidden>Please fill in your name, phone number, event, possible date and a short description.</p>
    <div class="send"><button type="submit" class="btn primary big" data-send="wa">{icon("wa")}Send message on WhatsApp</button></div>
    <p class="fine">Your message is sent directly and we will get back to you as soon as possible.</p>
    {f'<p class="fine mailline">Prefer email? <a href="mailto:{e(email)}">{e(email)}</a></p>' if email else ""}
    <p class="done" id="formDone" role="status" hidden></p>
  </form>
  <div class="confirm" id="formConfirm" role="status" tabindex="-1" hidden>
    <span class="tick" aria-hidden="true">✓</span>
    <h3 id="cfTitle">Thank you. Your message has been sent.</h3>
    <p id="cfLead"></p>
    <dl id="cfList"></dl>
    <p class="cfnote" id="cfNote"></p>
    <button type="button" class="btn ghost" id="cfAgain">Send another message</button>
  </div>'''
    return f'''
<section class="invite" id="invite" aria-labelledby="invite-title"><div class="wrap"><div class="icard">
  <h2 id="invite-title">Invite Chathurya to perform</h2>
  <p class="si" lang="si">වැඩසටහනකට ආරාධනා කරන්න</p>
  <p>For concerts, musical shows, television and talk show programmes, school and community events, in Sri Lanka or overseas.</p>
  <p class="howto">Please fill in the details below with as much information as possible. We will contact you on WhatsApp.</p>
  <p class="quiet">Commercial and bridal modelling considered selectively.</p>
  {form_html}
  <div class="direct"><a href="{e(contact["youtube"])}" target="_blank" rel="noopener">{icon("yt")}YouTube</a></div>
</div></div></section>'''


# ---------------------------------------------------------------- page
CSS = open(os.path.join(ROOT, "tools", "site.css"), encoding="utf-8").read()
JS = open(os.path.join(ROOT, "tools", "site.js"), encoding="utf-8").read()

body = "".join([section_hero(), section_next(), section_highlights(), section_places(), divider(), section_music(), section_press(), divider(),
                section_about(), divider(), section_performances(), divider(), section_invite()])

person_ld = {"@context": "https://schema.org", "@type": "Person", "name": site["name"], "url": site["url"],
             "jobTitle": "Singer", "homeLocation": {"@type": "Place", "name": site["hometown"]},
             "alumniOf": {"@type": "CollegeOrUniversity", "name": "Kingston University London"},
             "sameAs": [contact["facebook"], contact["youtube"]], "image": site["url"] + "assets/share.jpg"}
ld = [person_ld]
for d, c in upcoming():
    if c.get("venue") and c.get("city"):
        ld.append({"@context": "https://schema.org", "@type": "MusicEvent", "name": c["title"], "startDate": d.isoformat(),
                   "eventStatus": "https://schema.org/EventScheduled",
                   "location": {"@type": "Place", "name": c["venue"], "address": {"@type": "PostalAddress", "addressLocality": c["city"], "addressCountry": "LK"}},
                   "performer": {"@type": "Person", "name": site["name"], "url": site["url"]}})

def make_page(body, title, desc, canonical, nav, home="", ld_list=None):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{site["url"]}assets/share.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0C241F">
<link rel="icon" href="assets/icon.png">
<link rel="preload" href="assets/fonts/rozha-one-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="assets/fonts/hanken-grotesk-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld_list or [], ensure_ascii=False)}</script>
</head>
<body>
<header class="bar" id="bar"><div class="wrap">
  <a class="mark" href="{home}#top">Chathurya</a>
  <nav aria-label="Main">{nav}</nav>
</div></header>
<main id="top">{body}</main>
<footer><div class="wrap"><span>&copy; {TODAY.year} {e(site["name"])}</span><span>Photographs credited to their photographers.</span><a href="#top">Back to top</a></div></footer>
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


# Show non-English words in Sinhala script (visible text and gallery captions only; head, attributes and JSON-LD stay English)
def sinhalise(page):
    SI = {k: v for k, v in site.get("sinhala_terms", {}).items() if not k.startswith("_")}
    if not SI:
        return page
    term_re = re.compile("|".join(re.escape(k) for k in sorted(SI, key=len, reverse=True)))
    head, sep, rest = page.partition("<body")
    parts = re.split(r'(<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>)', rest)
    for i, part in enumerate(parts):
        if part.startswith('<script id="galleries"'):
            parts[i] = term_re.sub(lambda m: SI[m.group(0)], part)
        elif part and not part.startswith("<"):
            parts[i] = term_re.sub(lambda m: f'<span lang="si" class="si-t" title="{m.group(0)}">{SI[m.group(0)]}</span>', part)
    return head + sep + "".join(parts)


page = sinhalise(make_page(body, site["name"] + " | Singer", site["description"], site["url"], '<a href="#about" class="hide-xs">About</a><a href="education.html" class="hide-xs">Education</a><a href="#performances">Performances</a><a href="#invite" class="cta">Invite</a>', ld_list=ld))
edu_page = sinhalise(make_page(education_body(), "Education | " + site["name"],
    site["name"] + " graduated in Aerospace Engineering in the United Kingdom with First Class Honours.", site["url"] + "education.html",
    '<a href="./#about" class="hide-xs">About</a><a href="./#performances">Performances</a><a href="./#invite" class="cta">Invite</a>', home="./",
    ld_list=[person_ld]))
with open(os.path.join(ROOT, "education.html"), "w", encoding="utf-8") as f:
    f.write(edu_page)
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
    f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{site["url"]}</loc><lastmod>{TODAY.isoformat()}</lastmod></url><url><loc>{site["url"]}education.html</loc><lastmod>{TODAY.isoformat()}</lastmod></url></urlset>\n')
with open(os.path.join(ROOT, "robots.txt"), "w") as f:
    f.write(f"User-agent: *\nAllow: /\nDisallow: /content/inbox/\nDisallow: /tools/\nSitemap: {site['url']}sitemap.xml\n")

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
