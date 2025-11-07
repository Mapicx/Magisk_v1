# Agent/tools/pdf_tools.py
# Stylish PDF: Headings in Montserrat (Gotham-ish), body in Source Serif 4 (Times-style).
# Auto-downloads fonts from Google Fonts repo (cached); no local install needed.
# Saves to optimized_resumes/<orig_name>_optimised_<uuid>.pdf

import os
import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, HRFlowable,
    Table, TableStyle
)

# -----------------------------
# Paths & font URLs
# -----------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OPT_DIR = os.path.join(PROJECT_ROOT, "optimized_resumes")
FONT_CACHE_DIR = os.path.join(PROJECT_ROOT, "assets", "font_cache")

# Headings (Gotham-like): Montserrat
MONTS_REG = "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
# Body (Times-like): Source Serif 4
SSER4_REG = "https://raw.githubusercontent.com/google/fonts/main/ofl/sourceserif4/SourceSerif4%5Bwght%5D.ttf"

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

# -----------------------------
# Font registration
# -----------------------------
HEADING_FONT = "Helvetica-Bold"
BODY_FONT = "Helvetica"

def _dl(url: str, target_path: str) -> str:
    _ensure_dir(os.path.dirname(target_path))
    if not os.path.exists(target_path):
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(target_path, "wb") as f:
            f.write(r.content)
    return target_path

def _register_variable_font(name: str, path: str) -> bool:
    try:
        pdfmetrics.registerFont(TTFont(name, path))
        return True
    except Exception:
        return False

def _register_fonts() -> None:
    """
    Register Montserrat (variable) for headings and Source Serif 4 (variable) for body.
    Fallback gracefully to Helvetica if download/registration fails.
    """
    global HEADING_FONT, BODY_FONT
    _ensure_dir(FONT_CACHE_DIR)
    try:
        monopath = _dl(MONTS_REG, os.path.join(FONT_CACHE_DIR, "Montserrat[wght].ttf"))
        sserpath = _dl(SSER4_REG, os.path.join(FONT_CACHE_DIR, "SourceSerif4[wght].ttf"))
        ok1 = _register_variable_font("Montserrat", monopath)
        ok2 = _register_variable_font("SourceSerif4", sserpath)
        if ok1: HEADING_FONT = "Montserrat"
        if ok2: BODY_FONT = "SourceSerif4"
    except Exception:
        # keep Helvetica fallbacks
        pass

_register_fonts()

# -----------------------------
# Styles (smaller, tighter)
# -----------------------------
styles = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    'Title',
    parent=styles['Title'],
    fontName=HEADING_FONT,  # Montserrat (or Helvetica-Bold)
    fontSize=16,            # smaller than before
    leading=19,
    alignment=TA_LEFT,
    textColor=colors.black,
    spaceAfter=2,
)

SUBTITLE_STYLE = ParagraphStyle(
    'Subtitle',
    parent=styles['Normal'],
    fontName=HEADING_FONT,
    fontSize=10,
    leading=12.5,
    textColor=colors.HexColor('#444444'),
    spaceAfter=5
)

CONTACT_STYLE = ParagraphStyle(
    'Contact',
    parent=styles['Normal'],
    fontName=BODY_FONT,
    fontSize=9,
    leading=11.5,
    textColor=colors.HexColor('#555555'),
    spaceAfter=6
)

SECTION_HEADER_STYLE = ParagraphStyle(
    'SectionHeader',
    parent=styles['Heading2'],
    fontName=HEADING_FONT,
    fontSize=10.5,
    leading=13,
    textColor=colors.black,
    backColor=colors.HexColor('#F2F2F2'),
    spaceBefore=10,
    spaceAfter=5,
)

ROLE_LINE_STYLE = ParagraphStyle(
    'RoleLine',
    parent=styles['Normal'],
    fontName=BODY_FONT,
    fontSize=9.8,
    leading=13,
    textColor=colors.HexColor('#222222'),
    spaceAfter=1.6
)

BODY_STYLE = ParagraphStyle(
    'Body',
    parent=styles['Normal'],
    fontName=BODY_FONT,
    fontSize=9.2,
    leading=12.4,
    textColor=colors.black,
    spaceAfter=2.2
)

BULLET_STYLE = ParagraphStyle(
    'Bullet',
    parent=styles['Normal'],
    fontName=BODY_FONT,
    fontSize=9.2,
    leading=12.4,
    leftIndent=13,
    bulletIndent=6,
    spaceBefore=0.2,
    spaceAfter=0.2
)

SMALL_STYLE = ParagraphStyle(
    'Small',
    parent=styles['Normal'],
    fontName=BODY_FONT,
    fontSize=9.0,
    leading=12.0,
    textColor=colors.HexColor('#111111'),
    spaceAfter=1.2
)

# -----------------------------
# Auto-bold utilities
# -----------------------------
KEY_TECH = [
    'Python','LangChain','TensorFlow','PyTorch','Docker','React','FastAPI','RAG','FAISS',
    'Pinecone','Weaviate','Chroma','SQL','PostgreSQL','MongoDB','AWS','GCP','Kubernetes',
    'Solidity','ERC-721','ERC-1155','OpenAI','Hugging Face','Transformers','OpenCV',
    'Brownie','Chainlink','GraphQL','TypeScript','JavaScript','Next.js','Flask','Django'
]
TECH_REGEX = re.compile(r'\b(' + '|'.join(map(re.escape, KEY_TECH)) + r')\b')

def autobold_full(text: str) -> str:
    """Bold numbers/percents AND known tech tokens (used outside Skills)."""
    if not text: return text
    text = re.sub(r'(?<!\w)(~?\d+(?:\.\d+)?%?)', r'<b>\1</b>', text)
    return TECH_REGEX.sub(lambda m: f'<b>{m.group(1)}</b>', text)

def autobold_light(text: str) -> str:
    """Bold numbers/percents only (used inside Skills to avoid over-bolding)."""
    if not text: return text
    return re.sub(r'(?<!\w)(~?\d+(?:\.\d+)?%?)', r'<b>\1</b>', text)

def process_text_formatting(text: Optional[str]) -> str:
    if not text: return ""
    text = re.sub(r'^[\u2022\-\*]\s+', '• ', text, flags=re.MULTILINE)  # normalize bullets
    text = re.sub(r'\*\*([^\*]+)\*\*', r'<b>\1</b>', text)              # markdown bold
    # protect <b> tags then escape
    text = text.replace('<b>', '[[[B]]]').replace('</b>', '[[[/B]]]').replace('<br/>', '[[[BR]]]')
    text = re.sub(r'&(?![a-zA-Z]+;|#\d+;)', '&amp;', text)
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    return text.replace('[[[B]]]', '<b>').replace('[[[/B]]]', '</b>').replace('[[[BR]]]', '<br/>')

# -----------------------------
# Page deco
# -----------------------------
def on_page(canvas, doc):
    canvas.saveState()
    x0 = doc.leftMargin
    x1 = doc.pagesize[0] - doc.rightMargin
    y  = doc.pagesize[1] - doc.topMargin + 5
    canvas.setStrokeColor(colors.HexColor('#DDDDDD'))
    canvas.setLineWidth(0.5)
    canvas.line(x0, y, x1, y)
    canvas.restoreState()

# -----------------------------
# Data model
# -----------------------------
@dataclass
class ResumeData:
    name: str
    title: Optional[str]
    contact: str
    sections: Dict[str, List[str]]

# -----------------------------
# Render helpers
# -----------------------------
def _section_header(title: str) -> List:
    return [Paragraph(process_text_formatting(title.upper()), SECTION_HEADER_STYLE), Spacer(1, 0.05 * inch)]

def _role_or_plain_paragraph(line: str) -> Paragraph:
    if ' - ' in line or '→' in line:
        return Paragraph(process_text_formatting(line), ROLE_LINE_STYLE)
    return Paragraph(process_text_formatting(line), BODY_STYLE)

def _bullet_paragraph(line: str) -> Paragraph:
    raw = line.lstrip('•').strip()
    return Paragraph(process_text_formatting(raw), BULLET_STYLE, bulletText='•')

def _two_column_skills(lines: List[str]) -> List:
    """
    Skills:
      - Only category (before ':') bold.
      - Numbers/percentages bold via autobold_light.
      - Tech tokens NOT auto-bolded here → cleaner second column.
    """
    processed = []
    for ln in lines:
        ln = ln.strip()
        if not ln: continue
        if ':' in ln:
            head, rest = ln.split(':', 1)
            rest = autobold_light(rest)
            ln_out = f"<b>{head.strip()}:</b>{rest}"
        else:
            ln_out = autobold_light(ln)
        processed.append(process_text_formatting(ln_out))

    mid = (len(processed) + 1) // 2
    col1 = '<br/>'.join(processed[:mid])
    col2 = '<br/>'.join(processed[mid:]) if len(processed) > 1 else ''

    tbl = Table([[Paragraph(col1, SMALL_STYLE), Paragraph(col2, SMALL_STYLE)]],
                colWidths=[3.6 * inch, 3.6 * inch])
    tbl.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING',(0,0), (-1,-1), 8),
        ('TOPPADDING',  (0,0), (-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
    ]))
    return [tbl]

# -----------------------------
# PDF renderer
# -----------------------------
def create_optimized_pdf(output_path: str, data: ResumeData):
    _ensure_dir(os.path.dirname(output_path))
    doc = BaseDocTemplate(
        output_path,
        pagesize=LETTER,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    doc.addPageTemplates([PageTemplate(id='page', frames=[frame], onPage=on_page)])

    story: List = []
    # Header (Heading font for name/title, body font for contact)
    story.append(Paragraph(process_text_formatting(data.name), TITLE_STYLE))
    if data.title:
        story.append(Paragraph(process_text_formatting(data.title), SUBTITLE_STYLE))
    story.append(Paragraph(process_text_formatting(data.contact), CONTACT_STYLE))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#DDDDDD')))
    story.append(Spacer(1, 0.05 * inch))

    for sec_title, lines in data.sections.items():
        if not lines: continue
        story.extend(_section_header(sec_title))
        low = sec_title.strip().lower()
        if low in {"technical skills", "skills", "tech skills"}:
            story.extend(_two_column_skills(lines)); continue
        for ln in lines:
            ln = autobold_full(ln)  # outside Skills, allow bolding tech + numbers
            if ln.strip().startswith('•'):
                story.append(_bullet_paragraph(ln))
            else:
                story.append(_role_or_plain_paragraph(ln))

    doc.build(story)

# -----------------------------
# Parsing helpers (Markdown → sections)
# -----------------------------
def _parse_markdown_sections(md: str) -> Dict[str, List[str]]:
    if not md or not isinstance(md, str): return {}
    lines = md.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    sections: Dict[str, List[str]] = {}
    current_title: Optional[str] = None
    buffer: List[str] = []

    def flush():
        nonlocal current_title, buffer
        if current_title is not None:
            content = [ln for ln in buffer if ln is not None]
            compacted: List[str] = []
            prev_blank = False
            for ln in content:
                is_blank = (ln.strip() == "")
                if is_blank and prev_blank: continue
                compacted.append(ln); prev_blank = is_blank
            sections[current_title] = [ln for ln in compacted if ln.strip() or ln == ""]
        buffer = []

    header_re = re.compile(r'^(#{1,6})\s+(.*)\s*$')
    i = 0
    if i < len(lines):
        m = header_re.match(lines[i])
        if m and len(m.group(1)) == 1:
            i += 1  # skip H1 (name)
    while i < len(lines):
        line = lines[i]
        m = header_re.match(line)
        if m:
            flush()
            title = m.group(2).strip()
            current_title = title if title else "Section"
        else:
            if current_title is None:
                current_title = "Summary"
            buffer.append(line)
        i += 1
    flush()
    if not sections and md.strip():
        sections = {"Content": [ln for ln in md.splitlines() if ln.strip()]}
    return sections

def _parse_sections_flex(optimized_text_sections_or_md):
    if optimized_text_sections_or_md is None: return {}
    if isinstance(optimized_text_sections_or_md, dict):
        out = {}
        for k, v in optimized_text_sections_or_md.items():
            if isinstance(v, list): out[k] = v
            elif isinstance(v, str): out[k] = [ln.strip() for ln in v.splitlines() if ln.strip()]
            else: out[k] = [str(v)]
        return out
    if isinstance(optimized_text_sections_or_md, str):
        text = optimized_text_sections_or_md
        if re.search(r'^\s*#{1,6}\s+\S+', text, flags=re.MULTILINE):
            return _parse_markdown_sections(text)
        # naive key: value fallback
        lines = text.splitlines()
        current_key = None; buff = []; result = {}
        def flush():
            nonlocal current_key, buff, result
            if current_key is not None:
                chunk = "\n".join(buff).strip()
                section_lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
                result[current_key] = section_lines
            current_key, buff = None, []
        for raw in lines:
            ln = raw.strip()
            if not ln: buff.append(""); continue
            if ':' in ln:
                key_candidate, rest = ln.split(':', 1)
                key_norm = key_candidate.strip().lower().replace(" ", "_")
                if key_norm.isidentifier():
                    flush(); current_key = key_candidate.strip()
                    if rest.strip(): buff.append(rest.strip()); continue
            buff.append(ln)
        flush()
        if not result: result = {"Content": [l for l in lines if l.strip()]}
        return result
    return {"Content": [str(optimized_text_sections_or_md)]}

def _normalize_call_args(args, kwargs):
    merged = dict(kwargs or {})
    order = ["optimized_text_sections", "output_path", "name", "title", "contact_line"]
    for i, val in enumerate(args or ()):
        if i < len(order) and order[i] not in merged:
            merged[order[i]] = val
    if "optimized_markdown" in merged and "optimized_text_sections" not in merged:
        merged["optimized_text_sections"] = merged.pop("optimized_markdown")
    merged.setdefault("optimized_text_sections", {})
    merged.setdefault("output_path", "optimized_resume.pdf")
    merged.setdefault("name", "Candidate")
    merged.setdefault("title", None)
    merged.setdefault("contact_line", "")
    merged["optimized_text_sections"] = _parse_sections_flex(merged["optimized_text_sections"])
    return merged

# -----------------------------
# Public API (tolerant)
# -----------------------------
def execute_resume_optimization(*args, **kwargs):
    """
    Tolerant wrapper.
    Accepted kwargs:
      - output_path (ignored if original_file_name provided; kept for compatibility)
      - optimized_text_sections (dict | str | markdown)
      - name, contact_line, title
      - original_file_name (optional) -> builds '<orig>_optimised_<uuid>.pdf'
    """
    if args:  # drop stray positional arg (e.g., state)
        args = args[1:]

    original_file_name = kwargs.pop("original_file_name", None)
    output_path = kwargs.get("output_path", "optimized_resume.pdf")
    name         = kwargs.get("name", "Candidate")
    title        = kwargs.get("title")
    contact_line = kwargs.get("contact_line", "")
    optimized_text_sections = kwargs.get("optimized_text_sections")

    _ensure_dir(OPT_DIR)
    if original_file_name:
        base = os.path.splitext(os.path.basename(original_file_name))[0]
        dest_name = f"{base}_optimised_{uuid.uuid4().hex}.pdf"
        output_path = os.path.join(OPT_DIR, dest_name)
    else:
        dest_name = os.path.basename(output_path)
        output_path = os.path.join(OPT_DIR, dest_name)

    if isinstance(optimized_text_sections, str):
        optimized_text_sections = _parse_markdown_sections(optimized_text_sections)

    data = ResumeData(
        name=name,
        title=title,
        contact=contact_line,
        sections=optimized_text_sections or {},
    )
    create_optimized_pdf(output_path, data)
    return f"Saved optimized PDF to {output_path}"

def optimize_resume_sections(*args, **kwargs):
    merged = _normalize_call_args(args, kwargs)
    return execute_resume_optimization(
        output_path=merged["output_path"],
        optimized_text_sections=merged["optimized_text_sections"],
        name=merged["name"],
        title=merged["title"],
        contact_line=merged["contact_line"],
    )

optimize = optimize_resume_sections
