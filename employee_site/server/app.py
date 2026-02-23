"""Employee-facing Backend-For-Frontend (BFF).

Validates Cognito JWTs and proxies requests to:
- Product Catalogue API  (read-only: products, stores)
- Inventory API          (CRUD: stock per store)
"""

import os
import logging

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from auth import require_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

PRODUCT_CATALOGUE_API_URL = os.environ.get(
    "PRODUCT_CATALOGUE_API_URL", "http://localhost:8000"
).rstrip("/")

INVENTORY_API_URL = os.environ.get(
    "INVENTORY_API_URL", "http://localhost:9000"
).rstrip("/")

PROXY_TIMEOUT = 10  # seconds


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "employee-bff"})


# ---------------------------------------------------------------------------
# Proxied read endpoints (Product Catalogue)
# ---------------------------------------------------------------------------

@app.route("/api/stores", methods=["GET"])
@require_auth
def list_stores():
    resp = requests.get(f"{PRODUCT_CATALOGUE_API_URL}/stores", timeout=PROXY_TIMEOUT)
    return (resp.content, resp.status_code, {"Content-Type": resp.headers.get("Content-Type", "application/json")})


@app.route("/api/products", methods=["GET"])
@require_auth
def list_products():
    resp = requests.get(
        f"{PRODUCT_CATALOGUE_API_URL}/products",
        params=request.args,
        timeout=PROXY_TIMEOUT,
    )
    return (resp.content, resp.status_code, {"Content-Type": resp.headers.get("Content-Type", "application/json")})


# ---------------------------------------------------------------------------
# Proxied read endpoints (Inventory API)
# ---------------------------------------------------------------------------

@app.route("/api/inventory/<store_id>", methods=["GET"])
@require_auth
def list_inventory(store_id):
    resp = requests.get(
        f"{INVENTORY_API_URL}/inventory/{store_id}", timeout=PROXY_TIMEOUT
    )
    return (resp.content, resp.status_code, {"Content-Type": resp.headers.get("Content-Type", "application/json")})


# ---------------------------------------------------------------------------
# CRUD endpoints (Inventory API)
# ---------------------------------------------------------------------------

@app.route("/api/inventory/<store_id>/<barcode>", methods=["POST"])
@require_auth
def create_stock(store_id, barcode):
    """Add a product to a store's stock."""
    resp = requests.post(
        f"{INVENTORY_API_URL}/inventory/{store_id}/{barcode}",
        json=request.get_json(force=True),
        timeout=PROXY_TIMEOUT,
    )
    return (resp.content, resp.status_code, {"Content-Type": resp.headers.get("Content-Type", "application/json")})


@app.route("/api/inventory/<store_id>/<barcode>", methods=["PUT"])
@require_auth
def update_stock(store_id, barcode):
    """Update quantity of a product in a store's stock."""
    resp = requests.put(
        f"{INVENTORY_API_URL}/inventory/{store_id}/{barcode}",
        json=request.get_json(force=True),
        timeout=PROXY_TIMEOUT,
    )
    return (resp.content, resp.status_code, {"Content-Type": resp.headers.get("Content-Type", "application/json")})


@app.route("/api/inventory/<store_id>/<barcode>", methods=["DELETE"])
@require_auth
def delete_stock(store_id, barcode):
    """Remove a product from a store's stock."""
    resp = requests.delete(
        f"{INVENTORY_API_URL}/inventory/{store_id}/{barcode}",
        timeout=PROXY_TIMEOUT,
    )
    return (resp.content, resp.status_code, {"Content-Type": resp.headers.get("Content-Type", "application/json")})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
