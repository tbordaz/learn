Traffic flow when the Lambda function makes a call to the getmyip endpoint (https://ifconfig.me/ip):

## Architecture Flow for `/getmyip` Request in Different Deployment Modes

### PUBLIC Mode Flow

1. **Client Request Initiation:**
   - A user sends a request to the API Gateway endpoint URL (https://{API-ID}.execute-api.{region}.amazonaws.com/prod/getmyip)
   - This goes through the public internet to reach the Regional API Gateway endpoint

2. **API Gateway Processing:**
   - The API Gateway receives the request and routes it to the Lambda function based on the configured integration
   - The request passes through the ANY method on either the root path or the {proxy+} resource

3. **Lambda Function Execution:**
   - The Lambda function executes in the default AWS Lambda service environment (not in a VPC)
   - It processes the request, identifying that the path is `/getmyip`

4. **Outbound Request from Lambda:**
   - The Lambda function makes an outbound HTTP request to https://ifconfig.me/ip using the `urllib.request.urlopen` function
   - This outbound traffic goes through the Lambda service's NAT gateway (AWS-MANAGED) to the public internet
   - The IP address seen by ifconfig.me will be an AWS-owned IP from the Lambda service's pool

5. **Response Processing:**
   - The Lambda function receives the response containing its public outbound IP
   - It formats this information into an HTML page
   - Returns the response back to API Gateway

6. **Response to Client:**
   - API Gateway forwards the response back to the client
   - The client sees the HTML page displaying the Lambda's outbound IP (which will be an AWS-managed IP)

### PRIVATE Mode Flow

1. **Client Request Initiation:**
   - A user must be inside the VPC (typically connected to the Test EC2 instance via Systems Manager Session Manager)
   - The user sends a request to the API Gateway endpoint URL
   - The request goes to the private VPC endpoint for API Gateway (ApiGatewayEndpoint)

2. **VPC Endpoint Processing:**
   - The VPC endpoint, which is an Interface Endpoint (powered by AWS PrivateLink):
     - Has a security group allowing HTTPS traffic (port 443) from the VPC CIDR range (10.0.0.0/16)
     - Is deployed in the private subnet
     - Has private DNS enabled, allowing the API Gateway hostname to resolve to a private IP
   - The VPC endpoint forwards the request to the private API Gateway

3. **API Gateway Authorization:**
   - The private API Gateway has a resource policy permitting traffic only from the specific VPC endpoint
   - It validates the request is coming from the authorized VPC endpoint
   - Then routes it to the Lambda function

4. **Lambda Function Execution:**
   - The Lambda function now executes inside the VPC, using:
     - The private subnet (PrivateSubnet) for networking
     - The Lambda security group (LambdaSecurityGroup) for traffic control
   - It processes the request, identifying the path as `/getmyip`

5. **Outbound Request from Lambda:**
   - The Lambda function makes an outbound HTTP request to https://ifconfig.me/ip
   - Since the Lambda is in a private subnet with no direct internet access:
     - The traffic first goes to the NAT Gateway (NATGateway)
     - Which is deployed in the public subnet (PublicSubnet)
     - The NAT Gateway has an Elastic IP (EIP) attached to it
   - The NAT Gateway then sends the traffic out to the internet via the Internet Gateway (InternetGateway)
   - The IP address seen by ifconfig.me will be the Elastic IP of the NAT Gateway

6. **Response Path:**
   - The response follows the reverse path:
     - From ifconfig.me to the Internet Gateway
     - Through the NAT Gateway
     - To the Lambda function in the private subnet
   - The Lambda formats the response as HTML showing the NAT Gateway's Elastic IP
   - Returns back through the API Gateway private endpoint
   - To the client in the VPC

## Key Architectural Differences Between Modes

The key differences between PUBLIC and PRIVATE modes that affect the getmyip flow are:

1. **Access Method**:
   - PUBLIC: Accessible from anywhere on the internet
   - PRIVATE: Only accessible from within the VPC through the VPC Endpoint

2. **Lambda Networking**:
   - PUBLIC: Lambda runs in the AWS service environment with default networking
   - PRIVATE: Lambda runs inside your VPC in the private subnet

3. **Outbound IP Address**:
   - PUBLIC: Outbound requests show an AWS-owned IP from the Lambda service
   - PRIVATE: Outbound requests show the Elastic IP of your NAT Gateway

4. **Security Controls**:
   - PUBLIC: Limited network isolation
   - PRIVATE: Multiple layers of network controls:
     - VPC boundaries
     - Subnet segmentation
     - Security groups
     - Resource policies on API Gateway

This architecture demonstrates how you can progressively restrict and control both inbound and outbound traffic for a serverless application, providing greater security and network isolation when needed.
