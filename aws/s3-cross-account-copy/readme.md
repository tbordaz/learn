# initiate environment

### references
https://repost.aws/knowledge-center/s3-bucket-access-default-encryption
https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/copy-data-from-an-s3-bucket-to-another-account-and-region-by-using-the-aws-cli.html
https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/copy-data-from-s3-bucket-to-another-account-region-using-s3-batch-replication.html

# create bucket

```bash
export AWS_PROFILE=$SOURCE_ACCOUNT
aws sso login 
aws cloudformation deploy \
  --template-file s3-template.yaml \
  --stack-name sources3 \
  --region $AWS_REGION \
  --parameter-overrides BucketNamePrefix=mysourcebucket

SOURCE_BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name sources3 \
    --region $AWS_REGION \
    --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
    --output text)

SOURCE_BUCKET_KMS_KEY_ARN=$(aws cloudformation describe-stacks \
    --stack-name sources3 \
    --region $AWS_REGION \
    --query "Stacks[0].Outputs[?OutputKey=='KmsKeyArn'].OutputValue" \
    --output text)

python3 generate-sample-files.py 

# upload sample files to source s3
aws s3 cp sample_files/ "s3://$SOURCE_BUCKET_NAME/" --recursive

# Create destination bucket
export AWS_PROFILE=$DESTINATION_ACCOUNT
aws sso login

aws cloudformation deploy \
  --template-file s3-template.yaml \
  --stack-name destinations3 \
  --region $AWS_REGION \
  --parameter-overrides BucketNamePrefix=mydestinationbucket

DEST_BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name destinations3 \
    --region $AWS_REGION \
    --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
    --output text)

DEST_BUCKET_KMS_KEY_ARN=$(aws cloudformation describe-stacks \
    --stack-name destinations3 \
    --region $AWS_REGION \
    --query "Stacks[0].Outputs[?OutputKey=='KmsKeyArn'].OutputValue" \
    --output text)
```

# Create Identity Center Permissions
``` bash
export AWS_PROFILE=$MANAGEMENT_ACCOUNT
aws sso login

# Configure these variables
INSTANCE_ARN="arn:aws:sso:::instance/$ID_CENTER_INSTANCEID"
PERMISSION_SET_NAME="CrossAccountS3WriteAccess"
CROSS_ACCOUNT_ROLE_NAME="CrossAccountS3CopyRole"

PERMISSION_SET_ARN=$(aws sso-admin create-permission-set \
    --instance-arn $INSTANCE_ARN \
    --name $PERMISSION_SET_NAME \
    --output text --query 'PermissionSet.PermissionSetArn')

aws sso-admin put-inline-policy-to-permission-set \
    --instance-arn $INSTANCE_ARN \
    --permission-set-arn $PERMISSION_SET_ARN \
    --inline-policy '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["sts:AssumeRole"],
            "Resource": ["arn:aws:iam::'"$AccountB_ID"':role/'"$CROSS_ACCOUNT_ROLE_NAME"'"]
        }
    ]
}'

echo "Permission set ARN: $PERMISSION_SET_ARN"

# Assign permission set to destination account and admins group
aws sso-admin create-account-assignment \
    --instance-arn $INSTANCE_ARN \
    --target-id $AccountB_ID \
    --target-type AWS_ACCOUNT \
    --permission-set-arn $PERMISSION_SET_ARN \
    --principal-type GROUP \
    --principal-id $ADMINS_GROUP_ID

# Verify assignment
aws sso-admin list-account-assignments \
    --instance-arn $INSTANCE_ARN \
    --account-id $AccountB_ID \
    --permission-set-arn $PERMISSION_SET_ARN \
    --query "AccountAssignments[?PrincipalId=='$ADMINS_GROUP_ID']" \
    --output table

aws sts get-caller-identity
```

# test sign in as user with the new Identity Center permission
``` bash
export AWS_PROFILE=$DEST_CROSS_ACCOUNT
aws sso login 

aws sts get-caller-identity
```

# Create IAM Role for Cross Account Access to the Source Account
# Source Account IAM Role
``` bash
export AWS_PROFILE=$DESTINATION_ACCOUNT
aws sso login 

# Create IAM role with trust policy
aws cloudformation deploy \
  --template-file iam-role-s3-cross-account-template.yaml \
  --stack-name crossAccountS3IamRole \
  --region $AWS_REGION \
  --parameter-overrides \
    IamRoleName=$CROSS_ACCOUNT_ROLE_NAME \
    SourceBucketName=$SOURCE_BUCKET_NAME \
    DestinationBucketName=$DEST_BUCKET_NAME \
    KMSKeyArnSource=$SOURCE_BUCKET_KMS_KEY_ARN \
    KMSKeyArnDestination=$DEST_BUCKET_KMS_KEY_ARN \
  --capabilities CAPABILITY_NAMED_IAM

CROSS_ACCOUNT_ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name crossAccountS3IamRole \
    --region $AWS_REGION \
    --query "Stacks[0].Outputs[?OutputKey=='CrossAccountS3CopyRoleArn'].OutputValue" \
    --output text)

# Check role properties
aws iam get-role --role-name "$CROSS_ACCOUNT_ROLE_NAME"

# Verify attached policies
aws iam list-role-policies --role-name "$CROSS_ACCOUNT_ROLE_NAME"
```

# Perform the cross-account S3 copy
``` bash
export AWS_PROFILE=$DEST_CROSS_ACCOUNT
aws sso login

# Assume the role
CREDENTIALS=$(aws sts assume-role --role-arn "arn:aws:iam::${AccountB_ID}:role/${CROSS_ACCOUNT_ROLE_NAME}" --role-session-name CrossAccountCopy)

aws sts get-caller-identity

export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r .Credentials.AccessKeyId)
export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r .Credentials.SecretAccessKey)
export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r .Credentials.SessionToken)

aws sts get-caller-identity

# Perform the S3 copy
aws s3 cp s3://$SOURCE_BUCKET_NAME s3://$DEST_BUCKET_NAME
```
# Error
You will get error 
```bash
fatal error: An error occurred (AccessDenied) when calling the ListObjectsV2 operation: Access Denied

unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
```
This is because the source account bucket policy needs to be updated to allow the desination account access to the source bucket

# update source account bucket policy and kms permission
```bash
export AWS_PROFILE=$SOURCE_ACCOUNT
aws sso login 

aws cloudformation deploy \
  --template-file s3-source-template-updated-bucket-policy.yaml \
  --stack-name sources3 \
  --region $AWS_REGION \
  --parameter-overrides BucketNamePrefix=mysourcebucket CrossAccountRoleArn=$CROSS_ACCOUNT_ROLE_ARN \
  --capabilities CAPABILITY_NAMED_IAM
```

# Assume cross account role 
```bash
export AWS_PROFILE=$DEST_CROSS_ACCOUNT
aws sso login
aws sts get-caller-identity
# Assume the role
CREDENTIALS=$(aws sts assume-role --role-arn "arn:aws:iam::${AccountB_ID}:role/${CROSS_ACCOUNT_ROLE_NAME}" --role-session-name CrossAccountCopy)

export AWS_ACCESS_KEY_ID=$(echo $CREDENTIALS | jq -r .Credentials.AccessKeyId)
export AWS_SECRET_ACCESS_KEY=$(echo $CREDENTIALS | jq -r .Credentials.SecretAccessKey)
export AWS_SESSION_TOKEN=$(echo $CREDENTIALS | jq -r .Credentials.SessionToken)

aws sts get-caller-identity
# Perform copy using destination role
aws s3 cp s3://$SOURCE_BUCKET_NAME/ s3://$DEST_BUCKET_NAME/ \
    --recursive
```

# Clean up
``` bash
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN

# Permission set
export AWS_PROFILE=$MANAGEMENT_ACCOUNT
aws sso login
# 1. Remove the account assignment
aws sso-admin delete-account-assignment \
    --instance-arn $INSTANCE_ARN \
    --target-id $AccountB_ID \
    --target-type AWS_ACCOUNT \
    --permission-set-arn $PERMISSION_SET_ARN \
    --principal-type GROUP \
    --principal-id $ADMINS_GROUP_ID

# 2. Delete the permission set
aws sso-admin delete-permission-set \
    --instance-arn $INSTANCE_ARN \
    --permission-set-arn $PERMISSION_SET_ARN

# Delete Cross Account S3 Copy IAM role
export AWS_PROFILE=$DESTINATION_ACCOUNT
aws sso login 

aws cloudformation delete-stack --stack-name crossAccountS3IamRole --region $AWS_REGION

# delete s3 buckets
aws cloudformation delete-stack --stack-name destinations3 --region $AWS_REGION

export AWS_PROFILE=$SOURCE_ACCOUNT
aws sso login 
aws s3 rm s3://$SOURCE_BUCKET_NAME --recursive
aws cloudformation delete-stack --stack-name sources3 --region $AWS_REGION
```

