# Forecast table schema (`surf_forecasts`)

## New table only

Create a **new** DynamoDB table with the schema below. The forecaster writes to the table named in `FORECAST_TABLE`.

**Key schema:**

| Key type      | Attribute name | Type   | Description                                              |
| ------------- | -------------- | ------ | -------------------------------------------------------- |
| Partition key | `spot_id`      | String | `country#region#spot#source`                             |
| Sort key      | `timestamp_ts` | Number | Unix seconds for `dateForecastedFor`                      |

**Non-key attributes:** `generated_at` (String), `source` (String), `data` (Map).

## Create the table

**Option 1 – Script (from repo root):**

```bash
chmod +x scripts/create_forecast_table.sh
./scripts/create_forecast_table.sh surf_forecasts eu-west-1
```

Then set Lambda env `FORECAST_TABLE=surf_forecasts` (the deploy workflow uses this) and redeploy.

**Option 2 – AWS CLI:**

```bash
aws dynamodb create-table \
  --table-name surf_forecasts \
  --attribute-definitions \
    AttributeName=spot_id,AttributeType=S \
    AttributeName=timestamp_ts,AttributeType=N \
  --key-schema \
    AttributeName=spot_id,KeyType=HASH \
    AttributeName=timestamp_ts,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region eu-west-1
```

**Option 3 – AWS Console:** DynamoDB → Create table → name `surf_forecasts` → partition key `spot_id` (String), sort key `timestamp_ts` (Number).

## Source identifiers

- `stormglass` – StormGlass API (written for spots outside Irish IMI shelf logic, and for Ireland outside IMI bounds).
- `imi_swan+weatherkit` – Pre-merged Irish shelf forecast (SWAN swell + WeatherKit weather), written only when both IMI and WeatherKit runs succeed inside bounds.
