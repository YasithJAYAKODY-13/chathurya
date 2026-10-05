"""Original illustrations and medallions for the education page (no third-party images)."""
import math

CAPSULE = 'M0 -22 C 10 -22 26 -14 30 0 C 26 14 10 22 0 22 C -6 12 -6 -12 0 -22 Z'


def _stars(n, w, h, seed):
    out = []
    x = seed
    for i in range(n):
        x = (x * 9301 + 49297) % 233280
        px = x / 233280 * w
        x = (x * 9301 + 49297) % 233280
        py = x / 233280 * h
        r = 0.6 + (i % 3) * 0.35
        out.append(f'<circle class="tw" style="animation-delay:{(i % 7) * 0.4:.1f}s" cx="{px:.1f}" cy="{py:.1f}" r="{r:.2f}"/>')
    return "".join(out)


ORBIT = f'''<svg viewBox="0 0 320 210" class="art" aria-hidden="true">
<defs><radialGradient id="earth" cx="50%" cy="20%" r="70%"><stop offset="0" stop-color="#1F5A47"/><stop offset=".6" stop-color="#0E3328"/><stop offset="1" stop-color="#06140F"/></radialGradient>
<linearGradient id="atm" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#ECCF85" stop-opacity=".55"/><stop offset="1" stop-color="#ECCF85" stop-opacity="0"/></linearGradient></defs>
<g fill="#FFF3CC">{_stars(34, 320, 120, 7)}</g>
<circle cx="160" cy="420" r="260" fill="url(#earth)"/>
<circle cx="160" cy="420" r="266" fill="none" stroke="url(#atm)" stroke-width="10" opacity=".7"/>
<path id="orb" d="M -20 140 Q 160 20 340 140" fill="none" stroke="#D4A53A" stroke-opacity=".55" stroke-dasharray="3 6"/>
<g><path d="{CAPSULE}" transform="scale(.6) rotate(180)" fill="#ECCF85"/><animateMotion class="smil" dur="9s" repeatCount="indefinite" rotate="auto"><mpath href="#orb"/></animateMotion></g>
</svg>'''

FIREBALL = f'''<svg viewBox="0 0 320 210" class="art" aria-hidden="true">
<defs><radialGradient id="plasma" cx="35%" cy="50%" r="60%"><stop offset="0" stop-color="#FFF8E1"/><stop offset=".25" stop-color="#FFD27A"/><stop offset=".55" stop-color="#F08A2E" stop-opacity=".75"/><stop offset="1" stop-color="#B8321A" stop-opacity="0"/></radialGradient>
<linearGradient id="trail2" gradientUnits="userSpaceOnUse" x1="30" x2="230" y1="0" y2="0"><stop offset="0" stop-color="#F08A2E" stop-opacity=".9"/><stop offset="1" stop-color="#F08A2E" stop-opacity="0"/></linearGradient></defs>
<g transform="translate(130 112) rotate(-28)">
  <g class="streaks" stroke="url(#trail2)" stroke-linecap="round">
    <path d="M30 -10 H 230" stroke-width="3"/><path d="M28 8 H 200" stroke-width="2"/><path d="M24 -26 H 170" stroke-width="1.5"/><path d="M24 24 H 180" stroke-width="1.5"/></g>
  <ellipse class="glow" cx="-6" cy="0" rx="58" ry="46" fill="url(#plasma)"/>
  <path class="shock" d="M-40 -64 Q -78 0 -40 64" fill="none" stroke="#FFF3CC" stroke-opacity=".7" stroke-width="2"/>
  <path d="{CAPSULE}" fill="#2B2520" stroke="#ECCF85" stroke-width="1.2"/>
  <path d="M0 -22 C -6 -12 -6 12 0 22" fill="none" stroke="#FFF3CC" stroke-width="4"/>
</g></svg>'''

HEAT = '''<svg viewBox="0 0 320 210" class="art" aria-hidden="true">
<defs><linearGradient id="hs" x1="0" x2="1"><stop offset="0" stop-color="#FFF8E1"/><stop offset=".18" stop-color="#FFD27A"/><stop offset=".42" stop-color="#F08A2E"/><stop offset=".7" stop-color="#8E2A17"/><stop offset="1" stop-color="#1E1612"/></linearGradient>
<linearGradient id="therm" x1="0" x2="0" y1="1" y2="0"><stop offset="0" stop-color="#ECCF85"/><stop offset=".6" stop-color="#F08A2E"/><stop offset="1" stop-color="#FFF8E1"/></linearGradient>
<clipPath id="tclip"><rect x="262" y="34" width="14" height="140" rx="7"/></clipPath></defs>
<path d="M60 30 C 30 70 30 140 60 180 L 210 150 L 210 60 Z" fill="url(#hs)"/>
<path d="M60 30 C 30 70 30 140 60 180" fill="none" stroke="#FFF8E1" stroke-width="3"/>
<g stroke="#06140F" stroke-opacity=".35"><path d="M95 26 L 95 184"/><path d="M130 33 L 130 170"/><path d="M165 42 L 165 160"/></g>
<text x="70" y="200" class="artlbl">hot side</text><text x="170" y="200" class="artlbl">inside</text>
<rect x="262" y="34" width="14" height="140" rx="7" fill="none" stroke="#ECCF85" stroke-opacity=".6"/>
<g clip-path="url(#tclip)"><rect class="mercury" x="262" y="34" width="14" height="140" fill="url(#therm)"/></g>
<circle cx="269" cy="182" r="11" fill="#F08A2E" stroke="#ECCF85" stroke-opacity=".6"/>
<text x="262" y="24" text-anchor="middle" class="artbig">1,500°C+</text>
</svg>'''


def _mesh():
    cells = []
    cx, cy = 120, 105
    for ring in range(1, 5):
        r0, r1 = (ring - 1) * 18, ring * 18
        n = 6 + ring * 3
        for k in range(n):
            a0 = math.pi / 2 + k * math.pi / n
            a1 = math.pi / 2 + (k + 1) * math.pi / n
            pts = [(cx + r0 * math.cos(a0), cy - r0 * math.sin(a0)), (cx + r1 * math.cos(a0), cy - r1 * math.sin(a0)),
                   (cx + r1 * math.cos(a1), cy - r1 * math.sin(a1)), (cx + r0 * math.cos(a1), cy - r0 * math.sin(a1))]
            nose = 1 - abs(((a0 + a1) / 2) - math.pi) / (math.pi / 2)
            t = max(0.0, min(1.0, 0.25 + 0.75 * nose * (ring / 4)))
            col = (int(30 + t * 210), int(40 + t * 120), int(30 + t * 10))
            d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
            cells.append(f'<path d="{d}" fill="rgb{col}" fill-opacity=".85"/>')
    return "".join(cells)


SIM = f'''<svg viewBox="0 0 320 210" class="art" aria-hidden="true">
<g class="flow" fill="none" stroke="#ECCF85" stroke-opacity=".7" stroke-width="1.3" stroke-dasharray="6 10">
  <path d="M0 30 C 80 30 90 22 140 20 S 260 40 320 40"/><path d="M0 55 C 60 55 80 36 120 32 S 250 58 320 64"/>
  <path d="M0 80 C 50 80 70 58 100 48 S 250 80 320 88"/>
  <path d="M0 130 C 50 130 70 152 100 162 S 250 130 320 122"/><path d="M0 155 C 60 155 80 174 120 178 S 250 152 320 146"/>
  <path d="M0 180 C 80 180 90 188 140 190 S 260 170 320 170"/></g>
<g stroke="#06140F" stroke-opacity=".55" stroke-width=".6">{_mesh()}</g>
<path d="M120 33 A 72 72 0 0 0 120 177" fill="none" stroke="#FFF8E1" stroke-width="2.5"/>
<text x="304" y="106" text-anchor="end" class="artlbl">airflow (CFD)</text><text x="84" y="204" text-anchor="middle" class="artlbl">heat (FEA)</text>
</svg>'''

JOURNEY = [
    ("Step 1", "In orbit", "A spacecraft circles Earth at about 28,000 km/h.", ORBIT),
    ("Step 2", "Hitting the air", "Coming home, it slams into the atmosphere at around 25 times the speed of sound. The air in front glows.", FIREBALL),
    ("Step 3", "Over 1,500°C", "The heat shield faces temperatures hotter than molten lava, while the inside must stay safe.", HEAT),
    ("Step 4", "Her work", "Chathurya simulates the airflow (CFD) and the heat moving through the structure (FEA) to find materials that survive.", SIM),
]


def journey_html(e):
    cards = "".join(
        f'<li class="jstep"><div class="jart">{art}</div><span class="jn">{e(n)}</span><h3>{e(t)}</h3><p>{e(d)}</p></li>'
        for n, t, d, art in JOURNEY)
    return f'<ol class="journey">{cards}</ol>'


def medal(i, icon_svg, big, ring, label, sub, e):
    pid = f"ring{i}"
    ticks = "".join(
        f'<line x1="100" y1="{6 if k % 5 == 0 else 9}" x2="100" y2="14" transform="rotate({k * 6} 100 100)"/>' for k in range(60))
    return f'''<div class="medal"><div class="coin"><div class="coin-face">
<svg class="coin-ring" viewBox="0 0 200 200" aria-hidden="true"><defs><path id="{pid}" d="M100,100 m-74,0 a74,74 0 1,1 148,0 a74,74 0 1,1 -148,0"/></defs>
<g stroke="#ECCF85" stroke-opacity=".7" stroke-width="1">{ticks}</g>
<circle cx="100" cy="100" r="62" fill="none" stroke="#ECCF85" stroke-opacity=".5"/>
<text class="ringtxt"><textPath href="#{pid}" textLength="460" lengthAdjust="spacing">{e(ring)}</textPath></text></svg>
<span class="coin-mid">{icon_svg}<b{' class="long"' if len(big) > 7 and ' ' not in big else ""}>{e(big)}</b></span></div></div>
<strong>{e(label)}</strong><span>{e(sub)}</span></div>'''
