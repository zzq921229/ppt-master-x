#!/usr/bin/env python3
"""Generate a modern local HTML gallery for built-in layout templates.

Usage:
    python3 scripts/template_gallery.py [filter_keyword]

Two-view design:
  - List view: cover thumbnails, style description, color palette, keywords
  - Detail view: full slide deck browser with prev/next and thumbnail strip
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
  :root {
    --bg: #f4f6f9;
    --surface: #ffffff;
    --text: #1e293b;
    --muted: #64748b;
    --border: #e2e8f0;
    --accent: #4f46e5;
    --accent-light: #eef2ff;
    --radius: 16px;
    --radius-sm: 10px;
    --shadow: 0 1px 3px rgba(0,0,0,0.06);
    --shadow-hover: 0 12px 32px rgba(0,0,0,0.10);
    --shadow-lg: 0 20px 48px rgba(0,0,0,0.14);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--text); min-height: 100vh;
  }
  /* Header */
  .site-header {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    color: #fff; padding: 40px 24px 32px; text-align: center;
  }
  .site-header h1 { font-size: 32px; font-weight: 700; margin-bottom: 8px; letter-spacing: -0.5px; }
  .site-header p { font-size: 15px; opacity: 0.9; max-width: 520px; margin: 0 auto; }
  .search-bar {
    margin-top: 20px; display: flex; justify-content: center;
  }
  .search-bar input {
    width: 100%; max-width: 440px; padding: 12px 18px; border: none; border-radius: 999px;
    font-size: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); outline: none;
  }
  .search-bar input::placeholder { color: #94a3b8; }

  /* List view */
  #list-view { padding: 28px 24px 48px; }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px; max-width: 1200px; margin: 0 auto;
  }
  .list-card {
    background: var(--surface); border-radius: var(--radius); overflow: hidden;
    box-shadow: var(--shadow); cursor: pointer; transition: transform .2s, box-shadow .2s;
    border: 1px solid var(--border);
  }
  .list-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-hover); }
  .list-cover-wrap {
    position: relative; width: 100%; padding-top: 56.25%; background: #f8fafc;
    overflow: hidden;
  }
  .list-cover-wrap svg {
    position: absolute; inset: 0; width: 100%; height: 100%;
    transition: transform .4s ease;
  }
  .list-card:hover .list-cover-wrap svg { transform: scale(1.03); }
  .list-body { padding: 18px 20px 20px; }
  .list-title { font-size: 17px; font-weight: 700; margin-bottom: 4px; }
  .list-desc { font-size: 13px; color: var(--muted); line-height: 1.45; margin-bottom: 12px; }
  .palette { display: flex; gap: 6px; margin-bottom: 12px; }
  .palette-dot {
    width: 18px; height: 18px; border-radius: 50%;
    border: 1px solid rgba(0,0,0,0.06); flex-shrink: 0;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.3);
  }
  .keywords { display: flex; flex-wrap: wrap; gap: 6px; }
  .keyword {
    font-size: 11px; padding: 4px 10px; border-radius: 999px;
    background: var(--accent-light); color: var(--accent); font-weight: 500;
  }

  /* Detail view */
  #detail-view { display: none; }
  .detail-header {
    position: sticky; top: 0; z-index: 100;
    background: rgba(255,255,255,0.92); backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border); padding: 14px 24px;
    display: flex; align-items: center; gap: 14px;
  }
  .back-btn {
    display: flex; align-items: center; gap: 6px; padding: 8px 14px;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: var(--surface); cursor: pointer; font-size: 14px; color: var(--text);
    transition: background .15s;
  }
  .back-btn:hover { background: var(--bg); }
  .detail-title { font-size: 18px; font-weight: 700; }
  .detail-meta { font-size: 13px; color: var(--muted); margin-left: auto; }

  .detail-body { padding: 24px; max-width: 1100px; margin: 0 auto; }
  .viewer { margin-bottom: 28px; }
  .stage-wrap {
    position: relative; width: 100%; max-width: 960px; margin: 0 auto;
    background: #000; border-radius: var(--radius-sm); overflow: hidden;
    box-shadow: var(--shadow-lg);
  }
  .stage { position: relative; width: 100%; padding-top: 56.25%; }
  .slide-layer {
    position: absolute; inset: 0; opacity: 0; transition: opacity .35s ease;
    display: flex; align-items: center; justify-content: center; background: #fff;
  }
  .slide-layer.active { opacity: 1; z-index: 2; }
  .slide-layer svg { width: 100%; height: 100%; display: block; }
  .arrow {
    position: absolute; top: 50%; transform: translateY(-50%);
    width: 44px; height: 44px; border-radius: 50%;
    background: rgba(255,255,255,0.95); border: none;
    cursor: pointer; z-index: 10; display: flex; align-items: center; justify-content: center;
    font-size: 18px; color: #334155; box-shadow: 0 2px 8px rgba(0,0,0,0.18);
    transition: background .15s;
  }
  .arrow:hover { background: #fff; }
  .arrow.prev { left: 14px; }
  .arrow.next { right: 14px; }
  .arrow:disabled { opacity: .35; cursor: default; }
  .page-counter {
    position: absolute; bottom: 12px; right: 16px;
    background: rgba(0,0,0,0.55); color: #fff;
    font-size: 12px; padding: 5px 12px; border-radius: 6px;
    z-index: 10; pointer-events: none; font-weight: 500;
  }
  .strip {
    display: flex; gap: 10px; margin-top: 14px;
    overflow-x: auto; padding-bottom: 4px;
    justify-content: center;
  }
  .strip-item {
    flex: 0 0 auto; width: 130px; cursor: pointer;
    border: 2px solid transparent; border-radius: 8px;
    overflow: hidden; background: #f1f5f9;
    transition: border-color .2s, transform .15s;
  }
  .strip-item:hover { transform: translateY(-2px); }
  .strip-item.active { border-color: var(--accent); }
  .strip-thumb {
    height: 74px; display: flex; align-items: center; justify-content: center;
    padding: 4px;
  }
  .strip-thumb svg { max-width: 100%; max-height: 100%; width: auto; height: auto; }
  .strip-label {
    font-size: 11px; text-align: center; padding: 5px 6px;
    color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    background: #fff; border-top: 1px solid var(--border); font-weight: 500;
  }

  .detail-info {
    background: var(--surface); border-radius: var(--radius); padding: 22px 24px;
    border: 1px solid var(--border); box-shadow: var(--shadow);
  }
  .detail-info h3 { font-size: 15px; margin-bottom: 12px; color: var(--text); }
  .info-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; font-size: 14px; }
  .info-row .label { color: var(--muted); min-width: 80px; }

  @media (max-width: 640px) {
    .grid { grid-template-columns: 1fr; }
    .site-header h1 { font-size: 24px; }
    .stage-wrap { max-width: 100%; }
    .strip-item { width: 100px; }
    .strip-thumb { height: 56px; }
    .detail-header { padding: 12px 16px; }
    .detail-body { padding: 16px; }
  }
</style>
</head>
<body>

<!-- LIST VIEW -->
<div id="list-view">
  <div class="site-header">
    <h1>Template Gallery</h1>
    <p>Browse 17 built-in themes. Click any card to explore the full slide deck.</p>
    <div class="search-bar">
      <input type="text" id="search" placeholder="Search templates, styles, keywords..." value="{filter_value}">
    </div>
  </div>
  <div class="grid" id="grid">
{list_cards}
  </div>
</div>

<!-- DETAIL VIEW -->
<div id="detail-view">
  <div class="detail-header">
    <button class="back-btn" id="back-btn">&#10094; Back to Gallery</button>
    <span class="detail-title" id="detail-title">Template</span>
    <span class="detail-meta" id="detail-meta"></span>
  </div>
  <div class="detail-body" id="detail-body">
    <!-- Injected by JS -->
  </div>
</div>

<script>
(function() {
  const templates = {templates_json};

  const listView = document.getElementById('list-view');
  const detailView = document.getElementById('detail-view');
  const detailBody = document.getElementById('detail-body');
  const detailTitle = document.getElementById('detail-title');
  const detailMeta = document.getElementById('detail-meta');
  const backBtn = document.getElementById('back-btn');
  const search = document.getElementById('search');
  const grid = document.getElementById('grid');

  function showList() {
    listView.style.display = '';
    detailView.style.display = 'none';
    window.location.hash = '';
    document.title = 'PPT Master - Template Gallery';
    window.scrollTo(0, 0);
  }

  function showDetail(id) {
    const t = templates[id];
    if (!t) return;
    listView.style.display = 'none';
    detailView.style.display = '';
    window.location.hash = 'detail-' + id;
    document.title = t.label + ' - Template Gallery';

    detailTitle.textContent = t.label;
    detailMeta.textContent = t.summary;

    // Build slides
    let layers = '', thumbs = '';
    t.slides.forEach((s, i) => {
      const active = i === 0 ? ' active' : '';
      layers += '<div class="slide-layer' + active + '">' + s.svg + '</div>';
      thumbs += '<div class="strip-item' + active + '" data-idx="' + i + '">' +
        '<div class="strip-thumb">' + s.svg + '</div>' +
        '<div class="strip-label">' + s.label + '</div></div>';
    });

    const paletteDots = (t.colors || []).map(c =>
      '<span class="palette-dot" style="background:' + c + '" title="' + c + '"></span>'
    ).join('');

    detailBody.innerHTML =
      '<div class="viewer">' +
        '<div class="stage-wrap">' +
          '<div class="stage">' + layers + '</div>' +
          '<button class="arrow prev">&#10094;</button>' +
          '<button class="arrow next">&#10095;</button>' +
          '<div class="page-counter">1 / ' + t.slides.length + '</div>' +
        '</div>' +
        '<div class="strip">' + thumbs + '</div>' +
      '</div>' +
      '<div class="detail-info">' +
        '<h3>About this template</h3>' +
        '<div class="info-row"><span class="label">ID:</span> ' + id + '</div>' +
        '<div class="info-row"><span class="label">Summary:</span> ' + t.summary + '</div>' +
        '<div class="info-row"><span class="label">Palette:</span> ' + paletteDots + '</div>' +
        '<div class="info-row"><span class="label">Keywords:</span> ' + (t.keywords || []).join(', ') + '</div>' +
      '</div>';

    // Wire up slide viewer
    const layersEls = detailBody.querySelectorAll('.slide-layer');
    const thumbsEls = detailBody.querySelectorAll('.strip-item');
    const prevBtn = detailBody.querySelector('.arrow.prev');
    const nextBtn = detailBody.querySelector('.arrow.next');
    const counter = detailBody.querySelector('.page-counter');
    let idx = 0;
    const total = layersEls.length;

    function show(i) {
      if (i < 0) i = 0;
      if (i >= total) i = total - 1;
      idx = i;
      layersEls.forEach((el, n) => el.classList.toggle('active', n === idx));
      thumbsEls.forEach((el, n) => el.classList.toggle('active', n === idx));
      if (prevBtn) prevBtn.disabled = idx === 0;
      if (nextBtn) nextBtn.disabled = idx === total - 1;
      if (counter) counter.textContent = (idx + 1) + ' / ' + total;
      const activeThumb = thumbsEls[idx];
      if (activeThumb) activeThumb.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
    if (prevBtn) prevBtn.addEventListener('click', () => show(idx - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => show(idx + 1));
    thumbsEls.forEach(el => el.addEventListener('click', () => show(+el.dataset.idx)));
    show(0);
    window.scrollTo(0, 0);
  }

  // Hash routing
  function route() {
    const hash = window.location.hash;
    const m = hash.match(/^#detail-(.+)/);
    if (m && templates[m[1]]) showDetail(m[1]);
    else showList();
  }
  window.addEventListener('hashchange', route);
  backBtn.addEventListener('click', showList);

  // Search
  function updateSearch() {
    const q = search.value.trim().toLowerCase();
    const cards = grid.querySelectorAll('.list-card');
    let n = 0;
    cards.forEach(c => {
      const text = c.dataset.search || '';
      const show = !q || text.includes(q);
      c.style.display = show ? '' : 'none';
      if (show) n++;
    });
  }
  search.addEventListener('input', updateSearch);

  // Initial route
  route();
})();
</script>
</body>
</html>
"""


def _extract_colors(text: str) -> list[str]:
    """Extract all unique HEX colors from design_spec.md text."""
    found = re.findall(r"#(?:[0-9a-fA-F]{3}){1,2}\b", text)
    # Preserve order, deduplicate (case-insensitive)
    seen = set()
    result: list[str] = []
    for c in found:
        upper = c.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result[:6]  # max 6 colors


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


def generate_gallery(filter_keyword: str | None = None) -> Path:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Template index not found: {INDEX_PATH}")

    with INDEX_PATH.open("r", encoding="utf-8") as f:
        index: dict[str, dict] = json.load(f)

    list_cards: list[str] = []
    templates_json: dict[str, dict] = {}

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

        # Read colors from design_spec.md
        colors: list[str] = []
        spec_path = template_dir / "design_spec.md"
        if spec_path.exists():
            try:
                spec_text = spec_path.read_text(encoding="utf-8", errors="replace")
                colors = _extract_colors(spec_text)
            except Exception:
                pass

        # Collect SVGs
        svg_files = sorted(
            [p for p in template_dir.iterdir() if p.suffix.lower() == ".svg"],
            key=lambda p: p.name,
        )
        slides_data: list[dict] = []
        cover_svg = ""
        for svg_path in svg_files:
            inline = _read_svg_safe(svg_path)
            if not inline:
                continue
            lbl = _svg_label(svg_path.name)
            slides_data.append({"label": lbl, "svg": inline})
            if svg_path.name == "01_cover.svg" or not cover_svg:
                cover_svg = inline

        if not slides_data:
            continue

        label = meta.get("label", tid)
        summary = meta.get("summary", "")
        keywords = meta.get("keywords", [])
        kw_html = "".join(f'<span class="keyword">{k}</span>' for k in keywords)
        palette_html = "".join(f'<span class="palette-dot" style="background:{c}" title="{c}"></span>' for c in colors)
        search_text = " ".join([tid, label, summary, " ".join(keywords)]).lower()

        list_cards.append(f"""<div class="list-card" data-search="{search_text}" onclick="window.location.hash='#detail-{tid}'">
  <div class="list-cover-wrap">{cover_svg}</div>
  <div class="list-body">
    <div class="list-title">{label}</div>
    <div class="list-desc">{summary}</div>
    <div class="palette">{palette_html}</div>
    <div class="keywords">{kw_html}</div>
  </div>
</div>""")

        templates_json[tid] = {
            "label": label,
            "summary": summary,
            "keywords": keywords,
            "colors": colors,
            "slides": slides_data,
        }

    # Escape JSON for inline JS
    import json as _json
    json_str = _json.dumps(templates_json, ensure_ascii=False)

    html = HTML_TEMPLATE.format(
        list_cards="\n".join(list_cards),
        templates_json=json_str,
        filter_value=(filter_keyword or "").replace('"', '\&quot;'),
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
