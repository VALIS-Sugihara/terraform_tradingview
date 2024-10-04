locals {
  project_name             = "vls-trdvw"
  ACCOUNT_MODE_DEMO        = "DEMO"                                                              # デモ環境であることを示す
  ACCOUNT_MODE_PERS        = "PERS"                                                              # 個人用本番環境であることを示す
  ACCOUNT_MODE_CORP        = "CORP"                                                              # 法人用本番環境であることを示す
  PERS_OANDA_ACCOUNT_ID    = "001-009-12298567-001"                                              # for PERS
  PERS_OANDA_RESTAPI_TOKEN = "943477fc4e952452ce1fc2f88fa3d8bf-40be1a4b46642007286ce4d82676b759" # for PERS
  PERS_OANDA_API_URL       = "https://api-fxtrade.oanda.com"                                     # デモアカウントの場合 "https://api-fxpractice.oanda.com"。ライブアカウントの場合は'https://api-fxtrade.oanda.com'
  DEMO_OANDA_ACCOUNT_ID    = "101-009-30020937-001"                                              # for DEMO
  DEMO_OANDA_RESTAPI_TOKEN = "6197f9b13865185a88321925cb9d0e44-f2cbf4f1305c54dcb0a16422f76fb69c" # for DEMO
  DEMO_OANDA_API_URL       = "https://api-fxpractice.oanda.com"                                  # デモアカウントの場合 "https://api-fxpractice.oanda.com"。ライブアカウントの場合は'https://api-fxtrade.oanda.com'
  CORP_OANDA_ACCOUNT_ID    = "001-009-12556146-001"                                              # for CORP
  CORP_OANDA_RESTAPI_TOKEN = "fd523da41d1c7a81d4d545716ada49f5-a6b91f8e0e828b0a91f519870008438e" # for CORP
  CORP_OANDA_API_URL       = "https://api-fxtrade.oanda.com"                                     # デモアカウントの場合 "https://api-fxpractice.oanda.com"。ライブアカウントの場合は'https://api-fxtrade.oanda.com'
  INFO_FILTER_NAME         = "info_filter"
  ERROR_FILTER_NAME        = "error_filter"
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
    OANDA_RESTAPI_TOKEN = local.DEMO_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.DEMO_OANDA_ACCOUNT_ID
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
    OANDA_RESTAPI_TOKEN = local.DEMO_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.DEMO_OANDA_ACCOUNT_ID
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

module "lambda_demo_accumulation_controller" {
  source                 = "./modules/lambda/functions/accumulation_controller"
  function_name          = "${local.project_name}-demo-accumulation-controller-function"
  event_bridge_rule_name = "${local.project_name}-demo-accumulation-rule"
  function_path          = "accumulation_controller"
  handler                = "lambda_function.lambda_handler"
  runtime                = "python3.12"
  role_arn               = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.DEMO_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.DEMO_OANDA_ACCOUNT_ID
    OANDA_API_URL       = local.DEMO_OANDA_API_URL
    ACCOUNT_MODE        = local.ACCOUNT_MODE_DEMO # デモ環境
    MONTHLY_AMOUNT      = 800000
    LEVERAGE            = 7.7
  }
  log_processor_lambda_arn  = aws_lambda_function.log_processor_lambda.arn
  log_processor_lambda_name = aws_lambda_function.log_processor_lambda.function_name
  logs_role_arn             = aws_iam_role.log_to_lambda_role.arn
  info_filter_name          = local.INFO_FILTER_NAME
  error_filter_name         = local.ERROR_FILTER_NAME
}

module "lambda_pers_accumulation_controller" {
  source                 = "./modules/lambda/functions/accumulation_controller"
  function_name          = "${local.project_name}-pers-accumulation-controller-function"
  event_bridge_rule_name = "${local.project_name}-pers-accumulation-rule"
  function_path          = "accumulation_controller"
  handler                = "lambda_function.lambda_handler"
  runtime                = "python3.12"
  role_arn               = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.PERS_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.PERS_OANDA_ACCOUNT_ID
    OANDA_API_URL       = local.PERS_OANDA_API_URL
    ACCOUNT_MODE        = local.ACCOUNT_MODE_PERS # 個人環境
    MONTHLY_AMOUNT      = 800000
    LEVERAGE            = 3.0
  }
  log_processor_lambda_arn  = aws_lambda_function.log_processor_lambda.arn
  log_processor_lambda_name = aws_lambda_function.log_processor_lambda.function_name
  logs_role_arn             = aws_iam_role.log_to_lambda_role.arn
  info_filter_name          = local.INFO_FILTER_NAME
  error_filter_name         = local.ERROR_FILTER_NAME
}

module "lambda_corp_accumulation_controller" {
  source                 = "./modules/lambda/functions/accumulation_controller"
  function_name          = "${local.project_name}-corp-accumulation-controller-function"
  event_bridge_rule_name = "${local.project_name}-corp-accumulation-rule"
  function_path          = "accumulation_controller"
  handler                = "lambda_function.lambda_handler"
  runtime                = "python3.12"
  role_arn               = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.CORP_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.CORP_OANDA_ACCOUNT_ID
    OANDA_API_URL       = local.CORP_OANDA_API_URL
    ACCOUNT_MODE        = local.ACCOUNT_MODE_CORP # 法人環境
    MONTHLY_AMOUNT      = 800000
    LEVERAGE            = 3.0
  }
  log_processor_lambda_arn  = aws_lambda_function.log_processor_lambda.arn
  log_processor_lambda_name = aws_lambda_function.log_processor_lambda.function_name
  logs_role_arn             = aws_iam_role.log_to_lambda_role.arn
  info_filter_name          = local.INFO_FILTER_NAME
  error_filter_name         = local.ERROR_FILTER_NAME
}

module "lambda_demo_compound_investment_controller" {
  source                 = "./modules/lambda/functions/compound_investment_controller"
  function_name          = "${local.project_name}-demo-compound_investment-controller-function"
  event_bridge_rule_name = "${local.project_name}-demo-compound_investment-rule"
  function_path          = "compound_investment_controller"
  handler                = "lambda_function.lambda_handler"
  runtime                = "python3.12"
  role_arn               = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.DEMO_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.DEMO_OANDA_ACCOUNT_ID
    OANDA_API_URL       = local.DEMO_OANDA_API_URL
    ACCOUNT_MODE        = local.ACCOUNT_MODE_DEMO # デモ環境
    LEVERAGE            = 7.7
  }
  log_processor_lambda_arn  = aws_lambda_function.log_processor_lambda.arn
  log_processor_lambda_name = aws_lambda_function.log_processor_lambda.function_name
  logs_role_arn             = aws_iam_role.log_to_lambda_role.arn
  info_filter_name          = local.INFO_FILTER_NAME
  error_filter_name         = local.ERROR_FILTER_NAME
}

module "lambda_pers_compound_investment_controller" {
  source                 = "./modules/lambda/functions/compound_investment_controller"
  function_name          = "${local.project_name}-pers-compound_investment-controller-function"
  event_bridge_rule_name = "${local.project_name}-pers-compound_investment-rule"
  function_path          = "compound_investment_controller"
  handler                = "lambda_function.lambda_handler"
  runtime                = "python3.12"
  role_arn               = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.PERS_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.PERS_OANDA_ACCOUNT_ID
    OANDA_API_URL       = local.PERS_OANDA_API_URL
    ACCOUNT_MODE        = local.ACCOUNT_MODE_PERS # 個人環境
    LEVERAGE            = 3.0
  }
  log_processor_lambda_arn  = aws_lambda_function.log_processor_lambda.arn
  log_processor_lambda_name = aws_lambda_function.log_processor_lambda.function_name
  logs_role_arn             = aws_iam_role.log_to_lambda_role.arn
  info_filter_name          = local.INFO_FILTER_NAME
  error_filter_name         = local.ERROR_FILTER_NAME
}

module "lambda_corp_compound_investment_controller" {
  source                 = "./modules/lambda/functions/compound_investment_controller"
  function_name          = "${local.project_name}-corp-compound_investment-controller-function"
  event_bridge_rule_name = "${local.project_name}-corp-compound_investment-rule"
  function_path          = "compound_investment_controller"
  handler                = "lambda_function.lambda_handler"
  runtime                = "python3.12"
  role_arn               = aws_iam_role.lambda_exec.arn
  environment_variables = {
    OANDA_RESTAPI_TOKEN = local.CORP_OANDA_RESTAPI_TOKEN
    OANDA_ACCOUNT_ID    = local.CORP_OANDA_ACCOUNT_ID
    OANDA_API_URL       = local.CORP_OANDA_API_URL
    ACCOUNT_MODE        = local.ACCOUNT_MODE_CORP # 法人環境
    LEVERAGE            = 3.0
  }
  log_processor_lambda_arn  = aws_lambda_function.log_processor_lambda.arn
  log_processor_lambda_name = aws_lambda_function.log_processor_lambda.function_name
  logs_role_arn             = aws_iam_role.log_to_lambda_role.arn
  info_filter_name          = local.INFO_FILTER_NAME
  error_filter_name         = local.ERROR_FILTER_NAME
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

###
# LogProcesser to SNS
###
# Lambda function to process logs and send to SNS
resource "aws_lambda_function" "log_processor_lambda" {
  function_name = "${local.project_name}-log-processor-function"
  role          = aws_iam_role.log_processor_lambda_role.arn
  runtime       = "python3.12"
  handler       = "log_processor_lambda.lambda_handler"
  filename      = "log_processor_lambda.zip" # Replace with your packaged Lambda zip

  environment {
    variables = {
      INFO_FILTER_NAME    = local.INFO_FILTER_NAME
      ERROR_FILTER_NAME   = local.ERROR_FILTER_NAME
      INFO_SNS_TOPIC_ARN  = aws_sns_topic.infolog_topic.arn
      ERROR_SNS_TOPIC_ARN = aws_sns_topic.errorlog_topic.arn
    }
  }
}

resource "aws_iam_role" "log_processor_lambda_role" {
  name = "${local.project_name}-log-processor-function-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Grant permission to CloudWatch SubscriptionFilter to invoke the Lambda function
resource "aws_lambda_permission" "log_permission" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.log_processor_lambda.function_name
  principal     = "logs.us-east-1.amazonaws.com"
  # source_arn    = aws_cloudwatch_log_group.lambda_log_group.arn
}

# Attach a policy to the role to allow it to publish to SNS
resource "aws_iam_role_policy" "log_processor_lambda_policy" {
  role = aws_iam_role.log_processor_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sns:Publish",
        Effect = "Allow",
        Resource = [
          aws_sns_topic.infolog_topic.arn,
          aws_sns_topic.errorlog_topic.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "log_processor_lambda_exec_policy" {
  role       = aws_iam_role.log_processor_lambda_role.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


resource "aws_iam_role" "log_to_lambda_role" {
  name = "${local.project_name}-cloudwatch-logs-to-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "logs.us-east-1.amazonaws.com"
        }
      }
    ]
  })
}

# Attach a policy to the role to allow it to publish to SNS
resource "aws_iam_role_policy" "log_to_lambda_policy" {
  role = aws_iam_role.log_to_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "lambda:Invoke",
        Effect = "Allow",
        Resource = [
          aws_lambda_function.log_processor_lambda.arn
        ]
      }
    ]
  })
}

###
# Common SNS Topics
###
resource "aws_sns_topic" "infolog_topic" {
  name = "infolog-topic"
}

resource "aws_sns_topic" "errorlog_topic" {
  name = "errorlog-topic"
}
