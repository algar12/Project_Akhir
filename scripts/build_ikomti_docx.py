#!/usr/bin/env python3
"""
build_ikomti_docx.py — Konversi Artikel_Ilmiah_Unified_Network_Guard.md
menjadi file .docx yang diturunkan dari template IKOMTI (style/font/margin
mengikuti template). Output: artikel/Artikel_Ilmiah_Unified_Network_Guard.docx
"""
import re
from pathlib import Path
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parent.parent
TPL  = ROOT / "artikel" / "IKOMTI - Journal Template (Nov 2023).docx"
SRC  = ROOT / "artikel" / "Artikel_Ilmiah_Unified_Network_Guard.md"
OUT  = ROOT / "artikel" / "Artikel_Ilmiah_Unified_Network_Guard.docx"

doc = Document(str(TPL))

# --- kosongkan isi body template, pertahankan styles & sectPr ---
body = doc.element.body
for child in list(body):
    if child.tag.endswith('}sectPr'):
        continue
    body.remove(child)


# ---------- helper inline formatting (bold/italic/code) ----------
def add_runs(p, text):
    """Parse **bold**, *italic*, `code` dan terapkan ke paragraph p."""
    # tokenisasi: urutan potongan dengan markup
    pattern = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)')
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            p.add_run(text[pos:m.start()])
        tok = m.group()
        if tok.startswith('**') and tok.endswith('**'):
            r = p.add_run(tok[2:-2]); r.bold = True
        elif tok.startswith('*') and tok.endswith('*'):
            r = p.add_run(tok[1:-1]); r.italic = True
        elif tok.startswith('`') and tok.endswith('`'):
            r = p.add_run(tok[1:-1]); r.font.name = 'Courier New'; r.font.size = Pt(10)
        pos = m.end()
    if pos < len(text):
        p.add_run(text[pos:])


def set_table_borders(table):
    """Tambah border garis tunggal pada seluruh sisi tabel (kompatibel template)."""
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '4')
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), '000000')
        borders.append(el)
    tblPr.append(borders)


def style_of(line):
    """Kembalikan (level, text) untuk heading, atau (0, line) bila bukan heading."""
    m = re.match(r'^(#{1,4})\s+(.*)$', line)
    if m:
        return len(m.group(1)), m.group(2).strip()
    return 0, line


# ---------- parse markdown ----------
lines = SRC.read_text(encoding='utf-8').splitlines()
i = 0
H1 = 'Heading 1'; H2 = 'Heading 2'; H3 = 'Heading 3'
PT = 'paper title'

def add_para(style, text=''):
    p = doc.add_paragraph(style=style)
    if text:
        add_runs(p, text)
    return p

while i < len(lines):
    line = lines[i]
    # --- judul utama (# ...) → paper title ---
    if line.startswith('# ') and not line.startswith('## '):
        add_para(PT, line[2:].strip())
        i += 1; continue
    lvl, txt = style_of(line)
    if lvl == 2:
        # ## Abstrak / ## Abstract / ## 1. Pendahuluan / ## Daftar Pustaka
        add_para(H1, re.sub(r'^\d+\.\s*', '', txt))
        i += 1; continue
    if lvl == 3:
        add_para(H2, re.sub(r'^\d+\.\d+\s*', '', txt))
        i += 1; continue
    if lvl == 4:
        add_para(H3, re.sub(r'^\d+\.\d+\.\d+\s*', '', txt))
        i += 1; continue
    # --- code block ```
    if line.strip().startswith('```'):
        i += 1
        code = []
        while i < len(lines) and not lines[i].strip().startswith('```'):
            code.append(lines[i]); i += 1
        i += 1  # skip closing ```
        p = doc.add_paragraph(style='Body Text')
        r = p.add_run('\n'.join(code))
        r.font.name = 'Courier New'; r.font.size = Pt(9)
        continue
    # --- formula $$ ... $$  (bisa multi-baris) ---
    if line.strip().startswith('$$'):
        s = line.strip()
        # formula satu-baris: $$...$$ pada baris yang sama
        if s.count('$$') >= 2:
            p = doc.add_paragraph(style='RESTI_BodyText')
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(s.replace('$$', ''))
            i += 1
            continue
        formula = [s.replace('$$', '')]
        i += 1
        while i < len(lines) and '$$' not in lines[i]:
            formula.append(lines[i]); i += 1
        if i < len(lines):
            tail = lines[i].split('$$', 1)
            if tail[0].strip():
                formula.append(tail[0])
            i += 1
        p = doc.add_paragraph(style='RESTI_BodyText')
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run('\n'.join(x for x in formula if x.strip()))
        continue
    # --- tabel ---
    if line.strip().startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|[\s:|-]+\|?\s*$', lines[i+1]):
        # header
        hdr = [c.strip() for c in line.strip().strip('|').split('|')]
        i += 2  # skip header + separator
        rows = [hdr]
        while i < len(lines) and lines[i].strip().startswith('|'):
            rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
            i += 1
        t = doc.add_table(rows=len(rows), cols=len(hdr))
        set_table_borders(t)
        for ri, row in enumerate(rows):
            for ci, cell in enumerate(row):
                if ci < len(row):
                    tc = t.cell(ri, ci)
                    tc.text = ''
                    pp = tc.paragraphs[0]
                    add_runs(pp, cell)
                    if ri == 0:
                        for r in pp.runs:
                            r.bold = True
        doc.add_paragraph('')  # spacer
        continue
    # --- bullet list ---
    if re.match(r'^\s*[-*]\s+', line):
        txt = re.sub(r'^\s*[-*]\s+', '', line)
        p = doc.add_paragraph(style='List Paragraph')
        p.paragraph_format.left_indent = Pt(18)
        p.add_run('• ')
        add_runs(p, txt)
        i += 1; continue
    # --- numbered list ---
    m = re.match(r'^\s*(\d+)\.\s+(.*)$', line)
    if m:
        p = doc.add_paragraph(style='List Paragraph')
        p.paragraph_format.left_indent = Pt(18)
        p.add_run(f"{m.group(1)}. ")
        add_runs(p, m.group(2))
        i += 1; continue
    # --- baris kosong ---
    if not line.strip():
        i += 1; continue
    # --- baris meta (**Penulis:**, **Afiliasi:**, **Kontak:**, ---) ---
    if line.strip() == '---':
        i += 1; continue
    # --- referensi [n] ... → style 'references' ---
    if re.match(r'^\[(\d+)\]\s', line.strip()):
        p = doc.add_paragraph(style='references')
        add_runs(p, line.strip())
        i += 1; continue
    # --- baris penutup *...*  ---
    if line.strip().startswith('*') and line.strip().endswith('*') and not line.strip().startswith('**'):
        p = add_para('Body Text', line.strip().strip('*'))
        for r in p.runs:
            r.italic = True
        i += 1; continue
    # --- paragraf biasa (gabung multi-baris) ---
    para = [line]
    j = i + 1
    while j < len(lines) and lines[j].strip() and not lines[j].startswith('#') \
          and not lines[j].strip().startswith('|') and not lines[j].strip().startswith('```') \
          and not lines[j].strip().startswith('$$') and not re.match(r'^\s*[-*]\s+', lines[j]) \
          and not re.match(r'^\s*\d+\.\s+', lines[j]) and not re.match(r'^\[(\d+)\]\s', lines[j].strip()):
        para.append(lines[j]); j += 1
    i = j
    p = add_para('Body Text', ' '.join(x.strip() for x in para))

doc.save(str(OUT))
print(f"OK → {OUT}  ({OUT.stat().st_size} bytes)")
