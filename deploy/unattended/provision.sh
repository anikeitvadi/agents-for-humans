#!/usr/bin/env bash
# Provisions the unattended run: SNS topic + email subscription, a Lambda
# that invokes the AgentCore Runtime, and an EventBridge schedule.
# Run from the repo root on a machine with AWS credentials for the account
# that owns the Runtime. Idempotent where the AWS CLI allows it.
#
#   AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/xxx \
#   NOTIFY_EMAIL=you@example.com \
#   bash deploy/unattended/provision.sh
#
# Then confirm the SNS subscription email, and fire one run for the demo:
#   aws lambda invoke --function-name guardian-unattended-check --payload '{"month":"2025-10"}' /dev/stdout
set -euo pipefail

: "${AGENT_RUNTIME_ARN:?set AGENT_RUNTIME_ARN}"
: "${NOTIFY_EMAIL:?set NOTIFY_EMAIL}"
REGION="${AWS_REGION:-us-east-1}"
NAME="${NAME:-guardian-unattended-check}"
SCHEDULE="${SCHEDULE:-cron(0 14 * * ? *)}"   # daily 14:00 UTC; the demo also invokes on demand
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "== SNS topic + email subscription"
TOPIC_ARN=$(aws sns create-topic --name "$NAME" --region "$REGION" --query TopicArn --output text)
aws sns subscribe --topic-arn "$TOPIC_ARN" --protocol email --notification-endpoint "$NOTIFY_EMAIL" --region "$REGION" >/dev/null
echo "   $TOPIC_ARN  (confirm the subscription email sent to $NOTIFY_EMAIL)"

echo "== Runtime execution role may publish to the topic"
RUNTIME_ROLE=$(grep -E "^\s*execution_role:" .bedrock_agentcore.yaml | head -1 | awk '{print $2}' | sed 's#.*role/##')
if [ -n "$RUNTIME_ROLE" ] && [ "$RUNTIME_ROLE" != "null" ]; then
  aws iam put-role-policy --role-name "$RUNTIME_ROLE" --policy-name "${NAME}-sns-publish" --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{\"Effect\": \"Allow\", \"Action\": \"sns:Publish\", \"Resource\": \"$TOPIC_ARN\"}]
  }"
  echo "   attached sns:Publish to $RUNTIME_ROLE"
else
  echo "   WARNING: could not read execution_role from .bedrock_agentcore.yaml; attach sns:Publish on $TOPIC_ARN to the Runtime role by hand"
fi

echo "== Lambda role"
LAMBDA_ROLE="${NAME}-lambda-role"
aws iam get-role --role-name "$LAMBDA_ROLE" >/dev/null 2>&1 || aws iam create-role --role-name "$LAMBDA_ROLE" --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}' >/dev/null
aws iam attach-role-policy --role-name "$LAMBDA_ROLE" --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
aws iam put-role-policy --role-name "$LAMBDA_ROLE" --policy-name "${NAME}-invoke-runtime" --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{\"Effect\": \"Allow\", \"Action\": [\"bedrock-agentcore:InvokeAgentRuntime\"], \"Resource\": [\"$AGENT_RUNTIME_ARN\", \"${AGENT_RUNTIME_ARN}/*\"]}]
}"
sleep 8  # IAM propagation

echo "== Lambda function"
ZIP="$(mktemp -d)/lambda.zip"
(cd "$HERE" && zip -q -j "$ZIP" lambda_function.py)
LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT}:function:${NAME}"
if aws lambda get-function --function-name "$NAME" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$NAME" --zip-file "fileb://$ZIP" --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$NAME" --region "$REGION"
  aws lambda update-function-configuration --function-name "$NAME" --region "$REGION" \
    --environment "Variables={AGENT_RUNTIME_ARN=$AGENT_RUNTIME_ARN,TOPIC_ARN=$TOPIC_ARN,MONTH=2025-10}" >/dev/null
else
  aws lambda create-function --function-name "$NAME" --region "$REGION" --runtime python3.12 --handler lambda_function.handler \
    --role "arn:aws:iam::${ACCOUNT}:role/${LAMBDA_ROLE}" --zip-file "fileb://$ZIP" --timeout 120 \
    --environment "Variables={AGENT_RUNTIME_ARN=$AGENT_RUNTIME_ARN,TOPIC_ARN=$TOPIC_ARN,MONTH=2025-10}" >/dev/null
fi
aws lambda wait function-active --function-name "$NAME" --region "$REGION"
echo "   $LAMBDA_ARN"

echo "== EventBridge schedule ($SCHEDULE)"
SCHED_ROLE="${NAME}-scheduler-role"
aws iam get-role --role-name "$SCHED_ROLE" >/dev/null 2>&1 || aws iam create-role --role-name "$SCHED_ROLE" --assume-role-policy-document '{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "scheduler.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}' >/dev/null
aws iam put-role-policy --role-name "$SCHED_ROLE" --policy-name "${NAME}-invoke-lambda" --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{\"Effect\": \"Allow\", \"Action\": \"lambda:InvokeFunction\", \"Resource\": \"$LAMBDA_ARN\"}]
}"
sleep 8
TARGET="{\"Arn\": \"$LAMBDA_ARN\", \"RoleArn\": \"arn:aws:iam::${ACCOUNT}:role/${SCHED_ROLE}\", \"Input\": \"{\\\"month\\\": \\\"2025-10\\\"}\"}"
if aws scheduler get-schedule --name "$NAME" --region "$REGION" >/dev/null 2>&1; then
  aws scheduler update-schedule --name "$NAME" --region "$REGION" --schedule-expression "$SCHEDULE" \
    --flexible-time-window '{"Mode": "OFF"}' --target "$TARGET" >/dev/null
else
  aws scheduler create-schedule --name "$NAME" --region "$REGION" --schedule-expression "$SCHEDULE" \
    --flexible-time-window '{"Mode": "OFF"}' --target "$TARGET" >/dev/null
fi
echo "   schedule $NAME -> $LAMBDA_ARN"

echo
echo "Done. Next:"
echo "  1. Confirm the SNS subscription email."
echo "  2. Fire a run now:  aws lambda invoke --function-name $NAME --region $REGION --payload '{\"month\":\"2025-10\"}' --cli-binary-format raw-in-base64-out /dev/stdout"
echo "  3. Expect an email with subject 'Document review needed: Sample Bulletin Case — EB2-India' and notified=true in the output."
echo "  4. CloudWatch: /aws/lambda/$NAME and the Runtime's log group show the scheduled invocation."
