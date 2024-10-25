#!/usr/bin/bash

service_id=$(yc iam service-account create --name trigger-service | grep "^id:" | awk '{print $2}')
function_id=$(yc serverless function create --name=parse-github-function | grep "^id:" | awk '{print $2}')

yc serverless function version create \
  --function-name=parse-github-function \
  --runtime python312 \
  --entrypoint main.main \
  --memory 128m \
  --execution-timeout 10s \
  --source-path ./github_parser.zip \
  --async-service-account-id "$service_id"\
  --environment API_GITHUB_TOKEN="$1",DB_USER="$2",DB_PASS="$3",DB_HOST="$4",DB_PORT="$5",DB_NAME="$6"

yc serverless trigger create timer \
  --name parser-trigger \
  --cron-expression '55 23 ? * * *' \
  --payload '' \
  --invoke-function-id "$function_id" \
  --invoke-function-service-account-id "$service_id"