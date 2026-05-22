"""Phase C — Supplier risk scorecard PDF for SupplierSense.

Compiles a one-page scorecard the procurement manager can hand to a sourcing
committee with the full decision basis: supplier profile + scores, latest
voice review-call excerpt, detected commitments/acknowledgments, findings
with remediation actions, and a banded grade (A/B/C/D).
"""
from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


_STYLES = getSampleStyleSheet()
_BODY = _STYLES["BodyText"]
_H1 = ParagraphStyle("H1", parent=_STYLES["Heading1"], spaceAfter=10)
_H2 = ParagraphStyle("H2", parent=_STYLES["Heading2"], spaceBefore=14, spaceAfter=6)
_META = ParagraphStyle("Meta", parent=_BODY, textColor=colors.HexColor("#555555"), fontSize=9)


def _money(v: Any) -> str:
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return "—"


def _band_color(band: str) -> colors.Color:
    return {
        "A": colors.HexColor("#15803d"),
        "B": colors.HexColor("#65a30d"),
        "C": colors.HexColor("#a16207"),
        "D": colors.HexColor("#b91c1c"),
    }.get(band, colors.HexColor("#1f2937"))


def _severity_color(sev: str) -> colors.Color:
    return {
        "critical": colors.HexColor("#b91c1c"),
        "major": colors.HexColor("#c2410c"),
        "minor": colors.HexColor("#a16207"),
    }.get(str(sev).lower(), colors.HexColor("#1f2937"))


def render_scorecard_pdf(
    supplier: Dict[str, Any],
    voice_transcript: Optional[str],
    voice_provider: Optional[str],
    signals: Dict[str, List[str]],
    findings: List[Dict[str, Any]],
    band: str,
    generated_by: str,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.6 * inch,
        title=f"SupplierSense AI — Scorecard ({supplier.get('name','supplier')})",
    )

    story: List[Any] = []
    story.append(Paragraph("SupplierSense AI — Supplier Risk Scorecard", _H1))
    story.append(Paragraph(
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · by {generated_by}",
        _META,
    ))
    story.append(Spacer(1, 8))

    band_clr = _band_color(band)
    band_table = Table(
        [
            [Paragraph(f"<b>Grade: {band}</b>", _BODY),
             Paragraph(f"Risk score: <b>{float(supplier.get('risk_score') or 0):.1f}</b> / 100", _BODY)],
            [Paragraph(
                f"Criticality: <b>{supplier.get('criticality','medium').title()}</b> · "
                f"Compliance: <b>{float(supplier.get('compliance_score') or 0):.0f}</b> · "
                f"Financial: <b>{float(supplier.get('financial_health_score') or 0):.0f}</b> · "
                f"Relationship: <b>{float(supplier.get('relationship_score') or 0):.0f}</b>",
                _BODY,
             ), ""],
        ],
        colWidths=[4.6 * inch, 2.2 * inch],
    )
    band_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, band_clr),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f9fafb")),
        ("SPAN", (0, 1), (1, 1)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(band_table)

    story.append(Paragraph("Supplier profile", _H2))
    rows = [
        ["Name", supplier.get("name", "—"), "Country", supplier.get("country", "—")],
        ["Type", supplier.get("supplier_type") or "—",
         "Commodity", supplier.get("commodity_category") or "—"],
        ["Annual spend", _money(supplier.get("annual_spend")),
         "Active", str(supplier.get("is_active", "true"))],
    ]
    info_tbl = Table(rows, colWidths=[1.1 * inch, 2.2 * inch, 1.2 * inch, 2.3 * inch])
    info_tbl.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6b7280")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#6b7280")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
        ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(info_tbl)

    story.append(Paragraph("Latest review-call transcript", _H2))
    if voice_transcript:
        story.append(Paragraph(f"Provider: <b>{voice_provider or 'n/a'}</b>", _META))
        story.append(Spacer(1, 3))
        story.append(Paragraph(voice_transcript[:1800], _BODY))
    else:
        story.append(Paragraph("<i>No supplier-review-call transcript on file.</i>", _BODY))

    story.append(Paragraph("Detected verbal commitments + acknowledgments", _H2))
    if any(signals.values()):
        for cat, quotes in signals.items():
            if not quotes:
                continue
            story.append(Paragraph(
                f"<b>{cat.replace('_', ' ').title()}</b>: "
                + "; ".join(f"&ldquo;{q}&rdquo;" for q in quotes[:3]),
                _BODY,
            ))
    else:
        story.append(Paragraph("<i>No verbal commitments detected in the transcript.</i>", _BODY))

    story.append(Paragraph("Findings + remediation actions", _H2))
    if findings:
        for f in findings:
            sev = (f.get("severity") or "").title()
            sev_clr = _severity_color(sev)
            story.append(Paragraph(
                f"<font color='{sev_clr.hexval()}'><b>[{sev}]</b></font> "
                f"<b>{f.get('description', '')}</b>",
                _BODY,
            ))
            if f.get("voice_evidence"):
                story.append(Paragraph(
                    f"<i>Voice evidence:</i> &ldquo;{f['voice_evidence']}&rdquo;",
                    _META,
                ))
            if f.get("recommended_action"):
                story.append(Paragraph(f"• {f['recommended_action']}", _BODY))
            score_impact = f.get("score_impact")
            if score_impact is not None and score_impact != 0:
                sign = "+" if score_impact > 0 else ""
                story.append(Paragraph(
                    f"<font color='{(_severity_color('major') if score_impact < 0 else _severity_color('minor')).hexval()}'>"
                    f"Score impact: {sign}{score_impact:.1f}</font>",
                    _META,
                ))
            story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("<i>No SLA-impacting findings from the latest call.</i>", _BODY))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Generated by SupplierSense AI — Voice cross-validation surface (Phase B). "
        "Scorecard band is computed from the supplier's risk score and criticality "
        "at generation time; subsequent events may change the band.",
        _META,
    ))
    doc.build(story)
    return buf.getvalue()


def safe_pdf_filename(supplier_name: Optional[str]) -> str:
    base = (supplier_name or "supplier").replace("/", "_").replace("\\", "_").replace(" ", "_")
    return f"suppliersense-scorecard-{base}.pdf"
