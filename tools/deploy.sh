#!/bin/sh
# Publish ONLY the built website to gh-pages (no content JSON, notes, tools or private files).
set -e
cd "$(dirname "$0")/.."
python3 tools/build.py
rm -rf dist && mkdir dist
cp index.html education.html robots.txt sitemap.xml CNAME .nojekyll dist/
cp -r assets dist/
for f in $(grep -ohE 'content/[^"'"'"' )]+\.(webp|jpg|png|mp4)' index.html education.html | sort -u); do
  mkdir -p "dist/$(dirname "$f")"; cp "$f" "dist/$f"; done
cd dist && git init -q && git checkout -q -b gh-pages && git add -A
git -c user.name="Chathurya site" -c user.email="noreply@caeleon.net" commit -q -m "Publish built site"
git push -q -f "$(cd .. && git remote get-url origin)" gh-pages
echo "published $(git ls-files | wc -l) files"
