#!/usr/bin/env bash

if [ -f .aws-profile ]; then
  export AWS_PROFILE=$(cat .aws-profile)
  echo "Using saved AWS_PROFILE=$AWS_PROFILE"
else
  echo "No saved AWS_PROFILE found."
  read -p "Enter your AWS SSO profile name: " entered_profile
  export AWS_PROFILE=$entered_profile
  echo "$AWS_PROFILE" > .aws-profile
  echo "Saved AWS_PROFILE to .aws-profile"
fi

# if the profile is not found, launch the aws configure sso command
if ! grep -q "\[profile $AWS_PROFILE\]" ~/.aws/config 2>/dev/null; then
  echo "AWS profile '$AWS_PROFILE' not found in ~/.aws/config. Launching 'aws configure sso'..."
  aws configure sso
fi

echo "Triggering AWS SSO login for profile '$AWS_PROFILE'..."
if ! aws sts get-caller-identity --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  aws sso login --profile "$AWS_PROFILE"
fi
