from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .assets import FONTS

FONT_DEVANAGARI_REGULAR_PATH = FONTS / "NotoSansDevanagari-Regular.ttf"
FONT_DEVANAGARI_BOLD_PATH = FONTS / "NotoSansDevanagari-Bold.ttf"
FONT_DEVANAGARI_VARIABLE_PATH = FONTS / "NotoSansDevanagari-Variable.ttf"
FONT_REGULAR_PATH = FONTS / "NotoSans-Regular.ttf"
FONT_BOLD_PATH = FONTS / "NotoSans-Bold.ttf"


def _usable_font(path):
    try:
        return path.exists() and path.stat().st_size > 10_000
    except Exception:
        return False


# Returns a tuple: (regular_font_name, bold_font_name)
def register_fonts():
    regular = "Helvetica"
    bold = "Helvetica-Bold"
    has_unicode_regular = False

    try:
        if _usable_font(FONT_DEVANAGARI_REGULAR_PATH):
            pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(FONT_DEVANAGARI_REGULAR_PATH)))
            regular = "NotoSansDevanagari"
            has_unicode_regular = True
        elif _usable_font(FONT_DEVANAGARI_VARIABLE_PATH):
            pdfmetrics.registerFont(TTFont("NotoSansDevanagari", str(FONT_DEVANAGARI_VARIABLE_PATH)))
            regular = "NotoSansDevanagari"
            has_unicode_regular = True
    except Exception:
        pass

    try:
        if not has_unicode_regular and _usable_font(FONT_REGULAR_PATH):
            pdfmetrics.registerFont(TTFont("NotoSans", str(FONT_REGULAR_PATH)))
            regular = "NotoSans"
            has_unicode_regular = True
    except Exception:
        pass

    try:
        if _usable_font(FONT_DEVANAGARI_BOLD_PATH):
            pdfmetrics.registerFont(TTFont("NotoSansDevanagari-Bold", str(FONT_DEVANAGARI_BOLD_PATH)))
            bold = "NotoSansDevanagari-Bold"
        elif _usable_font(FONT_DEVANAGARI_VARIABLE_PATH):
            # Variable font fallback: use same Devanagari family for bold fragments.
            bold = "NotoSansDevanagari"
        elif _usable_font(FONT_BOLD_PATH):
            pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(FONT_BOLD_PATH)))
            bold = "NotoSans-Bold"
        elif has_unicode_regular:
            # Keep Hindi readable even when a dedicated bold TTF is absent.
            bold = regular
    except Exception:
        if has_unicode_regular:
            bold = regular

    try:
        # Ensure Paragraph inline tags like <b> stay in a Unicode-capable font family.
        pdfmetrics.registerFontFamily(
            regular,
            normal=regular,
            bold=bold,
            italic=regular,
            boldItalic=bold,
        )
    except Exception:
        pass

    return regular, bold
