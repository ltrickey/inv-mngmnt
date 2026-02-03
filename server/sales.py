"""Sales API: GET all sales for a store, GET one sale by store_id and barcode."""

from flask import Blueprint, jsonify

from data import get_sale, get_sales_for_store

sales_bp = Blueprint('sales', __name__, url_prefix='/sales')


@sales_bp.route('/<store_id>', methods=['GET'])
def list_sales_for_store(store_id):
    """GET all sales for a given store."""
    items = get_sales_for_store(store_id)
    return jsonify(items)


@sales_bp.route('/<store_id>/<barcode>', methods=['GET'])
def get_sale_by_store_and_barcode(store_id, barcode):
    """GET one sale (product at store) by store_id and barcode."""
    item = get_sale(store_id, barcode)
    if item is None:
        return jsonify({'error': 'Sale not found'}), 404
    return jsonify(item)
