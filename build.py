#!/usr/bin/env python3
"""Build wiki: converts wiki/*.md → docs/*.html"""
import re
import shutil
import sys
import markdown
from pathlib import Path

WIKI_DIR = Path("wiki")
DOCS_DIR = Path("docs")

# Pages always shown first/last in sidebar regardless of alpha sort
PINNED_FIRST = ["index"]
PINNED_LAST = ["log"]

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       font-size: 16px; line-height: 1.65; color: #222; background: #fff; }

.layout { display: flex; min-height: 100vh; }

/* Sidebar */
.sidebar {
  width: 240px; min-width: 240px; background: #f6f6f6; border-right: 1px solid #e0e0e0;
  padding: 1.5rem 1rem; position: sticky; top: 0; height: 100vh; overflow-y: auto;
}
.site-title { margin-bottom: 1.2rem; }
.site-title a {
  font-size: 1rem; font-weight: 700; color: #1a1a1a; text-decoration: none;
  line-height: 1.3;
}
.site-title a:hover { color: #1a73e8; }
.sidebar ul { list-style: none; }
.sidebar li { margin-bottom: 0.15rem; }
.sidebar li a {
  display: block; padding: 0.3rem 0.5rem; border-radius: 4px;
  color: #444; text-decoration: none; font-size: 0.875rem;
}
.sidebar li a:hover { background: #e8e8e8; color: #1a1a1a; }
.sidebar li.active a { background: #1a73e8; color: #fff; font-weight: 600; }
.sidebar-section {
  font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
  color: #888; margin: 1rem 0.5rem 0.3rem;
}

/* Content */
.content {
  flex: 1; padding: 2.5rem 3rem; max-width: 820px;
}
.content h1 { font-size: 1.9rem; font-weight: 700; margin-bottom: 1.2rem;
               border-bottom: 2px solid #e0e0e0; padding-bottom: 0.5rem; color: #1a1a1a; }
.content h2 { font-size: 1.25rem; font-weight: 600; margin: 2rem 0 0.6rem; color: #1a1a1a; }
.content h3 { font-size: 1.05rem; font-weight: 600; margin: 1.4rem 0 0.4rem; color: #333; }
.content p { margin-bottom: 0.9rem; }
.content a { color: #1a73e8; text-decoration: none; }
.content a:hover { text-decoration: underline; }
.content ul, .content ol { margin: 0.5rem 0 0.9rem 1.5rem; }
.content li { margin-bottom: 0.25rem; }
.content blockquote {
  border-left: 3px solid #ccc; margin: 1rem 0; padding: 0.5rem 1rem;
  color: #555; background: #f9f9f9; border-radius: 0 4px 4px 0; font-style: italic;
}
.content table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
.content th { background: #f0f0f0; font-weight: 600; }
.content th, .content td { border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }
.content tr:nth-child(even) td { background: #fafafa; }
.content code { background: #f0f0f0; padding: 0.1em 0.3em; border-radius: 3px;
                font-size: 0.875em; font-family: "SF Mono", Consolas, monospace; }
.content pre { background: #f0f0f0; padding: 1rem; border-radius: 6px; overflow-x: auto;
               margin: 1rem 0; }
.content pre code { background: none; padding: 0; }
.content hr { border: none; border-top: 1px solid #e0e0e0; margin: 1.5rem 0; }

/* Responsive */
@media (max-width: 700px) {
  .layout { flex-direction: column; }
  .sidebar { width: 100%; min-width: unset; height: auto; position: static;
             border-right: none; border-bottom: 1px solid #e0e0e0; padding: 1rem; }
  .content { padding: 1.5rem 1.2rem; }
}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Wiki Gabilondo</title>
  <style>{css}</style>
</head>
<body>
  <div class="layout">
    <nav class="sidebar">
      <div class="site-title"><a href="index.html">🏛 Wiki Gabilondo</a></div>
      <ul>{nav}</ul>
    </nav>
    <main class="content">
      {body}
    </main>
  </div>
</body>
</html>
"""

NAV_LABELS = {
    "index": "Página Principal",
    "familia_gabilondo": "Árbol Familiar",
    "leto_gabilondo": "Leto Gabilondo",
    "elvira_gabilondo": "Elvira Gabilondo",
    "carmen_gabilondo": "Carmen Gabilondo",
    "cesar_rodriguez_gabilondo": "César Rodríguez Gabilondo",
    "calle_gabilondo": "Calle de Gabilondo",
    "talleres_gabilondo": "Talleres Gabilondo",
    "log": "Registro",
}

NAV_SECTIONS = {
    "familia_gabilondo": "Familia",
    "leto_gabilondo": "Personas",
    "calle_gabilondo": "Lugares",
    "log": "Meta",
}


def get_title(md_text: str, slug: str) -> str:
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return slug.replace("_", " ").title()


def rewrite_md_links(text: str) -> str:
    return re.sub(r'\[([^\]]+)\]\(([^)#\s]+)\.md([^)]*)\)',
                  lambda m: f'[{m.group(1)}]({m.group(2)}.html{m.group(3)})',
                  text)


def sort_pages(slugs):
    first = [s for s in PINNED_FIRST if s in slugs]
    last = [s for s in PINNED_LAST if s in slugs]
    middle = sorted(s for s in slugs if s not in PINNED_FIRST and s not in PINNED_LAST)
    return first + middle + last


def build_nav(ordered_slugs: list, active_slug: str) -> str:
    items = []
    seen_sections = set()
    for slug in ordered_slugs:
        section = NAV_SECTIONS.get(slug)
        if section and section not in seen_sections:
            items.append(f'<li><div class="sidebar-section">{section}</div></li>')
            seen_sections.add(section)
        label = NAV_LABELS.get(slug, slug.replace("_", " ").title())
        active = ' class="active"' if slug == active_slug else ''
        items.append(f'<li{active}><a href="{slug}.html">{label}</a></li>')
    return "\n".join(items)


def build():
    DOCS_DIR.mkdir(exist_ok=True)

    pages = list(WIKI_DIR.glob("*.md"))
    if not pages:
        print("No markdown files found in wiki/")
        sys.exit(1)

    slugs = sort_pages([p.stem for p in pages])
    slug_to_path = {p.stem: p for p in pages}

    for slug in slugs:
        path = slug_to_path[slug]
        md_text = path.read_text(encoding="utf-8")
        title = get_title(md_text, slug)
        md_text = rewrite_md_links(md_text)

        body_html = markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code", "nl2br"],
        )

        nav_html = build_nav(slugs, slug)
        html = TEMPLATE.format(title=title, css=CSS, nav=nav_html, body=body_html)
        out_path = DOCS_DIR / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  {path.name} → {out_path.name}")

    # Copy assets
    assets_src = WIKI_DIR / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, DOCS_DIR / "assets", dirs_exist_ok=True)

    print(f"\nBuilt {len(slugs)} pages → {DOCS_DIR}/")


if __name__ == "__main__":
    build()
