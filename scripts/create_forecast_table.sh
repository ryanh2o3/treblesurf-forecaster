#!/usr/bin/env bash
# Create the surf_forecasts DynamoDB table (PK includes source, numeric SK).
# Usage: ./scripts/create_forecast_table.sh [TABLE_NAME] [REGION]
# Defaults: TABLE_NAME=surf_forecasts, REGION=eu-west-1

set -e
TABLE_NAME="${1:-surf_forecasts}"
REGION="${2:-eu-west-1}"

aws dynamodb create-table \
  --table-name "$TABLE_NAME" \
  --attribute-definitions \
    AttributeName=spot_id,AttributeType=S \
    AttributeName=timestamp_ts,AttributeType=N \
  --key-schema \
    AttributeName=spot_id,KeyType=HASH \
    AttributeName=timestamp_ts,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region "$REGION"

echo "Created table: $TABLE_NAME (region: $REGION)"
echo "Set Lambda env FORECAST_TABLE=$TABLE_NAME and (re)deploy."
