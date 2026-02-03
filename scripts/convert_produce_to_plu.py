#!/usr/bin/env python3
"""
Convert produce products from GTIN to PLU codes in products.json, sales.json,
stock.json, and rename image files. Run from repo root.
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_JSON = PROJECT_ROOT / "server" / "seed_data" / "products.json"
SALES_JSON = PROJECT_ROOT / "server" / "seed_data" / "sales.json"
STOCK_JSON = PROJECT_ROOT / "server" / "seed_data" / "stock.json"
IMAGES_DIR = PROJECT_ROOT / "infrastructure" / "images"

# Standard PLU codes for produce (IFPS-style). Only produce currently using GTIN.
GTIN_TO_PLU = {
    "0123456789018": "4090",   # Organic Spinach
    "0123456789021": "4799",   # Tomatoes
    "0123456789025": "4021",   # Strawberries
    "0123456789026": "4062",   # Broccoli
    "0123456789029": "4664",   # Onions
    "0123456789031": "4027",   # Blueberries
    "0123456789034": "4046",   # Avocados
    "0123456789037": "4783",   # Kale
    "0123456789039": "4076",   # Green Beans
    "0123456789042": "4688",   # Bell Peppers
    "0123456789044": "4554",   # Cucumber
    "0123456789047": "4731",   # Raspberries
    "0123456789050": "4816",   # Sweet Potato
    "0123456789053": "4067",   # Zucchini
    "0123456789056": "4028",   # Grapes
    "0123456789059": "4729",   # Cauliflower
    "0123456789063": "4680",   # Mushrooms
    "0123456789066": "4053",   # Lemon
    "0123456789069": "4048",   # Garlic
    "0123456789072": "4049",   # Lime
    "0123456789075": "4070",   # Celery
    "0123456789079": "4550",   # Brussels Sprouts
    "0123456789081": "4078",   # Corn on the Cob
    "0123456789085": "4085",   # Asparagus
    "0123456789087": "4318",   # Cantaloupe
    "0123456789090": "4072",   # Potatoes
    "0123456789092": "4626",   # Lettuce
    "0123456789095": "4414",   # Pear
    "0123456789098": "4032",   # Watermelon
    "0123456789099": "4881",   # Eggplant
    "0123456789101": "4430",   # Pineapple
    "0123456789104": "4959",   # Mango
    "0123456789108": "4889",   # Cilantro
}


def main():
    with open(PRODUCTS_JSON, encoding="utf-8") as f:
        products = json.load(f)

    for p in products:
        if p.get("primary_category") != "Produce" or p.get("barcode_type") != "GTIN":
            continue
        gtin = p["barcode"]
        if gtin not in GTIN_TO_PLU:
            continue
        plu = GTIN_TO_PLU[gtin]
        old_image_url = p["image_url"]
        # image_url is e.g. "infrastructure/images/0123456789031-blueberries.jpg"
        old_filename = Path(old_image_url).name
        # new filename: PLU + same suffix (e.g. 4027-blueberries.jpg)
        suffix = "-".join(old_filename.split("-")[1:])  # blueberries.jpg
        new_filename = f"{plu}-{suffix}"
        p["barcode"] = plu
        p["barcode_type"] = "PLU"
        p["image_url"] = f"infrastructure/images/{new_filename}"

        # Rename image file
        old_path = IMAGES_DIR / old_filename
        new_path = IMAGES_DIR / new_filename
        if old_path.exists():
            old_path.rename(new_path)
            print(f"  Renamed {old_filename} -> {new_filename}")

    with open(PRODUCTS_JSON, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2)
    print(f"Updated {PRODUCTS_JSON}")

    for path in (SALES_JSON, STOCK_JSON):
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
        for row in rows:
            bc = row.get("barcode")
            if bc in GTIN_TO_PLU:
                row["barcode"] = GTIN_TO_PLU[bc]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
        print(f"Updated {path}")

    print("Done. Produce items now use PLU codes.")


if __name__ == "__main__":
    main()
