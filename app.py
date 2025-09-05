import aws_cdk as cdk
from stack.khalid_stack import KhalidStack   # clean import

app = cdk.App()
KhalidStack(app, "KhalidStack")
app.synth()
