#!/usr/bin/env python3
"""
Fetch free-to-use product images from Pexels for all products in products.json.
Replaces placeholder or missing images with real photos. Saves to infrastructure/images/
with the filenames expected by products.json.

Requirements:
  - Pexels API key (free): https://www.pexels.com/api/
  - Set: export PEXELS_API_KEY=your_key
  - Use the raw API key only (no "Bearer " prefix).
  - Python 3 with urllib (stdlib). Optional: pip install requests (not required).

Usage (from repo root):
  python3 scripts/fetch_pexels_product_images.py

Attribution: Pexels requires a prominent link back (e.g. "Photos provided by Pexels").
Rate limit: 200 requests/hour by default; script adds a short delay between requests.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SEED_DATA = PROJECT_ROOT / "server" / "seed_data" / "products.json"
IMAGES_DIR = PROJECT_ROOT / "infrastructure" / "images"

# Override search query for products where "name" gives poor or irrelevant results
SEARCH_OVERRIDES = {
    # Dairy / beverages
    "Half and Half": "half and half cream",
    "Sparkling Water": "sparkling water bottles",
    "Green Tea": "green tea bags",
    "Vegetable Oil": "vegetable oil bottle",
    "Yogurt Drink": "yogurt drink bottle",
    "Coconut Milk": "coconut milk can",
    "Ice Cream": "vanilla ice cream",
    "Cola": "cola cans",
    "Cereal": "oat cereal box",
    # Condiments / pantry
    "Hot Sauce": "hot sauce bottle",
    "Soy Sauce": "soy sauce bottle",
    "Ketchup": "ketchup bottle",
    "Mustard": "dijon mustard jar",
    "Salsa": "salsa jar",
    "Maple Syrup": "maple syrup bottle",
    "Peanut Butter": "peanut butter jar",
    # Canned / packaged
    "Canned Tuna": "canned tuna can",
    "Canned Tomatoes": "canned tomatoes",
    "Canned Chickpeas": "chickpeas can",
    "Black Beans": "black beans can",
    "Frozen Peas": "frozen peas bag",
    "Corn on the Cob": "corn on the cob",
    # Produce (better Pexels results)
    "Organic Bananas": "organic bananas fruit",
    "Organic Apples": "organic apples fruit",
    "Organic Carrots": "organic carrots vegetable",
    "Organic Spinach": "fresh spinach leaves",
    "Strawberries": "fresh strawberries fruit",
    "Blueberries": "fresh blueberries fruit",
    "Avocados": "ripe avocados",
    "Kale": "kale vegetable",
    "Green Beans": "green beans vegetable",
    "Bell Peppers": "bell peppers vegetable",
    "Cucumber": "fresh cucumber",
    "Raspberries": "fresh raspberries",
    "Cauliflower": "cauliflower vegetable",
    "Sweet Potato": "sweet potato vegetable",
    "Zucchini": "zucchini vegetable",
    "Garlic": "garlic bulbs",
    "Lemon": "lemons citrus",
    "Lime": "limes citrus",
    "Celery": "celery stalks",
    "Potatoes": "potatoes vegetable",
    "Corn": "fresh corn ears",
    "Asparagus": "asparagus vegetable",
    "Cantaloupe": "cantaloupe melon",
    "Lettuce": "lettuce vegetable",
    "Mushrooms": "fresh mushrooms",
    "Brussels Sprouts": "brussels sprouts",
    "Onions": "yellow onions",
    "Pear": "pear fruit",
    "Pineapple": "fresh pineapple",
    "Mango": "fresh mango fruit",
    "Cilantro": "cilantro herb",
    "Eggplant": "eggplant vegetable",
    "Watermelon": "watermelon slice",
    "Grapes": "fresh grapes fruit",
}


def search_pexels(api_key: str, query: str) -> dict:
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": query, "per_page": 1, "orientation": "square"}
    )
    headers = {
        "Authorization": api_key,
        "User-Agent": "ProductCatalogue/1.0 (https://github.com/pexels)",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def download_image(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "ProductCatalogue/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        dest.write_bytes(resp.read())


def main() -> None:
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        print("Error: Set PEXELS_API_KEY (get a free key at https://www.pexels.com/api/)", file=sys.stderr)
        sys.exit(1)
    # Remove "Bearer " if user pasted it; Pexels expects the raw key only
    if api_key.lower().startswith("bearer "):
        api_key = api_key[7:].strip()

    # Validate API key with one request before processing all products
    try:
        search_pexels(api_key, "test")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print(
                "Error: Pexels API key rejected (401/403). Check that PEXELS_API_KEY is set to the\n"
                "  full key (no line breaks or spaces in the middle), raw key only (no 'Bearer ' prefix),\n"
                "  and that the key is active at https://www.pexels.com/api/key/",
                file=sys.stderr,
            )
            sys.exit(1)
        raise

    if not SEED_DATA.exists():
        print(f"Error: {SEED_DATA} not found", file=sys.stderr)
        sys.exit(1)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEED_DATA, encoding="utf-8") as f:
        products = json.load(f)

    fetched = 0
    for p in products:
        name = p.get("name", "Product")
        image_url = p.get("image_url")
        if not image_url:
            continue
        filename = Path(image_url).name
        dest = IMAGES_DIR / filename

        query = SEARCH_OVERRIDES.get(name, name)
        try:
            data = search_pexels(api_key, query)
            photos = data.get("photos") or []
            if not photos:
                print(f"  Skip (no results): {name}")
                time.sleep(1)
                continue
            # Use 'medium' (h=350) or 'large' (940x650) for good quality
            src = photos[0].get("src") or {}
            image_url_dl = src.get("large") or src.get("medium") or src.get("original")
            if not image_url_dl:
                print(f"  Skip (no URL): {name}")
                time.sleep(1)
                continue
            download_image(image_url_dl, dest)
            print(f"  Fetched: {filename} ({name})")
            fetched += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("  Rate limit hit; wait a moment and re-run.", file=sys.stderr)
                sys.exit(1)
            if e.code in (401, 403):
                print(
                    f"  Error {e.code}: API key rejected. Check PEXELS_API_KEY at https://www.pexels.com/api/",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"  Error {e.code} for {name}: {e.reason}")
        except Exception as e:
            print(f"  Error for {name}: {e}")
        time.sleep(1.2)  # Stay under 200/hour

    print(f"Done. Fetched {fetched} image(s) from Pexels.")
    print("Attribution: Photos from Pexels (https://www.pexels.com) - link back in your app.")


if __name__ == "__main__":
    main()
