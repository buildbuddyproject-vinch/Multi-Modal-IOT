"""One-off generator for a plain-language, client-facing project overview PDF
-- reuses the same premium navy/teal branding as src/reports/patient_report_pdf.py
so it reads as the same product, but explains the project (not a patient) in
simple words: what problem it solves, how it works step by step, what has
been built so far, what technology was used (in plain terms), how it has been
tested, and what is still left to do.

Run with: .venv/Scripts/python.exe scripts/generate_project_overview_pdf.py
Writes to: docs/Project_Overview_For_Client.pdf
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT_PATH = Path(__file__).resolve().parents[1] / "docs" / "Project_Overview_For_Client.pdf"

NAVY = colors.HexColor("#0b1f3a")
NAVY_LIGHT = colors.HexColor("#12315c")
TEAL = colors.HexColor("#0891b2")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6b7280")
FAINT = colors.HexColor("#9ca3af")
LINE = colors.HexColor("#e2e8f0")
PANEL = colors.HexColor("#f8fafc")
DONE = colors.HexColor("#0d9488")
PLANNED = colors.HexColor("#ca8a04")
WHITE = colors.white

GENERATED_AT = datetime.now(timezone.utc)


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("H1", parent=base["Title"], fontName="Helvetica-Bold", fontSize=20,
                              textColor=NAVY, alignment=TA_LEFT, spaceAfter=4, leading=24),
        "h1_sub": ParagraphStyle("H1Sub", parent=base["Normal"], fontName="Helvetica", fontSize=11,
                                  textColor=MUTED, leading=15, spaceAfter=2),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontName="Helvetica-Bold",
                                   fontSize=13.5, textColor=NAVY, spaceBefore=16, spaceAfter=8),
        "subsection": ParagraphStyle("Subsection", parent=base["Heading3"], fontName="Helvetica-Bold",
                                      fontSize=10.5, textColor=NAVY_LIGHT, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("Body", parent=base["Normal"], fontName="Helvetica", fontSize=9.7,
                                textColor=INK, leading=15),
        "bullet": ParagraphStyle("Bullet", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
                                  textColor=INK, leading=14),
        "muted": ParagraphStyle("Muted", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=8.7,
                                 textColor=MUTED, leading=13),
        "cell": ParagraphStyle("Cell", parent=base["Normal"], fontName="Helvetica", fontSize=8.6,
                                textColor=INK, leading=12.5),
        "cell_bold": ParagraphStyle("CellBold", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.6,
                                     textColor=INK, leading=12.5),
        "cell_head": ParagraphStyle("CellHead", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8,
                                     textColor=WHITE, leading=11),
        "flow_step": ParagraphStyle("FlowStep", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
                                     textColor=WHITE, alignment=TA_CENTER, leading=11),
        "flow_step_sub": ParagraphStyle("FlowStepSub", parent=base["Normal"], fontName="Helvetica", fontSize=7,
                                         textColor=colors.HexColor("#d7e6f7"), alignment=TA_CENTER, leading=9),
        "pill_done": ParagraphStyle("PillDone", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.6,
                                     textColor=WHITE, alignment=TA_CENTER, leading=10),
        "disclaimer": ParagraphStyle("Disclaimer", parent=base["Normal"], fontName="Helvetica-Oblique",
                                      fontSize=6.8, textColor=FAINT, leading=9),
    }


def _section(text, styles):
    return [Paragraph(text, styles["section"]), HRFlowable(width="100%", thickness=0.75, color=LINE, spaceAfter=6)]


def _bullets(items, styles):
    return ListFlowable(
        [ListItem(Paragraph(t, styles["bullet"]), bulletColor=TEAL) for t in items],
        bulletType="bullet", start="circle", leftIndent=12, bulletFontSize=6, spaceBefore=2, spaceAfter=8,
    )


def _pill(text, color, styles, style_key="pill_done"):
    t = Table([[Paragraph(text, styles[style_key])]], colWidths=[26 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _status_table(rows, styles, col_widths, header_labels=("#", "What was built", "In plain words", "Status")):
    header = [Paragraph(h, styles["cell_head"]) for h in header_labels]
    body = []
    for num, title, plain, status in rows:
        pill = _pill("DONE" if status == "done" else "PLANNED", DONE if status == "done" else PLANNED, styles)
        body.append([
            Paragraph(num, styles["cell_bold"]),
            Paragraph(title, styles["cell_bold"]),
            Paragraph(plain, styles["cell"]),
            pill,
        ])
    table = Table([header] + body, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_LIGHT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, NAVY_LIGHT),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i in range(1, len(body) + 1):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    table.setStyle(TableStyle(style))
    return table


def _plain_table(header_labels, rows, col_widths, styles):
    header = [Paragraph(h, styles["cell_head"]) for h in header_labels]
    body = [[Paragraph(str(v), styles["cell"]) for v in row] for row in rows]
    table = Table([header] + body, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_LIGHT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, NAVY_LIGHT),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i in range(1, len(body) + 1):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    table.setStyle(TableStyle(style))
    return table


def _flow_strip(steps, styles):
    """A left-to-right pipeline strip: [box] -> [box] -> [box] ... used to show
    the sensor-to-doctor data journey in one glance."""
    box_w = 26 * mm
    arrow_w = 6 * mm
    row = []
    widths = []
    for i, (title, sub) in enumerate(steps):
        box = Table([[Paragraph(title, styles["flow_step"])], [Paragraph(sub, styles["flow_step_sub"])]],
                     colWidths=[box_w], rowHeights=[16 * mm, 8 * mm])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY_LIGHT if i % 2 == 0 else TEAL),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        row.append(box)
        widths.append(box_w)
        if i != len(steps) - 1:
            row.append(Paragraph('<font color="#0891b2" size="14"><b>&#8594;</b></font>', styles["body"]))
            widths.append(arrow_w)
    outer = Table([row], colWidths=widths, hAlign="LEFT")
    outer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    return outer


def build_project_overview_pdf() -> bytes:
    import io
    buffer = io.BytesIO()
    styles = _styles()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=32 * mm, bottomMargin=16 * mm, leftMargin=16 * mm, rightMargin=16 * mm,
        title="Sepsis ICU Monitor -- Project Overview", author="Sepsis ICU Monitor",
    )
    story = []

    # ---- Intro -----------------------------------------------------------
    story.append(Paragraph("Project Overview & Status Report", styles["h1"]))
    story.append(Paragraph("Multi-Modal IoT &amp; Deep Learning Framework for Early Prediction of Sepsis in Smart ICU Environments", styles["h1_sub"]))
    story.append(Paragraph("Final-year B.E. CSE project &nbsp;|&nbsp; Written for a non-technical audience", styles["h1_sub"]))
    story.append(Spacer(1, 4 * mm))

    story += _section("1. What Problem Are We Solving?", styles)
    story.append(Paragraph(
        "Sepsis is a life-threatening condition where the body's response to an infection starts damaging its own organs. "
        "It can turn fatal within hours, but caught early it is very treatable. The problem is that early warning signs "
        "(small changes in heart rate, temperature, blood pressure, breathing rate) are easy for a busy nursing staff to "
        "miss, especially when watching many patients at once.", styles["body"],
    ))
    story.append(Paragraph(
        "This project builds a computer system that watches a patient's vital signs continuously (the same way a hospital "
        "monitor would), and uses Artificial Intelligence to calculate a running \"risk score\" for sepsis. If that score "
        "gets dangerously high, the system immediately raises a clear, impossible-to-miss alert for the clinical staff, "
        "and explains, in plain terms, which vital signs are driving the concern.", styles["body"],
    ))

    story += _section("2. How The System Works, Step By Step", styles)
    story.append(Paragraph(
        "Think of the system as a pipeline. Data flows from the patient's bedside all the way to the doctor's screen "
        "in a few seconds:", styles["body"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_flow_strip([
        ("1. Vitals\nCollected", "sensors / device"),
        ("2. Sent\nLive", "secure stream"),
        ("3. AI Reads\nthe Pattern", "trained model"),
        ("4. Risk Score\nCalculated", "0-100%"),
        ("5. Alert If\nDangerous", "red pop-up"),
        ("6. Doctor\nDecides", "dashboard / PDF"),
    ], styles))
    story.append(Spacer(1, 5 * mm))
    story.append(_bullets([
        "<b>Step 1 -- Collecting vitals:</b> Heart rate, oxygen level, temperature, blood pressure and breathing rate are "
        "read continuously. Today this is a realistic simulator that behaves exactly like real hospital sensor hardware "
        "would (so swapping in real sensors later needs no changes anywhere else in the system).",
        "<b>Step 2 -- Sending the data live:</b> Every reading is streamed in real time over a lightweight, industry-standard "
        "messaging protocol (the same kind of technology used in IoT devices worldwide), so the system reacts within "
        "seconds of a change, not minutes.",
        "<b>Step 3 -- The AI reads the pattern:</b> A deep-learning model -- trained on thousands of real ICU patient "
        "records -- looks at the recent trend of vitals (not just one reading) and recognises patterns that historically "
        "led to sepsis.",
        "<b>Step 4 -- A risk score is calculated:</b> The AI outputs a probability (e.g. \"78% risk\") which is then "
        "translated into a simple label anyone can understand: <b>Low, Medium, High,</b> or <b>Critical.</b>",
        "<b>Step 5 -- An alert is raised if needed:</b> For High or Critical risk, the system immediately shows a red "
        "pop-up alert on every screen the clinician has open, explaining <i>why</i> (e.g. \"Heart rate elevated at 128 "
        "bpm, Temperature elevated at 39.4&deg;C\") -- not just a number, but the reasoning behind it.",
        "<b>Step 6 -- The doctor decides:</b> The clinician sees the full picture on a live dashboard (charts, trends, "
        "AI explanation) and can download a professional, hospital-style PDF report to print, archive, or hand off "
        "to another doctor.",
    ], styles))

    story.append(PageBreak())

    # ---- What has been built ----------------------------------------------
    story += _section("3. What Has Been Built So Far", styles)
    story.append(Paragraph(
        "The project is organised into 12 planned steps. All 12 are complete for the software side of the system "
        "(everything that does not require physical sensor hardware). Physical hardware integration is a separate, "
        "not-yet-started phase, explained in Section 6.", styles["body"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_status_table([
        ("1", "Blueprint & Design", "Planned out the whole system on paper first: how data flows, how the database is organised, and the exact data format any sensor (real or simulated) must send.", "done"),
        ("2", "Real Hospital Data", "Loaded two well-known, publicly available real ICU patient datasets (PhysioNet and MIMIC-IV) and cleaned/organised them so the AI could learn from real cases.", "done"),
        ("3", "Data Exploration", "Studied the data in depth -- which vital signs matter most, what's missing, what's normal vs. abnormal -- before building anything, so the AI is built on solid understanding.", "done"),
        ("4", "AI Model Design", "Designed the \"brain\" of the system: a deep-learning model that reads a sequence of vitals over time and understands trends, not just single snapshots.", "done"),
        ("5", "AI Model Training", "Trained that AI model on the real hospital data, tuning it carefully so it learns genuine warning patterns rather than memorising the data.", "done"),
        ("6", "Explainable AI", "Added a layer that makes the AI show its reasoning -- which specific vital signs pushed the risk score up or down -- so results aren't a \"black box.\"", "done"),
        ("7", "Secure Database", "Built a proper database to permanently and safely store every patient, every vital reading, every AI prediction, and every alert, with built-in data-quality checks.", "done"),
        ("8", "Backend Engine", "Built the server that all other parts talk to -- it handles every request (add a patient, fetch vitals, run a prediction) securely and consistently.", "done"),
        ("9", "Live Dashboard", "Built the premium, hospital-themed web dashboard clinicians actually use: login, patient list, live monitoring charts, AI explanations, and an admin panel.", "done"),
        ("10", "Alert System", "Built the engine that watches every new AI result and automatically raises an alert (with cooldown rules to avoid spamming) whenever risk crosses a dangerous threshold.", "done"),
        ("11", "Real-Time Streaming", "Connected everything end to end so vitals flow in live, get analysed by the AI, and appear on the dashboard within seconds -- proven with a realistic simulated data stream.", "done"),
        ("12", "Full Integration & Testing", "Wired every piece together and tested the entire system as a whole, from a vital-sign reading arriving to a doctor seeing an alert and downloading a report.", "done"),
    ], styles, col_widths=[9 * mm, 33 * mm, 90 * mm, 24 * mm]))

    story += _section("4. Key Features, In Detail", styles)
    story.append(Paragraph("Beyond the core AI pipeline, several client-facing features have been added recently:", styles["body"]))
    story.append(_bullets([
        "<b>Premium, hospital-grade dashboard:</b> A dark, modern clinical interface (not a generic admin template) with "
        "live charts, colour-coded risk badges, and a dedicated Admin panel showing system health and every user action.",
        "<b>Real-time red-alert pop-ups:</b> The moment the AI flags a patient as High or Critical risk, a red alert "
        "pops up on screen -- with a siren icon and a plain-English reason -- no matter which page the clinician is on.",
        "<b>Downloadable clinical PDF reports:</b> One click produces a formatted, hospital-branded PDF for any patient: "
        "current risk, vitals history, AI trend, explanation, and full alert history -- ready to print or archive.",
        "<b>Private accounts for every clinician/admin:</b> Each login only ever sees the patients it admitted. A brand "
        "new clinician account starts completely empty -- no old test data, no other clinician's patients -- exactly "
        "like separate real hospital accounts should behave.",
        "<b>Self-service \"Admit Patient\":</b> Any clinician or admin can add a new patient themselves directly from "
        "the dashboard, rather than relying on someone else to seed data for them.",
        "<b>Full audit trail:</b> Every login, every alert raised, every alert acknowledged, and every patient admitted "
        "is permanently logged -- so there is always a record of who did what and when, which is essential for a "
        "healthcare-style system.",
    ], styles))

    story.append(PageBreak())

    # ---- Technology ---------------------------------------------------------
    story += _section("5. Technology Used (In Plain Terms)", styles)
    story.append(_plain_table(
        ["Technology", "What it actually does here"],
        [
            ["Python", "The programming language the entire system (AI, server, dashboard) is written in."],
            ["TensorFlow / Keras", "The toolkit used to build and train the AI model that predicts sepsis risk."],
            ["Deep Learning Model\n(CNN + LSTM + Transformer)", "The AI \"brain\" itself -- a model specifically good at spotting patterns in data that changes over time, like vital signs."],
            ["SHAP", "The \"explainability\" tool that lets the AI show which vital signs influenced its decision, and by how much."],
            ["MongoDB", "The database that permanently and safely stores every patient, reading, prediction and alert."],
            ["FastAPI", "The backend engine/server that every other part of the system talks to, in a secure, organised way."],
            ["MQTT (Mosquitto)", "The live-messaging technology used to stream sensor readings in real time -- the same standard used across real-world IoT devices."],
            ["Plotly Dash", "The framework used to build the live, interactive web dashboard clinicians use."],
            ["ReportLab", "The tool used to generate the formatted, hospital-style PDF clinical reports."],
            ["JWT (secure login tokens)", "The technology that keeps every login secure and makes sure each account only ever sees its own patients."],
            ["Docker", "Used to run supporting services (the database, the messaging system) in a consistent, easy-to-set-up way."],
            ["Pytest (testing)", "The tool used to automatically re-check that every part of the system still works correctly after every change."],
        ],
        col_widths=[48 * mm, 108 * mm], styles=styles,
    ))

    story += _section("6. How Do We Know It Works?", styles)
    story.append(Paragraph(
        "The system isn't just \"built\" -- it has been actively tested at every level:", styles["body"],
    ))
    story.append(_bullets([
        "<b>300+ automated tests</b> run against the real database and real server on every change, covering everything "
        "from \"does login work\" to \"does a full patient journey from admission to alert to PDF report work end to end.\"",
        "<b>Live, real demonstrations were run</b> -- not just automated tests -- including creating a brand-new "
        "clinician account and confirming it genuinely sees zero other patients, and manually triggering High/Critical "
        "predictions to confirm the red alert really appears with the correct reasoning.",
        "<b>Model accuracy is measured honestly:</b> on held-out real patient data the AI achieves an AUROC of 0.766 "
        "(a standard accuracy measure where 0.5 is random guessing and 1.0 is perfect) -- meaningfully better than chance, "
        "and its risk ranking (Low/Medium/High/Critical) has been checked against real patient trajectories.",
    ], styles))
    story.append(Paragraph("<b>An honest limitation, stated plainly:</b>", styles["subsection"]))
    story.append(Paragraph(
        "Sepsis is rare in the training data used (under 2% of records), which makes it a genuinely hard prediction "
        "problem, and the current model is a single model (not a large ensemble) trained on limited compute. This means "
        "it is meaningfully useful as a research and educational system, and its risk stratification is directionally "
        "correct, but it is <b>not yet a clinically validated medical device</b> and must not be used as the sole basis "
        "for a real clinical decision. This caveat is deliberately shown on every generated PDF report as well.", styles["body"],
    ))

    story.append(PageBreak())

    # ---- What's left -----------------------------------------------------
    story += _section("7. What's Left To Do", styles)
    story.append(Paragraph(
        "The entire software system described above (Steps 1-12) is complete and working end to end. What remains is "
        "everything that requires either physical hardware or a level of validation beyond a student project's scope:", styles["body"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(_status_table([
        ("A", "Real Sensor Hardware", "Connect actual physical sensors (ESP32 microcontroller + real heart-rate/temperature/etc. sensors) at a real bedside, instead of the current realistic simulator. The system was deliberately designed so this requires zero changes to the AI, database, or dashboard -- only the sensor device changes.", "planned"),
        ("B", "Larger, More Balanced Training Data", "Sepsis cases are rare in the current dataset. Training on more data (or combining several hospitals' data) would likely improve the AI's accuracy further, especially at catching more of the true sepsis cases.", "planned"),
        ("C", "Clinical Validation", "Before any real hospital use, the system would need to be reviewed and validated by qualified medical professionals, and likely go through a formal clinical trial process -- standard for any medical decision-support tool.", "planned"),
        ("D", "Notifications Beyond the Dashboard", "Currently alerts appear on-screen; SMS, mobile push notifications, or a dedicated mobile app for on-call staff would extend reach beyond someone actively watching the dashboard.", "planned"),
        ("E", "Production Hardening", "Before any live deployment beyond a demo/academic setting: a formal security review, load-testing for many simultaneous patients, and a professional deployment (cloud hosting, backups, monitoring) would be needed.", "planned"),
    ], styles, col_widths=[9 * mm, 30 * mm, 93 * mm, 24 * mm],
       header_labels=("#", "What's needed", "In plain words", "Status")))

    story += _section("8. Summary", styles)
    story.append(Paragraph(
        "In short: the full software pipeline -- from collecting live vital signs, through an AI model that predicts "
        "sepsis risk and explains its reasoning, to real-time red alerts and downloadable clinical PDF reports, all "
        "wrapped in a secure, multi-account dashboard -- is built, tested, and working today with realistic simulated "
        "sensor data. What remains is connecting real physical hardware, growing the training data, and the formal "
        "clinical validation any tool would need before real hospital use.", styles["body"],
    ))
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LINE))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "This document is a plain-language summary for review purposes. Technical documentation (architecture, "
        "database design, API reference, and full test reports) is maintained separately in the project's own "
        "documentation folder.", styles["disclaimer"],
    ))

    def _draw_page_frame(canvas, _doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 26 * mm, A4[0], 26 * mm, stroke=0, fill=1)
        canvas.setFillColor(TEAL)
        canvas.rect(0, A4[1] - 26.5 * mm, A4[0], 0.5 * mm, stroke=0, fill=1)

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawString(16 * mm, A4[1] - 12 * mm, "Sepsis ICU Monitor")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#bcd2ee"))
        canvas.drawString(16 * mm, A4[1] - 18 * mm, "Multi-Modal IoT & Deep Learning Sepsis Prediction -- Project Overview")

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawRightString(A4[0] - 16 * mm, A4[1] - 12 * mm, "Status Report")
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#bcd2ee"))
        canvas.drawRightString(A4[0] - 16 * mm, A4[1] - 18 * mm, GENERATED_AT.strftime("%Y-%m-%d"))

        canvas.setStrokeColor(LINE)
        canvas.line(16 * mm, 12 * mm, A4[0] - 16 * mm, 12 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(16 * mm, 7 * mm, "Sepsis ICU Monitor -- final-year academic project, research/educational system")
        canvas.drawRightString(A4[0] - 16 * mm, 7 * mm, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_page_frame, onLaterPages=_draw_page_frame)
    return buffer.getvalue()


if __name__ == "__main__":
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_bytes(build_project_overview_pdf())
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size:,} bytes)")
