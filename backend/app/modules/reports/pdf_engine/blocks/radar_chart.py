from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle


LABELS = [
    ("जीवन स्थिरता | Life Stability", "Life Stability"),
    ("निर्णय स्पष्टता | Decision Clarity", "Decision Clarity"),
    ("धर्म संतुलन | Dharma Alignment", "Dharma Alignment"),
    ("भावनात्मक संतुलन | Emotional Regulation", "Emotional Regulation"),
    ("वित्तीय अनुशासन | Financial Discipline", "Financial Discipline"),
    ("कर्म दबाव | Karma Pressure", "Karma Pressure"),
]


def _score(metrics, key, default=0):
    value = metrics.get(key, default)
    try:
        return max(0, min(100, int(value)))
    except Exception:
        return default


def radar_chart(metrics, styles, total_width):
    values = [_score(metrics, metric_key) for _label, metric_key in LABELS]

    chart_width = total_width * 0.62
    legend_width = total_width - chart_width
    drawing = Drawing(chart_width, 180)

    chart = LinePlot()
    chart.x = 38
    chart.y = 26
    chart.height = 118
    chart.width = max(220, chart_width - 56)
    chart.data = [[(index + 1, value) for index, value in enumerate(values)]]
    chart.lines[0].strokeColor = HexColor("#1b2f4b")
    chart.lines[0].strokeWidth = 2
    chart.lines[0].symbol = makeMarker("Circle")
    chart.lines[0].symbol.size = 5

    chart.yValueAxis.valueMin = 0
    chart.yValueAxis.valueMax = 100
    chart.yValueAxis.valueStep = 20
    chart.xValueAxis.valueMin = 1
    chart.xValueAxis.valueMax = len(LABELS)
    chart.xValueAxis.valueStep = 1
    chart.yValueAxis.labels.fontName = styles["SmallText"].fontName
    chart.yValueAxis.labels.fontSize = 7
    chart.xValueAxis.labels.fontName = styles["SmallText"].fontName
    chart.xValueAxis.labels.fontSize = 7

    drawing.add(chart)

    legend_title_style = ParagraphStyle(
        "RadarLegendTitle",
        parent=styles["Heading4"],
        textColor=HexColor("#1b2f4b"),
        leading=14,
    )
    legend_label_style = ParagraphStyle(
        "RadarLegendLabel",
        parent=styles["SmallText"],
        textColor=HexColor("#4a5568"),
        leading=11,
    )
    legend_value_style = ParagraphStyle(
        "RadarLegendValue",
        parent=styles["SmallText"],
        alignment=1,
        textColor=HexColor("#1b2f4b"),
        leading=11,
    )

    legend_rows = [[Paragraph("मेट्रिक स्कोर | Metric Scores", legend_title_style), Paragraph("", legend_title_style)]]
    for (label, _metric_key), value in zip(LABELS, values):
        legend_rows.append(
            [
                Paragraph(label, legend_label_style),
                Paragraph(f"<b>{value}</b>", legend_value_style),
            ]
        )

    legend = Table(
        legend_rows,
        colWidths=[legend_width * 0.77, legend_width * 0.23],
    )
    legend.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("SPAN", (0, 0), (-1, 0)),
            ]
        )
    )

    wrapper = Table([[drawing, legend]], colWidths=[chart_width, legend_width])
    wrapper.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return wrapper
