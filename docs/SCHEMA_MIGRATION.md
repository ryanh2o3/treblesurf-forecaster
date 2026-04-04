# Forecast table schema (multi-source)

## New table only

Create a **new** DynamoDB table with the schema below. The forecaster does not run any migration from old data; it only writes to the table named in `FORECAST_TABLE`.

**Key schema:**

| Key type      | Attribute name       | Type   | Description                                           |
| ------------- | -------------------- | ------ | ----------------------------------------------------- |
| Partition key | `spot_id`            | String | `country#region#spot`                                 |
| Sort key      | `forecast_timestamp` | String | `{unix_timestamp}#{source}` (e.g. `1705312800#stormglass`) |

**Non-key attributes:** `generated_at` (String), `source` (String), `data` (Map).

## Create the table

**Option 1 – Script (from repo root):**

```bash
chmod +x scripts/create_forecast_table.sh
./scripts/create_forecast_table.sh FORECAST_DATA eu-west-1
```

Then set Lambda env `FORECAST_TABLE=FORECAST_DATA` (the deploy workflow already uses this) and redeploy.

**Option 2 – AWS CLI:**

```bash
aws dynamodb create-table \
  --table-name FORECAST_DATA \
  --attribute-definitions \
    AttributeName=spot_id,AttributeType=S \
    AttributeName=forecast_timestamp,AttributeType=S \
  --key-schema \
    AttributeName=spot_id,KeyType=HASH \
    AttributeName=forecast_timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1
```

**Option 3 – AWS Console:** DynamoDB → Create table → name e.g. `FORECAST_DATA` → partition key `spot_id` (String), sort key `forecast_timestamp` (String).

## Source identifiers

- `stormglass` – StormGlass API (written for all spots on full runs).
- `imi_swan+weatherkit` – Pre-merged Irish shelf forecast (SWAN swell + WeatherKit weather). The forecaster fetches IMI and WeatherKit only inside SWAN bounds and persists this single merged source (no separate `imi_swan` or `weatherkit` rows from new runs). Legacy items may still exist until TTL.
