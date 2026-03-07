"""Employee-facing Backend-For-Frontend (BFF).

Validates Cognito JWTs and proxies requests to:
- Product Catalogue API  (read-only: products, stores)
- Inventory API          (CRUD: stock per store)
"""

import json
import os
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
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
# Report scheduling config (DynamoDB + EventBridge Scheduler + S3)
# ---------------------------------------------------------------------------

REPORT_SCHEDULES_TABLE = os.environ.get("REPORT_SCHEDULES_TABLE", "")
REPORT_RESULTS_TABLE   = os.environ.get("REPORT_RESULTS_TABLE", "")
REPORTS_BUCKET         = os.environ.get("REPORTS_BUCKET", "")
REPORT_LAMBDA_ARN      = os.environ.get("REPORT_LAMBDA_ARN", "")
REPORT_SCHEDULE_GROUP  = os.environ.get("REPORT_SCHEDULE_GROUP", "")
LAB_ROLE_ARN           = os.environ.get("LAB_ROLE_ARN", "")
AWS_REGION             = os.environ.get("AWS_REGION", "us-east-1")

_dynamodb  = boto3.client("dynamodb", region_name=AWS_REGION)
_scheduler = boto3.client("scheduler", region_name=AWS_REGION)
_s3        = boto3.client("s3", region_name=AWS_REGION)

FREQUENCY_EXPRESSIONS = {
    "minute": "rate(1 minute)",
    "hour":   "rate(1 hour)",
    "day":    "rate(1 day)",
    "week":   "rate(7 days)",
}

def _decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


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


@app.route("/api/categories", methods=["GET"])
@require_auth
def list_categories():
    resp = requests.get(f"{PRODUCT_CATALOGUE_API_URL}/categories", timeout=PROXY_TIMEOUT)
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
# Report Scheduling Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/reports/schedules", methods=["POST"])
@require_auth
def create_report_schedule():
    """Create a recurring report schedule."""
    body = request.get_json(force=True) or {}
    filter_type    = body.get("filter_type")
    filter_value   = body.get("filter_value")
    lookback_window = body.get("lookback_window")
    frequency      = body.get("frequency")

    if not all([filter_type, filter_value, lookback_window, frequency]):
        return jsonify({"error": "filter_type, filter_value, lookback_window, and frequency are required"}), 400
    if filter_type not in ("store", "category"):
        return jsonify({"error": "filter_type must be 'store' or 'category'"}), 400
    if lookback_window not in ("hour", "day", "week"):
        return jsonify({"error": "lookback_window must be 'hour', 'day', or 'week'"}), 400
    if frequency not in FREQUENCY_EXPRESSIONS:
        return jsonify({"error": f"frequency must be one of: {list(FREQUENCY_EXPRESSIONS)}"}), 400

    schedule_id       = str(uuid.uuid4())
    created_at        = datetime.now(timezone.utc).isoformat()
    eb_schedule_name  = f"report-{schedule_id}"

    # Write schedule record to DynamoDB
    _dynamodb.put_item(
        TableName=REPORT_SCHEDULES_TABLE,
        Item={
            "schedule_id":      {"S": schedule_id},
            "filter_type":      {"S": filter_type},
            "filter_value":     {"S": filter_value},
            "lookback_window":  {"S": lookback_window},
            "frequency":        {"S": frequency},
            "created_at":       {"S": created_at},
            "eb_schedule_name": {"S": eb_schedule_name},
        },
    )

    # Create EventBridge Scheduler schedule
    _scheduler.create_schedule(
        Name=eb_schedule_name,
        GroupName=REPORT_SCHEDULE_GROUP,
        ScheduleExpression=FREQUENCY_EXPRESSIONS[frequency],
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn":     REPORT_LAMBDA_ARN,
            "RoleArn": LAB_ROLE_ARN,
            "Input":   json.dumps({"schedule_id": schedule_id}),
        },
    )

    return jsonify({
        "schedule_id":      schedule_id,
        "filter_type":      filter_type,
        "filter_value":     filter_value,
        "lookback_window":  lookback_window,
        "frequency":        frequency,
        "created_at":       created_at,
    }), 201


@app.route("/api/reports/schedules", methods=["GET"])
@require_auth
def list_report_schedules():
    """List all report schedules."""
    resp  = _dynamodb.scan(TableName=REPORT_SCHEDULES_TABLE)
    items = []
    for raw in resp.get("Items", []):
        items.append({k: list(v.values())[0] for k, v in raw.items()})
    # Sort newest first
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(items)


@app.route("/api/reports/schedules/<schedule_id>", methods=["DELETE"])
@require_auth
def delete_report_schedule(schedule_id):
    """Delete a report schedule and its EventBridge rule."""
    # Fetch schedule to get the EventBridge schedule name
    resp = _dynamodb.get_item(
        TableName=REPORT_SCHEDULES_TABLE,
        Key={"schedule_id": {"S": schedule_id}},
    )
    item = resp.get("Item")
    if not item:
        return jsonify({"error": "Schedule not found"}), 404

    eb_schedule_name = item.get("eb_schedule_name", {}).get("S", f"report-{schedule_id}")

    # Delete from EventBridge Scheduler (ignore if already gone)
    try:
        _scheduler.delete_schedule(Name=eb_schedule_name, GroupName=REPORT_SCHEDULE_GROUP)
    except _scheduler.exceptions.ResourceNotFoundException:
        pass

    # Delete from DynamoDB
    _dynamodb.delete_item(
        TableName=REPORT_SCHEDULES_TABLE,
        Key={"schedule_id": {"S": schedule_id}},
    )

    return "", 204


@app.route("/api/reports/schedules/<schedule_id>/results", methods=["GET"])
@require_auth
def list_schedule_results(schedule_id):
    """List all generated reports for a schedule, newest first."""
    resp = _dynamodb.query(
        TableName=REPORT_RESULTS_TABLE,
        KeyConditionExpression="schedule_id = :sid",
        ExpressionAttributeValues={":sid": {"S": schedule_id}},
        ScanIndexForward=False,  # newest first
    )
    items = []
    for raw in resp.get("Items", []):
        items.append({k: list(v.values())[0] for k, v in raw.items()})
    return jsonify(items)


@app.route("/api/reports/results/download", methods=["GET"])
@require_auth
def download_report():
    """Return a presigned S3 URL for a report CSV (s3_key query param required)."""
    s3_key = request.args.get("s3_key")
    if not s3_key:
        return jsonify({"error": "s3_key query parameter is required"}), 400

    url = _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": REPORTS_BUCKET, "Key": s3_key},
        ExpiresIn=3600,
    )
    return jsonify({"url": url})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
