import aws_cdk as core
import aws_cdk.assertions as assertions

from marketplace_cognito_demo.marketplace_cognito_demo_stack import MarketplaceCognitoDemoStack

# example tests. To run these tests, uncomment this file along with the example
# resource in marketplace_cognito_demo/marketplace_cognito_demo_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = MarketplaceCognitoDemoStack(app, "marketplace-cognito-demo")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
