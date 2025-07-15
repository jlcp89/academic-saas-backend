import json
import boto3
import os
from datetime import datetime, timedelta
from typing import Dict, List

def handler(event, context):
    """
    AWS Lambda function to monitor costs and automatically shutdown
    resources that exceed budget thresholds.
    """
    
    # Initialize AWS clients
    ce_client = boto3.client('ce')  # Cost Explorer
    ec2_client = boto3.client('ec2')
    rds_client = boto3.client('rds')
    elasticache_client = boto3.client('elasticache')
    sns_client = boto3.client('sns')
    
    # Environment variables
    environment = os.environ.get('ENVIRONMENT', 'dev')
    project_name = os.environ.get('PROJECT_NAME', 'academic-saas')
    max_monthly_cost = float(os.environ.get('MAX_MONTHLY_COST', '500'))
    
    # SNS topic ARN for alerts
    sns_topic_arn = f"arn:aws:sns:{boto3.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:{project_name}-{environment}-cost-alerts"
    
    try:
        # Get current month's cost
        current_cost = get_current_month_cost(ce_client, project_name)
        
        # Calculate cost percentage
        cost_percentage = (current_cost / max_monthly_cost) * 100
        
        print(f"Current month cost: ${current_cost:.2f}")
        print(f"Budget limit: ${max_monthly_cost:.2f}")
        print(f"Cost percentage: {cost_percentage:.2f}%")
        
        # Alert thresholds and actions
        if cost_percentage >= 120:  # 120% of budget - Emergency shutdown
            message = f"🚨 EMERGENCY: Cost exceeded 120% of budget (${current_cost:.2f}/${max_monthly_cost:.2f})"
            
            if environment == 'dev':
                # Shutdown all non-critical resources in dev
                shutdown_dev_resources(ec2_client, rds_client, elasticache_client, project_name, environment)
                message += "\n🛑 All development resources have been shut down."
            else:
                # Scale down production resources
                scale_down_production(ec2_client, project_name, environment)
                message += "\n📉 Production resources have been scaled down."
            
            send_alert(sns_client, sns_topic_arn, "CRITICAL COST ALERT", message)
            
        elif cost_percentage >= 100:  # 100% of budget - Critical alert
            message = f"🔥 CRITICAL: Monthly budget exceeded! Current: ${current_cost:.2f}, Budget: ${max_monthly_cost:.2f}"
            
            if environment == 'dev':
                # Stop non-essential dev resources
                stop_dev_resources(ec2_client, rds_client, project_name, environment)
                message += "\n⏸️ Non-essential development resources stopped."
            
            send_alert(sns_client, sns_topic_arn, "BUDGET EXCEEDED", message)
            
        elif cost_percentage >= 90:  # 90% of budget - Warning
            message = f"⚠️ WARNING: Approaching budget limit. Current: ${current_cost:.2f}, Budget: ${max_monthly_cost:.2f} ({cost_percentage:.1f}%)"
            send_alert(sns_client, sns_topic_arn, "BUDGET WARNING", message)
            
        elif cost_percentage >= 80:  # 80% of budget - Info
            message = f"📊 INFO: 80% of monthly budget used. Current: ${current_cost:.2f}, Budget: ${max_monthly_cost:.2f} ({cost_percentage:.1f}%)"
            send_alert(sns_client, sns_topic_arn, "BUDGET INFO", message)
        
        # Check for cost anomalies (sudden spikes)
        check_cost_anomalies(ce_client, sns_client, sns_topic_arn, project_name)
        
        # Generate daily cost report
        generate_cost_report(ce_client, sns_client, sns_topic_arn, project_name)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cost monitoring completed successfully',
                'current_cost': current_cost,
                'budget_limit': max_monthly_cost,
                'cost_percentage': cost_percentage
            })
        }
        
    except Exception as e:
        error_message = f"Error in cost monitoring: {str(e)}"
        print(error_message)
        send_alert(sns_client, sns_topic_arn, "COST MONITORING ERROR", error_message)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_message
            })
        }

def get_current_month_cost(ce_client, project_name: str) -> float:
    """Get current month's cost for the project."""
    
    # Get first day of current month
    today = datetime.now()
    start_date = today.replace(day=1).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='MONTHLY',
        Metrics=['BlendedCost'],
        GroupBy=[
            {
                'Type': 'TAG',
                'Key': 'Project'
            }
        ]
    )
    
    total_cost = 0.0
    for result in response['ResultsByTime']:
        for group in result['Groups']:
            if project_name in group['Keys']:
                total_cost += float(group['Metrics']['BlendedCost']['Amount'])
    
    return total_cost

def shutdown_dev_resources(ec2_client, rds_client, elasticache_client, project_name: str, environment: str):
    """Shutdown all development resources to prevent cost overrun."""
    
    # Stop EC2 instances
    instances = ec2_client.describe_instances(
        Filters=[
            {'Name': 'tag:Project', 'Values': [project_name]},
            {'Name': 'tag:Environment', 'Values': [environment]},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    
    instance_ids = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    if instance_ids:
        ec2_client.stop_instances(InstanceIds=instance_ids)
        print(f"Stopped EC2 instances: {instance_ids}")
    
    # Stop RDS instances
    db_instances = rds_client.describe_db_instances()
    for db in db_instances['DBInstances']:
        tags = rds_client.list_tags_for_resource(ResourceName=db['DBInstanceArn'])['TagList']
        project_tag = next((tag for tag in tags if tag['Key'] == 'Project' and tag['Value'] == project_name), None)
        env_tag = next((tag for tag in tags if tag['Key'] == 'Environment' and tag['Value'] == environment), None)
        
        if project_tag and env_tag and db['DBInstanceStatus'] == 'available':
            rds_client.stop_db_instance(DBInstanceIdentifier=db['DBInstanceIdentifier'])
            print(f"Stopped RDS instance: {db['DBInstanceIdentifier']}")

def stop_dev_resources(ec2_client, rds_client, project_name: str, environment: str):
    """Stop non-essential development resources."""
    
    # Stop instances tagged as 'non-essential'
    instances = ec2_client.describe_instances(
        Filters=[
            {'Name': 'tag:Project', 'Values': [project_name]},
            {'Name': 'tag:Environment', 'Values': [environment]},
            {'Name': 'tag:Essential', 'Values': ['false']},
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    
    instance_ids = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    if instance_ids:
        ec2_client.stop_instances(InstanceIds=instance_ids)
        print(f"Stopped non-essential instances: {instance_ids}")

def scale_down_production(ec2_client, project_name: str, environment: str):
    """Scale down production resources to minimum capacity."""
    
    autoscaling_client = boto3.client('autoscaling')
    
    # Get Auto Scaling Groups
    response = autoscaling_client.describe_auto_scaling_groups()
    
    for asg in response['AutoScalingGroups']:
        tags = {tag['Key']: tag['Value'] for tag in asg['Tags']}
        
        if tags.get('Project') == project_name and tags.get('Environment') == environment:
            # Scale down to minimum capacity
            autoscaling_client.update_auto_scaling_group(
                AutoScalingGroupName=asg['AutoScalingGroupName'],
                DesiredCapacity=asg['MinSize']
            )
            print(f"Scaled down ASG {asg['AutoScalingGroupName']} to minimum capacity: {asg['MinSize']}")

def check_cost_anomalies(ce_client, sns_client, sns_topic_arn: str, project_name: str):
    """Check for unusual cost spikes in the last 7 days."""
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date.strftime('%Y-%m-%d'),
            'End': end_date.strftime('%Y-%m-%d')
        },
        Granularity='DAILY',
        Metrics=['BlendedCost'],
        GroupBy=[
            {
                'Type': 'SERVICE',
                'Key': 'SERVICE'
            }
        ]
    )
    
    # Analyze daily costs for anomalies
    daily_costs = []
    for result in response['ResultsByTime']:
        daily_cost = sum(float(group['Metrics']['BlendedCost']['Amount']) for group in result['Groups'])
        daily_costs.append(daily_cost)
    
    if len(daily_costs) >= 3:
        avg_cost = sum(daily_costs[:-1]) / len(daily_costs[:-1])
        latest_cost = daily_costs[-1]
        
        # If latest day cost is 200% higher than average, it's an anomaly
        if latest_cost > avg_cost * 2:
            message = f"🚨 COST ANOMALY DETECTED!\nLatest daily cost: ${latest_cost:.2f}\nAverage daily cost: ${avg_cost:.2f}\nIncrease: {((latest_cost/avg_cost-1)*100):.1f}%"
            send_alert(sns_client, sns_topic_arn, "COST ANOMALY", message)

def generate_cost_report(ce_client, sns_client, sns_topic_arn: str, project_name: str):
    """Generate and send daily cost report."""
    
    # Get yesterday's cost breakdown by service
    yesterday = datetime.now() - timedelta(days=1)
    start_date = yesterday.strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    response = ce_client.get_cost_and_usage(
        TimePeriod={
            'Start': start_date,
            'End': end_date
        },
        Granularity='DAILY',
        Metrics=['BlendedCost'],
        GroupBy=[
            {
                'Type': 'SERVICE',
                'Key': 'SERVICE'
            }
        ]
    )
    
    if response['ResultsByTime']:
        services_cost = {}
        total_cost = 0
        
        for group in response['ResultsByTime'][0]['Groups']:
            service = group['Keys'][0]
            cost = float(group['Metrics']['BlendedCost']['Amount'])
            services_cost[service] = cost
            total_cost += cost
        
        # Sort services by cost (descending)
        sorted_services = sorted(services_cost.items(), key=lambda x: x[1], reverse=True)
        
        report = f"📊 Daily Cost Report - {yesterday.strftime('%Y-%m-%d')}\n"
        report += f"Total Cost: ${total_cost:.2f}\n\n"
        report += "Top Services:\n"
        
        for service, cost in sorted_services[:5]:  # Top 5 services
            if cost > 0:
                percentage = (cost / total_cost) * 100
                report += f"• {service}: ${cost:.2f} ({percentage:.1f}%)\n"
        
        send_alert(sns_client, sns_topic_arn, "Daily Cost Report", report)

def send_alert(sns_client, topic_arn: str, subject: str, message: str):
    """Send alert to SNS topic."""
    
    try:
        sns_client.publish(
            TopicArn=topic_arn,
            Subject=f"[Academic SaaS] {subject}",
            Message=message
        )
        print(f"Alert sent: {subject}")
    except Exception as e:
        print(f"Failed to send alert: {str(e)}")