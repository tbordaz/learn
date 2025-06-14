# AWS Zero Trust Demo

This repository contains the complete setup for the YouTube video Securing your resources in AWS https://youtu.be/KNCpiYYCaOU. Follow along to build a hands-on Zero Trust architecture demonstrating AWS authorisation layers.

## What You'll Learn

- How AWS authorisation differs from Azure RBAC
- IAM policies vs resource policies vs VPC endpoint policies
- Gateway endpoints vs Interface endpoints
- Zero Trust architecture implementation
- S3 access logging and analysis with Athena

## Cost Estimate

**Approximately $0.11 per hour** to run this demo:
- 3 x t3.micro instances: $0.03/hour
- 4 x Interface endpoints (2 AZs): $0.08/hour  
- S3 Gateway endpoint: Free
- S3 storage/requests: ~$0.01/hour

**Remember to run `terraform destroy` when finished to avoid ongoing charges!**

## Prerequisites

### Required Tools
- [Terraform](https://www.terraform.io/downloads) (>= 1.2.0)
- [AWS CLI](https://aws.amazon.com/cli/) (configured with credentials)

### AWS Requirements
- Admin permissions (or sufficient permissions to create IAM roles, VPC endpoints, EC2 instances, S3 buckets)
- Access to AWS Systems Manager Session Manager (for connecting to instances)

### AWS Profile Setup
Configure your AWS CLI with appropriate credentials:
```bash
aws configure
# OR if using SSO:
aws sso login --profile your-profile-name
export AWS_PROFILE=your-profile-name
```

## Setup

### 1. Clone and Configure
```bash
git clone <your-repo-url>
cd aws-zerotrust-demo

# Set your preferred AWS region
export AWS_DEFAULT_REGION=us-east-1  # Change to your preferred region
```

### 2. Deploy Infrastructure
```bash
terraform init
terraform plan -out=myplan.tfplan
terraform apply myplan.tfplan
```

### 3. Store Output Variables
```bash
# Store Terraform outputs for easy reference
DEMO_BUCKET_NAME=$(terraform output -raw demo_bucket_name)
LOGGING_BUCKET_NAME=$(terraform output -raw logging_bucket_name)
PUBLIC_INSTANCE_ID=$(terraform output -raw public_instance_id)
PRIVATE_INSTANCE_A_ID=$(terraform output -raw private_instance_a_id)
PRIVATE_INSTANCE_B_ID=$(terraform output -raw private_instance_b_id)
S3_VPC_ENDPOINT_ID=$(terraform output -raw s3_vpc_endpoint_id)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Demo Bucket: $DEMO_BUCKET_NAME"
echo "Public Instance: $PUBLIC_INSTANCE_ID"
echo "Private Instance A: $PRIVATE_INSTANCE_A_ID"
echo "Private Instance B: $PRIVATE_INSTANCE_B_ID"
```

## Stage 1: Baseline Security (IAM Only)

In this stage, we test basic IAM-based access to S3.

### Test from Your Local Machine
```bash
# Verify your identity
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://$DEMO_BUCKET_NAME
echo "Test from local machine" > test-local.txt
aws s3 cp test-local.txt s3://$DEMO_BUCKET_NAME/
```

### Test from Public EC2 Instance
Connect to the public instance using [AWS Systems Manager Session Manager](https://console.aws.amazon.com/systems-manager/session-manager/):
1. Go to Systems Manager > Session Manager in AWS Console
2. Click "Start session"
3. Select the public instance
4. Click "Start session"

**Run these commands in the public instance terminal:**
```bash
# Verify instance identity
aws sts get-caller-identity

# Test S3 access
cd /tmp
echo "This is from the stage 1 public instance!" > test-stage1-public.txt
aws s3 cp test-stage1-public.txt s3://REPLACE_WITH_YOUR_BUCKET_NAME
```
Replace `REPLACE_WITH_YOUR_BUCKET_NAME` with your actual bucket name from the terraform output.

**Expected Result:** Both tests should succeed - anyone with IAM permissions can access S3 from anywhere.

## Stage 2: Network Restrictions (IAM + VPC Endpoint)

Now we add network-based access control using S3 bucket policies.

### Apply Network Restriction Policy

**Run from your local machine:**
```bash
# Get your current user/role information for the policy exception
# Note: This works for both IAM users and assumed roles (including SSO)
CURRENT_USER_ARN=$(aws sts get-caller-identity --query 'Arn' --output text)
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

# For assumed roles, extract the role ARN
if [[ $CURRENT_USER_ARN == *"assumed-role"* ]]; then
    ROLE_NAME=$(echo $CURRENT_USER_ARN | cut -d'/' -f2)
    ADMIN_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
else
    # For IAM users, use the user ARN directly
    ADMIN_ROLE_ARN=$CURRENT_USER_ARN
fi

echo "Using admin ARN: $ADMIN_ROLE_ARN"

# Apply bucket policy that restricts access to VPC endpoint only
aws s3api put-bucket-policy --bucket $DEMO_BUCKET_NAME --policy "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAdminFromAnywhere",
      "Effect": "Allow",
      "Principal": {
        "AWS": "${ADMIN_ROLE_ARN}"
      },
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${DEMO_BUCKET_NAME}",
        "arn:aws:s3:::${DEMO_BUCKET_NAME}/*"
      ]
    },
    {
      "Sid": "DenyAllOtherAccessFromInternet",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${DEMO_BUCKET_NAME}",
        "arn:aws:s3:::${DEMO_BUCKET_NAME}/*"
      ],
      "Condition": {
        "StringNotEquals": {
          "aws:sourceVpce": "${S3_VPC_ENDPOINT_ID}"
        },
        "StringNotLike": {
          "aws:userid": "*:*"
        }
      }
    }
  ]
}
EOF
)"

echo "Stage 2 bucket policy applied!"
```

### Test Network Restrictions

**Test from Public Instance (Should FAIL):**
```bash
cd /tmp
echo "This is from the stage 2 public instance!" > test-stage2-public.txt
aws s3 cp test-stage2-public.txt s3://REPLACE_WITH_YOUR_BUCKET_NAME
```
**Expected Result:** Access Denied - public instance can't reach S3 through internet

**Test from Private Instance A (Should SUCCEED):**
Connect to Private Instance A via Session Manager, then run:
```bash
cd /tmp
echo "This is from the stage 2 private instance!" > test-stage2-private.txt
aws s3 cp test-stage2-private.txt s3://REPLACE_WITH_YOUR_BUCKET_NAME
```
**Expected Result:** Success - private instance uses VPC endpoint

**Test from Your Local Machine (Should SUCCEED):**
```bash
echo "Stage 2 test from local machine" > test-stage2-local.txt
aws s3 cp test-stage2-local.txt s3://$DEMO_BUCKET_NAME/
```
**Expected Result:** Success - your admin role is explicitly allowed

## Stage 3: Zero Trust (Identity + Network)

Final stage adds identity restrictions on top of network restrictions.

### Apply Zero Trust Policy

**Run from your local machine:**
```bash
# Get the restricted role info
RESTRICTED_ROLE_ARN=$(terraform output -raw private_instance_a_role_arn)

echo "Applying Zero Trust policy..."
echo "Admin ARN: $ADMIN_ROLE_ARN"
echo "Allowed Role ARN: $RESTRICTED_ROLE_ARN"

# Apply the zero trust bucket policy
aws s3api put-bucket-policy --bucket $DEMO_BUCKET_NAME --policy "$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAdminFromAnywhere",
      "Effect": "Allow",
      "Principal": {
        "AWS": "${ADMIN_ROLE_ARN}"
      },
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${DEMO_BUCKET_NAME}",
        "arn:aws:s3:::${DEMO_BUCKET_NAME}/*"
      ]
    },
    {
      "Sid": "AllowRoleAOnlyFromVPCEndpoint",
      "Effect": "Allow",
      "Principal": {
        "AWS": "${RESTRICTED_ROLE_ARN}"
      },
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${DEMO_BUCKET_NAME}",
        "arn:aws:s3:::${DEMO_BUCKET_NAME}/*"
      ],
      "Condition": {
        "StringEquals": {
          "aws:sourceVpce": "${S3_VPC_ENDPOINT_ID}"
        }
      }
    },
    {
      "Sid": "DenyAllOtherAccess",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::${DEMO_BUCKET_NAME}",
        "arn:aws:s3:::${DEMO_BUCKET_NAME}/*"
      ],
      "Condition": {
        "Bool": {
          "aws:ViaAWSService": "false"
        },
        "StringNotEquals": {
          "aws:PrincipalArn": [
            "${ADMIN_ROLE_ARN}",
            "${RESTRICTED_ROLE_ARN}"
          ]
        }
      }
    }
  ]
}
EOF
)"

echo "Zero Trust policy applied!"
```

### Test Zero Trust Access

**Test from Private Instance A (Should SUCCEED):**
```bash
cd /tmp
echo "This is from private instance A in stage 3!" > test-stage3-private-A.txt
aws s3 cp test-stage3-private-A.txt s3://REPLACE_WITH_YOUR_BUCKET_NAME
```
**Expected Result:** Success - Instance A has the specific allowed identity

**Test from Private Instance B (Should FAIL):**
```bash
cd /tmp
echo "This is from private instance B in stage 3!" > test-stage3-private-B.txt
aws s3 cp test-stage3-private-B.txt s3://REPLACE_WITH_YOUR_BUCKET_NAME
```
**Expected Result:** Access Denied - Instance B doesn't have the allowed identity

## S3 Access Logging with Athena

This demo includes S3 access logging configuration. To analyze the logs:

1. **Wait for logs**: S3 access logs are delivered on a best-effort basis. Most log records are delivered within a few hours of the time they are recorded, though they can be delivered more frequently.

2. **Set up Athena**: Follow the [AWS S3 Server Access Logging guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html) to configure Athena for log analysis

3. **Query examples**:
   ```sql
   SELECT 
       requestdatetime,
       remoteip,
       requester,
       operation,
       key,
       httpstatus,
       errorcode
   FROM s3_access_logs_db.mybucket_logs
   WHERE httpstatus = '403'  -- See all denied requests
   ORDER BY requestdatetime DESC;
   ```

The logging bucket name is available in terraform output: `terraform output logging_bucket_name`

## Cleanup

**Important: Always clean up to avoid ongoing charges!**

```bash
terraform destroy -auto-approve
```

## Key Concepts Demonstrated

1. **IAM Policies**: What identities can do
2. **Resource Policies**: What can be done to resources  
3. **VPC Endpoints**: Private network paths to AWS services
4. **Zero Trust**: Verify both identity AND network path
5. **Gateway vs Interface Endpoints**: Cost vs functionality tradeoffs
6. **S3 Access Logging**: Complete audit trail of access attempts

## Useful Links

- [AWS S3 Server Access Logging](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html)
- [VPC Endpoints Documentation](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-endpoints.html)
- [S3 Bucket Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html)
- [Zero Trust Architecture on AWS](https://aws.amazon.com/security/zero-trust/)

## Troubleshooting

- **Access Denied errors**: Check both IAM permissions AND bucket policy
- **Session Manager won't connect**: Ensure SSM endpoints are created and security groups allow HTTPS
- **Terraform errors**: Ensure your AWS credentials have sufficient permissions
- **Wrong region**: Make sure `AWS_DEFAULT_REGION` matches your terraform deployment
