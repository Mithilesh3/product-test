from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


# =====================================================
# THEME COLORS
# =====================================================

HEADER_COLOR = colors.HexColor("#1f3c88")
SECONDARY_COLOR = colors.HexColor("#f5b041")

GRID_COLOR = colors.HexColor("#d5d8dc")

ROW_LIGHT = colors.HexColor("#f8f9f9")
ROW_ALT = colors.HexColor("#eef2f7")

MISSING_COLOR = colors.HexColor("#fdecea")


# =====================================================
# SAFE VALUE
# =====================================================

def _safe(value):

    if value is None:
        return "N/A"

    return str(value)


# =====================================================
# CORE NUMBERS TABLE
# =====================================================

def render_core_numbers_table(data: dict):

    pyth = data.get("pythagorean", {})
    chal = data.get("chaldean", {})
    email = data.get("email_analysis", {})
    name = data.get("name_correction", {})

    rows = [
        ["Numerology Metric", "Value"],

        ["Life Path Number", _safe(pyth.get("life_path_number"))],
        ["Destiny Number", _safe(pyth.get("destiny_number"))],
        ["Expression Number", _safe(pyth.get("expression_number"))],

        ["Name Number (Chaldean)", _safe(chal.get("name_number"))],

        ["Email Number", _safe(email.get("email_number"))],

        ["Name Correction Advice", _safe(name.get("suggestion"))],
    ]

    table = Table(rows, colWidths=[3.3 * inch, 2 * inch])

    style = [

        ("BACKGROUND", (0,0), (-1,0), HEADER_COLOR),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        ("GRID", (0,0), (-1,-1), 0.5, GRID_COLOR),

        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),

        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]

    for i in range(1, len(rows)):

        bg = ROW_LIGHT if i % 2 else ROW_ALT

        style.append(
            ("BACKGROUND", (0,i), (-1,i), bg)
        )

    table.setStyle(TableStyle(style))

    return table


# =====================================================
# LO SHU GRID TABLE (UPGRADED)
# =====================================================

def render_loshu_grid(grid_data: dict):

    grid_counts = grid_data.get("grid_counts", {})

    grid_layout = [
        ["4","9","2"],
        ["3","5","7"],
        ["8","1","6"]
    ]

    display_grid = []
    style_commands = []

    for r, row in enumerate(grid_layout):

        display_row = []

        for c, number in enumerate(row):

            count = grid_counts.get(number, 0)

            if count == 0:

                value = f"{number}\nMissing"

                style_commands.append(
                    ("BACKGROUND", (c,r), (c,r), MISSING_COLOR)
                )

            else:

                value = f"{number}\n×{count}"

                style_commands.append(
                    ("BACKGROUND", (c,r), (c,r), ROW_LIGHT)
                )

            display_row.append(value)

        display_grid.append(display_row)

    table = Table(
        display_grid,
        colWidths=1.7 * inch,
        rowHeights=1.7 * inch
    )

    style = [

        ("GRID", (0,0), (-1,-1), 1, GRID_COLOR),

        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),

        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),

    ]

    style.extend(style_commands)

    table.setStyle(TableStyle(style))

    return table


# =====================================================
# LUCKY NUMBERS TABLE
# =====================================================

def render_lucky_numbers_table(data: dict):

    rows = [["Category","Numbers"]]

    for k, v in data.items():

        rows.append([
            k.replace("_"," ").title(),
            _safe(v)
        ])

    table = Table(rows, colWidths=[2.5 * inch, 2.5 * inch])

    style = [

        ("BACKGROUND", (0,0), (-1,0), SECONDARY_COLOR),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),

        ("GRID", (0,0), (-1,-1), 0.5, GRID_COLOR),

        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),

        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]

    for i in range(1, len(rows)):

        bg = ROW_LIGHT if i % 2 else ROW_ALT

        style.append(("BACKGROUND",(0,i),(-1,i),bg))

    table.setStyle(TableStyle(style))

    return table


# =====================================================
# MOBILE NUMBER SUGGESTIONS
# =====================================================

def render_mobile_suggestions_table(data: dict):

    rows = [["Category","Recommendation"]]

    for k,v in data.items():

        rows.append([
            k.replace("_"," ").title(),
            _safe(v)
        ])

    table = Table(rows, colWidths=[2.5 * inch, 3 * inch])

    style = [

        ("BACKGROUND", (0,0), (-1,0), HEADER_COLOR),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),

        ("GRID", (0,0), (-1,-1), 0.5, GRID_COLOR),

        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),

        ("ALIGN", (1,1), (-1,-1), "LEFT"),
    ]

    for i in range(1, len(rows)):

        bg = ROW_LIGHT if i % 2 else ROW_ALT

        style.append(("BACKGROUND",(0,i),(-1,i),bg))

    table.setStyle(TableStyle(style))

    return table


# =====================================================
# REMEDY SUMMARY TABLE
# =====================================================

def render_remedy_table(data: dict):

    rows = [["Remedy Type","Details"]]

    for k,v in data.items():

        rows.append([
            k.replace("_"," ").title(),
            _safe(v)
        ])

    table = Table(rows, colWidths=[2.5 * inch, 3 * inch])

    style = [

        ("BACKGROUND", (0,0), (-1,0), SECONDARY_COLOR),

        ("GRID", (0,0), (-1,-1), 0.5, GRID_COLOR),

        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),

        ("ALIGN", (1,1), (-1,-1), "LEFT"),
    ]

    for i in range(1, len(rows)):

        bg = ROW_LIGHT if i % 2 else ROW_ALT

        style.append(("BACKGROUND",(0,i),(-1,i),bg))

    table.setStyle(TableStyle(style))

    return table