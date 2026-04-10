from reportlab.platypus import Table, Image, Spacer
from reportlab.lib.units import mm


def split_section(image_path, paragraph):

    img = Image(
        str(image_path),
        width=65 * mm,
        height=65 * mm
    )

    layout = Table(
        [
            [
                img,
                paragraph
            ]
        ],
        colWidths=[75 * mm, 105 * mm]
    )

    layout.setStyle([

        # alignment
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        # spacing
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),

        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),

    ])

    return layout