#!/bin/bash
echo "$(dirname "$0")/../functions/$1"
cd "$(dirname "$0")/../functions/$1/resources"
rm ../lambda_function.zip
zip -r ../lambda_function.zip .