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
  name                = "${var.event_bridge_rule_name}"
  description         = "Triggers Lambda MON-FRI day at 12:00 PM JST"
  schedule_expression = "cron(0 3 ? * MON-FRI *)"  # 平日 12時
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
