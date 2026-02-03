"""Stock API: GET stock by store, GET one item; stubs for CREATE, UPDATE, DELETE."""

from flask import Blueprint, jsonify, request

from data import get_stock_for_store, get_stock_item

stock_bp = Blueprint('stock', __name__, url_prefix='/stock')


@stock_bp.route('/<store_id>', methods=['GET'])
def list_stock_for_store(store_id):
    """GET all stock for a given store."""
    items = get_stock_for_store(store_id)
    return jsonify(items)


@stock_bp.route('/<store_id>/<barcode>', methods=['GET'])
def get_stock_item_by_store_and_barcode(store_id, barcode):
    """GET stock for one item (barcode) at one store."""
    item = get_stock_item(store_id, barcode)
    if item is None:
        return jsonify({'error': 'Stock record not found'}), 404
    return jsonify(item)


# --- Stubs for future CRUD ---

@stock_bp.route('/<store_id>/<barcode>', methods=['POST'])
def create_stock(store_id, barcode):
    # TODO: CREATE stock record (store_id, barcode, quantity)
    return jsonify({'message': 'TODO: CREATE stock not implemented'}), 501


@stock_bp.route('/<store_id>/<barcode>', methods=['PUT'])
def update_stock(store_id, barcode):
    # TODO: UPDATE stock record (e.g. quantity)
    return jsonify({'message': 'TODO: UPDATE stock not implemented'}), 501


@stock_bp.route('/<store_id>/<barcode>', methods=['DELETE'])
def delete_stock(store_id, barcode):
    # TODO: DELETE stock record
    return jsonify({'message': 'TODO: DELETE stock not implemented'}), 501
