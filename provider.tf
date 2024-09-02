provider "aws" {
  region  = "us-east-1"
  profile = "valis"
}

data "aws_caller_identity" "current" {}

terraform {
  backend "s3" {
    bucket = "valis-terraform-tfstates"
    key    = "tradingview/terraform.tfstate"
    region = "ap-northeast-1"
    # dynamodb_table = "your-lock-table" # オプション
    encrypt = true
  }
}