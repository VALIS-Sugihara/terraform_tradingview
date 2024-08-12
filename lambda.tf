locals {
  project_name        = "vls-trdvw"
  # OANDA_RESTAPI_TOKEN = "943477fc4e952452ce1fc2f88fa3d8bf-40be1a4b46642007286ce4d82676b759"  # for PRD
  OANDA_RESTAPI_TOKEN = "a59a8c2b423de36686bb646296e61af2-3b137c653def17e22e25196afd46ba5a"  # for DEMO
  DEMO_OANDA_RESTAPI_TOKEN = "a59a8c2b423de36686bb646296e61af2-3b137c653def17e22e25196afd46ba5a"  # for DEMO
  # OANDA_ACCOUNT_ID    = "001-009-12298567-001"  # for PRD
  OANDA_ACCOUNT_ID    = "101-009-29596086-001"  # for DEMO
  DEMO_OANDA_ACCOUNT_ID    = "101-009-29596086-001"  # for DEMO
}

###
# Each Modules
###
module "lambda_check_event" {
  source        = "./modules/lambda/functions/check_event"
  function_name = "${local.project_name}-check-event-function"
  function_path = "check_event"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  role_arn      = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.OANDA_ACCOUNT_ID
  }
}

module "lambda_oanda_controller" {
  source        = "./modules/lambda/functions/oanda_controller"
  function_name = "${local.project_name}-oanda-controller-function"
  function_path = "oanda_controller"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  role_arn      = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.OANDA_ACCOUNT_ID
  }
}

module "lambda_demo_esperanto_controller" {
  source        = "./modules/lambda/functions/esperanto_controller"
  function_name = "${local.project_name}-demo-esperanto-controller-function"
  function_path = "esperanto_controller"
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  role_arn      = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.DEMO_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.DEMO_OANDA_ACCOUNT_ID
  }
}

###
# Common IAM 
###
resource "aws_iam_role" "lambda_exec" {
  name = "${local.project_name}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_exec_policy" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

output "lambda_check_event_function_arn" {
  value = module.lambda_check_event.lambda_function_arn
}
