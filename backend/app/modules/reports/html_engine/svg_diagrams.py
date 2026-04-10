from __future__ import annotations

from html import escape
from math import cos, pi, sin
from typing import Any, Dict, List, Sequence

PLANET_BY_NUMBER: Dict[int, str] = {
    1: "Surya",
    2: "Chandra",
    3: "Guru",
    4: "Rahu",
    5: "Budh",
    6: "Shukra",
    7: "Ketu",
    8: "Shani",
    9: "Mangal",
    11: "Moon-Jupiter",
    22: "Rahu-Saturn",
}


LO_SHU_LAYOUT: List[List[int]] = [
    [4, 9, 2],
    [3, 5, 7],
    [8, 1, 6],
]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_text(value: Any, default: str = "") -> str:
    text = " ".join(str(value or "").split())
    return text or default


def _truncate(text: str, limit: int = 72) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "..."


def _wrap_lines(value: str, max_chars: int = 28, max_lines: int = 4) -> List[str]:
    words = _safe_text(value).split(" ")
    if not words:
        return [""]

    lines: List[str] = []
    current: List[str] = []

    for word in words:
        next_line = " ".join(current + [word]).strip()
        if len(next_line) <= max_chars or not current:
            current.append(word)
            continue

        lines.append(" ".join(current).strip())
        current = [word]

        if len(lines) >= max_lines:
            break

    if len(lines) < max_lines and current:
        lines.append(" ".join(current).strip())

    if len(lines) > max_lines:
        lines = lines[:max_lines]

    if lines and len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
        lines[-1] = _truncate(lines[-1], max_chars)

    return lines or [""]


def _format_number(value: Any) -> str:
    return str(_safe_int(value, 0)) if value not in (None, "") else "-"


def build_numerology_architecture_svg(
    foundation: Any,
    left_pillar: Any,
    right_pillar: Any,
    facade: Any,
) -> str:
    f_val = escape(_format_number(foundation))
    l_val = escape(_format_number(left_pillar))
    r_val = escape(_format_number(right_pillar))
    c_val = escape(_format_number(facade))

    return f"""
<svg viewBox="0 0 960 360" role="img" aria-label="Numerology architecture model" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="archBg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0%" stop-color="#f7fbff"/>
      <stop offset="100%" stop-color="#e8f1ff"/>
    </linearGradient>
    <linearGradient id="archNode" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color="#f4e7c8"/>
      <stop offset="100%" stop-color="#d4b070"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="960" height="360" rx="22" fill="url(#archBg)"/>

  <g fill="none" stroke="#b08b49" stroke-width="2.6" stroke-linecap="round">
    <path d="M130 260 H830"/>
    <path d="M240 140 L130 260"/>
    <path d="M720 140 L830 260"/>
    <path d="M480 92 V260"/>
  </g>

  <g font-family="Inter, Noto Sans Devanagari, sans-serif" text-anchor="middle">
    <rect x="70" y="230" width="120" height="68" rx="12" fill="url(#archNode)"/>
    <text x="130" y="255" font-size="11" font-weight="700" fill="#17355b">Foundation</text>
    <text x="130" y="279" font-size="24" font-weight="800" fill="#102544">{f_val}</text>

    <rect x="180" y="106" width="120" height="68" rx="12" fill="url(#archNode)"/>
    <text x="240" y="131" font-size="11" font-weight="700" fill="#17355b">Left Pillar</text>
    <text x="240" y="155" font-size="24" font-weight="800" fill="#102544">{l_val}</text>

    <rect x="420" y="58" width="120" height="68" rx="12" fill="url(#archNode)"/>
    <text x="480" y="83" font-size="11" font-weight="700" fill="#17355b">Facade</text>
    <text x="480" y="107" font-size="24" font-weight="800" fill="#102544">{c_val}</text>

    <rect x="660" y="106" width="120" height="68" rx="12" fill="url(#archNode)"/>
    <text x="720" y="131" font-size="11" font-weight="700" fill="#17355b">Right Pillar</text>
    <text x="720" y="155" font-size="24" font-weight="800" fill="#102544">{r_val}</text>
  </g>

  <text x="480" y="328" text-anchor="middle" font-family="Inter, Noto Sans Devanagari, sans-serif" font-size="13" fill="#35557f">
    निर्धारित संरचना: Life Path -> Destiny / Expression -> Name Number
  </text>
</svg>
""".strip()


def build_loshu_grid_svg(grid_counts: Dict[str, Any], missing_numbers: Sequence[Any]) -> str:
    normalized = {
        number: _safe_int(grid_counts.get(str(number), grid_counts.get(number, 0)), 0)
        for number in range(1, 10)
    }
    missing = {_safe_int(value, 0) for value in (missing_numbers or [])}

    cell_size = 150
    base_x = 40
    base_y = 40

    cells: List[str] = []

    for row_index, row in enumerate(LO_SHU_LAYOUT):
        for col_index, number in enumerate(row):
            x = base_x + (col_index * cell_size)
            y = base_y + (row_index * cell_size)
            count = normalized[number]
            is_missing = number in missing

            fill = "#fff1f4" if is_missing else "#edf4ff"
            stroke = "#d3899d" if is_missing else "#b08a46"
            count_color = "#7d4e5f" if is_missing else "#2f4f78"

            cells.append(
                f"""
<g>
  <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="2.4"/>
  <text x="{x + (cell_size / 2)}" y="{y + 52}" text-anchor="middle" font-family="Cinzel, serif" font-size="34" font-weight="700" fill="#8f6c31">{number}</text>
  <text x="{x + (cell_size / 2)}" y="{y + 96}" text-anchor="middle" font-family="Inter, Noto Sans Devanagari, sans-serif" font-size="14" fill="{count_color}">Count: {count}</text>
  <text x="{x + (cell_size / 2)}" y="{y + 124}" text-anchor="middle" font-family="Inter, Noto Sans Devanagari, sans-serif" font-size="11" fill="{count_color}">{'अनुपस्थित | Missing' if is_missing else 'उपस्थित | Present'}</text>
</g>
""".strip()
            )

    return f"""
<svg viewBox="0 0 550 550" role="img" aria-label="Lo Shu grid visualization" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="550" height="550" rx="20" fill="#f7fbff"/>
  {' '.join(cells)}
  <text x="275" y="525" text-anchor="middle" font-family="Inter, Noto Sans Devanagari, sans-serif" font-size="12" fill="#35557f">
    Lo Shu matrix (4-9-2 / 3-5-7 / 8-1-6) | निर्धारित ऊर्जा ग्रिड
  </text>
</svg>
""".strip()


def _build_flow_block(x: int, y: int, width: int, title: str, value: str) -> str:
    title_text = escape(_safe_text(title, "Block"))
    content_lines = _wrap_lines(value, max_chars=30, max_lines=5)

    line_markup = []
    for index, line in enumerate(content_lines):
        offset_y = y + 66 + (index * 18)
        line_markup.append(
            f"<text x=\"{x + (width / 2)}\" y=\"{offset_y}\" text-anchor=\"middle\" font-family=\"Inter, Noto Sans Devanagari, sans-serif\" font-size=\"13\" fill=\"#24446e\">{escape(line)}</text>"
        )

    return f"""
<g>
  <rect x="{x}" y="{y}" width="{width}" height="150" rx="14" fill="#edf4ff" stroke="#b08a46" stroke-width="2"/>
  <text x="{x + (width / 2)}" y="{y + 34}" text-anchor="middle" font-family="Cinzel, serif" font-size="16" fill="#8f6c31">{title_text}</text>
  {' '.join(line_markup)}
</g>
""".strip()


def build_structural_deficit_svg(deficit_model: Dict[str, Any]) -> str:
    deficit = _safe_text(
        deficit_model.get("deficit") or deficit_model.get("structural_deficit"),
        "Missing center 5",
    )
    symptom = _safe_text(
        deficit_model.get("symptom") or deficit_model.get("behavioral_symptom"),
        "Decision instability under pressure.",
    )
    patch = _safe_text(
        deficit_model.get("patch") or deficit_model.get("engineered_patch"),
        "Install a written decision protocol and daily rhythm lock.",
    )

    left = _build_flow_block(30, 70, 270, "Structural Deficit", _truncate(deficit, 150))
    middle = _build_flow_block(345, 70, 270, "Behavioral Symptom", _truncate(symptom, 150))
    right = _build_flow_block(660, 70, 270, "Engineered Patch", _truncate(patch, 150))

    return f"""
<svg viewBox="0 0 960 300" role="img" aria-label="Structural deficit flow diagram" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="960" height="300" rx="20" fill="#f7fbff"/>
  {left}
  {middle}
  {right}

  <g stroke="#b08a46" stroke-width="2.4" fill="none" stroke-linecap="round">
    <path d="M304 145 H338"/>
    <path d="M334 138 L344 145 L334 152"/>
    <path d="M619 145 H653"/>
    <path d="M649 138 L659 145 L649 152"/>
  </g>
</svg>
""".strip()


def build_planetary_orbit_svg(planetary_mapping: Dict[str, Any], numerology_core: Dict[str, Any]) -> str:
    pyth = numerology_core.get("pythagorean") or {}
    chaldean = numerology_core.get("chaldean") or {}

    life_path = _safe_int(pyth.get("life_path_number"), 5)
    destiny = _safe_int(pyth.get("destiny_number"), 1)
    expression = _safe_int(pyth.get("expression_number"), 3)
    name_number = _safe_int(chaldean.get("name_number"), 6)

    dominant_planet = _safe_text(
        planetary_mapping.get("primary_intervention_planet"),
        PLANET_BY_NUMBER.get(life_path, "Budh"),
    )

    orbit_nodes = [
        (f"Life Path {life_path}: {PLANET_BY_NUMBER.get(life_path, 'Budh')}", 0.0, 120),
        (f"Destiny {destiny}: {PLANET_BY_NUMBER.get(destiny, 'Surya')}", pi * 0.72, 150),
        (f"Expression {expression}: {PLANET_BY_NUMBER.get(expression, 'Guru')}", pi * 1.36, 120),
        (f"Name {name_number}: {PLANET_BY_NUMBER.get(name_number, 'Shukra')}", pi * 1.92, 150),
    ]

    circles: List[str] = []
    labels: List[str] = []

    center_x = 360
    center_y = 200

    for label, angle, radius in orbit_nodes:
        x = center_x + (cos(angle) * radius)
        y = center_y + (sin(angle) * radius)
        circles.append(
            f"<circle cx=\"{x:.1f}\" cy=\"{y:.1f}\" r=\"22\" fill=\"#edf4ff\" stroke=\"#b08a46\" stroke-width=\"2\"/>"
        )
        labels.append(
            f"<text x=\"{x:.1f}\" y=\"{y + 40:.1f}\" text-anchor=\"middle\" font-family=\"Inter, Noto Sans Devanagari, sans-serif\" font-size=\"11\" fill=\"#27466f\">{escape(_truncate(label, 32))}</text>"
        )

    return f"""
<svg viewBox="0 0 720 420" role="img" aria-label="Planetary orbit map" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="720" height="420" rx="20" fill="#f7fbff"/>

  <g fill="none" stroke="#8fb0d7" stroke-width="1.5">
    <circle cx="360" cy="200" r="82"/>
    <circle cx="360" cy="200" r="120"/>
    <circle cx="360" cy="200" r="150"/>
  </g>

  <circle cx="360" cy="200" r="42" fill="#e9d5ab"/>
  <text x="360" y="194" text-anchor="middle" font-family="Cinzel, serif" font-size="14" fill="#10223f">Core</text>
  <text x="360" y="214" text-anchor="middle" font-family="Inter, Noto Sans Devanagari, sans-serif" font-size="11" fill="#10223f">{escape(_truncate(dominant_planet, 16))}</text>

  {' '.join(circles)}
  {' '.join(labels)}

  <text x="360" y="392" text-anchor="middle" font-family="Inter, Noto Sans Devanagari, sans-serif" font-size="12" fill="#35557f">
    Planetary calibration cluster | निर्धारित numerology anchors
  </text>
</svg>
""".strip()

