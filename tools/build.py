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
whatsapp = "".join(ch for ch in contact.get("whatsapp", "") if ch.isdigit())
email = contact.get("email", "").strip()


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
    tiles = [
        (str(n_hand), "Handawaka shows", "Colombo, Kandy, Havelock grounds, Galle", "#concerts"),
        (str(n_concerts), "Concerts and events", "Across Sri Lanka and in Dubai since 2022", "#concerts"),
        ("Live Shows", "The Voice Sri Lanka", "Season 1, trained under Umaria Sinhawansa", "#voice"),
        ("Best of the Week", "The Voice Global", "Representing Sri Lanka, 8 January 2021", "#voice"),
    ]
    def tile(n, a, s, h):
        num = n.isdigit()
        cls = "big num" if num else "big"
        dc = f' data-count="{n}"' if num else ""
        return f'<a class="hl-tile" href="{h}"><span class="{cls}"{dc}>{e(n)}</span><strong>{e(a)}</strong><span>{e(s)}</span></a>'
    t = "".join(tile(*x) for x in tiles)
    award = ""
    if aw.get("text"):
        name = f" ({e(aw['award_name'])})" if aw.get("award_name") else ""
        award = f'<a class="award" href="#concerts">{icon("trophy")}<span><strong>{e(aw["text"])}{name}</strong><span>Chathurya has sung at four Handawaka shows.</span></span></a>'
    return f'''
<section class="highlights" aria-label="Highlights"><div class="wrap"><div class="hl-grid">{t}</div>{award}</div></section>'''


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
    facts = "".join(f"<li>{e(f)}</li>" for f in site.get("facts", []))
    return f'''
<section class="about" id="about" aria-labelledby="about-title"><div class="wrap about-grid">
  <h2 id="about-title">About Chathurya</h2>
  <div>
    <p>Chathurya Sandabarana is a singer from Tangalle, on Sri Lanka's southern coast. She came to national attention on The Voice Sri Lanka, Season 1, where she trained under Umaria Sinhawansa and reached the Live Shows. Her Blind Audition was selected for The Voice Global's "Best of the Week", representing Sri Lanka.</p>
    <p>Since then she has sung at concerts across Sri Lanka and in Dubai, including four Handawaka shows, released her single <em>Sayam Heene</em>, and made her screen debut in a Sinhala feature film. Alongside music, she is an aerospace engineering graduate.</p>
    <ul class="facts">{facts}</ul>
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
    return f'''<div class="lead"><h3>Singing</h3>
<p>Singing is at the heart of everything Chathurya does, from her own releases and duets to concert stages, television and community celebrations.</p>
<div class="rep"><h4>Songs she has performed</h4><ul class="songs">{sl}</ul>
<h4>Performance formats</h4><ul class="songs">{fm}</ul><p class="avail">{e(site.get("availability", ""))}</p></div></div>
<div class="items">{"".join(items)}</div>'''


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
    return f'''<div class="wide">
<div class="hhead"><h3>Handawaka</h3><p>Chathurya has sung at {n} Handawaka shows. Tap a show to see all its photos and videos.</p>{('<span class="hawards">' + icon("trophy") + e(site["handawaka_award"]["text"]) + '</span>') if site.get("handawaka_award", {}).get("text") else ""}</div>
<ol class="htimeline">{steps}</ol>
<h3 class="sub-h">Concerts and events</h3>
<p class="muted">Shows across Sri Lanka and overseas, newest first. Tap a poster for photos.</p>
<ul class="clist">{cards}</ul></div>'''


# ---------- tab: television
def tab_tv():
    son = next((c for c in concerts if "sonduru" in c["id"]), None)
    son_html = ""
    if son:
        _, pretty = parse_date(son["date"])
        son_html = f'<div class="item"><span class="when">{e(pretty)}</span><h4>{e(son["title"])}</h4><p>{e(son.get("description", ""))}</p></div>'
    return f'''<div class="lead"><h3>Television</h3>
<p>Chathurya first reached audiences across Sri Lanka on The Voice Sri Lanka on Sirasa TV, and her Blind Audition was later featured in The Voice Global's international highlights. She has also sung on television and been a guest on television podcasts.</p>
<a class="link" href="#voice" data-tab="t-voice">See her journey on The Voice</a></div>
<div class="items">
<div class="item"><span class="when">8 January 2021</span><h4>The Voice Global, Best of the Week</h4><p>Her Blind Audition of Hithala Wanniye, chosen to represent Sri Lanka.</p>
{video_facade("youtube", "JatYDHP0ARc", "Hithala Wanniye", "The Voice Global, Best of the Week", start=211, end=337, cls="video small")}</div>
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
<div class="global">{icon("globe")}<p><strong>A proud moment for Sri Lanka.</strong> Her Blind Audition of <em>Hithala Wanniye</em> was selected for The Voice Global's "Best of the Week" on 8 January 2021, representing Sri Lanka among standout performances from the international Voice franchise.</p></div>
<blockquote class="quote">"{e(bw.get("quote", ""))}"<cite>Chathurya</cite></blockquote>
{coach_html}</div>
<ol class="timeline">{"".join(rows)}</ol>'''


# ---------- tab: film
def tab_film():
    f = film[0]
    gid = gal("film", f["title"], "", slides_for(f, "film"))
    cover = img_tag(f'content/film/{f["images"][0]}', f'{f["title"]} poster', sizes="(max-width: 700px) 60vw, 300px", cls="fposter") if f.get("images") else ""
    return f'''<div class="lead"><h3>Film</h3><p>Alongside her music, Chathurya made her screen debut in a Sinhala feature film.</p></div>
<div class="items"><div class="item filmcard"><button data-gallery="{gid}" aria-label="Open poster">{cover}</button>
<div><span class="when">Screen debut, {e(f.get("year", ""))}</span><h4>{e(f["title"])}</h4>
<p>Directed by {e(f.get("director", ""))}, produced by {e(f.get("producer", ""))}.</p>
<a class="link" href="{e(contact["imdb"])}" target="_blank" rel="noopener">{icon("film")}Her profile on IMDb</a></div></div></div>'''


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
<p>{e(ed.get("plain_language", ""))}</p><h4>Research areas</h4><ul class="areas">{areas}</ul></div>
<div class="items"><button class="item gradbtn" data-gallery="{gid}" aria-label="Open graduation photo">{photo}</button>
<div class="item"><h4>Why her work matters to everyone</h4><ul class="why">{why}</ul></div></div>'''


TABS = [("singing", "Singing", tab_singing), ("concerts", "Concerts and events", tab_concerts), ("tv", "Television", tab_tv),
        ("voice", "The Voice", tab_voice), ("film", "Film", tab_film), ("education", "Education", tab_education)]


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
    btns = []
    if whatsapp:
        btns.append(f'<button type="submit" class="btn primary" data-send="wa">{icon("wa")}Send via WhatsApp</button>')
    if email:
        btns.append(f'<button type="submit" class="btn {"ghost" if whatsapp else "primary"}" data-send="mail">{icon("mail")}Send via email</button>')
    direct = []
    if whatsapp:
        direct.append(f'<a href="https://wa.me/{whatsapp}">{icon("wa")}WhatsApp +{whatsapp}</a>')
    if email:
        direct.append(f'<a href="mailto:{e(email)}">{icon("mail")}{e(email)}</a>')
    direct.append(f'<a href="{e(contact["youtube"])}" target="_blank" rel="noopener">{icon("yt")}YouTube</a>')
    if btns:
        form_html = f'''  <form id="inviteForm" novalidate data-wa="{whatsapp}" data-mail="{e(email)}">
    <label><span class="lt">Your name <span class="req">required</span></span><input name="name" autocomplete="name" required></label>
    <label><span class="lt">Organisation or event</span><input name="event" autocomplete="organization"></label>
    <div class="two"><label><span class="lt">Date</span><input name="date" type="date"></label><label><span class="lt">Town or city</span><input name="town" autocomplete="address-level2"></label></div>
    <label><span class="lt">Your phone or WhatsApp <span class="req">required</span></span><input name="phone" type="tel" inputmode="tel" autocomplete="tel" required></label>
    <label><span class="lt">Message <span class="opt">optional</span></span><textarea name="msg" rows="3"></textarea></label>
    <p class="err" id="formErr" role="alert" hidden>Please add your name and a phone number so she can reply.</p>
    <div class="send">{"".join(btns)}</div>
    <p class="done" id="formDone" role="status" hidden></p>
  </form>'''
    else:
        form_html = f'<p class="soon">{e(contact.get("coming_soon") or "Contact details will be updated here soon.")}</p>'
    person = f'<p class="person">Enquiries handled by {e(contact["contact_person"])}</p>' if contact.get("contact_person") else ""
    return f'''
<section class="invite" id="invite" aria-labelledby="invite-title"><div class="wrap"><div class="icard">
  <h2 id="invite-title">Invite to perform</h2>
  <p class="si" lang="si">වැඩසටහනකට ආරාධනා කරන්න</p>
  <p>For concerts, musical shows, school and community events, television and media, in Sri Lanka or overseas.</p>
  {form_html}
  {person}
  <div class="direct">{"".join(direct)}</div>
</div></div></section>'''


# ---------------------------------------------------------------- page
CSS = open(os.path.join(ROOT, "tools", "site.css"), encoding="utf-8").read()
JS = open(os.path.join(ROOT, "tools", "site.js"), encoding="utf-8").read()

body = "".join([section_hero(), section_next(), section_highlights(), divider(), section_music(), section_press(), divider(),
                section_about(), divider(), section_performances(), divider(), section_invite()])

person_ld = {"@context": "https://schema.org", "@type": "Person", "name": site["name"], "url": site["url"],
             "jobTitle": "Singer", "homeLocation": {"@type": "Place", "name": site["hometown"]},
             "alumniOf": {"@type": "CollegeOrUniversity", "name": "Kingston University London"},
             "sameAs": [contact["facebook"], contact["youtube"], contact["imdb"]], "image": site["url"] + "assets/share.jpg"}
ld = [person_ld]
for d, c in upcoming():
    if c.get("venue") and c.get("city"):
        ld.append({"@context": "https://schema.org", "@type": "MusicEvent", "name": c["title"], "startDate": d.isoformat(),
                   "eventStatus": "https://schema.org/EventScheduled",
                   "location": {"@type": "Place", "name": c["venue"], "address": {"@type": "PostalAddress", "addressLocality": c["city"], "addressCountry": "LK"}},
                   "performer": {"@type": "Person", "name": site["name"], "url": site["url"]}})

page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(site["name"])} | Singer</title>
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
<header class="bar" id="bar"><div class="wrap">
  <a class="mark" href="#top">Chathurya</a>
  <nav aria-label="Main"><a href="#about" class="hide-xs">About</a><a href="#performances">Performances</a><a href="#invite" class="cta">Invite</a></nav>
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

with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
    f.write(page)
with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
    f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{site["url"]}</loc><lastmod>{TODAY.isoformat()}</lastmod></url></urlset>\n')
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
