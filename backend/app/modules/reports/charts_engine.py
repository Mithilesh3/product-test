from io import BytesIO
from reportlab.platypus import Image

import matplotlib.pyplot as plt
import numpy as np


# =====================================================
# THEME COLORS
# =====================================================

PRIMARY_COLOR = "#1f3c88"
SECONDARY_COLOR = "#f5b041"
ACCENT_COLOR = "#2ecc71"

LOW_COLOR = "#e74c3c"
MID_COLOR = "#f39c12"
HIGH_COLOR = "#27ae60"


# =====================================================
# SAFE DATA NORMALIZER
# =====================================================

def _safe_chart_data(data: dict):

    if not data or not isinstance(data, dict):
        return ["N/A"], [0]

    labels = []
    values = []

    for k, v in data.items():

        try:
            value = float(v)
        except:
            value = 0

        labels.append(str(k))
        values.append(value)

    return labels, values


# =====================================================
# SAVE MATPLOTLIB FIGURE
# =====================================================

def _fig_to_image(fig, width=6, height=4):

    buffer = BytesIO()

    plt.tight_layout()
    plt.savefig(buffer, format="png", dpi=300)
    plt.close(fig)

    buffer.seek(0)

    return Image(buffer, width=width * 72, height=height * 72)


# =====================================================
# BAR CHART
# =====================================================

def generate_bar_chart(data: dict):

    labels, values = _safe_chart_data(data)

    fig, ax = plt.subplots(figsize=(7, 4))

    colors = []

    for v in values:

        if v < 40:
            colors.append(LOW_COLOR)
        elif v < 70:
            colors.append(MID_COLOR)
        else:
            colors.append(HIGH_COLOR)

    ax.bar(labels, values, color=colors)

    ax.set_title("Performance Metrics", fontsize=14)
    ax.set_ylabel("Score")

    ax.set_ylim(0, 100)

    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.xticks(rotation=25)

    return _fig_to_image(fig, 6, 3.5)


# =====================================================
# PIE CHART
# =====================================================

def generate_pie_chart(data: dict):

    labels, values = _safe_chart_data(data)

    fig, ax = plt.subplots(figsize=(6, 6))

    colors = [
        PRIMARY_COLOR,
        SECONDARY_COLOR,
        ACCENT_COLOR,
        "#8e44ad",
        "#e74c3c",
        "#3498db",
    ]

    ax.pie(
        values,
        labels=labels,
        autopct="%1.0f%%",
        startangle=90,
        colors=colors[:len(values)],
        wedgeprops={"edgecolor": "white"}
    )

    ax.set_title("Life Balance Distribution", fontsize=14)

    return _fig_to_image(fig, 5, 5)


# =====================================================
# RADAR CHART (UPGRADED)
# =====================================================

def generate_radar_chart(data: dict):

    labels, values = _safe_chart_data(data)

    if len(values) < 3:
        return generate_bar_chart(data)

    num_vars = len(labels)

    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()

    values_cycle = values + values[:1]
    angles_cycle = angles + angles[:1]

    fig, ax = plt.subplots(
        figsize=(7, 7),
        subplot_kw=dict(polar=True)
    )

    # Radar background grid
    ax.set_ylim(0, 100)

    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"])

    ax.grid(color="grey", linestyle="--", linewidth=0.5, alpha=0.6)

    # Plot line
    ax.plot(
        angles_cycle,
        values_cycle,
        color=PRIMARY_COLOR,
        linewidth=2.5
    )

    # Fill radar
    ax.fill(
        angles_cycle,
        values_cycle,
        color=SECONDARY_COLOR,
        alpha=0.25
    )

    # Labels
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=10)

    ax.set_title(
        "Life Intelligence Radar",
        fontsize=15,
        pad=20
    )

    return _fig_to_image(fig, 6, 6)