import aws_cdk as core
import aws_cdk.assertions as assertions

from khalid.khalid_stack import KhalidStack

# example tests. To run these tests, uncomment this file along with the example
# resource in khalid/khalid_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = KhalidStack(app, "khalid")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
