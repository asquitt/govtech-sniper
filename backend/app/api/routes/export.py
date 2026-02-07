"""
RFP Sniper - Export Routes
===========================
Export proposals to DOCX and PDF formats.
"""

import io
import os
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import structlog

from app.database import get_session
from app.models.proposal import Proposal, ProposalSection, SectionStatus
from app.models.rfp import RFP
from app.api.deps import get_current_user, UserAuth
from app.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


# =============================================================================
# HTML-to-DOCX helpers
# =============================================================================

_TAG_RE = re.compile(r"<[^>]+>")
_HEADING_RE = re.compile(r"<h([1-4])[^>]*>(.*?)</h\1>", re.DOTALL)
_LI_RE = re.compile(r"<li[^>]*>(.*?)</li>", re.DOTALL)
_BLOCK_RE = re.compile(
    r"<(p|blockquote|li|h[1-4])[^>]*>(.*?)</\1>", re.DOTALL
)


def _strip_tags(html: str) -> str:
    """Remove all HTML tags, returning plain text."""
    return _TAG_RE.sub("", html).strip()


def _has_html(text: str) -> bool:
    return bool(re.search(r"<[a-z][\s\S]*>", text, re.IGNORECASE))


def _render_html_to_docx(doc: "Document", html: str) -> None:  # type: ignore[name-defined]
    """Convert HTML content from TipTap into python-docx paragraphs.

    Handles <h1>-<h4>, <p>, <blockquote>, <ul>/<ol> <li>, and strips
    inline tags (<strong>, <em>) into plain text. For content that isn't
    HTML (legacy plain-text), falls back to newline splitting.
    """
    if not _has_html(html):
        # Legacy plain-text content
        for para in html.split("\n\n"):
            if para.strip():
                doc.add_paragraph(para.strip())
        return

    # Process headings
    pos = 0
    parts: list[tuple[str, str]] = []  # (type, text)

    # Walk through HTML extracting blocks in order
    block_pattern = re.compile(
        r"<(h[1-4]|p|blockquote|li|ul|ol)[^>]*>(.*?)</\1>",
        re.DOTALL,
    )
    for m in block_pattern.finditer(html):
        tag = m.group(1)
        inner = _strip_tags(m.group(2))
        if not inner:
            continue
        parts.append((tag, inner))

    if not parts:
        # Fallback: strip all tags and add as single paragraph
        plain = _strip_tags(html)
        if plain:
            doc.add_paragraph(plain)
        return

    for tag, text in parts:
        if tag.startswith("h") and len(tag) == 2:
            level = int(tag[1])
            doc.add_heading(text, level=min(level + 1, 4))
        elif tag == "blockquote":
            p = doc.add_paragraph(text)
            p.style = "Quote" if "Quote" in [s.name for s in doc.styles] else None
        elif tag == "li":
            doc.add_paragraph(text, style="List Bullet")
        else:
            doc.add_paragraph(text)


# =============================================================================
# DOCX Export
# =============================================================================

def create_docx_proposal(
    proposal: Proposal,
    sections: list[ProposalSection],
    rfp: RFP,
) -> bytes:
    """
    Generate a DOCX file from proposal sections.
    """
    try:
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.style import WD_STYLE_TYPE
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="python-docx not installed. Run: pip install python-docx",
        )

    doc = Document()

    # Set document properties
    doc.core_properties.title = proposal.title
    doc.core_properties.author = "RFP Sniper"
    doc.core_properties.created = datetime.utcnow()

    # Title page
    title = doc.add_heading(proposal.title, 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # RFP details
    details = doc.add_paragraph()
    details.add_run("Solicitation Number: ").bold = True
    details.add_run(rfp.solicitation_number)
    details.add_run("\n")
    details.add_run("Agency: ").bold = True
    details.add_run(rfp.agency)
    details.add_run("\n")
    if rfp.response_deadline:
        details.add_run("Due Date: ").bold = True
        details.add_run(rfp.response_deadline.strftime("%B %d, %Y"))

    doc.add_page_break()

    # Table of Contents placeholder
    doc.add_heading("Table of Contents", 1)
    doc.add_paragraph("(Update field to generate TOC)")
    doc.add_page_break()

    # Executive Summary (if exists)
    if proposal.executive_summary:
        doc.add_heading("Executive Summary", 1)
        doc.add_paragraph(proposal.executive_summary)
        doc.add_page_break()

    # Proposal sections
    for section in sorted(sections, key=lambda s: s.display_order):
        # Section heading
        doc.add_heading(f"{section.section_number}. {section.title}", 2)

        # Requirement text (if any)
        if section.requirement_text:
            req_para = doc.add_paragraph()
            req_para.add_run("Requirement: ").bold = True
            req_para.add_run(section.requirement_text[:500])
            if len(section.requirement_text) > 500:
                req_para.add_run("...")
            doc.add_paragraph()

        # Section content
        content = section.final_content
        if not content and section.generated_content:
            # Use clean text from generated content
            content = section.generated_content.get("clean_text", "")

        if content:
            _render_html_to_docx(doc, content)
        else:
            doc.add_paragraph("[Section content pending]")

        doc.add_paragraph()

    # Footer with generation info
    doc.add_page_break()
    footer = doc.add_paragraph()
    footer.add_run("Generated by RFP Sniper").italic = True
    footer.add_run(f" on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    # Save to bytes
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return buffer.getvalue()


@router.get("/proposals/{proposal_id}/docx")
async def export_proposal_docx(
    proposal_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export a proposal to Microsoft Word (DOCX) format.
    """
    # Get proposal
    result = await session.execute(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get sections
    sections_result = await session.execute(
        select(ProposalSection).where(
            ProposalSection.proposal_id == proposal_id
        ).order_by(ProposalSection.display_order)
    )
    sections = list(sections_result.scalars().all())

    # Get RFP
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == proposal.rfp_id)
    )
    rfp = rfp_result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail="Associated RFP not found")

    # Generate DOCX
    try:
        docx_bytes = create_docx_proposal(proposal, sections, rfp)
    except Exception as e:
        logger.error(f"DOCX generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    # Create filename
    safe_title = "".join(c for c in proposal.title[:50] if c.isalnum() or c in " -_")
    filename = f"{safe_title}_{datetime.utcnow().strftime('%Y%m%d')}.docx"

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# PDF Export
# =============================================================================

def create_pdf_proposal(
    proposal: Proposal,
    sections: list[ProposalSection],
    rfp: RFP,
) -> bytes:
    """
    Generate a PDF file from proposal sections.
    Uses weasyprint for HTML to PDF conversion.
    """
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="weasyprint not installed. Run: pip install weasyprint",
        )

    # Build HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: letter;
                margin: 1in;
                @bottom-center {{
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 10pt;
                    color: #666;
                }}
            }}
            body {{
                font-family: 'Georgia', serif;
                font-size: 12pt;
                line-height: 1.6;
                color: #333;
            }}
            h1 {{
                font-size: 24pt;
                text-align: center;
                margin-bottom: 0.5in;
                color: #1a1a1a;
            }}
            h2 {{
                font-size: 16pt;
                border-bottom: 2px solid #333;
                padding-bottom: 5pt;
                margin-top: 0.5in;
            }}
            .title-page {{
                text-align: center;
                page-break-after: always;
            }}
            .details {{
                margin: 1in auto;
                width: 80%;
            }}
            .details p {{
                margin: 0.2in 0;
            }}
            .requirement {{
                background: #f5f5f5;
                padding: 10pt;
                border-left: 3px solid #666;
                margin: 10pt 0;
                font-style: italic;
            }}
            .section-content {{
                margin: 0.2in 0;
            }}
            .footer {{
                margin-top: 1in;
                font-size: 10pt;
                color: #666;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="title-page">
            <h1>{proposal.title}</h1>
            <div class="details">
                <p><strong>Solicitation Number:</strong> {rfp.solicitation_number}</p>
                <p><strong>Agency:</strong> {rfp.agency}</p>
                <p><strong>Due Date:</strong> {rfp.response_deadline.strftime('%B %d, %Y') if rfp.response_deadline else 'TBD'}</p>
            </div>
        </div>
    """

    # Executive Summary
    if proposal.executive_summary:
        html_content += f"""
        <h2>Executive Summary</h2>
        <div class="section-content">
            {proposal.executive_summary.replace(chr(10), '<br>')}
        </div>
        """

    # Sections
    for section in sorted(sections, key=lambda s: s.display_order):
        html_content += f"""
        <h2>{section.section_number}. {section.title}</h2>
        """

        if section.requirement_text:
            html_content += f"""
            <div class="requirement">
                <strong>Requirement:</strong> {section.requirement_text[:500]}{'...' if len(section.requirement_text) > 500 else ''}
            </div>
            """

        content = section.final_content
        if not content and section.generated_content:
            content = section.generated_content.get("clean_text", "")

        if content:
            if _has_html(content):
                # TipTap HTML — inject directly
                html_content += f'<div class="section-content">{content}</div>'
            else:
                # Legacy plain text
                paragraphs = content.split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        html_content += f"<p>{para.strip()}</p>"
        else:
            html_content += "<p><em>[Section content pending]</em></p>"

    # Footer
    html_content += f"""
        <div class="footer">
            Generated by RFP Sniper on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
        </div>
    </body>
    </html>
    """

    # Convert to PDF
    pdf_bytes = HTML(string=html_content).write_pdf()

    return pdf_bytes


@router.get("/proposals/{proposal_id}/pdf")
async def export_proposal_pdf(
    proposal_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export a proposal to PDF format.
    """
    # Get proposal
    result = await session.execute(
        select(Proposal).where(
            Proposal.id == proposal_id,
            Proposal.user_id == current_user.id,
        )
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get sections
    sections_result = await session.execute(
        select(ProposalSection).where(
            ProposalSection.proposal_id == proposal_id
        ).order_by(ProposalSection.display_order)
    )
    sections = list(sections_result.scalars().all())

    # Get RFP
    rfp_result = await session.execute(
        select(RFP).where(RFP.id == proposal.rfp_id)
    )
    rfp = rfp_result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail="Associated RFP not found")

    # Generate PDF
    try:
        pdf_bytes = create_pdf_proposal(proposal, sections, rfp)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

    # Create filename
    safe_title = "".join(c for c in proposal.title[:50] if c.isalnum() or c in " -_")
    filename = f"{safe_title}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Compliance Matrix Export
# =============================================================================

@router.get("/rfps/{rfp_id}/compliance-matrix/xlsx")
async def export_compliance_matrix_xlsx(
    rfp_id: int,
    current_user: UserAuth = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export compliance matrix to Excel (XLSX) format.
    """
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl not installed. Run: pip install openpyxl",
        )

    from app.models.rfp import ComplianceMatrix

    # Get RFP
    result = await session.execute(
        select(RFP).where(
            RFP.id == rfp_id,
            RFP.user_id == current_user.id,
        )
    )
    rfp = result.scalar_one_or_none()

    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Get compliance matrix
    matrix_result = await session.execute(
        select(ComplianceMatrix).where(ComplianceMatrix.rfp_id == rfp_id)
    )
    matrix = matrix_result.scalar_one_or_none()

    if not matrix:
        raise HTTPException(status_code=404, detail="Compliance matrix not found")

    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Compliance Matrix"

    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    mandatory_fill = PatternFill(start_color="FFCCCB", end_color="FFCCCB", fill_type="solid")
    addressed_fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    # Headers
    headers = ["ID", "Section", "Requirement", "Type", "Importance", "Addressed", "Notes"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border

    # Data rows
    for row_num, req in enumerate(matrix.requirements, 2):
        ws.cell(row=row_num, column=1, value=req.get("id", ""))
        ws.cell(row=row_num, column=2, value=req.get("section", ""))
        ws.cell(row=row_num, column=3, value=req.get("requirement_text", ""))
        ws.cell(row=row_num, column=4, value=req.get("category", ""))
        ws.cell(row=row_num, column=5, value=req.get("importance", ""))
        ws.cell(row=row_num, column=6, value="Yes" if req.get("is_addressed") else "No")
        ws.cell(row=row_num, column=7, value=req.get("notes", ""))

        # Apply formatting
        for col in range(1, 8):
            cell = ws.cell(row=row_num, column=col)
            cell.border = thin_border
            cell.alignment = Alignment(wrap_text=True, vertical="top")

        # Highlight based on importance and status
        if req.get("importance") == "mandatory" and not req.get("is_addressed"):
            for col in range(1, 8):
                ws.cell(row=row_num, column=col).fill = mandatory_fill
        elif req.get("is_addressed"):
            ws.cell(row=row_num, column=6).fill = addressed_fill

    # Set column widths
    ws.column_dimensions['A'].width = 10
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 60
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 10
    ws.column_dimensions['G'].width = 30

    # Save to bytes
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"compliance_matrix_{rfp.solicitation_number}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
