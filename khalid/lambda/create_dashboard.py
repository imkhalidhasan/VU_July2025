
import json, boto3

# >>> EDIT THESE <<<
WEBSITE_URL   = "https://www.bbc.com"
AWS_REGION    = "ap-southeast-2"
DASHBOARD_NAME = "WebsiteHealth"
# <<<<<<<<<<<<<<<<<

NAMESPACE = "Website/Health"

def main():
    cw = boto3.client("cloudwatch", region_name=AWS_REGION)
    widgets = [
        {
            "type": "metric",
            "x": 0, "y": 0, "width": 12, "height": 6,
            "properties": {
                "region": AWS_REGION,
                "title": "Availability (avg, 0..1)",
                "period": 60,
                "yAxis": {"left": {"min": 0, "max": 1}},
                "metrics": [[NAMESPACE, "Availability", "Target", WEBSITE_URL, {"stat": "Average"}]],
            },
        },
        {
            "type": "metric",
            "x": 12, "y": 0, "width": 12, "height": 6,
            "properties": {
                "region": AWS_REGION,
                "title": "Latency p95 (ms)",
                "period": 60,
                "metrics": [[NAMESPACE, "LatencyMs", "Target", WEBSITE_URL, {"stat": "p95"}]],
            },
        },
    ]
    cw.put_dashboard(DashboardName=DASHBOARD_NAME, DashboardBody=json.dumps({"widgets": widgets}))
    print(f"Dashboard '{DASHBOARD_NAME}' created/updated in {AWS_REGION}.")

if __name__ == "__main__":
    main()
