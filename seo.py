#!/usr/bin/env python3
"""SEO pass for divijrakhra.com. Run after any page is built or edited:

    python3 seo.py

It is idempotent. For every page it writes one block between <!-- seo:start --> and
<!-- seo:end --> in <head>: a canonical tag (only if the page has none of its own) and
JSON-LD (Person on the homepage, BlogPosting on posts). It also regenerates sitemap.xml,
robots.txt and llms.txt. Dates come from git: first commit = published, last = modified.

The Zero-DR post must stay unlinked from Bricx, so its block is checked for the name.
"""
import html, json, re, subprocess
from pathlib import Path

ROOT = Path(__file__).parent
SITE = "https://divijrakhra.com"
PERSON = {
    "@type": "Person", "@id": SITE + "/#person", "name": "Divij Rakhra", "url": SITE + "/",
    "image": SITE + "/avatar.jpg",
    "description": "Runs growth experiments in AI search, demand gen and launches, and publishes every number.",
    "sameAs": ["https://linkedin.com/in/divijrakhra", "https://x.com/RakhraDivij"],
    "knowsAbout": ["AI search", "Answer engine optimization", "Demand generation", "B2B SaaS marketing", "AI agents for marketing"],
}
START, END = "<!-- seo:start -->", "<!-- seo:end -->"


def git_date(path, first):
    args = ["git", "log", "--format=%cI", "--", str(path.relative_to(ROOT))]
    if first:
        args.insert(2, "--diff-filter=A")
    out = subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.split()
    return (out[-1] if first else out[0]) if out else None


def meta(h, prop):
    m = re.search(r'<meta (?:property|name)="%s" content="([^"]*)"' % re.escape(prop), h)
    return html.unescape(m.group(1)) if m else None


def pages():
    yield ROOT / "index.html", SITE + "/"
    for p in sorted((ROOT / "blog").glob("*/index.html")):
        yield p, f"{SITE}/blog/{p.parent.name}/"


def block(h, url, path):
    h_wo = re.sub(re.escape(START) + ".*?" + re.escape(END), "", h, flags=re.S)
    parts = []
    if 'rel="canonical"' not in h_wo:
        parts.append(f'<link rel="canonical" href="{url}">')
    if url == SITE + "/":
        data = {"@context": "https://schema.org", "@graph": [
            PERSON,
            {"@type": "WebSite", "@id": SITE + "/#website", "url": SITE + "/", "name": "Divij Rakhra",
             "author": {"@id": PERSON["@id"]}, "inLanguage": "en"},
        ]}
    else:
        title = (meta(h, "og:title") or "").replace(" · Divij Rakhra", "")
        data = {"@context": "https://schema.org", "@type": "BlogPosting", "@id": url + "#post",
                "headline": title[:110], "description": meta(h, "og:description") or meta(h, "description"),
                "image": meta(h, "og:image"), "url": url, "mainEntityOfPage": url, "inLanguage": "en",
                "datePublished": git_date(path, True), "dateModified": git_date(path, False),
                "author": {"@type": "Person", "@id": PERSON["@id"], "name": PERSON["name"], "url": PERSON["url"],
                           "sameAs": PERSON["sameAs"]},
                "publisher": {"@type": "Person", "@id": PERSON["@id"], "name": PERSON["name"]}}
        data = {k: v for k, v in data.items() if v}
    parts.append('<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    return h_wo, START + "\n" + "\n".join(parts) + "\n" + END + "\n"


def main():
    rows = []
    for path, url in pages():
        h = path.read_text(encoding="utf-8")
        h_wo, blk = block(h, url, path)
        new = h_wo.replace("</head>", blk + "</head>", 1)
        if "zero-dr" in str(path):  # this post must never be tied to Bricx
            assert "bricx" not in blk.lower(), f"Bricx leaked into SEO block of {path}"
        if new != h:
            path.write_text(new, encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", h, re.S)
        rows.append((url, (git_date(path, False) or "")[:10], html.unescape(title.group(1)).strip() if title else url,
                     meta(h, "description") or ""))

    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sm += [f"  <url><loc>{u}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>" for u, d, _, _ in rows]
    (ROOT / "sitemap.xml").write_text("\n".join(sm + ["</urlset>", ""]), encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    llms = ["# Divij Rakhra", "", "> " + PERSON["description"], "",
            "Every post is a real experiment with the numbers published. Profiles: "
            + ", ".join(PERSON["sameAs"]) + ".", "", "## Experiments", ""]
    llms += [f"- [{t.replace(' · Divij Rakhra', '')}]({u}): {d}" for u, _, t, d in rows[1:]]
    (ROOT / "llms.txt").write_text("\n".join(llms) + "\n", encoding="utf-8")
    print(f"SEO pass done: {len(rows)} pages, sitemap.xml, robots.txt, llms.txt")


if __name__ == "__main__":
    main()
