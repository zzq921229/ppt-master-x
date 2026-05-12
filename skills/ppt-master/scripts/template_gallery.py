#!/usr/bin/env python3
"""Generate a local HTML gallery for built-in layout templates.

Usage:
    python3 scripts/template_gallery.py [filter_keyword]

Each template is presented as a slide deck viewer — browse pages inline
without leaving the gallery. Click thumbnails to switch pages; use arrow
buttons to navigate. Zero external dependencies.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import webbrowser
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TOOLS_DIR.parent
LAYOUTS_DIR = SKILL_DIR / "templates" / "layouts"
INDEX_PATH = LAYOUTS_DIR / "layouts_index.json"

SVG_LABELS: dict[str, str] = {
    "01_cover": "Cover",
    "02_toc": "TOC",
    "02_chapter": "Chapter",
    "03_content": "Content",
    "04_ending": "Ending",
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PPT Master - Template Gallery</title>
<style>
  :root {{
    --bg: #f0f2f5;
    --card-bg: #ffffff;
    --text: #1a1a1a;
    --muted: #666666;
    --border: #d0d7de;
    --accent: #1565c0;
    --radius: 12px;
    --shadow: 0 2px 8px rgba(0,0,0,0.06);
    --shadow-hover: 0 8px 28px rgba(0,0,0,0.12);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--text); padding: 32px 24px;
  }}
  h1 {{ font-size: 28px; margin-bottom: 6px; }}
  .subtitle {{ color: var(--muted); margin-bottom: 24px; }}
  .controls {{
    display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
    margin-bottom: 28px;
  }}
  .controls input {{
    padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px;
    font-size: 14px; min-width: 280px;
  }}
  .controls .count {{ color: var(--muted); font-size: 14px; margin-left: auto; }}

  /* Template card */
  .template {{
    background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius);
    margin-bottom: 28px; overflow: hidden;
    box-shadow: var(--shadow); transition: box-shadow .2s;
  }}
  .template:hover {{ box-shadow: var(--shadow-hover); }}
  .template-header {{
    padding: 18px 20px 14px; border-bottom: 1px solid var(--border);
    display: flex; align-items: flex-start; gap: 14px;
  }}
  .swatch {{
    width: 28px; height: 28px; border-radius: 6px; flex-shrink: 0;
    border: 1px solid rgba(0,0,0,0.08);
  }}
  .template-title {{ font-weight: 600; font-size: 17px; }}
  .template-meta {{ font-size: 13px; color: var(--muted); margin-top: 3px; }}
  .keywords {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
  .keyword {{
    font-size: 12px; padding: 3px 10px; border-radius: 999px;
    background: #eef2f7; color: var(--muted);
  }}

  /* Slide viewer */
  .viewer {{ padding: 20px; }}
  .stage-wrap {{
    position: relative; width: 100%; max-width: 960px; margin: 0 auto;
    background: #000; border-radius: 8px; overflow: hidden;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  }}
  .stage {{
    position: relative; width: 100%; padding-top: 56.25%; /* 16:9 */
  }}
  .slide-layer {{
    position: absolute; inset: 0; opacity: 0; transition: opacity .35s ease;
    display: flex; align-items: center; justify-content: center;
    background: #fff;
  }}
  .slide-layer.active {{ opacity: 1; z-index: 2; }}
  .slide-layer svg {{
    width: 100%; height: 100%; display: block;
  }}

  /* Arrows */
  .arrow {{
    position: absolute; top: 50%; transform: translateY(-50%);
    width: 40px; height: 40px; border-radius: 50%;
    background: rgba(255,255,255,0.9); border: none;
    cursor: pointer; z-index: 10; display: flex; align-items: center; justify-content: center;
    font-size: 18px; color: #333; box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    transition: background .15s;
  }}
  .arrow:hover {{ background: #fff; }}
  .arrow.prev {{ left: 12px; }}
  .arrow.next {{ right: 12px; }}
  .arrow:disabled {{ opacity: .35; cursor: default; }}

  /* Page counter */
  .page-counter {{
    position: absolute; bottom: 10px; right: 14px;
    background: rgba(0,0,0,0.6); color: #fff;
    font-size: 12px; padding: 4px 10px; border-radius: 4px;
    z-index: 10; pointer-events: none;
  }}

  /* Thumbnail strip */
  .strip {{
    display: flex; gap: 10px; margin-top: 14px;
    overflow-x: auto; padding-bottom: 4px;
    justify-content: center;
  }}
  .strip-item {{
    flex: 0 0 auto; width: 120px; cursor: pointer;
    border: 2px solid transparent; border-radius: 6px;
    overflow: hidden; background: #f6f8fa;
    transition: border-color .2s, transform .15s;
  }}
  .strip-item:hover {{ transform: translateY(-2px); }}
  .strip-item.active {{ border-color: var(--accent); }}
  .strip-thumb {{
    height: 68px; display: flex; align-items: center; justify-content: center;
    padding: 4px;
  }}
  .strip-thumb svg {{ max-width: 100%; max-height: 100%; width: auto; height: auto; }}
  .strip-label {{
    font-size: 11px; text-align: center; padding: 4px 6px;
    color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    background: #fff; border-top: 1px solid var(--border);
  }}

  @media (max-width: 720px) {{
    .stage-wrap {{ max-width: 100%; }}
    .strip-item {{ width: 90px; }}
    .strip-thumb {{ height: 52px; }}
  }}
</style>
</head>
<body>
<h1>PPT Master Template Gallery</h1>
<div class="subtitle">Browse each template like a slide deck — click thumbnails or use arrows to switch pages</div>
<div class="controls">
  <input type="text" id="search" placeholder="Filter by name, keyword, or description..." value="{filter_value}">
  <span class="count">Showing <span id="visible">{count}</span> / {count} templates</span>
</div>
<div id="gallery">
{cards}
</div>

<script>
(function() {{
  const galleries = document.querySelectorAll('.template');
  galleries.forEach(card => {{
    const tid = card.dataset.id;
    const layers = card.querySelectorAll('.slide-layer');
    const thumbs = card.querySelectorAll('.strip-item');
    const prevBtn = card.querySelector('.arrow.prev');
    const nextBtn = card.querySelector('.arrow.next');
    const counter = card.querySelector('.page-counter');
    let idx = 0;
    const total = layers.length;

    function show(i) {{
      if (i < 0) i = 0;
      if (i >= total) i = total - 1;
      idx = i;
      layers.forEach((el, n) => el.classList.toggle('active', n === idx));
      thumbs.forEach((el, n) => el.classList.toggle('active', n === idx));
      if (prevBtn) prevBtn.disabled = idx === 0;
      if (nextBtn) nextBtn.disabled = idx === total - 1;
      if (counter) counter.textContent = (idx + 1) + ' / ' + total;
      // scroll active thumb into view
      const activeThumb = thumbs[idx];
      if (activeThumb) activeThumb.scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
    }}

    if (prevBtn) prevBtn.addEventListener('click', () => show(idx - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => show(idx + 1));
    thumbs.forEach((t, n) => t.addEventListener('click', () => show(n)));
    show(0);
  }});

  const search = document.getElementById('search');
  const visible = document.getElementById('visible');
  function update() {{
    const q = search.value.trim().toLowerCase();
    let n = 0;
    galleries.forEach(c => {{
      const text = c.dataset.search || '';
      const show = !q || text.includes(q);
      c.style.display = show ? '' : 'none';
      if (show) n++;
    }});
    visible.textContent = n;
  }}
  search.addEventListener('input', update);
  update();
}})();
</script>
</body>
</html>
"""


def _hex_color_from_text(text: str) -> str | None:
    match = re.search(r"#(?:[0-9a-fA-F]{3}){1,2}\b", text)
    return match.group(0).upper() if match else None


def _read_design_spec_colors(spec_path: Path) -> dict[str, str]:
    colors: dict[str, str] = {}
    if not spec_path.exists():
        return colors
    try:
        text = spec_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return colors
    for key in ("primary", "accent", "primary_color", "theme_color"):
        m = re.search(rf"{key}\s*[:=]\s*['\"]?(#[0-9a-fA-F]{{3,6}})['\"]?", text, re.I)
        if m:
            colors[key] = m.group(1).upper()
    if not colors:
        first = _hex_color_from_text(text)
        if first:
            colors["primary"] = first
    return colors


def _read_svg_safe(svg_path: Path) -> str:
    if not svg_path.exists():
        return ""
    try:
        text = svg_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    text = re.sub(r"<\?xml[^?]*\?>", "", text)
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, flags=re.I)
    return text.strip()


def _svg_label(name: str) -> str:
    stem = name.replace(".svg", "")
    return SVG_LABELS.get(stem, stem.replace("_", " ").replace("-", " ").title())


def _build_card(template_id: str, meta: dict, svg_items: list[tuple[str, str]], primary_color: str | None) -> str:
    label = meta.get("label", template_id)
    summary = meta.get("summary", "")
    keywords = meta.get("keywords", [])
    kw_html = "".join(f'<span class="keyword">{k}</span>' for k in keywords)
    swatch = (
        f'<div class="swatch" style="background:{primary_color}"></div>'
        if primary_color else '<div class="swatch" style="background:#ccc"></div>'
    )

    # Build slides
    layers_html = ""
    thumbs_html = ""
    for i, (lbl, svg_inline) in enumerate(svg_items):
        active_cls = " active" if i == 0 else ""
        layers_html += f'<div class="slide-layer{active_cls}">{svg_inline}</div>\n'
        thumbs_html += f"""<div class="strip-item{active_cls}">
  <div class="strip-thumb">{svg_inline}</div>
  <div class="strip-label">{lbl}</div>
</div>"""

    search_text = " ".join([template_id, label, summary, " ".join(keywords)]).lower()

    return f"""<div class="template" data-id="{template_id}" data-search="{search_text}">
  <div class="template-header">
    {swatch}
    <div>
      <div class="template-title">{label}</div>
      <div class="template-meta">{template_id} &middot; {summary}</div>
      <div class="keywords">{kw_html}</div>
    </div>
  </div>
  <div class="viewer">
    <div class="stage-wrap">
      <div class="stage">{layers_html}</div>
      <button class="arrow prev">&#10094;</button>
      <button class="arrow next">&#10095;</button>
      <div class="page-counter">1 / {len(svg_items)}</div>
    </div>
    <div class="strip">{thumbs_html}</div>
  </div>
</div>"""


def generate_gallery(filter_keyword: str | None = None) -> Path:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Template index not found: {INDEX_PATH}")

    with INDEX_PATH.open("r", encoding="utf-8") as f:
        index: dict[str, dict] = json.load(f)

    cards: list[str] = []
    for tid in sorted(index.keys()):
        meta = index[tid]
        template_dir = LAYOUTS_DIR / tid
        if not template_dir.is_dir():
            continue

        search_blob = " ".join(
            [tid, meta.get("label", ""), meta.get("summary", ""), " ".join(meta.get("keywords", []))]
        ).lower()
        if filter_keyword and filter_keyword.lower() not in search_blob:
            continue

        colors = _read_design_spec_colors(template_dir / "design_spec.md")
        primary = colors.get("primary") or colors.get("theme_color") or colors.get("accent")

        svg_files = sorted(
            [p for p in template_dir.iterdir() if p.suffix.lower() == ".svg"],
            key=lambda p: p.name,
        )

        svg_items: list[tuple[str, str]] = []
        for svg_path in svg_files:
            inline = _read_svg_safe(svg_path)
            if not inline:
                continue
            lbl = _svg_label(svg_path.name)
            svg_items.append((lbl, inline))

        if not svg_items:
            continue

        cards.append(_build_card(tid, meta, svg_items, primary))

    html = HTML_TEMPLATE.format(
        cards="\n".join(cards),
        count=len(cards),
        filter_value=(filter_keyword or "").replace('"', '&quot;'),
    )

    fd, tmp_path = tempfile.mkstemp(prefix="ppt_master_gallery_", suffix=".html")
    with open(fd, "w", encoding="utf-8") as f:
        f.write(html)
    return Path(tmp_path)


def open_gallery(filter_keyword: str | None = None) -> Path:
    path = generate_gallery(filter_keyword=filter_keyword)
    url = path.as_uri()
    webbrowser.open(url, new=2)
    return path


def main(argv: list[str] | None = None) -> None:
    args = argv or sys.argv[1:]
    keyword = args[0] if args else None
    path = open_gallery(filter_keyword=keyword)
    print(f"Gallery opened in browser: {path}")
    if keyword:
        print(f"Filter keyword: {keyword}")


if __name__ == "__main__":
    main()
