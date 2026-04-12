"""Convert all Markdown files in docs/sprint-review/ to PDF using fpdf2.

Produces professionally formatted PDFs with:
- Dynamic table column widths with header repetition on page breaks
- Code blocks with line wrapping (no truncation)
- Properly sized blockquote backgrounds
- Clean typography with consistent spacing
"""

import os
import re
from fpdf import FPDF
from fpdf.enums import XPos, YPos

SPRINT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "sprint-review")

# ── Layout ────────────────────────────────────────────────────────
LEFT_MARGIN  = 18
RIGHT_MARGIN = 18
TOP_MARGIN   = 22
BOTTOM_MARGIN = 22
PAGE_W       = 210
CONTENT_W    = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN  # 174 mm

# ── Colours ───────────────────────────────────────────────────────
C_PRIMARY      = (30, 50, 95)
C_ACCENT       = (42, 93, 168)
C_HEADING3     = (50, 60, 76)
C_TEXT         = (35, 35, 35)
C_MUTED        = (120, 128, 140)
C_CODE_BG      = (245, 246, 248)
C_CODE_BORDER  = (210, 215, 222)
C_TABLE_HEADER = (30, 50, 95)
C_TABLE_ALT    = (242, 244, 250)
C_TABLE_BORDER = (200, 205, 215)
C_QUOTE_BAR    = (42, 93, 168)
C_QUOTE_BG     = (237, 242, 250)
C_HR           = (200, 205, 215)
C_WHITE        = (255, 255, 255)
C_BLACK        = (0, 0, 0)


# ══════════════════════════════════════════════════════════════════
#  Unicode → latin-1 sanitiser
# ══════════════════════════════════════════════════════════════════
_UNICODE_MAP = {
    '\u2014': '--', '\u2013': '-', '\u2018': "'", '\u2019': "'",
    '\u201c': '"',  '\u201d': '"', '\u2026': '...', '\u2192': '->',
    '\u2190': '<-', '\u2194': '<->', '\u2022': '-', '\u25cf': '-',
    '\u2713': '[x]', '\u2705': '[x]', '\u2717': '[ ]', '\u00a0': ' ',
    '\u25b6': '>', '\u25bc': 'v', '\u25b2': '^', '\u25c4': '<',
    '\u2502': '|', '\u2500': '-', '\u2551': '|', '\u2550': '=',
    '\u26a0': '!',
}
for _ch in ('\u250c\u2510\u2514\u2518\u251c\u2524\u252c\u2534\u253c'
            '\u255e\u2561\u2564\u2567\u256a\u2554\u2557\u255a\u255d'
            '\u2560\u2563\u2566\u2569\u256c'):
    _UNICODE_MAP[_ch] = '+'
for _ch in '\u2591\u2588\u25a0':
    _UNICODE_MAP[_ch] = '#'
for _ch in '\u258c\u2590':
    _UNICODE_MAP[_ch] = '|'
_UNICODE_MAP['\u25a1'] = '[ ]'
_UNICODE_MAP['\u25cb'] = 'o'


def sanitize(text):
    """Replace Unicode chars outside latin-1 with ASCII equivalents."""
    for old, new in _UNICODE_MAP.items():
        text = text.replace(old, new)
    out = []
    for ch in text:
        try:
            ch.encode('latin-1')
            out.append(ch)
        except UnicodeEncodeError:
            out.append('?')
    return ''.join(out)


def strip_md_bold(text):
    return re.sub(r'\*\*([^*]+)\*\*', r'\1', text)


# ══════════════════════════════════════════════════════════════════
#  PDF class with header / footer
# ══════════════════════════════════════════════════════════════════
class MarkdownPDF(FPDF):
    def __init__(self, title=""):
        super().__init__()
        self.doc_title = title
        self.set_margins(LEFT_MARGIN, TOP_MARGIN, RIGHT_MARGIN)
        self.set_auto_page_break(auto=True, margin=BOTTOM_MARGIN)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C_MUTED)
        self.cell(CONTENT_W, 6, self.doc_title,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        y = self.get_y()
        self.set_draw_color(*C_HR)
        self.line(LEFT_MARGIN, y, PAGE_W - RIGHT_MARGIN, y)
        self.set_draw_color(*C_BLACK)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*C_MUTED)
        self.cell(CONTENT_W, 8, f"Page {self.page_no()}/{{nb}}",
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.TOP)

    @property
    def usable_y(self):
        return self.h - BOTTOM_MARGIN - self.get_y()

    def need_space(self, h):
        if self.usable_y < h:
            self.add_page()


# ══════════════════════════════════════════════════════════════════
#  Markdown parser
# ══════════════════════════════════════════════════════════════════
def parse_blocks(md_text):
    lines = md_text.split('\n')
    blocks = []
    i = 0
    in_code = False
    code_lines = []
    in_table = False
    table_rows = []

    def flush_table():
        nonlocal in_table, table_rows
        if in_table and table_rows:
            blocks.append(('table', list(table_rows)))
        table_rows.clear()
        in_table = False

    while i < len(lines):
        line = lines[i]

        # ── code fence ────
        if line.strip().startswith('```'):
            if in_code:
                blocks.append(('code', '\n'.join(code_lines)))
                code_lines = []
                in_code = False
            else:
                flush_table()
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # ── table ────
        if '|' in line and line.strip().startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if all(re.match(r'^[-:]+$', c) for c in cells if c):
                i += 1
                continue
            in_table = True
            table_rows.append(cells)
            i += 1
            continue
        else:
            flush_table()

        # ── heading ────
        m = re.match(r'^(#{1,6})\s+(.*)', line)
        if m:
            blocks.append(('heading', len(m.group(1)), m.group(2).strip()))
            i += 1
            continue

        # ── horizontal rule ────
        if re.match(r'^---+\s*$', line.strip()):
            blocks.append(('hr',))
            i += 1
            continue

        # ── blockquote (collect consecutive lines) ────
        if line.strip().startswith('>'):
            quote_parts = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                txt = re.sub(r'^>\s?', '', lines[i])
                quote_parts.append(txt)
                i += 1
            blocks.append(('quote', '\n'.join(quote_parts)))
            continue

        # ── checkbox ────
        cm = re.match(r'^(\s*)[-*+]\s+\[([ xX])\]\s+(.*)', line)
        if cm:
            blocks.append(('checkbox', len(cm.group(1)),
                           cm.group(2).lower() == 'x', cm.group(3)))
            i += 1
            continue

        # ── bullet ────
        bm = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if bm:
            blocks.append(('bullet', len(bm.group(1)), bm.group(2)))
            i += 1
            continue

        # ── numbered list ────
        nm = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
        if nm:
            blocks.append(('numbered', len(nm.group(1)),
                           nm.group(2), nm.group(3)))
            i += 1
            continue

        # ── blank ────
        if line.strip() == '':
            blocks.append(('blank',))
            i += 1
            continue

        # ── text ────
        blocks.append(('text', line))
        i += 1

    if in_code and code_lines:
        blocks.append(('code', '\n'.join(code_lines)))
    flush_table()
    return blocks


# ══════════════════════════════════════════════════════════════════
#  Inline formatting writer  (**bold**, *italic*, `code`)
# ══════════════════════════════════════════════════════════════════
def write_inline(pdf, text, size=10):
    text = sanitize(text)
    parts = re.split(
        r'(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|_[^_]+_)', text)
    h = size * 0.55
    for p in parts:
        if not p:
            continue
        if p.startswith('**') and p.endswith('**'):
            pdf.set_font("Helvetica", "B", size)
            pdf.write(h, p[2:-2])
            pdf.set_font("Helvetica", "", size)
        elif p.startswith('__') and p.endswith('__'):
            pdf.set_font("Helvetica", "B", size)
            pdf.write(h, p[2:-2])
            pdf.set_font("Helvetica", "", size)
        elif p.startswith('`') and p.endswith('`'):
            pdf.set_font("Courier", "", size - 1)
            pdf.set_text_color(155, 35, 35)
            pdf.write(h, p[1:-1])
            pdf.set_text_color(*C_TEXT)
            pdf.set_font("Helvetica", "", size)
        elif p.startswith('*') and p.endswith('*') and len(p) > 2:
            pdf.set_font("Helvetica", "I", size)
            pdf.write(h, p[1:-1])
            pdf.set_font("Helvetica", "", size)
        elif p.startswith('_') and p.endswith('_') and len(p) > 2:
            pdf.set_font("Helvetica", "I", size)
            pdf.write(h, p[1:-1])
            pdf.set_font("Helvetica", "", size)
        else:
            pdf.write(h, p)


# ══════════════════════════════════════════════════════════════════
#  Table renderer — dynamic widths, wrapping, header repetition
# ══════════════════════════════════════════════════════════════════
def _calc_col_widths(pdf, rows, font_size):
    num_cols = max(len(r) for r in rows)
    raw = [0.0] * num_cols
    for row in rows:
        for ci in range(num_cols):
            cell = strip_md_bold(sanitize(row[ci])) if ci < len(row) else ''
            pdf.set_font("Helvetica", "", font_size)
            w = pdf.get_string_width(cell)
            raw[ci] = max(raw[ci], w)
    raw = [w + 6 for w in raw]
    total = sum(raw) or 1
    if total <= CONTENT_W:
        spare = CONTENT_W - total
        widths = [w + spare / num_cols for w in raw]
    else:
        widths = [w / total * CONTENT_W for w in raw]
    min_w = max(10, CONTENT_W / num_cols * 0.3)
    for i in range(num_cols):
        widths[i] = max(widths[i], min_w)
    s = sum(widths)
    return [w / s * CONTENT_W for w in widths]


def _wrap_cell_text(pdf, text, width, font, style, size):
    """Word-wrap text with character-level breaking for long words."""
    pdf.set_font(font, style, size)
    usable = width - 4
    if usable <= 0:
        return [text[:20]] if text else [""]
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        if pdf.get_string_width(test) <= usable:
            cur = test
        else:
            if cur:
                lines.append(cur)
            if pdf.get_string_width(w) > usable:
                chunk = ""
                for ch in w:
                    if pdf.get_string_width(chunk + ch) <= usable:
                        chunk += ch
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = ch
                cur = chunk
            else:
                cur = w
    if cur:
        lines.append(cur)
    return lines if lines else [""]


def _draw_table_row(pdf, cells, widths, is_header, font_size, line_h, row_even):
    """Draw one table row, returning its height."""
    num_cols = len(widths)
    cell_pad = 1.5

    cell_lines = []
    for ci in range(num_cols):
        raw = sanitize(cells[ci]) if ci < len(cells) else ''
        raw = strip_md_bold(raw)
        style = "B" if is_header else ""
        lines = _wrap_cell_text(pdf, raw, widths[ci],
                                "Helvetica", style, font_size)
        cell_lines.append(lines)

    max_lines = max(len(cl) for cl in cell_lines)
    row_h = max_lines * line_h + cell_pad * 2
    start_y = pdf.get_y()
    x = LEFT_MARGIN

    # Disable auto page break — page splitting is managed by render_table
    pdf.set_auto_page_break(auto=False)

    for ci in range(num_cols):
        w = widths[ci]
        if is_header:
            pdf.set_fill_color(*C_TABLE_HEADER)
            pdf.set_draw_color(*C_TABLE_HEADER)
        else:
            bg = C_TABLE_ALT if row_even else C_WHITE
            pdf.set_fill_color(*bg)
            pdf.set_draw_color(*C_TABLE_BORDER)
        pdf.rect(x, start_y, w, row_h, 'DF')

        if is_header:
            pdf.set_font("Helvetica", "B", font_size)
            pdf.set_text_color(*C_WHITE)
        else:
            pdf.set_font("Helvetica", "", font_size)
            pdf.set_text_color(*C_TEXT)

        ty = start_y + cell_pad
        for ln in cell_lines[ci]:
            pdf.set_xy(x + 2, ty)
            pdf.cell(w - 4, line_h, ln,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            ty += line_h
        x += w

    pdf.set_y(start_y + row_h)
    # Re-enable auto page break
    pdf.set_auto_page_break(auto=True, margin=BOTTOM_MARGIN)
    return row_h


def render_table(pdf, rows):
    if not rows:
        return
    num_cols = max(len(r) for r in rows)
    if num_cols == 0:
        return

    # Adaptive font / line height
    if num_cols <= 3:
        font_size, line_h = 9, 5
    elif num_cols <= 5:
        font_size, line_h = 8.5, 4.8
    elif num_cols <= 6:
        font_size, line_h = 8, 4.5
    else:
        font_size, line_h = 7.5, 4.2

    widths = _calc_col_widths(pdf, rows, font_size)
    header = rows[0]

    # Ensure enough room for at least the header row before starting
    pdf.need_space(line_h + 6)
    pdf.ln(3)
    _draw_table_row(pdf, header, widths, True, font_size, line_h, False)

    for ri in range(1, len(rows)):
        row = rows[ri]
        # Pre-measure row to check page break
        pre_lines = []
        for ci in range(num_cols):
            raw = strip_md_bold(sanitize(row[ci] if ci < len(row) else ''))
            pre_lines.append(
                _wrap_cell_text(pdf, raw, widths[ci],
                                "Helvetica", "", font_size))
        max_l = max(len(cl) for cl in pre_lines)
        est_h = max_l * line_h + 3

        if pdf.usable_y < est_h:
            pdf.add_page()
            _draw_table_row(pdf, header, widths, True,
                            font_size, line_h, False)

        _draw_table_row(pdf, row, widths, False,
                        font_size, line_h, ri % 2 == 0)

    pdf.set_text_color(*C_TEXT)
    pdf.set_draw_color(*C_BLACK)
    pdf.ln(4)


# ══════════════════════════════════════════════════════════════════
#  Code block renderer — wraps long lines, page-spanning
# ══════════════════════════════════════════════════════════════════
def _wrap_code_lines(lines, max_chars):
    """Wrap long code lines instead of truncating."""
    wrapped = []
    for line in lines:
        if len(line) <= max_chars:
            wrapped.append(line)
        else:
            pos = 0
            first = True
            while pos < len(line):
                end = pos + max_chars if first else pos + max_chars - 2
                chunk = line[pos:end]
                if not first:
                    chunk = '  ' + chunk
                wrapped.append(chunk)
                pos = end
                first = False
    return wrapped


def _draw_code_box(pdf, lines, line_h, pad, x, w, inner_x, font_size):
    h = len(lines) * line_h + pad * 2
    y = pdf.get_y()
    # Disable auto page break — page splitting is managed by render_code
    pdf.set_auto_page_break(auto=False)
    pdf.set_fill_color(*C_CODE_BG)
    pdf.set_draw_color(*C_CODE_BORDER)
    pdf.rect(x, y, w, h, 'DF')
    # Left accent bar
    pdf.set_fill_color(*C_ACCENT)
    pdf.rect(x, y, 1.5, h, 'F')
    # Text
    pdf.set_font("Courier", "", font_size)
    pdf.set_text_color(*C_TEXT)
    ty = y + pad
    for cl in lines:
        pdf.set_xy(inner_x, ty)
        pdf.cell(w - 8, line_h, cl, new_x=XPos.RIGHT, new_y=YPos.TOP)
        ty += line_h
    pdf.set_y(y + h)
    # Re-enable auto page break
    pdf.set_auto_page_break(auto=True, margin=BOTTOM_MARGIN)
    pdf.set_draw_color(*C_BLACK)


def render_code(pdf, code_text):
    code_text = sanitize(code_text)

    font_size = 7
    pdf.set_font("Courier", "", font_size)
    char_w = pdf.get_string_width('M')
    usable_w = CONTENT_W - 8
    max_chars = max(40, int(usable_w / char_w))

    raw_lines = code_text.split('\n')
    lines = _wrap_code_lines(raw_lines, max_chars)

    line_h = 3.8
    pad = 3
    code_x = LEFT_MARGIN
    code_w = CONTENT_W
    inner_x = code_x + 4

    pdf.ln(3)

    total_h = len(lines) * line_h + pad * 2
    if total_h <= pdf.usable_y:
        _draw_code_box(pdf, lines, line_h, pad,
                       code_x, code_w, inner_x, font_size)
    else:
        remaining = list(lines)
        while remaining:
            avail = pdf.usable_y - pad * 2
            # If not enough space for even 1 line, go to next page first
            if avail < line_h:
                pdf.add_page()
                avail = pdf.usable_y - pad * 2
            n_fit = max(1, int(avail / line_h))
            chunk = remaining[:n_fit]
            remaining = remaining[n_fit:]
            _draw_code_box(pdf, chunk, line_h, pad,
                           code_x, code_w, inner_x, font_size)
            if remaining:
                pdf.add_page()

    pdf.ln(3)


# ══════════════════════════════════════════════════════════════════
#  Blockquote renderer — proper height measurement
# ══════════════════════════════════════════════════════════════════
def _count_text_lines(pdf, text, width, font, style, size):
    """Count visual lines when word-wrapping text to width."""
    pdf.set_font(font, style, size)
    words = text.split()
    if not words:
        return 1
    lines = 1
    cur_w = 0.0
    sp_w = pdf.get_string_width(' ')
    for w in words:
        ww = pdf.get_string_width(w)
        if cur_w > 0 and cur_w + sp_w + ww > width:
            lines += 1
            cur_w = ww
        else:
            cur_w += (sp_w if cur_w > 0 else 0) + ww
    return lines


def render_blockquote(pdf, text):
    text = sanitize(strip_md_bold(text))

    qx = LEFT_MARGIN + 2
    qw = CONTENT_W - 4
    text_x = qx + 8
    text_w = qw - 12
    line_h = 5.5
    pad = 4

    text_lines = text.split('\n')
    total_vis = 0
    for tl in text_lines:
        tl = tl.strip()
        if not tl:
            total_vis += 1
        else:
            total_vis += _count_text_lines(
                pdf, tl, text_w, "Helvetica", "I", 10)

    box_h = total_vis * line_h + pad * 2
    pdf.need_space(box_h + 4)
    y0 = pdf.get_y()

    # Background
    pdf.set_fill_color(*C_QUOTE_BG)
    pdf.rect(qx, y0, qw, box_h, 'F')
    # Accent bar
    pdf.set_fill_color(*C_QUOTE_BAR)
    pdf.rect(qx, y0, 2.5, box_h, 'F')

    # Render text line-by-line for precise positioning
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*C_HEADING3)
    ty = y0 + pad

    for tl in text_lines:
        tl = tl.strip()
        if not tl:
            ty += line_h
            continue
        words = tl.split()
        visual = ""
        for w in words:
            test = f"{visual} {w}".strip()
            pdf.set_font("Helvetica", "I", 10)
            if pdf.get_string_width(test) <= text_w:
                visual = test
            else:
                if visual:
                    pdf.set_xy(text_x, ty)
                    pdf.cell(text_w, line_h, visual,
                             new_x=XPos.RIGHT, new_y=YPos.TOP)
                    ty += line_h
                visual = w
        if visual:
            pdf.set_xy(text_x, ty)
            pdf.cell(text_w, line_h, visual,
                     new_x=XPos.RIGHT, new_y=YPos.TOP)
            ty += line_h

    pdf.set_y(y0 + box_h + 2)
    pdf.set_text_color(*C_TEXT)


# ══════════════════════════════════════════════════════════════════
#  Main block dispatcher
# ══════════════════════════════════════════════════════════════════
def render_blocks(pdf, blocks):
    page_break_y = pdf.h - BOTTOM_MARGIN

    for block in blocks:
        btype = block[0]

        # Safety guard: if Y overflowed past the page bottom
        # (from rect/set_y in code boxes), start a fresh page
        if pdf.page > 0 and pdf.get_y() > page_break_y:
            pdf.add_page()

        # ── HEADING ───────────────────────────────────────────────
        if btype == 'heading':
            level, text = block[1], sanitize(block[2])
            sizes = {1: 18, 2: 14, 3: 12, 4: 11, 5: 10, 6: 9.5}
            size = sizes.get(level, 10)
            pdf.need_space(18)

            if level == 1:
                pdf.ln(2)
                pdf.set_fill_color(*C_PRIMARY)
                pdf.set_text_color(*C_WHITE)
                pdf.set_font("Helvetica", "B", size)
                # Use multi_cell so long titles wrap instead of being clipped
                pdf.multi_cell(CONTENT_W, 10, f"  {text}",
                               new_x=XPos.LMARGIN, new_y=YPos.NEXT,
                               fill=True, align="L")
                pdf.set_text_color(*C_TEXT)
                pdf.ln(5)
            elif level == 2:
                pdf.ln(6)
                pdf.set_font("Helvetica", "B", size)
                pdf.set_text_color(*C_PRIMARY)
                pdf.cell(CONTENT_W, 9, text,
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                y = pdf.get_y()
                pdf.set_draw_color(*C_ACCENT)
                pdf.set_line_width(0.4)
                pdf.line(LEFT_MARGIN, y, LEFT_MARGIN + CONTENT_W * 0.35, y)
                pdf.set_line_width(0.2)
                pdf.set_draw_color(*C_BLACK)
                pdf.set_text_color(*C_TEXT)
                pdf.ln(3)
            elif level == 3:
                pdf.ln(4)
                pdf.set_font("Helvetica", "B", size)
                pdf.set_text_color(*C_HEADING3)
                pdf.cell(CONTENT_W, 8, text,
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(*C_TEXT)
                pdf.ln(2)
            else:
                pdf.ln(3)
                pdf.set_font("Helvetica", "B", size)
                pdf.set_text_color(*C_HEADING3)
                pdf.cell(CONTENT_W, 7, text,
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(*C_TEXT)
                pdf.ln(2)

        # ── PARAGRAPH ─────────────────────────────────────────────
        elif btype == 'text':
            pdf.need_space(8)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*C_TEXT)
            write_inline(pdf, block[1])
            pdf.ln(5.5)

        # ── BULLET ────────────────────────────────────────────────
        elif btype == 'bullet':
            pdf.need_space(8)
            indent, text = block[1], block[2]
            depth = min(indent // 2, 3)
            x = LEFT_MARGIN + 5 + depth * 6
            marker = '-' if depth > 0 else '*'
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*C_TEXT)
            pdf.set_x(x)
            pdf.write(5.5, f"{marker}  ")
            write_inline(pdf, text)
            pdf.ln(4.5)

        # ── CHECKBOX ──────────────────────────────────────────────
        elif btype == 'checkbox':
            pdf.need_space(8)
            indent, checked, text = block[1], block[2], block[3]
            depth = min(indent // 2, 3)
            x = LEFT_MARGIN + 5 + depth * 6
            marker = '[x]' if checked else '[ ]'
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*C_TEXT)
            pdf.set_x(x)
            pdf.write(5.5, f"{marker}  ")
            write_inline(pdf, text)
            pdf.ln(4.5)

        # ── NUMBERED LIST ─────────────────────────────────────────
        elif btype == 'numbered':
            pdf.need_space(8)
            indent, num, text = block[1], block[2], block[3]
            depth = min(indent // 2, 3)
            x = LEFT_MARGIN + 5 + depth * 6
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*C_TEXT)
            pdf.set_x(x)
            pdf.write(5.5, f"{num}. ")
            write_inline(pdf, text)
            pdf.ln(4.5)

        # ── BLOCKQUOTE ────────────────────────────────────────────
        elif btype == 'quote':
            pdf.ln(2)
            render_blockquote(pdf, block[1])
            pdf.ln(2)

        # ── CODE ──────────────────────────────────────────────────
        elif btype == 'code':
            render_code(pdf, block[1])

        # ── TABLE ─────────────────────────────────────────────────
        elif btype == 'table':
            render_table(pdf, block[1])

        # ── HORIZONTAL RULE ───────────────────────────────────────
        elif btype == 'hr':
            pdf.need_space(12)
            pdf.ln(4)
            pdf.set_draw_color(*C_HR)
            y = pdf.get_y()
            pdf.line(LEFT_MARGIN, y, LEFT_MARGIN + CONTENT_W, y)
            pdf.set_draw_color(*C_BLACK)
            pdf.ln(4)

        # ── BLANK ─────────────────────────────────────────────────
        elif btype == 'blank':
            if pdf.usable_y > 4:
                pdf.ln(2)


# ══════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════
def convert_md_to_pdf(md_path, pdf_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    title_match = re.match(r'^#\s+(.+)', md_text)
    title = sanitize(title_match.group(1).strip()) \
        if title_match else os.path.basename(md_path)

    pdf = MarkdownPDF(title=title)
    pdf.alias_nb_pages()
    pdf.add_page()

    blocks = parse_blocks(md_text)
    render_blocks(pdf, blocks)

    pdf.output(pdf_path)
    print(f"  Created: {os.path.basename(pdf_path)}")


def main():
    sprint_dir = os.path.abspath(SPRINT_DIR)
    print(f"Converting markdown files in: {sprint_dir}\n")

    md_files = sorted(f for f in os.listdir(sprint_dir) if f.endswith('.md'))
    if not md_files:
        print("No markdown files found.")
        return

    for md_file in md_files:
        md_path = os.path.join(sprint_dir, md_file)
        pdf_file = md_file.replace('.md', '.pdf')
        pdf_path = os.path.join(sprint_dir, pdf_file)
        try:
            convert_md_to_pdf(md_path, pdf_path)
        except Exception as e:
            import traceback
            print(f"  ERROR converting {md_file}: {e}")
            traceback.print_exc()

    print(f"\nDone. {len(md_files)} files processed.")


if __name__ == "__main__":
    main()
