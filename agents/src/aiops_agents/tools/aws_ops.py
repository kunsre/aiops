import json
import subprocess

from langchain_core.tools import tool


@tool
def aws_cli(service: str, command: str, args: str = "", region: str = "ap-northeast-2") -> str:
    """Execute an AWS CLI command for infrastructure diagnostics.

    Args:
        service: AWS service (e.g., 'ec2', 'rds', 'ecs', 'cloudwatch', 'elbv2', 'autoscaling')
        command: CLI subcommand (e.g., 'describe-instances', 'get-metric-statistics')
        args: Additional arguments as a string (e.g., '--instance-ids i-abc123')
        region: AWS region

    Returns:
        JSON output from AWS CLI.
    """
    cmd = ["aws", service, command, "--region", region, "--output", "json"]
    if args:
        cmd.extend(args.split())

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def aws_cloudwatch_get_metric(
    namespace: str,
    metric_name: str,
    dimensions: str,
    period: int = 300,
    stat: str = "Average",
    minutes_back: int = 30,
) -> str:
    """Get CloudWatch metric data for AWS resource diagnostics.

    Args:
        namespace: CloudWatch namespace (e.g., 'AWS/EC2', 'AWS/RDS', 'AWS/ELB', 'ContainerInsights')
        metric_name: Metric name (e.g., 'CPUUtilization', 'DatabaseConnections', 'MemoryUtilization')
        dimensions: JSON string of dimensions (e.g., '[{"Name":"ClusterName","Value":"aiops-dev"}]')
        period: Data point period in seconds
        stat: Statistic type ('Average', 'Maximum', 'Sum', 'p99')
        minutes_back: How many minutes of data to retrieve

    Returns:
        Metric datapoints as JSON.
    """
    import datetime

    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(minutes=minutes_back)

    cmd = [
        "aws", "cloudwatch", "get-metric-statistics",
        "--namespace", namespace,
        "--metric-name", metric_name,
        "--dimensions", dimensions,
        "--start-time", start.isoformat() + "Z",
        "--end-time", end.isoformat() + "Z",
        "--period", str(period),
        "--statistics", stat,
        "--output", "json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def aws_describe_alarms(alarm_prefix: str = "", state: str = "ALARM") -> str:
    """List CloudWatch alarms, optionally filtered by prefix and state.

    Args:
        alarm_prefix: Filter alarms by name prefix
        state: Alarm state filter ('ALARM', 'OK', 'INSUFFICIENT_DATA')

    Returns:
        List of matching alarms with their details.
    """
    cmd = ["aws", "cloudwatch", "describe-alarms", "--state-value", state, "--output", "json"]
    if alarm_prefix:
        cmd.extend(["--alarm-name-prefix", alarm_prefix])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@tool
def aws_describe_ec2_instances(filters: str = "") -> str:
    """Describe EC2 instances (EKS worker nodes, etc).

    Args:
        filters: Optional JSON filters (e.g., '[{"Name":"tag:kubernetes.io/cluster/aiops-dev","Values":["owned"]}]')

    Returns:
        Instance details including state, type, IPs.
    """
    cmd = ["aws", "ec2", "describe-instances", "--output", "json"]
    if filters:
        cmd.extend(["--filters", filters])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout
