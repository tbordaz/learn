terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {}

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
  default     = "zerotrust-demo"
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

#####################################
# STAGE 1: PUBLIC INSTANCE (BASELINE)
#####################################

resource "aws_s3_bucket" "demo_bucket" {
  bucket = "${var.project_name}-bucket-${random_string.suffix.result}"
  tags = {
    Name = "Zero Trust Demo Bucket"
  }
}

resource "aws_iam_role" "public_instance_role" {
  name = "${var.project_name}-public-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "basic_s3_access" {
  name = "${var.project_name}-basic-s3-access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.demo_bucket.arn,
        "${aws_s3_bucket.demo_bucket.arn}/*"
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "public_s3_policy" {
  role       = aws_iam_role.public_instance_role.name
  policy_arn = aws_iam_policy.basic_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "public_ssm_policy" {
  role       = aws_iam_role.public_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "public_profile" {
  name = "${var.project_name}-public-profile"
  role = aws_iam_role.public_instance_role.name
}

resource "aws_security_group" "public_sg" {
  name_prefix = "${var.project_name}-public-"
  vpc_id      = data.aws_vpc.default.id
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS for SSM endpoints"
  }
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS"
  }
  tags = { Name = "Public Instance SG" }
}

resource "aws_instance" "public_instance" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = "t3.micro"
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.public_sg.id]
  iam_instance_profile        = aws_iam_instance_profile.public_profile.name
  associate_public_ip_address = true
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    bucket_name = aws_s3_bucket.demo_bucket.bucket
    stage       = "PUBLIC"
  }))
  tags = { Name = "Stage 1 - Public Instance" }
}

resource "aws_s3_bucket" "logging_bucket" {
  bucket = "${var.project_name}-logs-${random_string.suffix.result}"
  tags = { Name = "Zero Trust Demo Logging Bucket" }
}

resource "aws_s3_bucket_logging" "demo_bucket_logging" {
  bucket        = aws_s3_bucket.demo_bucket.id
  target_bucket = aws_s3_bucket.logging_bucket.id
  target_prefix = ""
}

resource "aws_s3_bucket_policy" "logging_bucket_policy" {
  bucket = aws_s3_bucket.logging_bucket.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowS3Logging"
      Effect = "Allow"
      Principal = { Service = "logging.s3.amazonaws.com" }
      Action = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.logging_bucket.arn}/*"
      Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id } }
    }]
  })
}

#####################################
# STAGE 2: PRIVATE VPC + VPC ENDPOINTS
#####################################

resource "aws_vpc" "private_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "Private VPC" }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "private_subnet" {
  vpc_id            = aws_vpc.private_vpc.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags = { Name = "Private Subnet" }
}

# Security group for private instances
resource "aws_security_group" "private_sg" {
  name_prefix = "${var.project_name}-private-"
  vpc_id      = aws_vpc.private_vpc.id
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS for SSM and S3 endpoints"
  }
  egress {
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "DNS"
  }
  tags = { Name = "Private Instance SG" }
}

# Security group for VPC Interface Endpoints
resource "aws_security_group" "vpc_endpoint_sg" {
  name_prefix = "${var.project_name}-endpoint-"
  vpc_id      = aws_vpc.private_vpc.id
  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.private_sg.id]
    description     = "HTTPS from private instances"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }
  tags = { Name = "VPC Endpoint SG" }
}

# Gateway Endpoint for S3
resource "aws_vpc_endpoint" "s3_gateway" {
  vpc_id            = aws_vpc.private_vpc.id
  service_name      = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_route_table.id]
  tags = { Name = "S3 Gateway Endpoint" }
}

# Route Table for Private Subnet
resource "aws_route_table" "private_route_table" {
  vpc_id = aws_vpc.private_vpc.id
  tags = { Name = "Private Route Table" }
}

# Associate Private Subnet with Route Table
resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private_subnet.id
  route_table_id = aws_route_table.private_route_table.id
}

# SSM, SSM Messages, EC2 Messages, sts Interface Endpoints
resource "aws_vpc_endpoint" "ssm" {
  vpc_id              = aws_vpc.private_vpc.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ssm"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_subnet.id]
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]
  private_dns_enabled = true
  tags = { Name = "SSM Endpoint" }
}

resource "aws_vpc_endpoint" "ssm_messages" {
  vpc_id              = aws_vpc.private_vpc.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ssmmessages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_subnet.id]
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]
  private_dns_enabled = true
  tags = { Name = "SSM Messages Endpoint" }
}

resource "aws_vpc_endpoint" "ec2_messages" {
  vpc_id              = aws_vpc.private_vpc.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.ec2messages"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_subnet.id]
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]
  private_dns_enabled = true
  tags = { Name = "EC2 Messages Endpoint" }
}

resource "aws_vpc_endpoint" "sts" {
  vpc_id              = aws_vpc.private_vpc.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.sts"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_subnet.id]
  security_group_ids  = [aws_security_group.vpc_endpoint_sg.id]
  private_dns_enabled = true
  tags = { Name = "STS Endpoint" }
}

# IAM Role A for Instance A (Stage 2)
resource "aws_iam_role" "role_a" {
  name = "${var.project_name}-role-a"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_policy" "s3_vpce_access" {
  name = "${var.project_name}-s3-vpce-access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:*"]
      Resource = [
        aws_s3_bucket.demo_bucket.arn,
        "${aws_s3_bucket.demo_bucket.arn}/*"
      ]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "role_a_s3" {
  role       = aws_iam_role.role_a.name
  policy_arn = aws_iam_policy.s3_vpce_access.arn
}

resource "aws_iam_role_policy_attachment" "role_a_ssm" {
  role       = aws_iam_role.role_a.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "role_a_profile" {
  name = "${var.project_name}-role-a-profile"
  role = aws_iam_role.role_a.name
}

# Private Instance A (Stage 2)
resource "aws_instance" "private_instance_a" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.private_subnet.id
  vpc_security_group_ids = [aws_security_group.private_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.role_a_profile.name
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    bucket_name = aws_s3_bucket.demo_bucket.bucket
    stage       = "PRIVATE"
  }))
  tags = { Name = "Stage 2 - Private Instance A" }
}

#####################################
# STAGE 3: ZERO TRUST RESTRICTIONS
#####################################

# IAM Role B for Instance B
resource "aws_iam_role" "role_b" {
  name = "${var.project_name}-role-b"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "role_b_s3" {
  role       = aws_iam_role.role_b.name
  policy_arn = aws_iam_policy.s3_vpce_access.arn
}

resource "aws_iam_role_policy_attachment" "role_b_ssm" {
  role       = aws_iam_role.role_b.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "role_b_profile" {
  name = "${var.project_name}-role-b-profile"
  role = aws_iam_role.role_b.name
}

# Private Instance B (Stage 3)
resource "aws_instance" "private_instance_b" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.private_subnet.id
  vpc_security_group_ids = [aws_security_group.private_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.role_b_profile.name
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    bucket_name = aws_s3_bucket.demo_bucket.bucket
    stage       = "ZEROTRUST"
  }))
  tags = { Name = "Stage 3 - Private Instance B" }
}

#####################################
# OUTPUTS
#####################################

output "demo_bucket_name" {
  value = aws_s3_bucket.demo_bucket.bucket
}

output "logging_bucket_name" {
  value = aws_s3_bucket.logging_bucket.bucket
}

output "public_instance_id" {
  value = aws_instance.public_instance.id
}

output "public_instance_ip" {
  value = aws_instance.public_instance.public_ip
}

output "private_instance_a_id" {
  value = aws_instance.private_instance_a.id
}

output "private_instance_b_id" {
  value = aws_instance.private_instance_b.id
}

output "s3_vpc_endpoint_id" {
  value = aws_vpc_endpoint.s3_gateway.id
}

output "private_instance_a_role_arn" {
  value = aws_iam_role.role_a.arn
}
output "private_instance_b_role_arn" {
  value = aws_iam_role.role_b.arn
}
output "session_manager_links" {
  value = {
    public_instance    = "https://${data.aws_region.current.name}.console.aws.amazon.com/systems-manager/session-manager/${aws_instance.public_instance.id}"
    private_instance_a = "https://${data.aws_region.current.name}.console.aws.amazon.com/systems-manager/session-manager/${aws_instance.private_instance_a.id}"
    private_instance_b = "https://${data.aws_region.current.name}.console.aws.amazon.com/systems-manager/session-manager/${aws_instance.private_instance_b.id}"
  }
}
