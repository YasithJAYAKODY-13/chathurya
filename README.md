# Chathurya Sandabarana

Official website: https://chathurya.caeleon.net (GitHub Pages, served from the `gh-pages` branch).

## How it is organised

- `content/` holds everything shown on the site, one folder per section (see `content/README.md`).
- `content/site.json` holds the site-wide settings: tagline, highlights, featured videos and contact details (email, WhatsApp, contact person).
- `tools/build.py` builds `index.html` from `content/`, makes phone-sized image versions in `assets/img/`, and writes `sitemap.xml` and `robots.txt`. It only publishes known fields, so internal notes in the JSON never appear on the site.
- `tools/site.css` and `tools/site.js` are the page's styling and behaviour.

## Updating

1. Add or edit items in `content/<folder>/items.json` and put photos in that folder's `images/`.
2. Run `python3 tools/build.py`. It reports any unused or missing media.
3. Commit and push `main` (source only), then run `tools/deploy.sh`, which publishes just the built pages and media to `gh-pages`. Private settings (phone keys, endpoint) live in `content/private.json`, which is never committed.
