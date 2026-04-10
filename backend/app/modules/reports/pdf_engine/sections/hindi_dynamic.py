import re

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, PageBreak


PAGE_WIDTH = 470


def _normalized_blocks(blocks):
    if isinstance(blocks, str):
        blocks = [blocks]
    return [str(block or "").strip() for block in (blocks or []) if str(block or "").strip()]


def _section_sort_key(section):
    title = str(section.get("title") or "")
    match = re.match(r"^\s*(\d+)\.", title)
    return (int(match.group(1)) if match else 10_000, int(section.get("order") or 10_000))


def _split_line(line):
    text = str(line or "").strip()
    if ":" in text:
        left, right = text.split(":", 1)
        return left.strip(), right.strip()
    return "विवरण", text


def _escape(text):
    return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ensure_styles(styles):
    if "HindiPremiumTitle" not in styles:
        styles.add(
            ParagraphStyle(
                "HindiPremiumTitle",
                parent=styles["Heading1"],
                fontSize=17,
                leading=21,
                textColor=HexColor("#183a63"),
            )
        )
    if "HindiPremiumSubtitle" not in styles:
        styles.add(
            ParagraphStyle(
                "HindiPremiumSubtitle",
                parent=styles["BodyText"],
                fontSize=10,
                leading=14,
                textColor=HexColor("#8d7a57"),
            )
        )
    if "HindiPremiumBody" not in styles:
        styles.add(
            ParagraphStyle(
                "HindiPremiumBody",
                parent=styles.get("CardBody", styles["BodyText"]),
                fontSize=10.4,
                leading=15,
                textColor=HexColor("#334e68"),
            )
        )
    return {
        "title": styles["HindiPremiumTitle"],
        "subtitle": styles["HindiPremiumSubtitle"],
        "body": styles["HindiPremiumBody"],
    }


def _section_header(section, idx, text_styles):
    title = str(section.get("title") or section.get("key") or "Strategic Section").strip()
    subtitle = str(section.get("subtitle") or "").strip()
    title_lines = [line.strip() for line in title.split("\n") if line.strip()]

    if title_lines:
        title_lines[0] = f"{idx}. {title_lines[0]}"
    else:
        title_lines = [f"{idx}. Strategic Section", "रणनीतिक अनुभाग"]

    title_html = "<br/>".join(_escape(line) for line in title_lines)
    header = Table(
        [[Paragraph(title_html, text_styles["title"])], [Paragraph(_escape(subtitle), text_styles["subtitle"])]] ,
        colWidths=[PAGE_WIDTH],
    )
    header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#fffdf8")),
                ("BOX", (0, 0), (-1, -1), 1, HexColor("#caa86a")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return header


def _build_waterfall_bullet_pages(elements, styles, sections, *, force_page_break: bool = False):
    text_styles = _ensure_styles(styles)
    sorted_sections = [s for s in sorted(sections, key=_section_sort_key) if isinstance(s, dict)]

    last_index = len(sorted_sections)
    for index, section in enumerate(sorted_sections, start=1):
        blocks = _normalized_blocks(section.get("blocks"))
        if not blocks:
            continue

        elements.append(_section_header(section, index, text_styles))
        elements.append(Spacer(1, 8))

        for line in blocks:
            label, value = _split_line(line)
            bullet_html = f"• <b>{_escape(label)}:</b> {_escape(value)}"
            elements.append(Paragraph(bullet_html, text_styles["body"]))
            elements.append(Spacer(1, 4))

        divider = Table([["" ]], colWidths=[PAGE_WIDTH], rowHeights=[1])
        divider.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#d7e1ec")),
                    ("BOX", (0, 0), (-1, -1), 0, HexColor("#d7e1ec")),
                ]
            )
        )
        elements.append(Spacer(1, 6))
        elements.append(divider)
        elements.append(Spacer(1, 10))
        if force_page_break and index < last_index:
            elements.append(PageBreak())


def build_hindi_dynamic_pages(elements, renderer, styles, data):
    _ = renderer
    sections = data.get("report_sections")
    if not isinstance(sections, list) or not sections:
        return

    plan = str((data.get("meta") or {}).get("plan_tier") or "").strip().lower()
    force_page_break = plan in {"enterprise", "premium"}
    # Uniform waterfall for all plans: cleaner, aligned, easy to scan.
    _build_waterfall_bullet_pages(elements, styles, sections, force_page_break=force_page_break)
