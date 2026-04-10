from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle


GRID_LAYOUT = [
    [(4, "North-West"), (9, "North"), (2, "North-East")],
    [(3, "West"), (5, "Center"), (7, "East")],
    [(8, "South-West"), (1, "South"), (6, "South-East")],
]


def _count(grid_counts, number):
    value = grid_counts.get(str(number), grid_counts.get(number, 0))
    try:
        return int(value)
    except Exception:
        return 0


def build_loshu_grid(styles, grid_counts):
    if not grid_counts:
        grid_counts = {}

    present_style = ParagraphStyle(
        "loshu_present",
        parent=styles["BodyText"],
        alignment=1,
        leading=13,
        textColor=HexColor("#14532d"),
    )
    missing_style = ParagraphStyle(
        "loshu_missing",
        parent=styles["BodyText"],
        alignment=1,
        leading=13,
        textColor=HexColor("#9f1239"),
    )

    rows = []
    cell_backgrounds = []

    for row_idx, row in enumerate(GRID_LAYOUT):
        rendered_row = []
        for col_idx, (number, direction) in enumerate(row):
            value = _count(grid_counts, number)
            present = value > 0
            style = present_style if present else missing_style
            status = f"x{value}" if present else "Missing"
            rendered_row.append(
                Paragraph(
                    f"<b>{number}</b><br/><font size='7'>{direction}</font><br/><font size='9'>{status}</font>",
                    style,
                )
            )

            if present:
                bg = HexColor("#eaf8ef")
            else:
                bg = HexColor("#fff1f2")
            cell_backgrounds.append(("BACKGROUND", (col_idx, row_idx), (col_idx, row_idx), bg))

        rows.append(rendered_row)

    table = Table(rows, colWidths=[126, 126, 126], rowHeights=[68, 68, 68])

    style_cmds = [
        ("BOX", (0, 0), (-1, -1), 1.5, HexColor("#c6a15b")),
        ("INNERGRID", (0, 0), (-1, -1), 1, HexColor("#d8caa3")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]
    style_cmds.extend(cell_backgrounds)

    table.setStyle(TableStyle(style_cmds))

    return table
