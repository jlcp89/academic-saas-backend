import json
import boto3
import os
from datetime import datetime

ec2 = boto3.client('ec2')
asg = boto3.client('autoscaling')

def handler(event, context):
    """
    Lambda function to optimize spot instance pricing
    by checking current spot prices and recommending instance types
    """
    
    # Get environment configuration
    project_name = os.environ.get('PROJECT_NAME', 'academic-saas')
    environment = os.environ.get('ENVIRONMENT', 'dev')
    
    try:
        # Get current spot price history
        response = ec2.describe_spot_price_history(
            InstanceTypes=['t3.micro', 't3.small', 't3.medium'],
            MaxResults=20,
            ProductDescriptions=['Linux/UNIX'],
            StartTime=datetime.utcnow()
        )
        
        # Find the cheapest instance type
        prices = {}
        for price in response['SpotPriceHistory']:
            instance_type = price['InstanceType']
            spot_price = float(price['SpotPrice'])
            
            if instance_type not in prices or spot_price < prices[instance_type]:
                prices[instance_type] = spot_price
        
        # Get the cheapest instance type
        if prices:
            cheapest = min(prices, key=prices.get)
            print(f"Cheapest spot instance: {cheapest} at ${prices[cheapest]}/hour")
            
            # You can implement logic here to update ASG configurations
            # based on spot pricing trends
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Spot price optimization completed',
                'prices': prices,
                'recommendation': cheapest if prices else None
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error optimizing spot prices',
                'error': str(e)
            })
        }