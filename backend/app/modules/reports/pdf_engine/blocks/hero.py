from reportlab.platypus import Paragraph, Spacer, Image, Table
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor


def hero_cover(styles, name, logo_path=None, symbol_path=None):

    title_style = ParagraphStyle(
        "hero_title",
        parent=styles["Heading1"],
        fontSize=36,
        alignment=1,
        textColor=HexColor("#0f2747")
    )

    subtitle_style = ParagraphStyle(
        "hero_subtitle",
        parent=styles["Heading2"],
        fontSize=18,
        alignment=1
    )

    name_style = ParagraphStyle(
        "hero_name",
        parent=styles["Heading3"],
        fontSize=20,
        alignment=1,
        spaceBefore=20
    )

    elements = []

    if symbol_path:
        elements.append(
            Image(str(symbol_path), width=50*mm, height=50*mm)
        )
        elements.append(Spacer(1,20))

    elements.append(Paragraph("Life Signify NumAI", title_style))

    elements.append(
        Paragraph(
            "Strategic Life Intelligence Report",
            subtitle_style
        )
    )

    elements.append(
        Paragraph(
            "ENTERPRISE Intelligence Report",
            subtitle_style
        )
    )

    elements.append(Spacer(1,30))

    elements.append(Paragraph(name, name_style))

    return elements