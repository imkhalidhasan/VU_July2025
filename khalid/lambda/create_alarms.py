import boto3
from botocore.exceptions import ClientError
from datetime import datetime


WEBSITE_URL = "https://bbc.com"
AWS_REGION  = "ap-southeast-2"
#ALERT_EMAIL = "you@example.com"   # or "" to skip email/SNS setup
AVAILABILITY_THRESHOLD = 0.99     # 99%
P95_LATENCY_THRESHOLD_MS = 800    # ms
# If you use a named AWS profile locally, set it here; otherwise leave as None
AWS_PROFILE = None
# <<<<<<<<<<<<<<<<<

NAMESPACE = "Website/Health"
DIMENSION = [{"Name": "Target", "Value": WEBSITE_URL}]

def session_and_clients():
    if AWS_PROFILE:
        print(f"[i] Using AWS profile: {AWS_PROFILE}")
        sess = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    else:
        sess = boto3.Session(region_name=AWS_REGION)

    sts = sess.client("sts")
    cw  = sess.client("cloudwatch")
    sns = sess.client("sns")
    return sess, sts, cw, sns

def whoami(sts):
    ident = sts.get_caller_identity()
    print(f"[i] Account: {ident['Account']}  UserArn: {ident['Arn']}")
    return ident

def check_metrics_exist(cw):
    print(f"[i] Verifying metrics exist in namespace '{NAMESPACE}' for Target='{WEBSITE_URL}' ...")
    resp = cw.list_metrics(
        Namespace=NAMESPACE,
        MetricName="LatencyMs",
        Dimensions=[{"Name": "Target", "Value": WEBSITE_URL}]
    )
    found_latency = len(resp.get("Metrics", [])) > 0

    resp2 = cw.list_metrics(
        Namespace=NAMESPACE,
        MetricName="Availability",
        Dimensions=[{"Name": "Target", "Value": WEBSITE_URL}]
    )
    found_avail = len(resp2.get("Metrics", [])) > 0

    print(f"    - LatencyMs metric found: {found_latency}")
    print(f"    - Availability metric found: {found_avail}")

    if not (found_latency and found_avail):
        print("[!] Metrics not found yet. Run your monitor script to publish data first "
              "(monitor_site.py), then re-run this alarms script.")
    return found_latency and found_avail

def ensure_sns_topic(sns):
    if not ALERT_EMAIL:
        print("[i] ALERT_EMAIL is empty — skipping SNS setup.")
        return None

    print("[i] Creating/Getting SNS topic 'WebsiteHealthAlerts' ...")
    topic_arn = sns.create_topic(Name="WebsiteHealthAlerts")["TopicArn"]
    print(f"    - TopicArn: {topic_arn}")

    # Check if already subscribed
    subs = sns.list_subscriptions_by_topic(TopicArn=topic_arn).get("Subscriptions", [])
    if any(s.get("Endpoint") == ALERT_EMAIL and s.get("Protocol") == "email" for s in subs):
        print(f"    - Email '{ALERT_EMAIL}' already subscribed.")
    else:
        print(f"    - Subscribing email: {ALERT_EMAIL}")
        sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=ALERT_EMAIL)
        print("      (Check your inbox and CONFIRM the subscription.)")

    return topic_arn

def put_availability_alarm(cw, topic_arn):
    alarm_name = f"AvailabilityLow-{WEBSITE_URL}"
    print(f"[i] Creating/Updating alarm: {alarm_name}")
    cw.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription=f"Average availability below {AVAILABILITY_THRESHOLD*100:.1f}% for {WEBSITE_URL}",
        Namespace=NAMESPACE,
        MetricName="Availability",
        Dimensions=DIMENSION,
        Statistic="Average",
        Period=60,
        EvaluationPeriods=5,
        DatapointsToAlarm=3,
        Threshold=AVAILABILITY_THRESHOLD,
        ComparisonOperator="LessThanThreshold",
        TreatMissingData="breaching",
        ActionsEnabled=bool(topic_arn),
        AlarmActions=[topic_arn] if topic_arn else [],
        OKActions=[topic_arn] if topic_arn else [],
    )
    print("    - Availability alarm configured.")
    return alarm_name

def put_latency_alarm(cw, topic_arn):
    alarm_name = f"LatencyP95High-{WEBSITE_URL}"
    print(f"[i] Creating/Updating alarm: {alarm_name}")
    cw.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription=f"p95 latency over {P95_LATENCY_THRESHOLD_MS} ms for {WEBSITE_URL}",
        Namespace=NAMESPACE,
        MetricName="LatencyMs",
        Dimensions=DIMENSION,
        ExtendedStatistic="p95",
        Period=60,
        EvaluationPeriods=5,
        DatapointsToAlarm=3,
        Threshold=float(P95_LATENCY_THRESHOLD_MS),
        ComparisonOperator="GreaterThanThreshold",
        TreatMissingData="notBreaching",
        ActionsEnabled=bool(topic_arn),
        AlarmActions=[topic_arn] if topic_arn else [],
        OKActions=[topic_arn] if topic_arn else [],
    )
    print("    - Latency p95 alarm configured.")
    return alarm_name

def show_alarm_state(cw, alarm_name):
    resp = cw.describe_alarms(AlarmNames=[alarm_name])
    alarms = resp.get("MetricAlarms", [])
    if not alarms:
        print(f"[!] Alarm '{alarm_name}' not found right after creation (unexpected).")
        return
    a = alarms[0]
    print(f"    - AlarmName: {a['AlarmName']}")
    print(f"      State: {a['StateValue']}  Reason: {a.get('StateReason','')[:160]}")
    print(f"      Metric: {a['MetricName']}  Namespace: {a['Namespace']}")
    print(f"      Dimensions: {a['Dimensions']}")
    print(f"      Period: {a['Period']}s  EvalPeriods: {a['EvaluationPeriods']}  DatapointsToAlarm: {a.get('DatapointsToAlarm')}")
    print(f"      Threshold: {a['Threshold']}  Comparison: {a['ComparisonOperator']}")

def main():
    print(f"[i] Region: {AWS_REGION}")
    print(f"[i] Namespace: {NAMESPACE}")
    print(f"[i] Target URL (dimension): {WEBSITE_URL}")
    print(f"[i] Started at: {datetime.utcnow().isoformat()}Z")

    sess, sts, cw, sns = session_and_clients()
    whoami(sts)

    # Sanity check: metrics exist
    metrics_ok = check_metrics_exist(cw)
    if not metrics_ok:
        print("[!] Aborting alarm creation until metrics appear.")
        return

    topic_arn = ensure_sns_topic(sns)

    # Put alarms
    avail_alarm = put_availability_alarm(cw, topic_arn)
    lat_alarm   = put_latency_alarm(cw, topic_arn)

    # Confirm alarms exist and show state
    print("[i] Verifying alarms just created...")
    show_alarm_state(cw, avail_alarm)
    show_alarm_state(cw, lat_alarm)

    print("\n[i] Done. In the Console, go to CloudWatch → Alarms (same region) to see them.")
    print("    New alarms may show 'INSUFFICIENT_DATA' for a few minutes until enough samples arrive.")

if __name__ == "__main__":
    try:
        main()
    except ClientError as e:
        print(f"[AWS ERROR] {e.response.get('Error', {}).get('Code')}: {e.response.get('Error', {}).get('Message')}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")