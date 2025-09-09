import json
import os
import time
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

TABLE_NAME = os.environ["TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def lambda_handler(event, context):
    # SNS → Lambda event shape: Records[ { Sns: { Message, Subject, Timestamp, MessageId, ... } } ]
    # CloudWatch Alarms publish a JSON "AlarmStateChange" message string in Sns.Message
    results = []
    for rec in event.get("Records", []):
        sns_rec = rec.get("Sns", {})
        msg_str = sns_rec.get("Message", "{}")
        subject = sns_rec.get("Subject")
        ts_sns  = sns_rec.get("Timestamp")
        msg_id  = sns_rec.get("MessageId")

        # Try to parse CW alarm message
        try:
            msg = json.loads(msg_str)
        except Exception:
            msg = {"raw": msg_str}  # if not JSON (e.g., test message), store raw string

        # Heuristics for CloudWatch Alarm payloads
        alarm_name   = msg.get("AlarmName") or subject or "UnknownAlarm"
        new_state    = msg.get("NewStateValue") or msg.get("State") or "UNKNOWN"
        reason       = msg.get("NewStateReason") or msg.get("Reason")
        region       = msg.get("Region") or msg.get("Trigger", {}).get("Region")
        namespace    = msg.get("Trigger", {}).get("Namespace")
        metric_name  = msg.get("Trigger", {}).get("MetricName")
        dimensions   = msg.get("Trigger", {}).get("Dimensions")
        threshold    = msg.get("Trigger", {}).get("Threshold")
        stat         = msg.get("Trigger", {}).get("Statistic") or msg.get("Trigger", {}).get("ExtendedStatistic")
        period       = msg.get("Trigger", {}).get("Period")

        item = {
            "alarmName": alarm_name,                # PK
            "eventTime": ts_sns or _now_iso(),      # SK
            "messageId": msg_id,
            "newState": new_state,
            "reason": reason,
            "region": region,
            "metricNamespace": namespace,
            "metricName": metric_name,
            "dimensions": json.dumps(dimensions) if dimensions else None,
            "threshold": str(threshold) if threshold is not None else None,
            "statistic": str(stat) if stat else None,
            "period": str(period) if period else None,
            "payload": msg if isinstance(msg, dict) else {"raw": msg_str},
        }

        # Remove None attributes (DynamoDB doesn't accept them)
        item = {k: v for k, v in item.items() if v is not None}

        try:
            table.put_item(Item=item)
            results.append({"messageId": msg_id, "status": "OK"})
        except ClientError as e:
            # In case of write errors, throw to trigger retry / DLQ
            print(f"[ERROR] put_item failed: {e}")
            raise

    return {"saved": results}
