"""Basic PDF/JSON report assembly; full Sec.63 formatting layered in Phase 7 and AI verification status annotations."""

import json
import os
from typing import Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.engine7_case_db.audit_log import verify_audit_chain, get_extracted_files, get_db_connection
from app.engine8_ai.model_registry import verify_all_models


def build_json_report(db_path: str, case_id: str) -> Dict[str, Any]:
    chain_valid = verify_audit_chain(db_path, case_id)
    files = get_extracted_files(db_path, case_id)
    models_status = verify_all_models()

    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, event_type, details, previous_hash, entry_hash FROM audit_log WHERE case_id = ? ORDER BY entry_id ASC", (case_id,))
    audit_rows = cursor.fetchall()
    
    # Query detections summary and items
    cursor.execute("SELECT detection_id, file_id, class_name, confidence, is_simulated FROM detections")
    det_rows = cursor.fetchall()
    det_items = [
        {
            "id": r["detection_id"],
            "file_id": r["file_id"],
            "class_name": r["class_name"],
            "confidence": r["confidence"],
            "is_simulated": bool(r["is_simulated"]),
        }
        for r in det_rows
    ]
    conn.close()

    return {
        "case_id": case_id,
        "audit_chain_valid": chain_valid,
        "models_verification": models_status,
        "detections_count": len(det_items),
        "detections": det_items,
        "extracted_files": [
            {
                "file_id": f.file_id,
                "channel_id": f.channel_id,
                "start_timestamp": f.start_timestamp,
                "end_timestamp": f.end_timestamp,
                "size_bytes": f.size_bytes,
                "file_hash": f.file_hash,
                "extraction_type": f.extraction_type,
            }
            for f in files
        ],
        "audit_log": [
            {
                "timestamp": row["timestamp"],
                "event_type": row["event_type"],
                "details": row["details"],
                "entry_hash": row["entry_hash"],
            }
            for row in audit_rows
        ]
    }


def generate_case_report_pdf(db_path: str, case_id: str, output_pdf_path: str) -> str:
    """
    Generates a basic PDF forensic report summarizing case data, audit chain verification status,
    and extracted files list showing extraction_type per file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    report_data = build_json_report(db_path, case_id)

    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=12)
    story.append(Paragraph(f"UniDVR-Forensics Case Summary Report", title_style))
    story.append(Paragraph(f"<b>Case ID:</b> {case_id}", styles['Normal']))
    story.append(Paragraph(f"<b>Audit Log Chain Integrity:</b> {'VALID (UNBROKEN)' if report_data['audit_chain_valid'] else 'INVALID / TAMPERED'}", styles['Normal']))
    story.append(Spacer(1, 14))

    # Extracted Files Section
    story.append(Paragraph("<b>Extracted Evidence Files:</b>", styles['Heading2']))
    story.append(Spacer(1, 6))

    files = report_data["extracted_files"]
    if files:
        table_data = [["File ID", "Channel", "Extraction Type", "Size (bytes)", "Hash (SHA256)"]]
        for f in files:
            ext_label = "parsed" if f["extraction_type"] == "parsed" else "carved / best-effort"
            table_data.append([
                f["file_id"],
                str(f["channel_id"]),
                ext_label,
                str(f["size_bytes"]),
                f["file_hash"][:16] + "..." if f["file_hash"] else "N/A"
            ])

        t = Table(table_data, colWidths=[110, 60, 130, 80, 120])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#252526')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No extracted files recorded.", styles['Normal']))

    story.append(Spacer(1, 14))

    # AI Verification Status Section
    story.append(Paragraph("<b>AI Analytics Verification Status:</b>", styles['Heading2']))
    story.append(Spacer(1, 6))
    for m_name, m_info in report_data["models_verification"].items():
        st = m_info["status"]
        st_text = f"<font color='green'>VERIFIED</font>" if st == "VERIFIED" else f"<font color='red'>SIMULATED / NO MODEL LOADED ({st})</font>"
        story.append(Paragraph(f"• <b>{m_name}:</b> {st_text}", styles['Normal']))

    # AI Findings Table
    detections = report_data.get("detections", [])
    if detections:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>Recorded AI Detections & Verification Ledger:</b>", styles['Heading2']))
        story.append(Spacer(1, 6))
        det_table_data = [["Detection ID", "File ID", "Class", "Confidence", "Model Status"]]
        for d in detections:
            sim_tag = "<font color='red'>(SIMULATED)</font>" if d["is_simulated"] else "<font color='green'>(VERIFIED)</font>"
            det_table_data.append([
                d["id"],
                d["file_id"],
                d["class_name"],
                f"{d['confidence']:.2f}",
                sim_tag
            ])
        dt = Table(det_table_data, colWidths=[90, 110, 110, 80, 110])
        dt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#252526')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(dt)

    story.append(Spacer(1, 14))

    # Audit Chain Log Section
    story.append(Paragraph("<b>Chain of Custody Audit Log:</b>", styles['Heading2']))
    story.append(Spacer(1, 6))

    audit_entries = report_data["audit_log"]
    if audit_entries:
        audit_table_data = [["Timestamp", "Event Type", "Entry Hash (SHA256)"]]
        for entry in audit_entries:
            audit_table_data.append([
                entry["timestamp"][:19],
                entry["event_type"],
                entry["entry_hash"][:24] + "..."
            ])
        at = Table(audit_table_data, colWidths=[140, 150, 210])
        at.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0078d4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        story.append(at)

    doc.build(story)
    return output_pdf_path


def generate_case_report_pdf_with_sec63(db_path: str, case_id: str, output_pdf_path: str) -> str:
    """
    Generates a full forensic report including Section 63 BSA draft certificate content
    and derivative export listings with mandatory convenience copy labels.
    """
    from app.engine10_compliance.bsa_sec63 import generate_bsa_sec63_cert_draft, SECTION_63_DISCLAIMER

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    report_data = build_json_report(db_path, case_id)

    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=8)
    story.append(Paragraph("UniDVR-Forensics Full Case & Sec. 63 BSA Draft Report", title_style))
    story.append(Paragraph(f"<b>Case ID:</b> {case_id}", styles['Normal']))
    story.append(Paragraph(f"<b>Audit Chain Verification:</b> {'VALID' if report_data['audit_chain_valid'] else 'INVALID'}", styles['Normal']))
    story.append(Paragraph(f"<b>Compliance Status:</b> {SECTION_63_DISCLAIMER}", styles['Normal']))
    story.append(Spacer(1, 10))

    # BSA Sec 63 Certificate Draft Section
    sec63_draft = generate_bsa_sec63_cert_draft({"case_id": case_id, "investigator": "Forensic Investigator"}, report_data["extracted_files"], report_data["audit_log"])
    story.append(Paragraph("<b>BSA 2023 Section 63 Draft Certificates:</b>", styles['Heading2']))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<pre>{sec63_draft['part_a']}</pre>", styles['Code']))
    story.append(Spacer(1, 6))

    # Derivative Exports Section
    story.append(Paragraph("<b>Derivative Exports (Non-Evidentiary):</b>", styles['Heading2']))
    story.append(Paragraph("<i>Notice: All MP4/MKV exports are labeled: convenience copy - not for submission as primary evidence</i>", styles['Normal']))
    story.append(Spacer(1, 8))

    doc.build(story)
    return output_pdf_path
