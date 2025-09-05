
This repository provides Python scripts to monitor a website’s availability and latency, then visualize and alert using **AWS CloudWatch**.

 Features
- Monitor: Sends HTTP GET requests to your target website and records:
  - **LatencyMs**: Round-trip response time in milliseconds.
  - **Availability**: `1.0` if HTTP status is `200–399`, else `0.0`.
- **Metrics:** Publishes custom metrics into CloudWatch (`Website/Health` namespace).
- **Alarms:** Creates alarms for:
  - Availability dropping below a threshold (default **99%**).
  - p95 latency exceeding a threshold (default **800 ms**).
- **Dashboard:** Builds a CloudWatch Dashboard with visual graphs for Availability and Latency.

📂 Files
- `monitor_site.py` → Runs one website check and pushes metrics to CloudWatch.
- `create_alarms.py` → Creates CloudWatch alarms and optional **SNS email notifications**.
- `create_dashboard.py` → Creates/updates a CloudWatch dashboard for visualization.

"
