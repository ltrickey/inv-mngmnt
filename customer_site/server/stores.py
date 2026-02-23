"""Stores API: GET all stores, GET store by store_id."""

from flask import Blueprint, jsonify

from data import get_all_stores, get_store

stores_bp = Blueprint('stores', __name__, url_prefix='/stores')


@stores_bp.route('', methods=['GET'])
@stores_bp.route('/', methods=['GET'])
def list_stores():
    """GET all stores."""
    stores = get_all_stores()
    return jsonify(stores)


@stores_bp.route('/<store_id>', methods=['GET'])
def get_store_by_id(store_id):
    """GET one store by store_id."""
    store = get_store(store_id)
    if store is None:
        return jsonify({'error': 'Store not found'}), 404
    return jsonify(store)
