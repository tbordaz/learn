# initiate environment

### references
https://repost.aws/knowledge-center/s3-bucket-access-default-encryption
https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/copy-data-from-s3-bucket-to-another-account-region-using-s3-batch-replication.html

# create bucket

```bash
export AWS_PROFILE=$SOURCE_ACCOUNT
aws sso login # source bucket account

aws cloudformation deploy \
  --template-file s3-template.yaml \
  --stack-name sources3 \
  --region ap-southeast-2 \
  --parameter-overrides BucketNamePrefix=mysourcebucket

SOURCE_BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name sources3 \
    --region ap-southeast-2 \
    --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
    --output text)

python3 generate-sample-files.py 

# upload sample files to source s3
aws s3 cp sample_files/ "s3://$SOURCE_BUCKET_NAME/" --recursive

####
export AWS_PROFILE=$DESTINATION_ACCOUNT
aws sso login # destination bucket account

aws cloudformation deploy \
  --template-file s3-template.yaml \
  --stack-name destinations3 \
  --region ap-southeast-2 \
  --parameter-overrides BucketNamePrefix=mydestinationbucket

DEST_BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name destinations3 \
    --region ap-southeast-2 \
    --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" \
    --output text)
```

# Create IAM Role for Cross Account Access
# Source Account IAM Role
``` bash
export AWS_PROFILE=$SOURCE_ACCOUNT
aws sso login # source bucket account

# Configure these variables before execution
ROLE_NAME="CrossAccountS3AccessRole"

# Create IAM role with trust policy
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document "$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::${AccountB_ID}:root"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
)"

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "S3BucketAccessPolicy" \
  --policy-document "$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::${SOURCE_BUCKET_NAME}",
                "arn:aws:s3:::${SOURCE_BUCKET_NAME}/*"
            ]
        }
    ]
}
EOF
)"

# Check role properties
aws iam get-role --role-name "$ROLE_NAME"

# Verify attached policies
aws iam list-role-policies --role-name "$ROLE_NAME"

```

# Create Identity Center Permissions
``` bash
export AWS_PROFILE=$MASTER_ACCOUNT
aws sso login # master account

# Configure these variables
INSTANCE_ARN="arn:aws:sso:::instance/$ID_CENTER_INSTANCEID"
PERMISSION_SET_NAME="CrossAccountS3WriteAccess"

# Create JSON policy document
POLICY_DOC=$(jq -n --arg bucket "$DEST_BUCKET_NAME" --arg account "$AccountA_ID" --arg rolename "$ROLE_NAME" '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": ["sts:AssumeRole"],
            "Resource": ["arn:aws:iam::\($account):role/\($rolename)"]
        },
        {
            "Effect": "Allow",
            "Action": ["s3:PutObject"],
            "Resource": ["arn:aws:s3:::\($bucket)/*"]
        }
    ]
}')

# Create permission set
PERMISSION_SET_ARN=$(aws sso-admin create-permission-set \
    --instance-arn $INSTANCE_ARN \
    --name $PERMISSION_SET_NAME \
    --output text --query 'PermissionSet.PermissionSetArn')

# Attach inline policy
aws sso-admin put-inline-policy-to-permission-set \
    --instance-arn $INSTANCE_ARN \
    --permission-set-arn $PERMISSION_SET_ARN \
    --inline-policy "$POLICY_DOC"

echo "Permission set ARN: $PERMISSION_SET_ARN"

    # Assign to users/groups (example for group)
GROUP_ID=$ADMINS_GROUP_ID  # From Identity Center groups list
aws sso-admin create-account-assignment \
    --instance-arn $INSTANCE_ARN \
    --target-id $AccountA_ID \
    --target-type AWS_ACCOUNT \
    --permission-set-arn $PERMISSION_SET_ARN \
    --principal-type GROUP \
    --principal-id $GROUP_ID

# verify 
aws sso-admin list-account-assignments \
    --instance-arn $INSTANCE_ARN \
    --account-id $AccountA_ID \
    --permission-set-arn $PERMISSION_SET_ARN \
    --query "AccountAssignments[?PrincipalId=='$GROUP_ID']" \
    --output table

aws sts get-caller-identity
```