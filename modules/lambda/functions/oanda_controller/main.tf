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

  depends_on = [null_resource.create_lambda_zip]

  environment {
    variables = var.environment_variables
  }
}
