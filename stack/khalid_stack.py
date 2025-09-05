from aws_cdk import (
    Stack, Duration,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
)
from constructs import Construct

class KhalidStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        website_url   = "https://www.bbc.com"
        namespace     = "Website/Health"
        region        = "ap-southeast-2"
        alert_email   = "khalidhasann@gmail.com"

        # Lambda
        monitor_fn = _lambda.Function(
            self, "WebsiteMonitorFn",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="monitor_site.lambda_handler",
            code=_lambda.Code.from_asset("/Users/khaled/VU_July2025/khalid/lambda"),   # 👈 update to your lambda folder
            timeout=Duration.seconds(30),
            environment={
                "WEBSITE_URL": website_url,
                "NAMESPACE": namespace,
            },
        )

        # Allow publishing metrics
        monitor_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={"StringEquals": {"cloudwatch:namespace": namespace}},
            )
        )

        # Schedule (EventBridge)
        rule = events.Rule(
            self, "WebsiteMonitorSchedule",
            schedule=events.Schedule.rate(Duration.minutes(1)),
            description="Run website health check every minute"
        )
        rule.add_target(targets.LambdaFunction(monitor_fn))

        # Metrics
        dims = {"Target": website_url}
        availability = cw.Metric(
            namespace=namespace, metric_name="Availability",
            dimensions_map=dims, period=Duration.minutes(1), statistic="Average",
        )
        latency_p95 = cw.Metric(
            namespace=namespace, metric_name="LatencyMs",
            dimensions_map=dims, period=Duration.minutes(1), statistic="p95",
        )

        # SNS topic
        topic = sns.Topic(self, "WebsiteHealthAlerts")
        if alert_email:
            topic.add_subscription(subs.EmailSubscription(alert_email))
        sns_action = cw_actions.SnsAction(topic)

        # Alarms
        availability_alarm = cw.Alarm(
            self, "AvailabilityLow",
            metric=availability,
            threshold=0.99,
            comparison_operator=cw.ComparisonOperator.LESS_THAN_THRESHOLD,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            treat_missing_data=cw.TreatMissingData.BREACHING,
        )
        latency_alarm = cw.Alarm(
            self, "LatencyP95High",
            metric=latency_p95,
            threshold=800,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
            evaluation_periods=5,
            datapoints_to_alarm=3,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )
        for a in (availability_alarm, latency_alarm):
            a.add_alarm_action(sns_action)
            a.add_ok_action(sns_action)

        # Dashboard
        board = cw.Dashboard(self, "WebsiteHealthDashboard", dashboard_name="WebsiteHealth")
        board.add_widgets(
            cw.TextWidget(
                markdown=f"# Website Health\nTarget: {website_url}\nNamespace: `{namespace}`",
                width=24, height=2
            ),
            cw.GraphWidget(title="Availability", left=[availability], width=12, height=6),
            cw.GraphWidget(title="Latency (p95)", left=[latency_p95], width=12, height=6),
            cw.AlarmWidget(title="Alarms — Availability", alarm=availability_alarm, width=12, height=3),
            cw.AlarmWidget(title="Alarms — Latency", alarm=latency_alarm, width=12, height=3),
        )
