from aws_cdk import (
    # duration
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
)
from constructs import Construct

class KhalidStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        hello_fn = _lambda.Function(
            self,
            "HelloFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset("./lambda"),
        )

        # # Simple REST API fronting the Lambda
        # apigw.LambdaRestApi(
        #     self,
        #     "HelloApi",
        #     handler=hello_fn,
        #     proxy=True,  # forwards all requests to the Lambda
        # )
