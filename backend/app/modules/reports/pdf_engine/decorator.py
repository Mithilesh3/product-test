import logging

from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

from .assets import LOGO
from .layout import PAGE_HEIGHT, PAGE_WIDTH

logger = logging.getLogger(__name__)


class PageDecorator:
    def __init__(self, force_watermark: bool = False):
        self.logo = self._reader(LOGO)
        self.force_watermark = force_watermark

        self.primary = colors.HexColor("#183a63")
        self.accent = colors.HexColor("#b99345")
        self.text_dark = colors.HexColor("#1f3552")
        self.text_muted = colors.HexColor("#66758b")

    def _reader(self, path):
        try:
            if path.exists():
                return ImageReader(str(path))
        except Exception as exc:
            logger.warning("Failed loading asset %s: %s", path, exc)
        return None

    def _set_alpha(self, canvas, alpha):
        try:
            canvas.setFillAlpha(alpha)
        except Exception:
            pass

    def draw_background(self, canvas, doc):
        _ = doc
        canvas.saveState()

        bands = 28
        band_h = PAGE_HEIGHT / bands
        for i in range(bands):
            t = i / max(1, bands - 1)
            r = int(250 - 8 * t)
            g = int(246 - 10 * t)
            b = int(238 - 12 * t)
            canvas.setFillColor(colors.Color(r / 255, g / 255, b / 255))
            canvas.rect(0, i * band_h, PAGE_WIDTH, band_h + 1, fill=1, stroke=0)

        self._set_alpha(canvas, 0.1)
        canvas.setStrokeColor(colors.HexColor("#d8c5a1"))
        canvas.setLineWidth(0.45)
        for i in range(4):
            inset = 12 * mm + i * 5 * mm
            canvas.rect(inset, inset, PAGE_WIDTH - inset * 2, PAGE_HEIGHT - inset * 2, fill=0, stroke=1)
        self._set_alpha(canvas, 1)

        if self.force_watermark:
            self._set_alpha(canvas, 0.12)
            canvas.setFillColor(colors.HexColor("#d8c29b"))
            canvas.setFont("Helvetica-Bold", 52)
            canvas.saveState()
            canvas.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
            canvas.rotate(32)
            canvas.drawCentredString(0, 0, "PREVIEW")
            canvas.restoreState()
            self._set_alpha(canvas, 1)

        canvas.setStrokeColor(colors.HexColor("#caa86a"))
        canvas.setLineWidth(0.9)
        canvas.line(16 * mm, PAGE_HEIGHT - 13 * mm, PAGE_WIDTH - 16 * mm, PAGE_HEIGHT - 13 * mm)
        canvas.line(16 * mm, 13 * mm, PAGE_WIDTH - 16 * mm, 13 * mm)

        canvas.restoreState()

    def draw_header(self, canvas):
        if canvas.getPageNumber() == 1:
            return

        canvas.saveState()

        if self.logo is not None:
            canvas.drawImage(
                self.logo,
                16 * mm,
                PAGE_HEIGHT - 22 * mm,
                width=85,
                height=20,
                mask="auto",
            )

        canvas.setFont("Helvetica-Bold", 10.5)
        canvas.setFillColor(self.text_dark)
        canvas.drawCentredString(
            PAGE_WIDTH / 2,
            PAGE_HEIGHT - 18 * mm,
            "Life Signify NumAI Strategic Report",
        )

        canvas.restoreState()

    def draw_footer(self, canvas):
        canvas.saveState()

        canvas.setFont("Helvetica", 9.5)
        canvas.setFillColor(self.text_muted)
        canvas.drawRightString(PAGE_WIDTH - 16 * mm, 8.5 * mm, f"Page {canvas.getPageNumber()}")

        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.setFillColor(self.accent)
        canvas.drawString(16 * mm, 8.5 * mm, "CONFIDENTIAL - STRATEGIC INTELLIGENCE")

        canvas.restoreState()

    def decorate(self, canvas, doc):
        self.draw_background(canvas, doc)
        self.draw_header(canvas)
        self.draw_footer(canvas)
