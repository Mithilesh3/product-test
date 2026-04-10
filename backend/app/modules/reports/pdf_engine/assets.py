from pathlib import Path

# Prefer Docker path in container, fallback to local repository path for non-Docker runs.
_MODULE_PATH = Path(__file__).resolve()
_LOCAL_ASSETS = _MODULE_PATH.parents[3] / "assets"
_DOCKER_ASSETS = Path("/app/app/assets")
BASE_ASSETS = _DOCKER_ASSETS if _DOCKER_ASSETS.exists() else _LOCAL_ASSETS

ICONS = BASE_ASSETS / "icons"
SACRED = BASE_ASSETS / "sacred"
DEITIES = BASE_ASSETS / "deities"
LOTUS = BASE_ASSETS / "lotus"
CHARTS = BASE_ASSETS / "charts"
BRANDING = BASE_ASSETS / "branding"
FONTS = BASE_ASSETS / "fonts"
BACKGROUND = BASE_ASSETS / "background"
COVER = BASE_ASSETS / "cover"


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


LOGO = _first_existing(
    BRANDING / "numai_logo.png",
    BRANDING / "logo.png",
)

MANDALA = _first_existing(
    SACRED / "mandala_bg.png",
    BACKGROUND / "mandala_bg.png",
)

OM_SYMBOL = _first_existing(
    COVER / "om_symbol.png",
    SACRED / "om_gold.png",
)

LOTUS_ICON = _first_existing(
    LOTUS / "lotus_gold.png",
    BACKGROUND / "lotus.png",
)

GANESHA = COVER / "ganesha.png"
KRISHNA = COVER / "krishna.png"

CHAKRA_ICON = ICONS / "chakra.png"

RADAR_CHART = CHARTS / "radar_chart.png"
LOSHE_GRID_CHART = CHARTS / "loshu_grid.png"
METRICS_BAR_CHART = CHARTS / "metrics_bar.png"


def asset_exists(path: Path) -> bool:
    return path.exists()
