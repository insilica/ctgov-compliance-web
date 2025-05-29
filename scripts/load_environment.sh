#!/usr/bin/env bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <aws-profile> <secret-name>"
    exit 1
fi

AWS_PROFILE="$1"
SECRET_NAME="$2"

echo "[load-aws-secret] Using AWS_PROFILE=$AWS_PROFILE"

# Fetch secret string
SECRET_JSON=$(aws secretsmanager get-secret-value \
  --profile "$AWS_PROFILE" \
  --secret-id "$SECRET_NAME" \
  --query SecretString \
  --output text)

# Parse and export each key/value
echo "$SECRET_JSON" | jq -r 'to_entries[] | "export \(.key)=\(.value)"' > .env

# Load into current shell
set -a
source .env
set +a

echo "[load-aws-secret] Loaded $(jq length <<< "$SECRET_JSON") keys into environment."
