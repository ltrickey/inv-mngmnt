#!/usr/bin/env python3
"""
Generate placeholder images for products that don't have one yet.
Reads server/seed_data/products.json and creates 600x400 JPEGs in infrastructure/images/.

Easiest (works with Homebrew Python):  ./scripts/run_generate_product_images.sh
Pass --force to overwrite existing images (e.g. after copy_product_placeholders.sh).
Otherwise use a venv:  python3 -m venv .venv && source .venv/bin/activate && pip install Pillow && python scripts/generate_product_images.py
"""
from pathlib import Path
import json
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: Pillow is required. Run:  ./scripts/run_generate_product_images.sh  (uses a venv)", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SEED_DATA = PROJECT_ROOT / "seed_data" / "products.json"
IMAGES_DIR = PROJECT_ROOT / "infrastructure" / "images"

# Barcode range for the 79 new products (--force only overwrites these)
NEW_PRODUCTS_BARCODE_MIN = "0123456789030"
NEW_PRODUCTS_BARCODE_MAX = "0123456789108"

# Soft neutral background (matches placeholder style)
BG_RGB = (248, 248, 250)
TEXT_RGB = (80, 80, 90)
WIDTH, HEIGHT = 600, 400


def make_placeholder(name: str, out_path: Path) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG_RGB)
    draw = ImageDraw.Draw(img)
    # Try a nice font; fall back to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
    except OSError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 32)
        except OSError:
            font = ImageFont.load_default()
    # Wrap long names (e.g. "Cottage Cheese" vs "Brussels Sprouts")
    words = name.split()
    lines = []
    current = []
    for w in words:
        current.append(w)
        if len(" ".join(current)) > 22:
            if len(current) > 1:
                lines.append(" ".join(current[:-1]))
                current = [current[-1]]
            else:
                lines.append(" ".join(current))
                current = []
    if current:
        lines.append(" ".join(current))
    # Center text vertically
    line_height = 40
    total_h = len(lines) * line_height
    y = (HEIGHT - total_h) // 2
    for line in lines:
        if hasattr(draw, "textbbox"):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
        else:
            tw, _ = draw.textsize(line, font=font)
        x = (WIDTH - tw) // 2
        draw.text((x, y), line, fill=TEXT_RGB, font=font)
        y += line_height
    img.save(out_path, "JPEG", quality=85)


def main() -> None:
    force = "--force" in sys.argv or "-f" in sys.argv
    if not SEED_DATA.exists():
        print(f"Error: {SEED_DATA} not found", file=sys.stderr)
        sys.exit(1)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEED_DATA, encoding="utf-8") as f:
        products = json.load(f)
    created = 0
    for p in products:
        image_url = p.get("image_url")
        name = p.get("name", "Product")
        if not image_url:
            continue
        # image_url is like "infrastructure/images/0123456789030-almond-milk.jpg"
        filename = Path(image_url).name
        out_path = IMAGES_DIR / filename
        if out_path.exists() and not force:
            continue
        make_placeholder(name, out_path)
        created += 1
        print(f"  Created {filename}")
    print(f"Done. Created {created} placeholder image(s).")


if __name__ == "__main__":
    main()
