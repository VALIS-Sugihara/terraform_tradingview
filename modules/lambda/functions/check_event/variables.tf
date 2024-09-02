variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "function_path" {
  description = "Name of Module Directory Path"
  type        = string
}

variable "role_arn" {
  description = "ARN of Common IAM Role"
  type = string
}

variable "handler" {
  description = "Handler for the Lambda function"
  type        = string
}

variable "runtime" {
  description = "Runtime for the Lambda function"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables for the Lambda function"
  type        = map(string)
  default     = {}
}
