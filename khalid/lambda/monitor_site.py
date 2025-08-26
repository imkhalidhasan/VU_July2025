
import time
from datetime import datetime, timezone
import boto3
import requests

# >>> EDIT THESE <<<
WEBSITE_URL = "https://bbc.com"        
AWS_REGION  = "ap-southeast-2"           
# <<<<<<<<<<<<<<<<<

NAMESPACE = "Website/Health"

def check_once(url: str, timeout_s: float = 10.0):
    t0 = time.perf_counter()
    code = None
    err = None
    try:
        r = requests.get(url, timeout=timeout_s)
        code = r.status_code
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

def main():
    cw = boto3.client("cloudwatch", region_name=AWS_REGION)
    ts = datetime.now(timezone.utc)
    latency_ms, availability, code, err = check_once(WEBSITE_URL, 10.0)
    put_metrics(cw, WEBSITE_URL, latency_ms, availability, ts)
    print(f"[{ts.isoformat()}] url={WEBSITE_URL} latency_ms={latency_ms} avail={availability} code={code} err={err}")

if __name__ == "__main__":
    main()
