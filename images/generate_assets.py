"""Generate hero virus illustration for the landing screen."""

from pathlib import Path

from PIL import Image, ImageDraw


def create_virus_hero(output_path: Path, size: int = 480) -> Path:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    core_r = int(size * 0.18)

    for i in range(36):
        angle = i * 10
        import math

        rad = math.radians(angle)
        sx = cx + math.cos(rad) * (core_r + 28)
        sy = cy + math.sin(rad) * (core_r + 28)
        ex = cx + math.cos(rad) * (core_r + 72)
        ey = cy + math.sin(rad) * (core_r + 72)
        draw.line([(sx, sy), (ex, ey)], fill=(248, 113, 113, 200), width=5)
        draw.ellipse(
            (ex - 14, ey - 14, ex + 14, ey + 14),
            fill=(252, 165, 165, 230),
            outline=(254, 202, 202, 255),
        )

    draw.ellipse(
        (cx - core_r, cy - core_r, cx + core_r, cy + core_r),
        fill=(239, 68, 68, 240),
        outline=(254, 226, 226, 255),
        width=3,
    )
    highlight_r = int(core_r * 0.35)
    draw.ellipse(
        (
            cx - core_r + 18,
            cy - core_r + 14,
            cx - core_r + 18 + highlight_r,
            cy - core_r + 14 + highlight_r,
        ),
        fill=(254, 202, 202, 90),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    path = Path(__file__).resolve().parent / "virus_hero.png"
    create_virus_hero(path)
    print(f"Created {path}")
