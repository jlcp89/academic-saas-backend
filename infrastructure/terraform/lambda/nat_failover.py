import json
import boto3
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    NAT Instance Failover Handler
    Monitors NAT instances and handles failover scenarios
    """
    
    # Initialize AWS clients
    ec2 = boto3.client('ec2')
    autoscaling = boto3.client('autoscaling')
    cloudwatch = boto3.client('cloudwatch')
    sns = boto3.client('sns')
    
    try:
        project_name = context.aws_request_id.split('-')[0]  # Simplified for demo
        
        # Get all NAT instances
        nat_instances = get_nat_instances(ec2, project_name)
        
        # Check health of each NAT instance
        for instance in nat_instances:
            health_status = check_nat_health(ec2, instance['InstanceId'])
            
            if not health_status['healthy']:
                logger.warning(f"NAT instance {instance['InstanceId']} is unhealthy: {health_status['reason']}")
                
                # Trigger failover
                failover_result = trigger_failover(ec2, autoscaling, instance)
                
                # Send notification
                send_alert(sns, instance, health_status, failover_result)
            else:
                logger.info(f"NAT instance {instance['InstanceId']} is healthy")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'NAT health check completed',
                'timestamp': datetime.utcnow().isoformat(),
                'instances_checked': len(nat_instances)
            })
        }
        
    except Exception as e:
        logger.error(f"Error in NAT failover handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

def get_nat_instances(ec2, project_name):
    """Get all NAT instances for the project"""
    
    response = ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag:Project',
                'Values': [project_name]
            },
            {
                'Name': 'tag:Type',
                'Values': ['NAT', 'NAT-HA']
            },
            {
                'Name': 'instance-state-name',
                'Values': ['running', 'pending']
            }
        ]
    )
    
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances.append(instance)
    
    return instances

def check_nat_health(ec2, instance_id):
    """Check the health of a NAT instance"""
    
    try:
        # Check instance status
        status_response = ec2.describe_instance_status(
            InstanceIds=[instance_id],
            IncludeAllInstances=True
        )
        
        if not status_response['InstanceStatuses']:
            return {
                'healthy': False,
                'reason': 'Instance status not available'
            }
        
        status = status_response['InstanceStatuses'][0]
        
        # Check system status
        if status['SystemStatus']['Status'] != 'ok':
            return {
                'healthy': False,
                'reason': f"System status: {status['SystemStatus']['Status']}"
            }
        
        # Check instance status
        if status['InstanceStatus']['Status'] != 'ok':
            return {
                'healthy': False,
                'reason': f"Instance status: {status['InstanceStatus']['Status']}"
            }
        
        # TODO: Add additional health checks like:
        # - HTTP health check
        # - Network connectivity test
        # - NAT functionality test
        
        return {
            'healthy': True,
            'reason': 'All checks passed'
        }
        
    except Exception as e:
        return {
            'healthy': False,
            'reason': f'Health check failed: {str(e)}'
        }

def trigger_failover(ec2, autoscaling, instance):
    """Trigger failover for unhealthy NAT instance"""
    
    instance_id = instance['InstanceId']
    
    try:
        # Find the Auto Scaling Group for this instance
        asg_response = autoscaling.describe_auto_scaling_instances(
            InstanceIds=[instance_id]
        )
        
        if not asg_response['AutoScalingInstances']:
            return {
                'success': False,
                'message': 'Instance not part of Auto Scaling Group'
            }
        
        asg_name = asg_response['AutoScalingInstances'][0]['AutoScalingGroupName']
        
        # Terminate the unhealthy instance
        # Auto Scaling will automatically launch a replacement
        autoscaling.terminate_instance_in_auto_scaling_group(
            InstanceId=instance_id,
            ShouldDecrementDesiredCapacity=False
        )
        
        logger.info(f"Initiated failover for instance {instance_id} in ASG {asg_name}")
        
        return {
            'success': True,
            'message': f'Failover initiated for {instance_id}',
            'asg_name': asg_name
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger failover for {instance_id}: {str(e)}")
        return {
            'success': False,
            'message': f'Failover failed: {str(e)}'
        }

def send_alert(sns, instance, health_status, failover_result):
    """Send alert notification"""
    
    instance_id = instance['InstanceId']
    
    # Get instance tags for context
    tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
    az = instance.get('Placement', {}).get('AvailabilityZone', 'unknown')
    
    subject = f"NAT Instance Failover Alert - {instance_id}"
    
    message = f"""
NAT Instance Health Alert

Instance Details:
- Instance ID: {instance_id}
- Availability Zone: {az}
- Project: {tags.get('Project', 'unknown')}
- Environment: {tags.get('Environment', 'unknown')}

Health Status:
- Status: UNHEALTHY
- Reason: {health_status['reason']}
- Timestamp: {datetime.utcnow().isoformat()}

Failover Action:
- Success: {failover_result['success']}
- Message: {failover_result['message']}

Next Steps:
1. Monitor the replacement instance launch
2. Verify network connectivity is restored
3. Check application logs for any impact
4. Review CloudWatch metrics for performance

This is an automated alert from the Academic SaaS monitoring system.
"""
    
    try:
        # Get SNS topic ARN (simplified - in real implementation, pass as parameter)
        topic_arn = f"arn:aws:sns:{boto3.Session().region_name}:*:academic-saas-*-alerts"
        
        sns.publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message
        )
        
        logger.info(f"Alert sent for instance {instance_id}")
        
    except Exception as e:
        logger.error(f"Failed to send alert: {str(e)}")

# Additional utility functions can be added here for:
# - EIP management
# - Route table updates
# - Custom health checks
# - Metrics publishing