from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1] / "public" / "report-assets"


DIRECTORY_SPECS = {
    "branding": {"max_edge": 1200, "quality": 86},
    "cover": {"max_edge": 1400, "quality": 84},
    "deities": {"max_edge": 900, "quality": 80},
    "icons": {"max_edge": 700, "quality": 82},
    "lotus": {"max_edge": 800, "quality": 82},
    "sacred": {"max_edge": 1400, "quality": 76},
}


def optimize_image(source: Path, max_edge: int, quality: int) -> Path:
    destination = source.with_suffix(".webp")

    with Image.open(source) as image:
        mode = "RGBA" if image.mode in ("RGBA", "LA") or "transparency" in image.info else "RGB"
        processed = image.convert(mode)
        processed.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        processed.save(destination, "WEBP", quality=quality, method=6)

    return destination


def main() -> None:
    optimized = []

    for directory, spec in DIRECTORY_SPECS.items():
        folder = ROOT / directory
        if not folder.exists():
            continue

        for source in folder.glob("*.png"):
            destination = optimize_image(
                source=source,
                max_edge=spec["max_edge"],
                quality=spec["quality"],
            )
            optimized.append((source, destination))

    total_before = sum(source.stat().st_size for source, _ in optimized)
    total_after = sum(destination.stat().st_size for _, destination in optimized)

    print(f"Optimized {len(optimized)} assets")
    print(f"Before: {total_before / (1024 * 1024):.2f} MB")
    print(f"After: {total_after / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    main()
