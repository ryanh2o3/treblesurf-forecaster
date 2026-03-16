#!/usr/bin/env bash
# Create the forecast DynamoDB table for multi-source schema.
# Usage: ./scripts/create_forecast_table.sh [TABLE_NAME] [REGION]
# Defaults: TABLE_NAME=FORECAST_DATA, REGION=eu-west-1

set -e
TABLE_NAME="${1:-FORECAST_DATA}"
REGION="${2:-eu-west-1}"

aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=spot_id,AttributeType=S \
    AttributeName=forecast_timestamp,AttributeType=S \
  --key-schema \
    AttributeName=spot_id,KeyType=HASH \
    AttributeName=forecast_timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"

echo "Created table: $TABLE_NAME (region: $REGION)"
echo "Set Lambda env FORECAST_TABLE=$TABLE_NAME and (re)deploy."
