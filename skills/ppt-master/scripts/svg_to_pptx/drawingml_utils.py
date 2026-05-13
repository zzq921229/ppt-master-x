"""Coordinate helpers, color parsing, and font utilities for DrawingML conversion."""

from __future__ import annotations

import functools
import os
import re
import math
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from PIL import ImageFont
    _HAS_PILLOW = True
except ImportError:
    _HAS_PILLOW = False

from .drawingml_context import AffineMatrix, ConvertContext, IDENTITY_MATRIX

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'

EMU_PER_PX = 9525  # 1 SVG px = 9525 EMU (96 DPI)
FONT_PX_TO_HUNDREDTHS_PT = 75  # 1px = 0.75pt -> 75 hundredths-of-a-point
ANGLE_UNIT = 60000  # DrawingML angle: 60000ths of a degree

# SVG attributes inheritable from parent <g>
INHERITABLE_ATTRS = [
    'fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap',
    'stroke-linejoin', 'opacity', 'fill-opacity', 'stroke-opacity',
    'font-family', 'font-size', 'font-weight', 'font-style',
    'text-anchor', 'letter-spacing', 'text-decoration',
]

# Known East Asian fonts
EA_FONTS = {
    'PingFang SC', 'PingFang TC', 'PingFang HK',
    'Microsoft YaHei', 'Microsoft JhengHei',
    'SimSun', 'SimHei', 'FangSong', 'KaiTi', 'STKaiti',
    'STHeiti', 'STSong', 'STFangsong', 'STXihei', 'STZhongsong',
    'Hiragino Sans', 'Hiragino Sans GB', 'Hiragino Mincho ProN',
    'Hiragino Kaku Gothic ProN', 'Hiragino Kaku Gothic Pro',
    'Hiragino Mincho Pro',
    'Noto Sans SC', 'Noto Sans TC', 'Noto Serif SC', 'Noto Serif TC',
    'Noto Sans JP', 'Noto Serif JP', 'Noto Sans CJK JP',
    'Source Han Sans SC', 'Source Han Sans TC',
    'Source Han Serif SC', 'Source Han Serif TC',
    'Source Han Sans JP', 'Source Han Serif JP',
    'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
    'YouYuan', 'LiSu', 'HuaWenKaiTi',
    'Songti SC', 'Songti TC',
    # Japanese fonts (Windows-available)
    'Yu Gothic', 'Yu Gothic UI', 'Yu Mincho',
    'Meiryo', 'Meiryo UI', 'メイリオ',
    'MS Gothic', 'MS Mincho', 'MS PGothic', 'MS PMincho', 'MS UI Gothic',
    # Korean
    'Malgun Gothic', 'Gulim', 'Dotum', 'Batang',
    'Noto Sans KR', 'Noto Serif KR',
}
SYSTEM_FONTS = {'system-ui', '-apple-system', 'BlinkMacSystemFont'}

# macOS/Linux-only fonts -> Windows equivalents
FONT_FALLBACK_WIN = {
    'PingFang SC': 'Microsoft YaHei',
    'PingFang TC': 'Microsoft JhengHei',
    'PingFang HK': 'Microsoft JhengHei',
    'Hiragino Sans': 'Microsoft YaHei',
    'Hiragino Sans GB': 'Microsoft YaHei',
    'Hiragino Mincho ProN': 'SimSun',
    'STHeiti': 'SimHei',
    'STSong': 'SimSun',
    'STKaiti': 'KaiTi',
    'STFangsong': 'FangSong',
    'STXihei': 'Microsoft YaHei',
    'STZhongsong': 'SimSun',
    'Songti SC': 'SimSun',
    'Songti TC': 'SimSun',
    'Noto Sans SC': 'Microsoft YaHei',
    'Noto Sans TC': 'Microsoft JhengHei',
    'Noto Serif SC': 'SimSun',
    'Noto Serif TC': 'SimSun',
    # Japanese: keep as-is if user specified (PowerPoint will fallback if uninstalled)
    # 'Noto Sans JP': → keep as 'Noto Sans JP' (do not map)
    # 'メイリオ': → keep as 'メイリオ' (Meiryo alias)
    'メイリオ': 'Meiryo',
    'Source Han Sans SC': 'Microsoft YaHei',
    'Source Han Sans TC': 'Microsoft JhengHei',
    'Source Han Serif SC': 'SimSun',
    'Source Han Serif TC': 'SimSun',
    'Source Han Sans JP': 'Noto Sans JP',
    'Source Han Serif JP': 'Noto Serif JP',
    'WenQuanYi Micro Hei': 'Microsoft YaHei',
    'WenQuanYi Zen Hei': 'Microsoft YaHei',
    # Latin fonts (macOS / Linux / Web -> Windows)
    'SF Pro': 'Segoe UI',
    'SF Pro Display': 'Segoe UI',
    'SF Pro Text': 'Segoe UI',
    'SF Mono': 'Consolas',
    'Menlo': 'Consolas',
    'Monaco': 'Consolas',
    'Helvetica Neue': 'Arial',
    'Helvetica': 'Arial',
    'Roboto': 'Segoe UI',
    'Ubuntu': 'Segoe UI',
    'Liberation Sans': 'Arial',
    'Liberation Serif': 'Times New Roman',
    'Liberation Mono': 'Consolas',
    'DejaVu Sans': 'Segoe UI',
    'DejaVu Serif': 'Times New Roman',
    'DejaVu Sans Mono': 'Consolas',
}

GENERIC_FONT_MAP = {
    'monospace': 'Consolas',
    'sans-serif': 'Segoe UI',
    'serif': 'Times New Roman',
}

# When the latin font is serif and no EA font is specified,
# prefer SimSun (serif CJK) over Microsoft YaHei (sans-serif CJK).
_SERIF_LATIN = {
    'Times New Roman', 'Georgia', 'Garamond', 'Palatino', 'Palatino Linotype',
    'Book Antiqua', 'Cambria', 'SimSun', 'Liberation Serif', 'DejaVu Serif',
}

# SVG stroke-dasharray -> DrawingML prstDash
DASH_PRESETS = {
    '4,4': 'dash',  '4 4': 'dash',
    '6,3': 'dash',  '6 3': 'dash',
    '2,2': 'sysDot', '2 2': 'sysDot',
    '8,4': 'lgDash', '8 4': 'lgDash',
    '8,4,2,4': 'lgDashDot', '8 4 2 4': 'lgDashDot',
}


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------

def px_to_emu(px: float) -> int:
    """Convert SVG pixels to EMU."""
    return round(px * EMU_PER_PX)


def _f(val: str | None, default: float = 0.0) -> float:
    """Parse a float attribute value, returning default if missing."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# SVG transform matrix helpers
# ---------------------------------------------------------------------------

_TRANSFORM_RE = re.compile(r'([a-zA-Z]+)\(([^)]*)\)')
_NUMBER_RE = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')


def matrix_multiply(left: AffineMatrix, right: AffineMatrix) -> AffineMatrix:
    """Compose two SVG affine matrices, applying ``right`` before ``left``."""
    a1, b1, c1, d1, e1, f1 = left
    a2, b2, c2, d2, e2, f2 = right
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def _translate_matrix(tx: float, ty: float = 0.0) -> AffineMatrix:
    return (1.0, 0.0, 0.0, 1.0, tx, ty)


def _scale_matrix(sx: float, sy: float | None = None) -> AffineMatrix:
    return (sx, 0.0, 0.0, sx if sy is None else sy, 0.0, 0.0)


def _rotate_matrix(angle_deg: float, cx: float | None = None, cy: float | None = None) -> AffineMatrix:
    rad = math.radians(angle_deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    rot = (cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0)
    if cx is None or cy is None:
        return rot
    return matrix_multiply(
        matrix_multiply(_translate_matrix(cx, cy), rot),
        _translate_matrix(-cx, -cy),
    )


def parse_transform_matrix(transform_str: str) -> AffineMatrix:
    """Parse an SVG transform list into one affine matrix."""
    if not transform_str:
        return IDENTITY_MATRIX

    matrix = IDENTITY_MATRIX
    for name, raw_args in _TRANSFORM_RE.findall(transform_str):
        args = [float(n) for n in _NUMBER_RE.findall(raw_args)]
        name = name.lower()
        local = IDENTITY_MATRIX

        if name == 'matrix' and len(args) >= 6:
            local = (args[0], args[1], args[2], args[3], args[4], args[5])
        elif name == 'translate' and args:
            local = _translate_matrix(args[0], args[1] if len(args) > 1 else 0.0)
        elif name == 'scale' and args:
            local = _scale_matrix(args[0], args[1] if len(args) > 1 else None)
        elif name == 'rotate' and args:
            local = _rotate_matrix(
                args[0],
                args[1] if len(args) > 2 else None,
                args[2] if len(args) > 2 else None,
            )

        matrix = matrix_multiply(matrix, local)

    return matrix


def transform_point(matrix: AffineMatrix, x: float, y: float) -> tuple[float, float]:
    """Apply an SVG affine matrix to a point."""
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def rect_to_dml_xfrm(
    x: float,
    y: float,
    w: float,
    h: float,
    matrix: AffineMatrix,
) -> tuple[str, int, int, int, int, tuple[int, int, int, int]]:
    """Map a transformed SVG rectangle to DrawingML xfrm attributes.

    DrawingML can represent rotated/flipped rectangles, but not arbitrary
    shear. Template-import picture wrappers only use translate/rotate/scale,
    so decomposing the transformed local X/Y axes is sufficient here.
    """
    p0 = transform_point(matrix, x, y)
    p1 = transform_point(matrix, x + w, y)
    p2 = transform_point(matrix, x + w, y + h)
    p3 = transform_point(matrix, x, y + h)

    ux = p1[0] - p0[0]
    uy = p1[1] - p0[1]
    vx = p3[0] - p0[0]
    vy = p3[1] - p0[1]

    rect_w = max(math.hypot(ux, uy), 0.001)
    rect_h = max(math.hypot(vx, vy), 0.001)
    cross = ux * vy - uy * vx

    if cross < 0:
        angle_deg = math.degrees(math.atan2(-uy, -ux))
        flip_attr = ' flipH="1"'
    else:
        angle_deg = math.degrees(math.atan2(uy, ux))
        flip_attr = ''

    rot = round(angle_deg * ANGLE_UNIT)
    rot_attr = f' rot="{rot}"' if rot else ''

    center_x = (p0[0] + p2[0]) / 2
    center_y = (p0[1] + p2[1]) / 2
    off_x = px_to_emu(center_x - rect_w / 2)
    off_y = px_to_emu(center_y - rect_h / 2)
    ext_cx = px_to_emu(rect_w)
    ext_cy = px_to_emu(rect_h)

    xs = [p0[0], p1[0], p2[0], p3[0]]
    ys = [p0[1], p1[1], p2[1], p3[1]]
    bounds = (
        px_to_emu(min(xs)),
        px_to_emu(min(ys)),
        px_to_emu(max(xs)),
        px_to_emu(max(ys)),
    )

    return f'{flip_attr}{rot_attr}', off_x, off_y, ext_cx, ext_cy, bounds


def _extract_inheritable_styles(elem: ET.Element) -> dict[str, str]:
    """Extract all SVG-inheritable presentation attributes from an element."""
    styles: dict[str, str] = {}
    for attr in INHERITABLE_ATTRS:
        val = elem.get(attr)
        if val is not None:
            styles[attr] = val
    return styles


def _get_attr(elem: ET.Element, attr: str, ctx: ConvertContext) -> str | None:
    """Get effective attribute: element's own value first, then inherited."""
    val = elem.get(attr)
    if val is not None:
        return val
    return ctx.inherited_styles.get(attr)


def ctx_x(val: float, ctx: ConvertContext) -> float:
    """Apply context scale + translate to an X coordinate."""
    return val * ctx.scale_x + ctx.translate_x


def ctx_y(val: float, ctx: ConvertContext) -> float:
    """Apply context scale + translate to a Y coordinate."""
    return val * ctx.scale_y + ctx.translate_y


def ctx_w(val: float, ctx: ConvertContext) -> float:
    """Apply context scale to a width value."""
    return val * ctx.scale_x


def ctx_h(val: float, ctx: ConvertContext) -> float:
    """Apply context scale to a height value."""
    return val * ctx.scale_y


# ---------------------------------------------------------------------------
# Color / style parsing
# ---------------------------------------------------------------------------

def parse_hex_color(color_str: str) -> str | None:
    """Parse '#RRGGBB' or '#RGB' to 'RRGGBB'. Returns None on failure."""
    if not color_str:
        return None
    color_str = color_str.strip()
    if color_str.startswith('#'):
        color_str = color_str[1:]
    if len(color_str) == 3:
        color_str = ''.join(c * 2 for c in color_str)
    if len(color_str) == 6 and all(c in '0123456789abcdefABCDEF' for c in color_str):
        return color_str.upper()
    return None


def parse_stop_style(style_str: str) -> tuple[str | None, float]:
    """Parse a gradient stop's style attribute.

    Args:
        style_str: Style string like 'stop-color:#XXX;stop-opacity:N'.

    Returns:
        (color, opacity) tuple.
    """
    color = None
    opacity = 1.0
    if not style_str:
        return color, opacity

    for part in style_str.split(';'):
        part = part.strip()
        if part.startswith('stop-color:'):
            color = parse_hex_color(part.split(':', 1)[1].strip())
        elif part.startswith('stop-opacity:'):
            try:
                opacity = float(part.split(':', 1)[1].strip())
            except ValueError:
                pass

    return color, opacity


def resolve_url_id(url_str: str) -> str | None:
    """Extract ID from 'url(#someId)' reference."""
    if not url_str:
        return None
    m = re.match(r'url\(#([^)]+)\)', url_str.strip())
    return m.group(1) if m else None


def get_effective_filter_id(elem: ET.Element, ctx: ConvertContext) -> str | None:
    """Get the effective filter ID for an element, including inherited context."""
    filt = elem.get('filter')
    if filt:
        return resolve_url_id(filt)
    return ctx.filter_id


# ---------------------------------------------------------------------------
# Font parsing
# ---------------------------------------------------------------------------

def parse_font_family(font_family_str: str) -> dict[str, str]:
    """Parse CSS font-family into latin/ea typeface names.

    Prioritizes Windows-available fonts since PPTX is primarily opened on
    Windows. macOS/Linux-only fonts are mapped via FONT_FALLBACK_WIN.
    """
    if not font_family_str:
        return {'latin': 'Segoe UI', 'ea': 'Microsoft YaHei'}

    fonts = [f.strip().strip("'\"") for f in font_family_str.split(',')]
    latin_font = None
    ea_font = None

    for font in fonts:
        if font in SYSTEM_FONTS:
            continue
        if font in GENERIC_FONT_MAP:
            resolved = GENERIC_FONT_MAP[font]
            latin_font = latin_font or resolved
            continue

        win_font = FONT_FALLBACK_WIN.get(font, font)
        if font in EA_FONTS:
            ea_font = ea_font or win_font
        else:
            latin_font = latin_font or win_font

    # PPT renders CJK text via latin typeface when ea doesn't match
    if not latin_font and ea_font:
        latin_font = ea_font

    final_latin = latin_font or 'Segoe UI'

    # EA must always be a CJK-capable font
    if not ea_font:
        ea_font = 'SimSun' if final_latin in _SERIF_LATIN else 'Microsoft YaHei'

    return {'latin': final_latin, 'ea': ea_font}


# ---------------------------------------------------------------------------
# Font file resolution (cross-platform)
# ---------------------------------------------------------------------------

_FONT_FILE_MAP: dict[str, dict[str, str]] = {
    # CJK fonts (Windows)
    'Microsoft YaHei':     {'regular': 'msyh.ttc',     'bold': 'msyhbd.ttc'},
    'Microsoft JhengHei':  {'regular': 'msjh.ttc',     'bold': 'msjhbd.ttc'},
    'SimSun':              {'regular': 'simsun.ttc',   'bold': 'simsunb.ttf'},
    'SimHei':              {'regular': 'simhei.ttf'},
    'FangSong':            {'regular': 'simfang.ttf'},
    'KaiTi':               {'regular': 'simkai.ttf'},
    'STKaiti':             {'regular': 'stkaiti.ttf'},
    'STHeiti':             {'regular': 'stheiti.ttf'},
    'STSong':              {'regular': 'stsong.ttf'},
    'STFangsong':          {'regular': 'stfangso.ttf'},
    'STXihei':             {'regular': 'stxihei.ttf'},
    'STZhongsong':         {'regular': 'stzhongs.ttf'},
    'YouYuan':             {'regular': 'youyuan.ttf'},
    'LiSu':                {'regular': 'lisu.ttf'},
    # CJK fonts (macOS)
    'PingFang SC':         {'regular': 'PingFang.ttc'},
    'PingFang TC':         {'regular': 'PingFang.ttc'},
    'PingFang HK':         {'regular': 'PingFang.ttc'},
    'Songti SC':           {'regular': 'STSong.ttf'},
    'Songti TC':           {'regular': 'STSong.ttf'},
    'Heiti SC':            {'regular': 'STHeiti Light.ttc', 'bold': 'STHeiti Medium.ttc'},
    'Heiti TC':            {'regular': 'STHeiti Light.ttc', 'bold': 'STHeiti Medium.ttc'},
    # CJK fonts (Linux / Noto)
    'Noto Sans SC':        {'regular': 'NotoSansCJK-Regular.ttc', 'bold': 'NotoSansCJK-Bold.ttc'},
    'Noto Sans TC':        {'regular': 'NotoSansCJK-Regular.ttc', 'bold': 'NotoSansCJK-Bold.ttc'},
    'Noto Serif SC':       {'regular': 'NotoSerifCJK-Regular.ttc', 'bold': 'NotoSerifCJK-Bold.ttc'},
    'Noto Serif TC':       {'regular': 'NotoSerifCJK-Regular.ttc', 'bold': 'NotoSerifCJK-Bold.ttc'},
    'Noto Sans JP':        {'regular': 'NotoSansCJK-Regular.ttc', 'bold': 'NotoSansCJK-Bold.ttc'},
    'Noto Serif JP':       {'regular': 'NotoSerifCJK-Regular.ttc', 'bold': 'NotoSerifCJK-Bold.ttc'},
    'Noto Sans KR':        {'regular': 'NotoSansCJK-Regular.ttc', 'bold': 'NotoSansCJK-Bold.ttc'},
    'WenQuanYi Micro Hei': {'regular': 'wqy-microhei.ttc'},
    'WenQuanYi Zen Hei':   {'regular': 'wqy-zenhei.ttc'},
    'Source Han Sans SC':  {'regular': 'SourceHanSansSC-Regular.otf', 'bold': 'SourceHanSansSC-Bold.otf'},
    'Source Han Serif SC': {'regular': 'SourceHanSerifSC-Regular.otf', 'bold': 'SourceHanSerifSC-Bold.otf'},
    # Japanese (Windows)
    'Yu Gothic':           {'regular': 'YuGothM.ttc',  'bold': 'YuGothB.ttc'},
    'Yu Gothic UI':        {'regular': 'YuGothM.ttc',  'bold': 'YuGothB.ttc'},
    'Yu Mincho':           {'regular': 'YuMincho.ttc', 'bold': 'YuMincho.ttc'},
    'Meiryo':              {'regular': 'meiryo.ttc',   'bold': 'meiryob.ttc'},
    'Meiryo UI':           {'regular': 'meiryo.ttc',   'bold': 'meiryob.ttc'},
    'MS Gothic':           {'regular': 'msgothic.ttc'},
    'MS Mincho':           {'regular': 'msmincho.ttc'},
    'MS PGothic':          {'regular': 'msgothic.ttc'},
    'MS PMincho':          {'regular': 'msmincho.ttc'},
    'MS UI Gothic':        {'regular': 'msgothic.ttc'},
    # Korean (Windows)
    'Malgun Gothic':       {'regular': 'malgun.ttf',   'bold': 'malgunbd.ttf'},
    'Gulim':               {'regular': 'gulim.ttc'},
    'Dotum':               {'regular': 'dotum.ttc'},
    'Batang':              {'regular': 'batang.ttc'},
    # Latin fonts (Windows)
    'Arial':               {'regular': 'arial.ttf',    'bold': 'arialbd.ttf',    'italic': 'ariali.ttf',    'bold_italic': 'arialbi.ttf'},
    'Arial Black':         {'regular': 'ariblk.ttf'},
    'Segoe UI':            {'regular': 'segoeui.ttf',  'bold': 'segoeuib.ttf',   'italic': 'segoeuii.ttf',  'bold_italic': 'segoeuiz.ttf'},
    'Segoe UI Emoji':      {'regular': 'seguiemj.ttf'},
    'Times New Roman':     {'regular': 'times.ttf',    'bold': 'timesbd.ttf',    'italic': 'timesi.ttf',    'bold_italic': 'timesbi.ttf'},
    'Consolas':            {'regular': 'consola.ttf',  'bold': 'consolab.ttf',   'italic': 'consolai.ttf',  'bold_italic': 'consolaz.ttf'},
    'Calibri':             {'regular': 'calibri.ttf',  'bold': 'calibrib.ttf',   'italic': 'calibrii.ttf',  'bold_italic': 'calibriz.ttf'},
    'Cambria':             {'regular': 'cambria.ttc',  'bold': 'cambriab.ttf',   'italic': 'cambriai.ttf'},
    'Georgia':             {'regular': 'georgia.ttf',  'bold': 'georgiab.ttf',   'italic': 'georgiai.ttf',  'bold_italic': 'georgiaz.ttf'},
    'Verdana':             {'regular': 'verdana.ttf',  'bold': 'verdanab.ttf',   'italic': 'verdanai.ttf',  'bold_italic': 'verdanaz.ttf'},
    'Impact':              {'regular': 'impact.ttf'},
    'Tahoma':              {'regular': 'tahoma.ttf',   'bold': 'tahomabd.ttf'},
    'Courier New':         {'regular': 'cour.ttf',     'bold': 'courbd.ttf',     'italic': 'couri.ttf',     'bold_italic': 'courbi.ttf'},
    'Trebuchet MS':        {'regular': 'trebuc.ttf',   'bold': 'trebucbd.ttf',   'italic': 'trebucit.ttf'},
    'Comic Sans MS':       {'regular': 'comic.ttf',    'bold': 'comicbd.ttf'},
    'Palatino Linotype':   {'regular': 'pala.ttf',     'bold': 'palab.ttf',      'italic': 'palai.ttf',     'bold_italic': 'palabi.ttf'},
    'Book Antiqua':        {'regular': 'bkant.ttf',    'bold': 'bkant.ttf'},
    'Garamond':            {'regular': 'gara.ttf',     'bold': 'garabd.ttf'},
    # Latin fonts (macOS)
    'Helvetica Neue':      {'regular': 'HelveticaNeue.ttc'},
    'Helvetica':           {'regular': 'Helvetica.dfont'},
    'SF Pro':              {'regular': 'SF-Pro.ttf'},
    'SF Pro Display':      {'regular': 'SF-Pro-Display-Regular.otf', 'bold': 'SF-Pro-Display-Bold.otf'},
    'SF Pro Text':         {'regular': 'SF-Pro-Text-Regular.otf',    'bold': 'SF-Pro-Text-Bold.otf'},
    'SF Mono':             {'regular': 'SF-Mono-Regular.otf',        'bold': 'SF-Mono-Bold.otf'},
    'Menlo':               {'regular': 'Menlo.ttc'},
    'Monaco':              {'regular': 'Monaco.dfont'},
    # Latin fonts (Linux)
    'DejaVu Sans':         {'regular': 'DejaVuSans.ttf',      'bold': 'DejaVuSans-Bold.ttf'},
    'DejaVu Serif':        {'regular': 'DejaVuSerif.ttf',     'bold': 'DejaVuSerif-Bold.ttf'},
    'DejaVu Sans Mono':    {'regular': 'DejaVuSansMono.ttf',  'bold': 'DejaVuSansMono-Bold.ttf'},
    'Liberation Sans':     {'regular': 'LiberationSans-Regular.ttf', 'bold': 'LiberationSans-Bold.ttf'},
    'Liberation Serif':    {'regular': 'LiberationSerif-Regular.ttf', 'bold': 'LiberationSerif-Bold.ttf'},
    'Liberation Mono':     {'regular': 'LiberationMono-Regular.ttf',  'bold': 'LiberationMono-Bold.ttf'},
    'Roboto':              {'regular': 'Roboto-Regular.ttf',  'bold': 'Roboto-Bold.ttf'},
    'Ubuntu':              {'regular': 'Ubuntu-Regular.ttf',  'bold': 'Ubuntu-Bold.ttf'},
}


# Directories to search for font files, populated lazily.
_font_search_dirs: list[Path] | None = None


def _get_font_dirs() -> list[Path]:
    """Return a list of platform-specific font directories."""
    global _font_search_dirs
    if _font_search_dirs is not None:
        return _font_search_dirs

    dirs: list[Path] = []

    # 1. User override via environment variable
    env_dir = os.environ.get('PPT_MASTER_FONT_DIR')
    if env_dir:
        dirs.extend(Path(p.strip()) for p in env_dir.split(os.pathsep) if p.strip())

    # 2. Platform defaults
    if sys.platform == 'win32':
        windir = os.environ.get('WINDIR', r'C:\Windows')
        dirs.append(Path(windir) / 'Fonts')
    elif sys.platform == 'darwin':
        dirs.extend([
            Path('/System/Library/Fonts'),
            Path('/Library/Fonts'),
            Path.home() / 'Library/Fonts',
        ])
    else:  # Linux / Unix
        dirs.extend([
            Path('/usr/share/fonts'),
            Path('/usr/local/share/fonts'),
            Path.home() / '.fonts',
            Path.home() / '.local/share/fonts',
        ])

    _font_search_dirs = dirs
    return dirs


@functools.lru_cache(maxsize=128)
def _resolve_font(font_family: str, font_weight: str = '400', font_style: str = '') -> Path | None:
    """Resolve a font family name to an actual font file path on disk.

    Uses a cross-platform lookup table. Falls back to directory scanning
    if the family is not in the hard-coded map.

    Args:
        font_family: The font family name (e.g. 'Microsoft YaHei').
        font_weight: CSS/SVG font-weight value.
        font_style:  'italic' or ''.

    Returns:
        Path to the font file, or None if not found.
    """
    if not font_family:
        return None

    is_bold = font_weight in ('bold', '600', '700', '800', '900')
    is_italic = font_style == 'italic'

    # Determine variant key
    if is_bold and is_italic:
        variant = 'bold_italic'
    elif is_bold:
        variant = 'bold'
    elif is_italic:
        variant = 'italic'
    else:
        variant = 'regular'

    family_map = _FONT_FILE_MAP.get(font_family)
    if family_map:
        filename = family_map.get(variant) or family_map.get('regular')
        if filename:
            for font_dir in _get_font_dirs():
                candidate = font_dir / filename
                if candidate.exists():
                    return candidate

    # Fallback: scan directories for any file whose stem loosely matches.
    # This catches fonts installed outside the hard-coded map.
    normalized = font_family.lower().replace(' ', '').replace('-', '')
    for font_dir in _get_font_dirs():
        if not font_dir.exists():
            continue
        try:
            for candidate in font_dir.iterdir():
                if candidate.suffix.lower() not in ('.ttf', '.ttc', '.otf', '.dfont'):
                    continue
                stem = candidate.stem.lower().replace(' ', '').replace('-', '')
                if stem == normalized:
                    return candidate
        except (OSError, PermissionError):
            continue

    return None


def is_cjk_char(ch: str) -> bool:
    """Check if a character is CJK (Chinese/Japanese/Korean)."""
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or
            0x2E80 <= cp <= 0x2EFF or 0x3000 <= cp <= 0x303F or
            0xFF00 <= cp <= 0xFFEF or 0xF900 <= cp <= 0xFAFF or
            0x20000 <= cp <= 0x2A6DF)


def estimate_text_width(text: str, font_size: float, font_weight: str = '400', font_family: str = '') -> float:
    """Estimate text width in SVG pixels.

    When Pillow is available and the font file can be resolved on disk,
    uses ``ImageFont.truetype().getlength()`` for precise measurement.
    Otherwise falls back to the legacy per-character heuristic.

    A 2 px safety margin is added to the Pillow path to avoid rounding
    errors causing overflow in PowerPoint.
    """
    if not text:
        return 0.0

    # --- Precise path (Pillow) ---
    if _HAS_PILLOW and font_family:
        font_path = _resolve_font(font_family, font_weight)
        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), int(round(font_size)))
                length = float(font.getlength(text))
                # Add a small safety margin; empirically 2 px avoids
                # sub-pixel rounding issues in PowerPoint.
                return length + 2.0
            except Exception:
                pass  # Fall through to heuristic

    # --- Heuristic fallback ---
    width = 0.0
    for ch in text:
        if is_cjk_char(ch):
            width += font_size
        elif ch == ' ':
            width += font_size * 0.3
        elif ch in 'mMwWOQ':
            width += font_size * 0.75
        elif ch in 'iIlj1!|':
            width += font_size * 0.3
        else:
            width += font_size * 0.55

    if font_weight in ('bold', '600', '700', '800', '900'):
        width *= 1.05

    return width


def _xml_escape(text: str) -> str:
    """Escape XML special characters."""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))
