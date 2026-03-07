"""
Report Generator Lambda

Triggered by EventBridge Scheduler on a recurring schedule.
Reads a report schedule config from DynamoDB, queries sales_events for the
lookback window, aggregates by product, generates a CSV, uploads to S3,
and records the result back in DynamoDB.

Event payload: { "schedule_id": "<uuid>" }
"""

import csv
import io
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.types import TypeDeserializer

# ---------------------------------------------------------------------------
# Config from Lambda environment variables
# ---------------------------------------------------------------------------
SALES_EVENTS_TABLE     = os.environ["SALES_EVENTS_TABLE"]
PRODUCTS_TABLE         = os.environ["PRODUCTS_TABLE"]
REPORTS_BUCKET         = os.environ["REPORTS_BUCKET"]
REPORT_SCHEDULES_TABLE = os.environ["REPORT_SCHEDULES_TABLE"]
REPORT_RESULTS_TABLE   = os.environ["REPORT_RESULTS_TABLE"]

# ---------------------------------------------------------------------------
# AWS clients (reused across warm invocations)
# ---------------------------------------------------------------------------
_dynamodb = boto3.client("dynamodb")
_s3       = boto3.client("s3")
_deser    = TypeDeserializer()

LOOKBACK_DELTAS = {
    "hour": timedelta(hours=1),
    "day":  timedelta(days=1),
    "week": timedelta(weeks=1),
}


def _deser_item(raw: dict) -> dict:
    """Deserialize a DynamoDB low-level item to a plain Python dict."""
    result = {}
    for k, v in raw.items():
        val = _deser.deserialize(v)
        result[k] = float(val) if isinstance(val, Decimal) else val
    return result


def _get_schedule(schedule_id: str) -> dict:
    resp = _dynamodb.get_item(
        TableName=REPORT_SCHEDULES_TABLE,
        Key={"schedule_id": {"S": schedule_id}},
    )
    item = resp.get("Item")
    if not item:
        raise ValueError(f"Schedule not found: {schedule_id}")
    return _deser_item(item)


def _time_window(lookback_window: str):
    """Return (t_start_str, t_end_str) as ISO UTC strings for the lookback window."""
    delta = LOOKBACK_DELTAS.get(lookback_window)
    if not delta:
        raise ValueError(f"Unknown lookback_window: {lookback_window}")
    t_end   = datetime.now(timezone.utc)
    t_start = t_end - delta
    # Format matches the sale_id prefix: "YYYY-MM-DDTHH:mm:ss.ffffffZ"
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    return t_start.strftime(fmt), t_end.strftime(fmt)


def _query_by_store(store_id: str, t_start: str, t_end: str) -> list[dict]:
    """Query sales_events by store_id + sale_id time range."""
    events = []
    kwargs = {
        "TableName": SALES_EVENTS_TABLE,
        "KeyConditionExpression": "store_id = :sid AND sale_id BETWEEN :t1 AND :t2",
        "ExpressionAttributeValues": {
            ":sid": {"S": store_id},
            ":t1":  {"S": t_start},
            ":t2":  {"S": t_end},
        },
    }
    paginator = _dynamodb.get_paginator("query")
    for page in paginator.paginate(**kwargs):
        for item in page.get("Items", []):
            events.append(_deser_item(item))
    return events


def _get_barcodes_for_category(category: str) -> list[str]:
    """Return all barcodes whose primary_category matches the given value."""
    barcodes = []
    kwargs = {
        "TableName": PRODUCTS_TABLE,
        "IndexName": "GSI_Category",
        "KeyConditionExpression": "primary_category = :cat",
        "ExpressionAttributeValues": {":cat": {"S": category}},
        "ProjectionExpression": "barcode",
    }
    paginator = _dynamodb.get_paginator("query")
    for page in paginator.paginate(**kwargs):
        for item in page.get("Items", []):
            barcodes.append(item["barcode"]["S"])
    return barcodes


def _query_by_barcode(barcode: str, t_start: str, t_end: str) -> list[dict]:
    """Query sales_events GSI_Barcode for a single barcode in the time range."""
    events = []
    kwargs = {
        "TableName": SALES_EVENTS_TABLE,
        "IndexName": "GSI_Barcode",
        "KeyConditionExpression": "barcode = :bc AND sale_id BETWEEN :t1 AND :t2",
        "ExpressionAttributeValues": {
            ":bc": {"S": barcode},
            ":t1": {"S": t_start},
            ":t2": {"S": t_end},
        },
    }
    paginator = _dynamodb.get_paginator("query")
    for page in paginator.paginate(**kwargs):
        for item in page.get("Items", []):
            events.append(_deser_item(item))
    return events


def _get_product_name(barcode: str) -> str:
    """Look up the product name from the products table by barcode."""
    resp = _dynamodb.get_item(
        TableName=PRODUCTS_TABLE,
        Key={"barcode": {"S": barcode}},
        ProjectionExpression="#n",
        ExpressionAttributeNames={"#n": "name"},  # "name" is not a reserved word, but alias for safety
    )
    item = resp.get("Item")
    return item["name"]["S"] if item and "name" in item else barcode


def _aggregate(events: list[dict]) -> dict[str, dict]:
    """Group sales events by barcode and sum quantity + revenue."""
    totals = defaultdict(lambda: {"quantity": 0, "revenue": 0.0})
    for e in events:
        bc = e["barcode"]
        totals[bc]["quantity"] += int(e.get("quantity", 0))
        totals[bc]["revenue"]  += float(e.get("revenue", 0.0))
    return totals


def _build_csv(totals: dict[str, dict]) -> tuple[str, int]:
    """Generate CSV content and return (csv_string, row_count)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["barcode", "product_name", "total_quantity", "total_revenue"])
    for barcode, agg in sorted(totals.items()):
        product_name = _get_product_name(barcode)
        writer.writerow([
            barcode,
            product_name,
            agg["quantity"],
            f"{agg['revenue']:.2f}",
        ])
    return buf.getvalue(), len(totals)


def _upload_csv(schedule_id: str, generated_at: str, csv_content: str) -> str:
    """Upload CSV to S3 and return the S3 key."""
    s3_key = f"reports/{schedule_id}/{generated_at}.csv"
    _s3.put_object(
        Bucket=REPORTS_BUCKET,
        Key=s3_key,
        Body=csv_content.encode("utf-8"),
        ContentType="text/csv",
    )
    return s3_key


def _record_result(schedule_id: str, generated_at: str, s3_key: str, row_count: int):
    """Write a result record to report_results DynamoDB table."""
    _dynamodb.put_item(
        TableName=REPORT_RESULTS_TABLE,
        Item={
            "schedule_id":   {"S": schedule_id},
            "generated_at":  {"S": generated_at},
            "s3_key":        {"S": s3_key},
            "row_count":     {"N": str(row_count)},
        },
    )


def lambda_handler(event, context):
    schedule_id = event.get("schedule_id")
    if not schedule_id:
        raise ValueError("Event must contain 'schedule_id'")

    print(f"Generating report for schedule: {schedule_id}")

    # 1. Load schedule config
    schedule = _get_schedule(schedule_id)
    filter_type    = schedule["filter_type"]    # "store" | "category"
    filter_value   = schedule["filter_value"]   # store_id or category name
    lookback_window = schedule["lookback_window"]  # "hour" | "day" | "week"

    # 2. Calculate time window
    t_start, t_end = _time_window(lookback_window)
    print(f"Window: {t_start} → {t_end}  filter: {filter_type}={filter_value}")

    # 3. Fetch sales events
    if filter_type == "store":
        events = _query_by_store(filter_value, t_start, t_end)
    elif filter_type == "category":
        barcodes = _get_barcodes_for_category(filter_value)
        events = []
        for bc in barcodes:
            events.extend(_query_by_barcode(bc, t_start, t_end))
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}")

    print(f"Found {len(events)} sale line items")

    # 4. Aggregate by barcode
    totals = _aggregate(events)

    # 5. Build CSV (product name lookup happens here)
    csv_content, row_count = _build_csv(totals)

    # 6. Upload to S3
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    s3_key = _upload_csv(schedule_id, generated_at, csv_content)
    print(f"Uploaded report to s3://{REPORTS_BUCKET}/{s3_key}  ({row_count} rows)")

    # 7. Record result in DynamoDB
    _record_result(schedule_id, generated_at, s3_key, row_count)

    return {
        "schedule_id":  schedule_id,
        "generated_at": generated_at,
        "s3_key":       s3_key,
        "row_count":    row_count,
    }
