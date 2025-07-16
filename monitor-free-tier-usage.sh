#!/bin/bash

# Free Tier Usage Monitoring Script
# Run this weekly to monitor AWS Free Tier usage

echo "🔍 Academic SaaS - Free Tier Usage Monitor"
echo "=========================================="

# Check EC2 usage
echo "📊 EC2 Usage (750 hours/month free):"
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceType,Value=t3.micro \
  --start-time $(date -d '1 month ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 86400 \
  --statistics Sum \
  --query 'Datapoints[0].Sum'

# Check RDS usage  
echo "📊 RDS Usage (750 hours/month free):"
aws rds describe-db-instances \
  --query 'DBInstances[?DBInstanceClass==`db.t3.micro`].[DBInstanceIdentifier,DBInstanceStatus]' \
  --output table

# Check S3 usage
echo "📊 S3 Usage (5GB storage free):"
aws s3api list-buckets \
  --query 'Buckets[?contains(Name, `academic-saas`)].Name' \
  --output table

for bucket in $(aws s3api list-buckets --query 'Buckets[?contains(Name, `academic-saas`)].Name' --output text); do
  echo "Bucket: $bucket"
  aws s3 ls s3://$bucket --recursive --human-readable --summarize | tail -2
done

# Check current month costs
echo "💰 Current Month Costs:"
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --query 'ResultsByTime[0].Total.BlendedCost.Amount' \
  --output text

echo ""
echo "🎯 Free Tier Limits to Watch:"
echo "- EC2: 750 hours/month (t2.micro or t3.micro)"
echo "- RDS: 750 hours/month (db.t2.micro or db.t3.micro)" 
echo "- S3: 5GB storage, 20K GET, 2K PUT requests"
echo "- CloudFront: 50GB data transfer out"
echo "- ElastiCache: 750 hours/month (cache.t3.micro)"
echo ""
echo "⚠️  Current setup uses ~$35/month (Elastic IPs + NAT Gateway)"
echo "💡 Everything else should be FREE for first 12 months!"