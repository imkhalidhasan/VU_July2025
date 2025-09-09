import time
from datetime import datetime, timezone
import json
import os
import urllib.request
import boto3

WEBSITE_URL = os.getenv("WEBSITE_URL", "https://www.bbc.com")
AWS_REGION  = os.getenv("AWS_REGION")
NAMESPACE   = os.getenv("NAMESPACE", "MNcloud")

def check_once(url: str, timeout_s: float = 10.0):
    t0 = time.perf_counter()
    code = None
    err = None
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            code = resp.status
            availability = 1.0 if 200 <= code < 400 else 0.0
    except Exception as e:
        availability = 0.0
        err = str(e)
    elapsed_ms = int(round((time.perf_counter() - t0) * 1000))
    return elapsed_ms, availability, code, err

def put_metrics(cw, url: str, latency_ms: int, availability: float, ts):
    dims = [{"Name": "Target", "Value": url}]
    cw.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {"MetricName": "LatencyMs", "Timestamp": ts, "Value": latency_ms, "Unit": "Milliseconds", "Dimensions": dims},
            {"MetricName": "Availability", "Timestamp": ts, "Value": availability, "Dimensions": dims},
        ],
    )

def lambda_handler(event, context):
    cw = boto3.client("cloudwatch", region_name=AWS_REGION)
    ts = datetime.now(timezone.utc)
    latency_ms, availability, code, err = check_once(WEBSITE_URL, 10.0)
    put_metrics(cw, WEBSITE_URL, latency_ms, availability, ts)
    body = {
        "timestamp": ts.isoformat(),
        "url": WEBSITE_URL,
        "latency_ms": latency_ms,
        "availability": availability,
        "status_code": code,
        "error": err
    }
    print(json.dumps(body))
    return {
        "statusCode": 200 if availability == 1.0 else 500,
        "body": json.dumps(body)
    }
