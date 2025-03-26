import os
from constructs import Construct
from aws_cdk import (
    App, 
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_cognito as cognito,
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_iam as iam,
    custom_resources as cr,
    Fn
)

class MarketplaceCognitoDemoStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a Cognito User Pool
        user_pool = cognito.UserPool(
            self, "EntraIntegrationDemoPool",
            self_sign_up_enabled=True,
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            custom_attributes={
                "groups": cognito.StringAttribute(mutable=True)
            },
            removal_policy=RemovalPolicy.DESTROY  # For demo only, not for production
        )

        # Create API Gateway with Cognito Authorizer
        api = apigateway.RestApi(
            self, "MarketplaceAPI",
            rest_api_name="Marketplace API",
            description="API for a marketplace demo with Cognito authentication",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            )
        )

        # Dynamic URLs based on API Gateway
        # Format: https://{api_id}.execute-api.{region}.amazonaws.com/{stage}
        base_url = Fn.join("", [
            "https://",
            api.rest_api_id,
            ".execute-api.",
            self.region,
            ".amazonaws.com/prod"
        ])
        
        callback_url = f"{base_url}/callback"
        logout_url = base_url

        # Create a User Pool Client for web applications
        user_pool_client = cognito.UserPoolClient(
            self, "EntraIntegrationDemoClient",
            user_pool=user_pool,
            generate_secret=False,  # No client secret for public web app clients
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    implicit_code_grant=True,
                    authorization_code_grant=True,
                ),
                scopes=[cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.COGNITO_ADMIN, cognito.OAuthScope.PROFILE],
                callback_urls=[
                    "http://localhost:3000/callback",  # Keep for local development
                    callback_url
                ],
                logout_urls=[
                    "http://localhost:3000",  # Keep for local development
                    logout_url
                ]
            )
        )

        # Add a domain name to the user pool to enable the hosted UI
        user_pool_domain = cognito.UserPoolDomain(
            self, "EntraIntegrationDemoDomain",
            user_pool=user_pool,
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix="marketplace-entra-demo"  # This creates a domain like: https://marketplace-entra-demo.auth.ap-southeast-2.amazoncognito.com
            )
        )

        # Create dummy Lambda functions for marketplace API
        products_lambda = lambda_.Function(
            self, "ListProductsFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="products.handler",
            code=lambda_.Code.from_asset("lambda"),
        )
        
        details_lambda = lambda_.Function(
            self, "ProductDetailsFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="product_details.handler",
            code=lambda_.Code.from_asset("lambda"),
        )
        
        admin_lambda = lambda_.Function(
            self, "AdminFunctionWithGroups",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="admin.handler",
            code=lambda_.Code.from_asset("lambda"),
        )

        # Create a Cognito Authorizer for API Gateway
        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self, "MarketplaceAuthorizer",
            cognito_user_pools=[user_pool]
        )

        # Create a Lambda function to handle the authentication callback
        callback_lambda = lambda_.Function(
            self, "AuthCallbackFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="auth_callback.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "USER_POOL_ID": user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                "USER_POOL_DOMAIN": f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
                "REDIRECT_URI": callback_url,
                "BASE_URL": base_url
            }
        )

        # Add callback endpoint to API Gateway
        callback_resource = api.root.add_resource("callback")
        callback_integration = apigateway.LambdaIntegration(callback_lambda)
        callback_resource.add_method("GET", callback_integration)

        # Add a login endpoint that redirects to Cognito hosted UI
        login_lambda = lambda_.Function(
            self, "LoginFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="login.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "USER_POOL_ID": user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                "USER_POOL_DOMAIN": f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
                "REDIRECT_URI": callback_url
            }
        )

        # Add login endpoint to API Gateway
        login_resource = api.root.add_resource("login")
        login_integration = apigateway.LambdaIntegration(login_lambda)
        login_resource.add_method("GET", login_integration)

        # Public endpoint - no authorization required
        products_resource = api.root.add_resource("products")
        products_integration = apigateway.LambdaIntegration(products_lambda)
        products_resource.add_method("GET", products_integration)

        # Product detail endpoint - now public, no authentication required
        product_detail = products_resource.add_resource("{id}")
        product_detail_integration = apigateway.LambdaIntegration(details_lambda)
        product_detail.add_method(
            "GET", 
            product_detail_integration
        )

        # Admin endpoint - requires admin group membership
        admin_resource = api.root.add_resource("admin")
        admin_integration = apigateway.LambdaIntegration(admin_lambda)
        admin_resource.add_method(
            "GET",
            admin_integration,
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO
        )

        # Add a test user to the user pool
        test_user = cognito.CfnUserPoolUser(
            self, "TestUser",
            user_pool_id=user_pool.user_pool_id,
            username="testuser",
            desired_delivery_mediums=["EMAIL"],
            force_alias_creation=False,
            user_attributes=[
                {"name": "email", "value": "test@example.com"},
                {"name": "email_verified", "value": "true"}
            ]
        )

        # Create a Lambda function for setting a user's password (for local authentication)
        add_admin_group_lambda = lambda_.Function(
            self, "AddAdminGroupFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="add_admin_group.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "USER_POOL_ID": user_pool.user_pool_id
            }
        )
        
        # Grant permissions to manage Cognito groups and users
        add_admin_group_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminAddUserToGroup",
                    "cognito-idp:GetGroup",
                    "cognito-idp:CreateGroup",
                ],
                resources=[
                    f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/{user_pool.user_pool_id}"
                ]
            )
        )
        
        # Add an endpoint for the admin group management
        admin_group_resource = api.root.add_resource("make-admin")
        admin_group_integration = apigateway.LambdaIntegration(add_admin_group_lambda)
        admin_group_resource.add_method("POST", admin_group_integration)
        
        # Create a Lambda function to toggle between local and SAML auth
        update_cognito_lambda = lambda_.Function(
            self, "UpdateCognitoFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="update_cognito.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "USER_POOL_ID": user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id
            }
        )
        
        # Grant permissions to update the User Pool client
        update_cognito_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:UpdateUserPoolClient",
                    "cognito-idp:DescribeUserPoolClient"
                ],
                resources=[
                    f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/{user_pool.user_pool_id}"
                ]
            )
        )
        
        # Add an endpoint to toggle authentication mode
        auth_mode_resource = api.root.add_resource("auth-mode")
        update_cognito_integration = apigateway.LambdaIntegration(update_cognito_lambda)
        auth_mode_resource.add_method("POST", update_cognito_integration)

        # Add a basic web app for demonstration
        index_lambda = lambda_.Function(
            self, "IndexFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "USER_POOL_ID": user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                "USER_POOL_DOMAIN": f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
                "LOGIN_URL": f"{base_url}/login",
                "API_URL": f"{base_url}/",
                "BASE_URL": base_url
            }
        )
        
        index_resource = api.root.add_resource("app")
        index_integration = apigateway.LambdaIntegration(index_lambda)
        index_resource.add_method("GET", index_integration)

        # Add configuration page
        config_lambda = lambda_.Function(
            self, "ConfigFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="config.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "USER_POOL_ID": user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                "USER_POOL_DOMAIN": f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
                "API_URL": f"{base_url}/",
                "BASE_URL": base_url
            }
        )
        
        # Add config endpoint
        config_resource = api.root.add_resource("config")
        config_integration = apigateway.LambdaIntegration(config_lambda)
        config_resource.add_method("GET", config_integration)
        
        # Add config under app path for a cleaner URL structure
        app_config_resource = index_resource.add_resource("config")
        app_config_integration = apigateway.LambdaIntegration(config_lambda)
        app_config_resource.add_method("GET", app_config_integration)

        # Create a custom resource to update the lambda environment variable
        api_url_updater = cr.AwsCustomResource(
            self, "ApiUrlUpdater",
            on_create={
                "service": "Lambda",
                "action": "updateFunctionConfiguration",
                "parameters": {
                    "FunctionName": index_lambda.function_name,
                    "Environment": {
                        "Variables": {
                            "USER_POOL_ID": user_pool.user_pool_id,
                            "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                            "API_URL": f"{base_url}/",
                            "USER_POOL_DOMAIN": f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
                            "LOGIN_URL": f"{base_url}/login",
                            "BASE_URL": base_url
                        }
                    }
                },
                "physical_resource_id": cr.PhysicalResourceId.of("ApiUrlUpdaterPhysicalId"),
            },
            on_update={
                "service": "Lambda",
                "action": "updateFunctionConfiguration",
                "parameters": {
                    "FunctionName": index_lambda.function_name,
                    "Environment": {
                        "Variables": {
                            "USER_POOL_ID": user_pool.user_pool_id,
                            "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                            "API_URL": f"{base_url}/",
                            "USER_POOL_DOMAIN": f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
                            "LOGIN_URL": f"{base_url}/login",
                            "BASE_URL": base_url
                        }
                    }
                },
                "physical_resource_id": cr.PhysicalResourceId.of("ApiUrlUpdaterPhysicalId"),
            },
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["lambda:UpdateFunctionConfiguration"],
                    resources=[index_lambda.function_arn]
                )
            ])
        )
        
        # Create a custom resource to update the config lambda environment variable
        config_url_updater = cr.AwsCustomResource(
            self, "ConfigUrlUpdater",
            on_create={
                "service": "Lambda",
                "action": "updateFunctionConfiguration",
                "parameters": {
                    "FunctionName": config_lambda.function_name,
                    "Environment": {
                        "Variables": {
                            "USER_POOL_ID": user_pool.user_pool_id,
                            "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                            "API_URL": f"{base_url}/",
                            "USER_POOL_DOMAIN": f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
                            "BASE_URL": base_url
                        }
                    }
                },
                "physical_resource_id": cr.PhysicalResourceId.of("ConfigUrlUpdaterPhysicalId"),
            },
            on_update={
                "service": "Lambda",
                "action": "updateFunctionConfiguration",
                "parameters": {
                    "FunctionName": config_lambda.function_name,
                    "Environment": {
                        "Variables": {
                            "USER_POOL_ID": user_pool.user_pool_id,
                            "USER_POOL_CLIENT_ID": user_pool_client.user_pool_client_id,
                            "API_URL": f"{base_url}/",
                            "USER_POOL_DOMAIN": f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com",
                            "BASE_URL": base_url
                        }
                    }
                },
                "physical_resource_id": cr.PhysicalResourceId.of("ConfigUrlUpdaterPhysicalId"),
            },
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=["lambda:UpdateFunctionConfiguration"],
                    resources=[config_lambda.function_arn]
                )
            ])
        )
        
        # Ensure the custom resources run after the API deployment is complete
        api_url_updater.node.add_dependency(api)
        config_url_updater.node.add_dependency(api)
        
        # Output important information
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "ApiGatewayURL", value=api.url)
        CfnOutput(self, "BaseURL", value=base_url) 
        CfnOutput(self, "DemoAppURL", value=f"{base_url}/app")
        CfnOutput(self, "ConfigURL", value=f"{base_url}/app/config")
        CfnOutput(self, "LoginURL", value=f"{base_url}/login")
        CfnOutput(self, "CognitoHostedUI", value=f"https://{user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com/login?client_id={user_pool_client.user_pool_client_id}&response_type=code&redirect_uri={callback_url}")



