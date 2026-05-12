#!/usr/bin/env python3
"""Generate a local HTML gallery for built-in layout templates.

Usage:
    python3 scripts/template_gallery.py [filter_keyword]

The gallery embeds SVG previews directly in the browser (zero external dependencies).
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

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PPT Master - Template Gallery</title>
<style>
  :root {{
    --bg: #f5f7fa;
    --card-bg: #ffffff;
    --text: #1a1a1a;
    --muted: #666666;
    --border: #e1e4e8;
    --accent: #1565c0;
    --radius: 12px;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 32px 24px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--text);
  }}
  h1 {{ margin: 0 0 8px; font-size: 28px; }}
  .subtitle {{ color: var(--muted); margin-bottom: 24px; }}
  .controls {{ margin-bottom: 24px; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }}
  .controls input {{
    padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px;
    font-size: 14px; min-width: 260px;
  }}
  .controls .count {{ color: var(--muted); font-size: 14px; margin-left: auto; }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 24px;
  }}
  .card {{
    background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius);
    overflow: hidden; transition: box-shadow .2s;
  }}
  .card:hover {{ box-shadow: 0 8px 24px rgba(0,0,0,0.08); }}
  .card-header {{
    padding: 16px 16px 12px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 12px;
  }}
  .swatch {{
    width: 24px; height: 24px; border-radius: 6px; flex-shrink: 0;
    border: 1px solid rgba(0,0,0,0.08);
  }}
  .card-title {{ font-weight: 600; font-size: 16px; margin: 0; }}
  .card-meta {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
  .keywords {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
  .keyword {{
    font-size: 12px; padding: 3px 10px; border-radius: 999px;
    background: #eef2f7; color: var(--muted);
  }}
  .previews {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 16px; }}
  .preview {{ border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #fafbfc; }}
  .preview-label {{
    font-size: 11px; color: var(--muted); padding: 6px 10px;
    border-bottom: 1px solid var(--border); background: #f5f7fa;
  }}
  .preview svg {{ display: block; width: 100%; height: auto; }}
  .no-preview {{
    padding: 40px 20px; text-align: center; color: var(--muted); font-size: 13px;
  }}
  @media (max-width: 640px) {{
    .grid {{ grid-template-columns: 1fr; }}
    .previews {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<h1>PPT Master Template Gallery</h1>
<div class="subtitle">Built-in layout templates — hover to inspect, scroll to compare</div>
<div class="controls">
  <input type="text" id="search" placeholder="Filter by name, keyword, or description..." value="{filter_value}">
  <span class="count">Showing <span id="visible">{count}</span> / {count} templates</span>
</div>
<div class="grid" id="grid">
{cards}
</div>
<script>
  const search = document.getElementById('search');
  const grid = document.getElementById('grid');
  const visible = document.getElementById('visible');
  const cards = Array.from(grid.children);
  function update() {{
    const q = search.value.trim().toLowerCase();
    let n = 0;
    cards.forEach(c => {{
      const text = c.dataset.search || '';
      const show = !q || text.includes(q);
      c.style.display = show ? '' : 'none';
      if (show) n++;
    }});
    visible.textContent = n;
  }}
  search.addEventListener('input', update);
  update();
</script>
</body>
</html>
"""


def _hex_color_from_text(text: str) -> str | None:
    """Extract the first HEX color from text."""
    match = re.search(r"#(?:[0-9a-fA-F]{3}){1,2}\b", text)
    return match.group(0).upper() if match else None


def _read_design_spec_colors(spec_path: Path) -> dict[str, str]:
    """Try to read primary/accent colors from design_spec.md frontmatter or body."""
    colors: dict[str, str] = {}
    if not spec_path.exists():
        return colors
    try:
        text = spec_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return colors

    # Try frontmatter YAML-style color fields
    for key in ("primary", "accent", "primary_color", "theme_color"):
        m = re.search(rf"{key}\s*[:=]\s*['\"]?(#[0-9a-fA-F]{{3,6}})['\"]?", text, re.I)
        if m:
            colors[key] = m.group(1).upper()

    # Fallback: first HEX in the color table
    if not colors:
        first = _hex_color_from_text(text)
        if first:
            colors["primary"] = first
    return colors


def _read_svg_safe(svg_path: Path) -> str:
    """Read an SVG file and strip XML declaration / DOCTYPE for inline HTML embedding."""
    if not svg_path.exists():
        return ""
    try:
        text = svg_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    # Remove XML declaration and DOCTYPE
    text = re.sub(r"<\?xml[^?]*\?>", "", text)
    text = re.sub(r"<!DOCTYPE[^>]*>", "", text, flags=re.I)
    return text.strip()


def _build_card(
    template_id: str,
    meta: dict,
    cover_svg: str,
    content_svg: str,
    primary_color: str | None,
) -> str:
    label = meta.get("label", template_id)
    summary = meta.get("summary", "")
    keywords = meta.get("keywords", [])
    kw_html = "".join(f'<span class="keyword">{k}</span>' for k in keywords)
    swatch = (
        f'<div class="swatch" style="background:{primary_color}"></div>'
        if primary_color else '<div class="swatch" style="background:#ccc"></div>'
    )

    cover_html = (
        f'<div class="preview-label">Cover</div>{cover_svg}'
        if cover_svg
        else '<div class="no-preview">No cover preview</div>'
    )
    content_html = (
        f'<div class="preview-label">Content</div>{content_svg}'
        if content_svg
        else '<div class="no-preview">No content preview</div>'
    )

    search_text = " ".join(
        [template_id, label, summary, " ".join(keywords)]
    ).lower()

    return f"""<div class="card" data-search="{search_text}">
  <div class="card-header">
    {swatch}
    <div>
      <div class="card-title">{label}</div>
      <div class="card-meta">{template_id} &middot; {summary}</div>
      <div class="keywords">{kw_html}</div>
    </div>
  </div>
  <div class="previews">
    <div class="preview">{cover_html}</div>
    <div class="preview">{content_html}</div>
  </div>
</div>"""


def generate_gallery(filter_keyword: str | None = None) -> Path:
    """Generate the gallery HTML and return its path."""
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

        # Filter
        search_blob = " ".join(
            [tid, meta.get("label", ""), meta.get("summary", ""), " ".join(meta.get("keywords", []))]
        ).lower()
        if filter_keyword and filter_keyword.lower() not in search_blob:
            continue

        # Read colors
        colors = _read_design_spec_colors(template_dir / "design_spec.md")
        primary = colors.get("primary") or colors.get("theme_color") or colors.get("accent")

        # Read SVGs
        cover_svg = _read_svg_safe(template_dir / "01_cover.svg")
        content_svg = _read_svg_safe(template_dir / "03_content.svg")

        cards.append(_build_card(tid, meta, cover_svg, content_svg, primary))

    html = HTML_TEMPLATE.format(
        cards="\n".join(cards),
        count=len(cards),
        filter_value=(filter_keyword or "").replace('"', '&quot;'),
    )

    # Write to a temp file
    fd, tmp_path = tempfile.mkstemp(prefix="ppt_master_gallery_", suffix=".html")
    with open(fd, "w", encoding="utf-8") as f:
        f.write(html)
    return Path(tmp_path)


def open_gallery(filter_keyword: str | None = None) -> Path:
    """Generate and open the gallery in the default browser."""
    path = generate_gallery(filter_keyword=filter_keyword)
    url = path.as_uri()
    webbrowser.open(url, new=2)  # new=2 → new tab
    return path


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    args = argv or sys.argv[1:]
    keyword = args[0] if args else None
    path = open_gallery(filter_keyword=keyword)
    print(f"Gallery opened in browser: {path}")
    if keyword:
        print(f"Filter keyword: {keyword}")


if __name__ == "__main__":
    main()
