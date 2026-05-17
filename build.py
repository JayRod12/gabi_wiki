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
PINNED_FIRST = ["index", "familia_gabilondo"]

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

/* Footnotes — estilo Wikipedia */
.content sup { font-size: 0.75em; line-height: 0; vertical-align: super; }
.content a.footnote-ref { color: #1a73e8; text-decoration: none; }
.content a.footnote-ref::before { content: "["; }
.content a.footnote-ref::after { content: "]"; }
.footnote { font-size: 0.875rem; }
.footnote hr { display: none; }
.footnote ol { margin: 0.4rem 0 0 1.8rem; }
.footnote li { margin-bottom: 0.5rem; color: #444; }
.footnote li p { margin-bottom: 0; display: inline; }
a.footnote-backref { color: #1a73e8; text-decoration: none; font-size: 0.85em; margin-left: 0.3rem; }

/* Mermaid fullscreen */
.mermaid-wrap { position: relative; border: 1px solid #e0e0e0; border-radius: 8px;
  margin: 1rem 0; overflow: hidden; background: #fafafa; }
.mermaid-fs-btn { position: absolute; top: 8px; right: 8px; background: rgba(255,255,255,0.92);
  border: 1px solid #ccc; border-radius: 4px; padding: 4px 10px; font-size: 0.8rem;
  cursor: pointer; color: #333; z-index: 1; }
.mermaid-fs-btn:hover { background: #e8e8e8; }
.mermaid-overlay { position: fixed; inset: 0; z-index: 9999; background: #fff;
  display: flex; flex-direction: column; outline: none; }
.mermaid-toolbar { display: flex; align-items: center; gap: 10px; padding: 8px 16px;
  background: #f6f6f6; border-bottom: 1px solid #e0e0e0; flex-shrink: 0; }
.mermaid-viewport { flex: 1; overflow: hidden; display: flex;
  align-items: center; justify-content: center; }
.mermaid-reset-btn, .mermaid-close-btn { border: none; border-radius: 4px; padding: 5px 12px;
  cursor: pointer; font-size: 0.8rem; }
.mermaid-reset-btn { background: #e5e7eb; color: #374151; }
.mermaid-reset-btn:hover { background: #d1d5db; }
.mermaid-close-btn { background: #dc2626; color: #fff; }
.mermaid-close-btn:hover { background: #b91c1c; }

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
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: false, theme: 'neutral' }});
    document.querySelectorAll('pre code.language-mermaid').forEach(el => {{
      const div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = el.textContent;
      el.parentElement.replaceWith(div);
    }});
    await mermaid.run();

    document.querySelectorAll('.mermaid svg').forEach(svg => {{
      const wrap = document.createElement('div');
      wrap.className = 'mermaid-wrap';
      svg.parentNode.insertBefore(wrap, svg);
      wrap.appendChild(svg);
      const btn = document.createElement('button');
      btn.textContent = '⛶ Pantalla completa';
      btn.className = 'mermaid-fs-btn';
      wrap.appendChild(btn);
      btn.addEventListener('click', () => openFullscreen(svg));
    }});

    function openFullscreen(svg) {{
      const overlay = document.createElement('div');
      overlay.className = 'mermaid-overlay';

      const toolbar = document.createElement('div');
      toolbar.className = 'mermaid-toolbar';
      const hint = document.createElement('span');
      hint.textContent = 'Arrastra para mover · Rueda del ratón para zoom';
      hint.style.cssText = 'font-size:0.8rem;color:#666;flex:1';
      const resetBtn = document.createElement('button');
      resetBtn.textContent = '⟳ Restablecer';
      resetBtn.className = 'mermaid-reset-btn';
      const closeBtn = document.createElement('button');
      closeBtn.textContent = '✕ Cerrar';
      closeBtn.className = 'mermaid-close-btn';
      toolbar.append(hint, resetBtn, closeBtn);

      const viewport = document.createElement('div');
      viewport.className = 'mermaid-viewport';
      viewport.style.cursor = 'grab';
      const clone = svg.cloneNode(true);
      clone.removeAttribute('width');
      clone.removeAttribute('height');
      clone.style.cssText = 'width:auto;height:90%;max-width:none;transform-origin:center;';
      viewport.appendChild(clone);

      overlay.append(toolbar, viewport);
      document.body.appendChild(overlay);
      overlay.tabIndex = 0;
      overlay.focus();

      let tx = 0, ty = 0, scale = 1, dragging = false, sx = 0, sy = 0;
      const apply = () => clone.style.transform = `translate(${{tx}}px,${{ty}}px) scale(${{scale}})`;

      viewport.addEventListener('mousedown', e => {{
        dragging = true; sx = e.clientX - tx; sy = e.clientY - ty;
        viewport.style.cursor = 'grabbing'; e.preventDefault();
      }});
      window.addEventListener('mousemove', e => {{
        if (!dragging) return; tx = e.clientX - sx; ty = e.clientY - sy; apply();
      }});
      window.addEventListener('mouseup', () => {{ dragging = false; viewport.style.cursor = 'grab'; }});
      viewport.addEventListener('wheel', e => {{
        e.preventDefault();
        scale = Math.min(Math.max(scale * (e.deltaY < 0 ? 1.1 : 0.9), 0.1), 8);
        apply();
      }}, {{ passive: false }});

      resetBtn.addEventListener('click', () => {{ tx = 0; ty = 0; scale = 1; apply(); }});
      closeBtn.addEventListener('click', () => overlay.remove());
      overlay.addEventListener('keydown', e => {{ if (e.key === 'Escape') overlay.remove(); }});
    }}
  </script>
</body>
</html>
"""

NAV_LABELS = {
    "index": "Página Principal",
    "familia_gabilondo": "Árbol Familiar",
    "leto_gabilondo": "Leto Gabilondo",
    "elvira_manso": "Elvira Manso",
    "carmen_gabilondo": "Carmen Gabilondo",
    "cesar_rodriguez_gabilondo": "César Rodríguez Gabilondo",
    "calle_gabilondo": "Calle de Gabilondo",
    "talleres_gabilondo": "Talleres Gabilondo",
    "log": "Registro",
}

# Maps each slug to its sidebar section
SLUG_SECTION = {
    "agustin_gabilondo":        "Personas",
    "leto_gabilondo":           "Personas",
    "elvira_manso":             "Personas",
    "fernando_gabilondo":       "Personas",
    "ignacio_gabilondo":        "Personas",
    "ubaldo_manso":             "Personas",
    "manuel_amoategui":         "Personas",
    "cesar_gabilondo":          "Personas",
    "carmen_gabilondo":         "Personas",
    "cesar_rodriguez_gabilondo":"Personas",
    "talleres_gabilondo":       "Lugares y negocios",
    "calle_gabilondo":          "Lugares y negocios",
    "log":                      "Meta",
}

SECTION_ORDER = ["Personas", "Lugares y negocios", "Meta"]


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
    from collections import defaultdict
    first = [s for s in PINNED_FIRST if s in slugs]
    rest = [s for s in slugs if s not in PINNED_FIRST]

    by_section = defaultdict(list)
    for slug in sorted(rest):
        by_section[SLUG_SECTION.get(slug, "")].append(slug)

    result = first[:]
    for section in SECTION_ORDER:
        result.extend(by_section[section])
    result.extend(by_section[""])
    return result


def build_nav(ordered_slugs: list, active_slug: str) -> str:
    items = []
    current_section = None
    for slug in ordered_slugs:
        section = SLUG_SECTION.get(slug)
        if section and section != current_section:
            items.append(f'<li><div class="sidebar-section">{section}</div></li>')
            current_section = section
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
            extensions=["tables", "fenced_code", "nl2br", "footnotes"],
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
