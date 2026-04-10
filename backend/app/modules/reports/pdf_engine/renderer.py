import re

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Table, TableStyle


class Renderer:
    def __init__(self, styles):
        self.styles = styles

        self.body_style = styles["BodyText"]
        self.section_style = styles.get("SectionBanner", styles["Heading2"])

        self.primary = HexColor("#1e3a5f")
        self.accent = HexColor("#0f766e")
        self.neutral = HexColor("#f8fafc")

        # Matches page frame width with current margins.
        self.full_width = 470
        self.two_col_width = 233
        self.two_col_inner_width = 225

        self.metric_label_style = ParagraphStyle(
            "MetricLabel",
            parent=self.body_style,
            alignment=1,
            fontSize=9.5,
            leading=12,
            textColor=HexColor("#475569"),
        )
        self.metric_value_style = ParagraphStyle(
            "MetricValue",
            parent=styles["Heading1"],
            alignment=1,
            fontSize=24,
            leading=28,
            textColor=self.primary,
        )
        self.center_body_style = ParagraphStyle(
            "CenterBody",
            parent=self.body_style,
            alignment=1,
        )
        self.large_body_style = ParagraphStyle(
            "LargeBody",
            parent=self.body_style,
            fontSize=11.5,
            leading=17,
            textColor=HexColor("#1f2937"),
            alignment=0,
        )

    def normalize_text(self, text):
        if text is None:
            return ""
        normalized = " ".join(str(text).split())
        return re.sub(r"([a-z])([A-Z])", r"\1 \2", normalized)

    def _to_rich_text(self, text):
        raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        escaped = (
            raw.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        escaped = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", escaped)
        escaped = escaped.replace("**", "")

        lines = []
        for line in escaped.split("\n"):
            trimmed = line.strip()
            if not trimmed:
                lines.append("")
                continue
            if trimmed.startswith("- "):
                lines.append(f"- {trimmed[2:]}")
            else:
                lines.append(trimmed)

        return "<br/>".join(lines)

    def section_banner(self, title):
        banner = Table(
            [[Paragraph(self.normalize_text(title).upper(), self.section_style)]],
            colWidths=[self.full_width],
        )

        banner.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), self.primary),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        banner.spaceAfter = 12
        return banner

    def paragraph(self, text):
        return Paragraph(self.normalize_text(text), self.body_style)

    def metric_card(self, label, value):
        score = 0
        try:
            score = int(value)
        except Exception:
            score = 0

        if score >= 75:
            color = HexColor("#dcfce7")
        elif score >= 50:
            color = HexColor("#fef9c3")
        else:
            color = HexColor("#fee2e2")

        table = Table(
            [
                [Paragraph(f"<b>{self.normalize_text(label).upper()}</b>", self.metric_label_style)],
                [Paragraph(str(value), self.metric_value_style)],
            ],
            colWidths=[150],
        )

        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color),
                    ("BOX", (0, 0), (-1, -1), 1, HexColor("#cbd5e1")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 12),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )

        return table

    def metric_grid(self, metric_pairs):
        cards = [self.metric_card(label, value) for label, value in metric_pairs[:6]]
        while len(cards) < 6:
            cards.append(self.metric_card("Metric", "-"))

        rows = [cards[:3], cards[3:6]]

        grid = Table(rows, colWidths=[156, 156, 156])
        grid.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        return grid

    def insight_box(self, title, text, tone="neutral", width=None):
        palette = {
            "neutral": (HexColor("#ffffff"), HexColor("#cbd5e1")),
            "info": (HexColor("#f0f9ff"), HexColor("#93c5fd")),
            "success": (HexColor("#f0fdf4"), HexColor("#86efac")),
            "risk": (HexColor("#fff1f2"), HexColor("#fda4af")),
        }
        bg, border = palette.get(tone, palette["neutral"])
        box_width = width or self.full_width

        box = Table(
            [
                [Paragraph(f"<b>{self.normalize_text(title)}</b>", self.styles["Heading4"])],
                [
                    Paragraph(
                        self._to_rich_text(text) or "Guidance is generated from available deterministic signals.",
                        self.large_body_style,
                    )
                ],
            ],
            colWidths=[box_width],
        )
        box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), bg),
                    ("BOX", (0, 0), (-1, -1), 1, border),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                ]
            )
        )
        return box

    def content_panel(self, text):
        panel = Table(
            [
                [
                    Paragraph(
                        self._to_rich_text(text)
                        or "Guidance is generated from available deterministic signals.",
                        self.large_body_style,
                    )
                ]
            ],
            colWidths=[self.full_width],
        )
        panel.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 1, HexColor("#cbd5e1")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ]
            )
        )
        return panel

    def bullet_block(self, title, items):
        clean_items = [self.normalize_text(i) for i in (items or []) if str(i).strip()]
        if not clean_items:
            clean_items = ["Guidance will appear from deterministic signals."]

        bullet_text = "<br/>".join([f"- {i}" for i in clean_items])
        return self.insight_box(title, bullet_text, tone="neutral")

    def icon_block(self, icon_path, title, text):
        if icon_path and getattr(icon_path, "exists", lambda: False)():
            img = Image(str(icon_path), width=26 * mm, height=26 * mm)
            img.hAlign = "CENTER"
            left = img
        else:
            left = Paragraph("", self.body_style)

        right = self.insight_box(title, text, tone="info", width=self.full_width - 80)

        block = Table([[left, right]], colWidths=[70, 400])
        block.setStyle(
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
        return block

    def two_column_cards(self, left_title, left_text, right_title, right_text):
        left = self.insight_box(left_title, left_text, tone="success", width=self.two_col_inner_width)
        right = self.insight_box(right_title, right_text, tone="risk", width=self.two_col_inner_width)

        table = Table([[left, right]], colWidths=[self.two_col_width, self.two_col_width])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        return table

