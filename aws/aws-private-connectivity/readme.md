# AWS Private Connectivity Demo

This project demonstrates AWS private connectivity concepts using AWS Lambda and API Gateway. It shows the difference between public and private connectivity patterns for enterprise applications with a simple web application.

## Architecture Overview

This demo can be deployed in two modes:

### 1. Public Mode
- Lambda function with default public networking
- Both inbound and outbound traffic flow through the public internet
- Demonstrates the default connectivity pattern

### 2. Private Mode
- Dedicated VPC with isolated subnets
- Private API Gateway with VPC endpoint
- Lambda function deployed in private subnet
- NAT Gateway for controlled outbound access
- Test EC2 instance in private subnet
- Demonstrates enterprise private connectivity pattern

## Prerequisites

1. **AWS CLI** installed and configured with appropriate permissions
   ```bash
   aws configure
   ```

2. **AWS Session Manager plugin** installed (for connecting to EC2 instances)
   ```bash
   # For macOS
   curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip" -o "sessionmanager-bundle.zip"
   unzip sessionmanager-bundle.zip
   sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin
   
   # For Windows
   # Download from: https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe
   # Run the installer
   
   # For Linux
   curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm" -o "session-manager-plugin.rpm"
   sudo yum install -y session-manager-plugin.rpm
   ```

3. **Basic Understanding** of AWS services:
   - VPC and networking concepts
   - Lambda functions
   - API Gateway
   - IAM roles and permissions
   - CloudFormation

## Deployment Guide

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd aws-private-connectivity
```

### Step 2: Make the Deployment Script Executable

```bash
chmod +x deploy-lambda.sh
```

### Step 3: Deploy in Public Mode

This step deploys the application with public inbound and outbound connectivity:

```bash
./deploy-lambda.sh PUBLIC
```

The deployment process:
1. Creates an S3 bucket to store your application code
2. Packages your Lambda function code
3. Creates a Lambda function and API Gateway endpoint
4. Outputs the API URL

Deployment takes approximately 3-5 minutes. When complete, you'll see:
```
=== Deployment Complete ===
Deployment Mode: PUBLIC
API URL: https://xxxxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/
```

### Step 4: Test Public Connectivity

1. Open the API URL in your browser
2. The homepage shows your inbound connection information
3. Click "Check My Outbound IP" to make an outbound request
4. Note the IP address - this is the public IP used by AWS Lambda

### Step 5: Deploy in Private Mode

Now redeploy the application with private connectivity:

```bash
./deploy-lambda.sh PRIVATE
```

This deployment:
1. Creates a dedicated VPC with public and private subnets
2. Deploys NAT Gateway in public subnet
3. Creates VPC endpoints for API Gateway and Lambda
4. Deploys test EC2 instance in private subnet
5. Configures private API Gateway with VPC endpoint
6. Deploys Lambda function in private subnet

When complete, you'll see:
```
=== Deployment Complete ===
Deployment Mode: PRIVATE
API URL: https://xxxxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/

=== Private Mode Details ===
Test Instance ID: i-xxxxxxxxxxxxxxxxx
VPC ID: vpc-xxxxxxxxxxxxxxxxx
Private Subnet ID: subnet-xxxxxxxxxxxxxxxxx
```

### Step 6: Test Private Connectivity

1. **Test Public Access**
   - Try accessing the API URL from your browser
   - You should receive an access denied error
   - This confirms the API is not publicly accessible

2. **Test Private Access**
   ```bash
   # Connect to the test instance using Session Manager
   aws ssm start-session --target $TEST_INSTANCE_ID
   
   # From the Session Manager terminal, test API access
   curl $API_URL
   curl $API_URL/getmyip
   ```
   - The API should be accessible from within the VPC
   - The outbound IP will be your NAT Gateway's IP
   - This demonstrates private connectivity

## Understanding the Infrastructure

### Network Architecture (Private Mode)

1. **VPC and Subnets**
   - VPC CIDR: 10.0.0.0/16
   - Public Subnet: 10.0.1.0/24 (NAT Gateway)
   - Private Subnet: 10.0.2.0/24 (Lambda, Test Instance)

2. **Internet Connectivity**
   - Public subnet: Internet Gateway
   - Private subnet: NAT Gateway
   - Security groups with least privilege access

3. **Private Service Access**
   - VPC endpoints for API Gateway and Lambda
   - Private API Gateway with resource policy
   - Lambda function in VPC

4. **Test Environment**
   - EC2 instance in private subnet
   - Session Manager for secure access
   - IAM roles with least privilege

### Security Controls

1. **Network Security**
   - Security groups with minimal access
   - VPC endpoints for AWS services
   - NAT Gateway for outbound control

2. **Access Control**
   - IAM roles with least privilege
   - Resource policies for service access
   - Session Manager for instance access

3. **Monitoring**
   - CloudWatch Logs for Lambda
   - VPC Flow Logs for network traffic
   - CloudTrail for API activity

## Troubleshooting

### Common Issues:

1. **Deployment Failures**
   - Check CloudFormation stack events
   - Verify IAM permissions
   - Review Lambda function logs

2. **Connectivity Issues**
   - Verify VPC endpoint status
   - Check security group rules
   - Test NAT Gateway connectivity

3. **Session Manager Issues**
   - Verify IAM role permissions
   - Check SSM agent status
   - Review security group rules

### Debugging Commands:

```bash
# Check CloudFormation stack status
aws cloudformation describe-stacks --stack-name private-connectivity-demo

# Check Lambda function configuration
aws lambda get-function --function-name connectivity-demo-${AWS_ACCOUNT_ID}

# View Lambda logs
aws logs describe-log-streams \
  --log-group-name /aws/lambda/connectivity-demo-${AWS_ACCOUNT_ID} \
  --order-by LastEventTime \
  --descending \
  --limit 1

# Check VPC endpoint status
aws ec2 describe-vpc-endpoints --filters "Name=vpc-id,Values=${VPC_ID}"

# Check NAT Gateway status
aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=${VPC_ID}"
```

## Cleaning Up

To avoid ongoing charges, clean up all resources:

```bash
# Delete the CloudFormation stack
aws cloudformation delete-stack --stack-name private-connectivity-demo

# Wait for stack deletion to complete
aws cloudformation wait stack-delete-complete --stack-name private-connectivity-demo

# Delete the S3 bucket
aws s3 rm s3://lambda-demo-${AWS_ACCOUNT_ID}-${AWS_REGION} --recursive
aws s3api delete-bucket --bucket lambda-demo-${AWS_ACCOUNT_ID}-${AWS_REGION}
```

## Cost Considerations

- **Lambda**: Extremely low cost, practically free for this demo with AWS Free Tier
- **API Gateway**: Minimal cost under normal usage patterns
- **S3 Storage**: Negligible storage costs
- **VPC Components**:
  - NAT Gateway (~$30-35/month)
  - VPC endpoints (priced per hour and per GB)
  - EC2 instance (t3.micro ~$8-10/month)

To minimize costs:
1. Clean up resources when not in use
2. Consider using AWS Free Tier accounts for the demo
3. Use private mode only when needed for demonstrations

## Enterprise Considerations

In a real enterprise environment, you would typically add:

1. **Network Infrastructure**
   - Transit Gateway for VPC connectivity
   - Direct Connect for on-premises access
   - Network Firewall for traffic inspection
   - Multiple VPCs for different environments

2. **Security Controls**
   - AWS WAF for application protection
   - AWS Shield for DDoS protection
   - Security Hub for compliance monitoring
   - GuardDuty for threat detection

3. **Access Management**
   - AWS SSO for user authentication
   - IAM roles with least privilege
   - Resource policies for service access
   - Private hosted zones for DNS

4. **Compliance and Governance**
   - AWS Config for resource compliance
   - CloudTrail for audit logging
   - AWS Organizations for multi-account management
   - Service Control Policies for guardrails 