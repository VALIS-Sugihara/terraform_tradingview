variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "event_bridge_rule_name" {
  description = "Name of the Event Bridge Rule Name."
  type        = string
}

variable "function_path" {
  description = "Name of Module Directory Path"
  type        = string
}

variable "role_arn" {
  description = "ARN of Common IAM Role"
  type        = string
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

variable "log_processor_lambda_arn" {
  description = "Lambda ARN for Trigger SNS Topics"
  type        = string
}

variable "log_processor_lambda_name" {
  description = "Lambda Name for Trigger SNS Topics"
  type        = string
}

variable "logs_role_arn" {
  description = "IAM Role for CWLogs ARN"
  type        = string
}

variable "info_filter_name" {
  description = "Subscription Filter Name for INFO Logging"
}

variable "error_filter_name" {
  description = "Subscription Filter Name for ERROR Logging"
}
