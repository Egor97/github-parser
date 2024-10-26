#!/usr/bin/bash
folder_name=gh-parse-1
yc resource-manager folder create --name "$folder_name"
service_id=$(yc iam service-account create --name=trigger-service --folder-name "$folder_name" | grep "^id:" | awk '{print $2}')

yc resource-manager folder add-access-binding "$folder_name" --role editor --subject serviceAccount:"$service_id"
function_id=$(yc serverless function create --name=parse-github-function --folder-name "$folder_name" --async | grep "^id:" | awk '{print $2}')

yc serverless function version create \
  --function-name=parse-github-function \
  --runtime python312 \
  --entrypoint main.main \
  --memory 128m \
  --execution-timeout 10s \
  --source-path ./github_parser.zip \
  --folder-name "$folder_name"\
  --async-service-account-id "$service_id"\
  --environment API_GITHUB_TOKEN="$1",DB_USER="$2",DB_PASS="$3",DB_HOST="$4",DB_PORT="$5",DB_NAME="$6"

yc serverless trigger create timer \
  --name parser-trigger \
  --cron-expression '55 23 ? * * *' \
  --payload '' \
  --folder-name "$folder_name"\
  --invoke-function-id "$function_id" \
  --invoke-function-service-account-id "$service_id"