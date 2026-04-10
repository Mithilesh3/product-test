# modules/numerology/loshu.py

from typing import Dict


def generate_loshu_grid(dob: str) -> Dict:
    if not dob:
        return {}

    digits = [int(d) for d in dob if d.isdigit()]
    grid = {str(i): digits.count(i) for i in range(1, 10)}

    missing = [k for k, v in grid.items() if v == 0]
    present = [k for k, v in grid.items() if v > 0]
    repeating = [k for k, v in grid.items() if v > 1]
    grid_rows = [
        [grid.get("4", 0), grid.get("9", 0), grid.get("2", 0)],
        [grid.get("3", 0), grid.get("5", 0), grid.get("7", 0)],
        [grid.get("8", 0), grid.get("1", 0), grid.get("6", 0)],
    ]

    return {
        "grid_counts": grid,
        "missing_numbers": missing,
        "present_numbers": present,
        "repeating_numbers": repeating,
        "grid_rows": grid_rows,
    }
