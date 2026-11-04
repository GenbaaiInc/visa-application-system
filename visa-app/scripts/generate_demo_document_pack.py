#!/usr/bin/env python3
"""Generate a fully fictional document pack for visa-app demos.

All generated identity-style documents are intentionally non-official samples:
they use fictional people, fictional organizations, invalid document numbers,
and prominent DEMO / NOT VALID markings.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


try:
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    BASE_FONT = "HeiseiKakuGo-W5"
except Exception:
    BASE_FONT = "Helvetica"


@dataclass(frozen=True)
class DemoCase:
    case_id: str = "demo-gijinkoku-001"
    application_type: str = "certificate_of_eligibility"
    target_status: str = "engineer_humanities_international"
    applicant_name: str = "SAMPLE ARIA"
    applicant_name_local: str = "サンプル アリア"
    nationality: str = "Nepal"
    sex: str = "female"
    birth_date: str = "1998-06-15"
    birth_place: str = "Luma City"
    marital_status: str = "single"
    passport_number: str = "ZZ0000000"
    passport_expiry: str = "2034-12-31"
    home_address: str = "77 Demo Lane, Luma City, Nepal"
    email: str = "sample.aria.demo@example.invalid"
    phone: str = "+977-01-000-0000"
    school: str = "Luminara Technical College"
    degree: str = "Bachelor of Computer Science"
    graduation_date: str = "2021-06-30"
    prior_employer: str = "DemoSoft Labs Pvt. Ltd."
    prior_employment_period: str = "2021-08 to 2024-03"
    employer_name: str = "株式会社デモリンクAI"
    employer_name_en: str = "DemoLink AI Inc."
    employer_number: str = "9999999999999"
    employer_postal_code: str = "9999999"
    employer_address: str = "東京都デモ区サンプル町0-0-0"
    employer_phone: str = "9999999999"
    employment_insurance_office_number: str = "99999999999"
    annual_sales_jpy: int = 120_000_000
    employee_count: int = 24
    foreign_employee_count: int = 4
    technical_intern_count: int = 0
    start_date: str = "2027-04-01"
    monthly_salary: int = 320_000
    conflict_salary: int = 300_000
    occupation: str = "Software Developer"
    job_category_primary: str = "情報処理・通信技術"
    job_title: str = "AI Data Application Engineer"
    contract_type: str = "雇用 Employment"
    employment_period_type: str = "Fixed-term"
    employment_period_years: int = 1
    employment_period_months: int = 0
    planned_entry_date: str = "2027-03-15"
    planned_port: str = "Narita International Airport"
    planned_period_years: int = 5
    planned_period_months: int = 0
    japan_contact_postal_code: str = "9999999"
    japan_contact_address: str = "東京都デモ区サンプル町0-0-0 Demo Residence 101"
    japan_contact_phone: str = "9999999999"
    prior_entries_count: int = 0
    prior_coe_count: int = 0
    job_activity: str = (
        "Develops AI-assisted data processing tools, prepares dataset quality reports, "
        "implements Python and SQL workflows, and coordinates technical specifications "
        "with product and client teams. The role requires university-level computer "
        "science knowledge and does not include manual labor."
    )


CASE = DemoCase()
OUTPUTS = [
    "DEMO_01_passport_style_sample_NOT_VALID.pdf",
    "DEMO_02_applicant_intake_sheet_NOT_VALID.xlsx",
    "DEMO_03_resume_NOT_VALID.pdf",
    "DEMO_04_graduation_certificate_NOT_VALID.pdf",
    "DEMO_05_academic_transcript_NOT_VALID.pdf",
    "DEMO_06_offer_letter_NOT_VALID.pdf",
    "DEMO_07_employment_terms_notice_NOT_VALID.docx",
    "DEMO_08_company_profile_registry_style_NOT_VALID.pdf",
    "DEMO_90_salary_conflict_optional_NOT_VALID.pdf",
]

LEGACY_OUTPUTS = [
    "DEMO_02_resume_NOT_VALID.pdf",
    "DEMO_03_graduation_certificate_NOT_VALID.pdf",
    "DEMO_04_academic_transcript_NOT_VALID.pdf",
    "DEMO_05_offer_letter_NOT_VALID.pdf",
    "DEMO_06_employment_terms_notice_NOT_VALID.docx",
    "DEMO_07_company_profile_registry_style_NOT_VALID.pdf",
]


def make_styles():
    styles = getSampleStyleSheet()
    for style_name in styles.byName:
        styles[style_name].fontName = BASE_FONT
    styles.add(
        ParagraphStyle(
            "DemoTitle",
            parent=styles["Title"],
            fontName=BASE_FONT,
            fontSize=20,
            leading=26,
            alignment=TA_CENTER,
            spaceAfter=14,
        )
    )
    styles.add(
        ParagraphStyle(
            "DemoHeading",
            parent=styles["Heading2"],
            fontName=BASE_FONT,
            fontSize=13,
            leading=17,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#1F2937"),
        )
    )
    styles.add(
        ParagraphStyle(
            "DemoBody",
            parent=styles["BodyText"],
            fontName=BASE_FONT,
            fontSize=10.3,
            leading=14,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            "SmallCenter",
            parent=styles["BodyText"],
            fontName=BASE_FONT,
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4B5563"),
        )
    )
    styles.add(
        ParagraphStyle(
            "SmallLeft",
            parent=styles["BodyText"],
            fontName=BASE_FONT,
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#4B5563"),
        )
    )
    return styles


def watermark(canvas, doc):
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFont(BASE_FONT, 46)
    canvas.setFillColor(colors.Color(0.75, 0.10, 0.10, alpha=0.14))
    canvas.translate(width / 2, height / 2)
    canvas.rotate(32)
    canvas.drawCentredString(0, 0, "DEMO / NOT VALID")
    canvas.restoreState()
    canvas.saveState()
    canvas.setFont(BASE_FONT, 8)
    canvas.setFillColor(colors.HexColor("#B91C1C"))
    canvas.drawString(
        doc.leftMargin,
        0.45 * inch,
        "Fictional sample for software demonstration only. Not an identity, immigration, employment, or corporate record.",
    )
    canvas.drawRightString(width - doc.rightMargin, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def demo_banner(styles):
    return Table(
        [
            [
                Paragraph(
                    "DEMO / NOT VALID - Fictional sample. Do not use as evidence or identity.",
                    styles["SmallCenter"],
                )
            ]
        ],
        colWidths=[7.1 * inch],
    )


def banner_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEE2E2")),
            ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#EF4444")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#991B1B")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def table_style(header=False):
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D1D5DB")),
        ("FONTNAME", (0, 0), (-1, -1), BASE_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9.2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    else:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F4F6")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#111827")),
            ]
        )
    return TableStyle(commands)


def p(text: str, styles, style="DemoBody"):
    return Paragraph(text, styles[style])


def build_standard_pdf(
    path: Path,
    title: str,
    blocks: Iterable,
    pagesize=letter,
    top_margin=0.72 * inch,
    bottom_margin=0.72 * inch,
):
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(path),
        pagesize=pagesize,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
    )
    story = [demo_banner(styles), Spacer(1, 0.16 * inch), p(title, styles, "DemoTitle")]
    story[0].setStyle(banner_style())
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            story.append(p(block[1], styles, "DemoHeading"))
        elif kind == "para":
            story.append(p(block[1], styles))
        elif kind == "kv":
            rows = [[p(k, styles, "SmallLeft"), p(str(v), styles, "SmallLeft")] for k, v in block[1]]
            table = Table(rows, colWidths=[2.15 * inch, 4.95 * inch])
            table.setStyle(table_style(header=False))
            story.append(table)
            story.append(Spacer(1, 0.08 * inch))
        elif kind == "table":
            rows = [[p(str(cell), styles, "SmallLeft") for cell in row] for row in block[1]]
            table = Table(rows, colWidths=block[2], repeatRows=1)
            table.setStyle(table_style(header=True))
            story.append(table)
            story.append(Spacer(1, 0.08 * inch))
        elif kind == "break":
            story.append(PageBreak())
    doc.build(story, onFirstPage=watermark, onLaterPages=watermark)


def make_portrait(path: Path):
    img = Image.new("RGB", (900, 1100), "#E5E7EB")
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 56)
        body_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 30)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    draw.rectangle((0, 0, 900, 1100), fill="#EEF2FF")
    draw.ellipse((280, 145, 620, 485), fill="#9CA3AF")
    draw.ellipse((385, 235, 515, 365), fill="#F3D7BF")
    draw.arc((365, 270, 535, 420), start=20, end=160, fill="#374151", width=5)
    draw.rectangle((285, 505, 615, 820), fill="#4B5563")
    draw.polygon([(285, 505), (615, 505), (450, 660)], fill="#F3D7BF")
    draw.rectangle((0, 900, 900, 1100), fill="#FEE2E2")
    draw.text((120, 920), "DEMO / NOT VALID", font=title_font, fill="#991B1B")
    draw.text((125, 995), "Fictional portrait placeholder", font=body_font, fill="#4B5563")
    img.save(path)


def make_passport_png(path: Path):
    img = Image.new("RGB", (1600, 1000), "#F3F4F6")
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 40)
        body_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 28)
        small_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
        mono_font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 24)
    except Exception:
        title_font = body_font = small_font = mono_font = ImageFont.load_default()

    draw.rounded_rectangle((70, 70, 1530, 930), radius=24, fill="#FFFFFF", outline="#CBD5E1", width=4)
    draw.line((800, 90, 800, 910), fill="#CBD5E1", width=3)
    draw.text((135, 118), "FICTIONAL PASSPORT", font=title_font, fill="#111827")
    draw.text((135, 168), "STYLE SAMPLE", font=title_font, fill="#111827")
    draw.text((135, 225), "DEMO COUNTRY - NOT A GOVERNMENT DOCUMENT", font=body_font, fill="#991B1B")
    draw.rectangle((135, 275, 465, 655), fill="#EEF2FF", outline="#6B7280", width=3)
    portrait = path.parent / "applicant_portrait.png"
    if portrait.exists():
        src = Image.open(portrait).convert("RGB")
        src = src.crop((0, 0, src.width, int(src.height * 0.86)))
        src.thumbnail((310, 360))
        img.paste(src, (145 + (310 - src.width) // 2, 285 + (360 - src.height) // 2))
    else:
        draw.ellipse((240, 330, 360, 450), fill="#F3D7BF", outline="#6B7280")
        draw.rectangle((215, 470, 385, 610), fill="#4B5563")
    fields = [
        ("Name", CASE.applicant_name),
        ("Nationality", CASE.nationality),
        ("Date of birth", CASE.birth_date),
        ("Birth place", CASE.birth_place),
        ("Sex", CASE.sex),
        ("Passport no", CASE.passport_number),
        ("Expiry", CASE.passport_expiry),
        ("Authority", "DEMO OFFICE"),
    ]
    y = 285
    for label, value in fields:
        draw.text((525, y), label, font=small_font, fill="#6B7280")
        draw.text((525, y + 32), value, font=body_font, fill="#111827")
        y += 82
    draw.text((870, 150), "Invalid sample machine-readable zone", font=body_font, fill="#111827")
    draw.text((870, 200), "ZZZ<DEMO<NOT<VALID<<<<<<<<<<<<<<", font=mono_font, fill="#111827")
    draw.text((870, 245), "ZZ0000000<0XXX9806150F3412310<<<<<<0", font=mono_font, fill="#111827")
    draw.multiline_text(
        (870, 335),
        "This page intentionally avoids real passport layouts,\nsecurity features, and valid MRZ encoding.",
        font=small_font,
        fill="#374151",
        spacing=10,
    )
    for angle_y in [405, 545, 685]:
        draw.text((880, angle_y), "DEMO / NOT VALID", font=title_font, fill="#FCA5A5")
    img.save(path)


def make_passport_pdf(path: Path, passport_png: Path):
    from reportlab.lib.utils import ImageReader

    page_size = landscape(A4)
    width, height = page_size
    c = __import__("reportlab.pdfgen.canvas", fromlist=["Canvas"]).Canvas(str(path), pagesize=page_size)
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(0, 0, width, height, fill=True, stroke=False)
    c.drawImage(ImageReader(str(passport_png)), 1.0 * cm, 1.2 * cm, width - 2.0 * cm, height - 2.4 * cm, preserveAspectRatio=True)
    c.saveState()
    c.setFont(BASE_FONT, 58)
    c.setFillColor(colors.Color(0.75, 0.10, 0.10, alpha=0.12))
    c.translate(width / 2, height / 2)
    c.rotate(28)
    c.drawCentredString(0, 0, "DEMO / NOT VALID")
    c.restoreState()
    c.setFont(BASE_FONT, 9)
    c.setFillColor(colors.HexColor("#991B1B"))
    c.drawString(1.0 * cm, 0.6 * cm, "Fictional sample. Not a passport. Not valid for identity, travel, immigration, or KYC.")
    c.save()


def make_resume(path: Path):
    build_standard_pdf(
        path,
        "Resume for Technology and Humanities Visa Demo",
        [
            ("heading", "Applicant"),
            (
                "kv",
                [
                    ("Name", CASE.applicant_name),
                    ("Nationality", CASE.nationality),
                    ("Date of birth", CASE.birth_date),
                    ("Birth place", CASE.birth_place),
                    ("Occupation", CASE.occupation),
                    ("Address", CASE.home_address),
                    ("Email", CASE.email),
                    ("Phone", CASE.phone),
                ],
            ),
            ("heading", "Education"),
            (
                "kv",
                [
                    ("School", CASE.school),
                    ("Degree", CASE.degree),
                    ("Graduation date", CASE.graduation_date),
                    ("Major field", "Computer Science and Data Systems"),
                ],
            ),
            ("heading", "Employment history"),
            (
                "kv",
                [
                    ("Employer", CASE.prior_employer),
                    ("Period", CASE.prior_employment_period),
                    ("Role", "Data Application Developer"),
                    (
                        "Duties",
                        "Python ETL scripts, SQL data validation, dashboard back-end support, and technical coordination with product managers.",
                    ),
                ],
            ),
            ("heading", "Japanese employer and planned role"),
            (
                "kv",
                [
                    ("Employer", f"{CASE.employer_name} / {CASE.employer_name_en}"),
                    ("Start date", CASE.start_date),
                    ("Job category primary", CASE.job_category_primary),
                    ("Contract type", CASE.contract_type),
                    ("Employment period type", CASE.employment_period_type),
                    ("Employment period years", str(CASE.employment_period_years)),
                    ("Employment period months", str(CASE.employment_period_months)),
                    ("Monthly salary", f"JPY {CASE.monthly_salary:,}"),
                ],
            ),
            ("para", CASE.job_activity),
        ],
        pagesize=A4,
        top_margin=0.45 * inch,
        bottom_margin=0.55 * inch,
    )


def make_graduation(path: Path):
    build_standard_pdf(
        path,
        "Graduation Certificate Demo",
        [
            ("para", "This certificate is a fictional sample generated for software demonstration only."),
            (
                "kv",
                [
                    ("Institution", CASE.school),
                    ("Student", CASE.applicant_name),
                    ("Degree awarded", CASE.degree),
                    ("Major", "Computer Science"),
                    ("Graduation date", CASE.graduation_date),
                    ("Certificate number", "DEMO-GRAD-0001"),
                ],
            ),
            ("heading", "Certification statement"),
            (
                "para",
                "The sample student completed a curriculum covering programming, databases, algorithms, statistics, and software engineering. This statement is fictional and has no legal effect.",
            ),
        ],
    )


def make_transcript(path: Path):
    subjects = [
        ["Course", "Year", "Grade", "Relation to planned AI data role"],
        ["Programming Fundamentals", "2017", "A", "Python programming and problem decomposition"],
        ["Data Structures and Algorithms", "2018", "A-", "Algorithmic design used in data processing workflows"],
        ["Database Systems", "2019", "A", "SQL schema design and validation queries"],
        ["Statistics for Computing", "2019", "B+", "Statistical interpretation of dataset quality"],
        ["Machine Learning Basics", "2020", "A-", "Model evaluation and feature preparation"],
        ["Software Engineering Project", "2021", "A", "Team development and requirements documentation"],
    ]
    build_standard_pdf(
        path,
        "Academic Transcript Demo",
        [
            ("kv", [("Student", CASE.applicant_name), ("Degree", CASE.degree), ("Institution", CASE.school)]),
            ("heading", "Selected coursework"),
            ("table", subjects, [2.05 * inch, 0.7 * inch, 0.7 * inch, 3.65 * inch]),
            ("heading", "Demo note"),
            (
                "para",
                "The coursework is intentionally aligned with the planned data application engineering role so that extraction and review screens can demonstrate education to duty matching.",
            ),
        ],
    )


def make_offer(path: Path):
    build_standard_pdf(
        path,
        "Offer Letter Demo",
        [
            ("para", f"Dear {CASE.applicant_name},"),
            (
                "para",
                f"{CASE.employer_name_en} offers you the position of {CASE.job_title}, starting {CASE.start_date}. "
                f"The offered salary is JPY {CASE.monthly_salary:,} per month.",
            ),
            ("heading", "Planned duties"),
            ("para", CASE.job_activity),
            (
                "kv",
                [
                    ("Employer", f"{CASE.employer_name} / {CASE.employer_name_en}"),
                    ("Corporate number", CASE.employer_number),
                    ("Contract type", CASE.contract_type),
                    ("Employment period type", CASE.employment_period_type),
                    ("Employment period years", str(CASE.employment_period_years)),
                    ("Employment period months", str(CASE.employment_period_months)),
                    ("Job category primary", CASE.job_category_primary),
                    ("Work location", CASE.employer_address),
                ],
            ),
            ("para", "This letter is fictional and is generated only for QA and demo uploads."),
        ],
    )


def make_conflict_salary(path: Path):
    build_standard_pdf(
        path,
        "Optional Salary Conflict Demo",
        [
            (
                "para",
                "This optional document intentionally conflicts with the main offer letter. Upload it only when demonstrating alternative value detection.",
            ),
            (
                "kv",
                [
                    ("Applicant", CASE.applicant_name),
                    ("Employer", CASE.employer_name_en),
                    ("Conflicting salary", f"JPY {CASE.conflict_salary:,} per month"),
                    ("Correct salary in normal set", f"JPY {CASE.monthly_salary:,} per month"),
                ],
            ),
        ],
    )


def make_company_docs(path: Path):
    build_standard_pdf(
        path,
        "Company Profile and Registry Style Demo",
        [
            ("heading", "Company profile"),
            (
                "kv",
                [
                    ("Company name", f"{CASE.employer_name} / {CASE.employer_name_en}"),
                    ("Corporate number", CASE.employer_number),
                    ("Postal code", CASE.employer_postal_code),
                    ("Address", CASE.employer_address),
                    ("Phone", CASE.employer_phone),
                    ("Employment insurance office number", CASE.employment_insurance_office_number),
                    ("Established", "2024-01-09"),
                    ("Capital", "JPY 10,000,000"),
                    ("Annual sales", f"JPY {CASE.annual_sales_jpy:,}"),
                    ("Employees", str(CASE.employee_count)),
                    ("Foreign employees", str(CASE.foreign_employee_count)),
                    ("Technical interns", str(CASE.technical_intern_count)),
                    ("Industry", "AI systems development and business process automation"),
                ],
            ),
            ("heading", "Planned business activity"),
            (
                "para",
                "The company develops AI workflow tools, data extraction utilities, and internal automation systems for corporate clients. The sample applicant will work on engineering and data processing duties.",
            ),
            ("heading", "Registry style notice"),
            (
                "para",
                "This section imitates the type of information used during a demo, but it is not a registry extract and is not issued by any authority.",
            ),
        ],
    )


def make_employment_terms_docx(path: Path):
    docx_font = "Liberation Sans"

    def apply_run_font(run, *, size=None, bold=None, color=None):
        run.font.name = docx_font
        run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), docx_font)
        run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), docx_font)
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), docx_font)
        if size is not None:
            run.font.size = size
        if bold is not None:
            run.bold = bold
        if color is not None:
            run.font.color.rgb = color

    def shade_cell(cell, fill):
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = tc_pr.find(qn("w:shd"))
        if shd is None:
            shd = OxmlElement("w:shd")
            tc_pr.append(shd)
        shd.set(qn("w:fill"), fill)

    doc = Document()
    section = doc.sections[0]
    section.page_width = int(8.5 * 914400)
    section.page_height = int(11 * 914400)
    section.top_margin = int(0.75 * 914400)
    section.bottom_margin = int(0.75 * 914400)
    section.left_margin = int(0.72 * 914400)
    section.right_margin = int(0.72 * 914400)

    header = section.header.paragraphs[0]
    header.text = "DEMO / NOT VALID - fictional employment terms sample"
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer = section.footer.paragraphs[0]
    footer.text = "Generated for software demonstration only. This is not a contract."
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

    style = doc.styles["Normal"]
    style.font.name = docx_font
    style.font.size = Pt(10.5)
    style._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), docx_font)
    style._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), docx_font)
    style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), docx_font)

    title_style = doc.styles["Title"]
    title_style.font.name = docx_font
    title_style.font.color.rgb = RGBColor(0, 0, 0)
    title_style._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), docx_font)
    title_style._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), docx_font)
    title_style._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), docx_font)
    title_ppr = title_style._element.get_or_add_pPr()
    title_border = title_ppr.find(qn("w:pBdr"))
    if title_border is not None:
        title_ppr.remove(title_border)

    title = doc.add_paragraph()
    title.style = doc.styles["Title"]
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Employment Terms Notice Demo")
    apply_run_font(run, size=Pt(20), bold=True, color=RGBColor(0, 0, 0))

    warning = doc.add_paragraph()
    warning.alignment = WD_ALIGN_PARAGRAPH.CENTER
    w = warning.add_run("DEMO / NOT VALID - Fictional sample. Do not use as employment evidence.")
    apply_run_font(w, bold=True, color=RGBColor(153, 27, 27))

    doc.add_paragraph(
        "This document is a fully fictional employment terms notice prepared for upload and extraction demos."
    )

    table = doc.add_table(rows=1, cols=2)
    table.autofit = True
    table.rows[0].cells[0].text = "Field"
    table.rows[0].cells[1].text = "Demo value"
    rows = [
        ("Applicant", CASE.applicant_name),
        ("Employer", CASE.employer_name_en),
        ("Corporate number", CASE.employer_number),
        ("Job category primary", "Information processing and communications technology"),
        ("Start date", CASE.start_date),
        ("Contract type", "Employment"),
        ("Employment period type", CASE.employment_period_type),
        ("Employment period years", str(CASE.employment_period_years)),
        ("Employment period months", str(CASE.employment_period_months)),
        ("Monthly salary", f"JPY {CASE.monthly_salary:,}"),
        ("Work location", "Demo Ward, Sample Town 0-0-0, Tokyo"),
        ("Work hours", "09:00 to 18:00, Monday to Friday"),
        ("Duties", CASE.job_activity),
    ]
    for key, value in rows:
        cells = table.add_row().cells
        cells[0].text = key
        cells[1].text = value

    table_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:color"), "D9D9D9")
        borders.append(border)
    table_pr.append(borders)

    for cell in table.rows[0].cells:
        shade_cell(cell, "1F2937")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            for cell_run in paragraph.runs:
                apply_run_font(cell_run, bold=True, color=RGBColor(255, 255, 255))

    for row in table.rows[1:]:
        for cell in row.cells:
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for paragraph in cell.paragraphs:
                for cell_run in paragraph.runs:
                    apply_run_font(cell_run)

    doc.add_paragraph()
    doc.add_paragraph(
        "The planned role is related to the applicant's computer science degree and prior data application development experience."
    )
    doc.add_paragraph("Authorized demo contact: Demo HR Team")

    for paragraph in list(doc.paragraphs) + list(section.header.paragraphs) + list(section.footer.paragraphs):
        for body_run in paragraph.runs:
            apply_run_font(body_run)
    doc.save(path)


def make_intake_xlsx(path: Path):
    script_dir = Path(__file__).resolve().parent
    dependency_node_modules = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
    )
    builder_dir = Path("tmp/demo-intake-builder").resolve()
    builder_dir.mkdir(parents=True, exist_ok=True)
    builder_script = builder_dir / "build_demo_intake_xlsx.mjs"
    shutil.copy2(script_dir / "build_demo_intake_xlsx.mjs", builder_script)
    link = builder_dir / "node_modules"
    if not link.exists():
        os.symlink(dependency_node_modules, link, target_is_directory=True)

    preview = Path("tmp/pdfs/demo-gijinkoku-rendered/intake_sheet.png")
    subprocess.run(
        [
            "node",
            str(builder_script),
            str(path),
            str(preview),
        ],
        check=True,
    )


def write_manifest(path: Path, output_dir: Path):
    manifest = {
        "case_id": CASE.case_id,
        "warning": "All files are fully fictional DEMO / NOT VALID samples.",
        "normal_upload_files": OUTPUTS[:-1],
        "optional_conflict_file": OUTPUTS[-1],
        "expected_core_fields": {
            "applicant.name_roman": CASE.applicant_name,
            "applicant.nationality_region": CASE.nationality,
            "applicant.birth_date": CASE.birth_date,
            "applicant.sex": CASE.sex,
            "applicant.passport.number": CASE.passport_number,
            "applicant.passport.expiry_date": CASE.passport_expiry,
            "applicant.occupation": CASE.occupation,
            "applicant.marital_status": CASE.marital_status,
            "applicant.education.0.school_name": CASE.school,
            "applicant.education.0.major_field": "Computer Science",
            "applicant.education.0.graduation_date": CASE.graduation_date,
            "employment.monthly_salary": CASE.monthly_salary,
            "employment.contract_type": CASE.contract_type,
            "employment.employment_period_type": CASE.employment_period_type,
            "employment.employment_period_years": CASE.employment_period_years,
            "employment.employment_period_months": CASE.employment_period_months,
            "employment.job_category_primary": CASE.job_category_primary,
            "employer.name": CASE.employer_name,
            "employer.corporate_number": CASE.employer_number,
            "employment.activity_details": CASE.job_activity,
        },
        "notes": [
            "Use the optional salary conflict PDF only when demonstrating alternative candidate values.",
            "The passport-style file deliberately avoids valid government document layout and valid MRZ data.",
            "No real person, school, employer, passport, or corporate record is represented.",
        ],
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_readme(path: Path):
    path.write_text(
        "\n".join(
            [
                "# Demo document pack for visa-app",
                "",
                "This folder contains fully fictional files for the engineer humanities international services COE demo.",
                "Every generated document is marked `DEMO / NOT VALID` and must not be used as evidence, identity, employment, or corporate records.",
                "",
                "Normal demo upload files:",
                *[f"- `{name}`" for name in OUTPUTS[:-1]],
                "",
                "Optional conflict demo:",
                f"- `{OUTPUTS[-1]}` intentionally says JPY {CASE.conflict_salary:,}, while the normal set says JPY {CASE.monthly_salary:,}.",
                "",
                "Suggested flow:",
                "1. Create a 技術・人文知識・国際業務 COE case.",
                "2. Upload the normal demo files.",
                "3. Run extraction and review the applicant, education, employer, and employment fields.",
                "4. Upload the optional conflict file only when testing alternative salary candidates.",
                "",
                "All names and numbers in this folder are synthetic.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def generate(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    assets = output_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    for name in [*OUTPUTS, *LEGACY_OUTPUTS]:
        target = output_dir / name
        if target.exists():
            target.unlink()
    for target in output_dir.glob("*.inspect.ndjson"):
        target.unlink()

    portrait = assets / "applicant_portrait.png"
    passport_png = assets / "passport_style_sample_NOT_VALID.png"
    if not portrait.exists():
        make_portrait(portrait)
    make_passport_png(passport_png)

    make_passport_pdf(output_dir / OUTPUTS[0], passport_png)
    make_intake_xlsx(output_dir / OUTPUTS[1])
    make_resume(output_dir / OUTPUTS[2])
    make_graduation(output_dir / OUTPUTS[3])
    make_transcript(output_dir / OUTPUTS[4])
    make_offer(output_dir / OUTPUTS[5])
    make_employment_terms_docx(output_dir / OUTPUTS[6])
    make_company_docs(output_dir / OUTPUTS[7])
    make_conflict_salary(output_dir / OUTPUTS[8])

    write_manifest(output_dir / "manifest.json", output_dir)
    write_readme(output_dir / "README.md")
    (output_dir / "upload_order.txt").write_text(
        "\n".join(OUTPUTS[:-1]) + "\n\nOptional:\n" + OUTPUTS[-1] + "\n",
        encoding="utf-8",
    )
    for target in output_dir.glob("*.inspect.ndjson"):
        target.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="qa/test-files/demo-gijinkoku",
        help="Directory to receive the generated demo document pack.",
    )
    args = parser.parse_args()
    generate(Path(args.output_dir))
    print(f"Generated demo document pack in {args.output_dir}")


if __name__ == "__main__":
    main()
