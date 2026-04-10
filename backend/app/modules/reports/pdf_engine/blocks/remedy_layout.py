from reportlab.platypus import Table, Image, Paragraph
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor


def remedy_layout(styles, deity_image, remedy):

    # ------------------------------------------------
    # Deity Image
    # ------------------------------------------------
    img = Image(
        str(deity_image),
        width=75 * mm,
        height=95 * mm
    )

    # ------------------------------------------------
    # Remedy Text
    # ------------------------------------------------
    deity = remedy.get("deity", "")
    mantra = remedy.get("mantra_pronunciation", "")
    mantra_sanskrit = remedy.get("mantra_sanskrit", "")
    practice = remedy.get("practice_guideline", "")
    donation = remedy.get("recommended_donation", "")

    text = f"""
    <b>Target Deity</b><br/>
    {deity}<br/><br/>

    <b>Mantra</b><br/>
    {mantra}<br/><br/>
    """

    # include Sanskrit if available
    if mantra_sanskrit:
        text += f"<font size=11>{mantra_sanskrit}</font><br/><br/>"

    text += f"""
    <b>Practice Guideline</b><br/>
    {practice}<br/><br/>

    <b>Recommended Action</b><br/>
    {donation}
    """

    paragraph = Paragraph(text, styles["BodyText"])

    # ------------------------------------------------
    # Layout Table
    # ------------------------------------------------
    table = Table(
        [[img, paragraph]],
        colWidths=[85 * mm, 95 * mm]
    )

    # ------------------------------------------------
    # Styling
    # ------------------------------------------------
    table.setStyle([

        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),

        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),

        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#faf8f2")),
        ("BOX", (0, 0), (-1, -1), 1, HexColor("#d6cda7"))

    ])

    return table