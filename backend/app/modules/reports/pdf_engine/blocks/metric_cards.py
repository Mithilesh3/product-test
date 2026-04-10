from reportlab.platypus import Table, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor


def metric_card(styles, title, value):

    # ------------------------------------------------
    # Value Style (large number)
    # ------------------------------------------------
    value_style = ParagraphStyle(
        "metric_value",
        parent=styles["Heading2"],
        alignment=1,
        fontSize=28,
        textColor=HexColor("#1b2f4b"),
        spaceAfter=6
    )

    # ------------------------------------------------
    # Title Style
    # ------------------------------------------------
    title_style = ParagraphStyle(
        "metric_title",
        parent=styles["BodyText"],
        alignment=1,
        fontSize=10,
        textColor=HexColor("#4a4a4a")
    )

    # ------------------------------------------------
    # Card Layout
    # ------------------------------------------------
    card = Table(
        [
            [Paragraph(str(value), value_style)],
            [Paragraph(title, title_style)]
        ],
        colWidths=[150]
    )

    # ------------------------------------------------
    # Card Styling
    # ------------------------------------------------
    card.setStyle([

        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#faf8f2")),

        ("BOX", (0, 0), (-1, -1), 1, HexColor("#d6cda7")),

        ("ALIGN", (0, 0), (-1, -1), "CENTER"),

        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),

        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),

    ])

    return card