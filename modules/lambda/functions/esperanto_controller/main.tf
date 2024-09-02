resource "null_resource" "create_lambda_zip" {
  provisioner "local-exec" {
    command = "bash ${path.module}/../../scripts/create_zip.sh ${var.function_path}"
  }

  triggers = {
    always_run = "${timestamp()}"
  }
}

resource "aws_lambda_function" "this" {
  function_name = var.function_name
  role          = var.role_arn
  handler       = var.handler
  runtime       = var.runtime
  filename      = "${path.module}/lambda_function.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda_function.zip")
  timeout = 30

  depends_on = [null_resource.create_lambda_zip]

  environment {
    variables = var.environment_variables
  }
}

# CloudWatch Event Rule to trigger Lambda on a schedule
resource "aws_cloudwatch_event_rule" "lambda_schedule" {
  name                = "${var.function_path}_lambda_scheduled_rule"
  description         = "Triggers Lambda every day at 12:00 PM UTC"
  # schedule_expression = "cron(0,5,10,15,20,25,30,35,40,45,50,55 * * * ? *)"  # １分間隔
  schedule_expression = "rate(1 minute)"  # １分間隔
}

# CloudWatch Event Target to attach the Lambda to the rule
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.lambda_schedule.name
  target_id = "lambda"
  arn       = aws_lambda_function.this.arn
}

# Grant permission to CloudWatch to invoke the Lambda function
resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedule.arn
}
