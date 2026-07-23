import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


# ---------------------------------------------------------------------------
# PDF Generation using ReportLab (Pure Python, Cross-Platform)
# ---------------------------------------------------------------------------

def _draw_page_number(canvas, doc):
    """
    Draws header page number '2.' in top-right corner on pages 2+.
    """
    if doc.page > 1:
        canvas.saveState()
        canvas.setFont("Courier", 12)
        # 1.0 inch from right edge, 0.75 inch from top edge
        x = 8.5 * inch - 1.0 * inch
        y = 11.0 * inch - 0.75 * inch
        canvas.drawRightString(x, y, f"{doc.page}.")
        canvas.restoreState()


def export_script_to_pdf(script) -> bytes:
    """
    Renders script lines into a paginated screenplay-format PDF byte stream.
    """
    buffer = io.BytesIO()
    
    # Standard Screenplay Document Template (Letter, 1.5" Left Margin, 1.0" Right/Top/Bottom)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=1.5 * inch,
        rightMargin=1.0 * inch,
        topMargin=1.0 * inch,
        bottomMargin=1.0 * inch,
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Screenplay Paragraph Styles (Courier 12pt, 14pt leading)
    style_heading = ParagraphStyle(
        'ScreenplaySceneHeading',
        fontName='Courier-Bold',
        fontSize=12,
        leading=14,
        leftIndent=0,
        rightIndent=0,
        spaceBefore=24,
        spaceAfter=0,
        keepWithNext=True,
    )
    
    style_action = ParagraphStyle(
        'ScreenplayAction',
        fontName='Courier',
        fontSize=12,
        leading=14,
        leftIndent=0,
        rightIndent=0,
        spaceBefore=12,
        spaceAfter=0,
    )
    
    style_character = ParagraphStyle(
        'ScreenplayCharacter',
        fontName='Courier-Bold',
        fontSize=12,
        leading=14,
        leftIndent=2.2 * inch,
        rightIndent=0,
        spaceBefore=12,
        spaceAfter=0,
        keepWithNext=True,
    )
    
    style_parenthetical = ParagraphStyle(
        'ScreenplayParenthetical',
        fontName='Courier',
        fontSize=12,
        leading=14,
        leftIndent=1.6 * inch,
        rightIndent=1.9 * inch,
        spaceBefore=0,
        spaceAfter=0,
        keepWithNext=True,
    )
    
    style_dialogue = ParagraphStyle(
        'ScreenplayDialogue',
        fontName='Courier',
        fontSize=12,
        leading=14,
        leftIndent=1.0 * inch,
        rightIndent=1.5 * inch,
        spaceBefore=0,
        spaceAfter=6,
    )
    
    style_transition = ParagraphStyle(
        'ScreenplayTransition',
        fontName='Courier-Bold',
        fontSize=12,
        leading=14,
        alignment=TA_RIGHT,
        spaceBefore=12,
        spaceAfter=12,
    )
    
    style_map = {
        "scene_heading": style_heading,
        "action": style_action,
        "character": style_character,
        "parenthetical": style_parenthetical,
        "dialogue": style_dialogue,
        "transition": style_transition,
    }

    story = []
    scenes = sorted(script.scenes.prefetch_related("lines").all(), key=lambda s: s.order)
    is_first = True
    
    for scene in scenes:
        lines = sorted(scene.lines.all(), key=lambda l: l.order)
        for line in lines:
            st = style_map.get(line.type, style_action)
            
            # Escape HTML characters for ReportLab XML rendering
            text_escaped = (
                line.text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            
            if is_first:
                # Remove space before top line on page 1
                first_style = ParagraphStyle('FirstStyle', parent=st, spaceBefore=0)
                story.append(Paragraph(text_escaped, first_style))
                is_first = False
            else:
                story.append(Paragraph(text_escaped, st))

    # Build PDF with page numbers on later pages
    doc.build(story, onFirstPage=lambda c, d: None, onLaterPages=_draw_page_number)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Word Document (.docx) Generation using python-docx
# ---------------------------------------------------------------------------

def add_page_number(run):
    """
    Appends a dynamic PAGE field code to a Word run.
    """
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = "PAGE"
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')
    
    r = run._r
    r.append(fldChar1)
    r.append(instrText)
    r.append(fldChar2)
    r.append(fldChar3)


def export_script_to_word(script) -> bytes:
    """
    Renders script lines into a formatted Word (.docx) file.
    """
    doc = Document()
    
    # Page setup: Standard Letter size
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11.0)
    
    # Standard screenplay margins (1.5" left for binding, 1.0" top/bottom/right)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.5)
    section.right_margin = Inches(1.0)
    
    # Header page numbers in top right corner (starting from page 2)
    section.different_first_page_header_footer = True
    header = section.header
    header_p = header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_run = header_p.add_run()
    header_run.font.name = 'Courier New'
    header_run.font.size = Pt(12)
    add_page_number(header_run)
    header_p.add_run(".")
    
    def add_paragraph_element(text, element_type):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        
        # Setup indents relative to section margins (left=1.5", right=1.0")
        if element_type == "scene_heading":
            p.paragraph_format.left_indent = Inches(0)
            p.paragraph_format.right_indent = Inches(0)
            p.paragraph_format.space_before = Pt(24)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = True
        elif element_type == "action":
            p.paragraph_format.left_indent = Inches(0)
            p.paragraph_format.right_indent = Inches(0)
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(0)
        elif element_type == "character":
            p.paragraph_format.left_indent = Inches(2.2)
            p.paragraph_format.right_indent = Inches(0)
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = True
        elif element_type == "parenthetical":
            p.paragraph_format.left_indent = Inches(1.6)
            p.paragraph_format.right_indent = Inches(1.9)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.keep_with_next = True
        elif element_type == "dialogue":
            p.paragraph_format.left_indent = Inches(1.0)
            p.paragraph_format.right_indent = Inches(1.5)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(6)
        elif element_type == "transition":
            p.paragraph_format.left_indent = Inches(4.0)
            p.paragraph_format.right_indent = Inches(0)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p.paragraph_format.space_before = Pt(12)
            p.paragraph_format.space_after = Pt(12)
        else:
            p.paragraph_format.left_indent = Inches(0)
            p.paragraph_format.space_before = Pt(6)
            
        run = p.add_run(text)
        run.font.name = 'Courier New'
        run.font.size = Pt(12)
        
        # Bold styling for scene headings/characters/transitions
        if element_type in ("scene_heading", "character", "transition"):
            run.font.bold = True
            
        return p

    # Pull scenes and lines
    scenes = sorted(script.scenes.prefetch_related("lines").all(), key=lambda s: s.order)
    is_first = True
    
    for scene in scenes:
        lines = sorted(scene.lines.all(), key=lambda l: l.order)
        for line in lines:
            p = add_paragraph_element(line.text, line.type)
            if is_first:
                # Page 1 top line has zero space_before
                p.paragraph_format.space_before = Pt(0)
                is_first = False
                
    # Save document to memory stream
    file_stream = io.BytesIO()
    doc.save(file_stream)
    return file_stream.getvalue()
