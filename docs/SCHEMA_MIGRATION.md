# SpotForecastData Schema and Multi-Source Migration

## New table key schema (multi-source)

To support multiple forecast sources per spot and time, the table uses a composite sort key that includes the source identifier.

| Key type     | Attribute name        | Type   | Description                                      |
| ------------ | ---------------------- | ------ | ------------------------------------------------- |
| Partition key | `spot_id`             | String | Format: `country#region#spot`                     |
| Sort key      | `forecast_timestamp`  | String | Format: `{unix_timestamp}#{source}` (e.g. `1705312800#stormglass`, `1705312800#imi_swan`) |

**Item attributes:**
- `spot_id` (partition key)
- `forecast_timestamp` (sort key)
- `generated_at` (String): When the forecast was generated (epoch seconds).
- `source` (String): Source identifier, e.g. `stormglass`, `imi_swan`.
- `data` (Map): Forecast payload (same shape as before).

## Creating a new table

DynamoDB does not allow changing the key schema of an existing table. For multi-source support you must either create a new table or migrate.

**Option A – New table**

1. Create a new table with the same partition key name (`spot_id`) and sort key name (`forecast_timestamp`), but ensure all new writes use the composite sort key value `{timestamp}#{source}`.
2. Set the Lambda environment variable `FORECAST_TABLE` to the new table name.
3. Run the forecaster; it will populate the new table. Old table can be retired or kept for read-only.

**Option B – Automatic migration (same table, old format present)**

If your current table already uses `spot_id` (partition) and `forecast_timestamp` (sort key) with plain timestamps (no `#source`):

1. Deploy this forecaster; it writes new data in the new format and runs a **migration step at the start of every Lambda run**.
2. The migration (`migrate_old_forecast_items_to_multi_source`) queries each known spot (from LocationData), finds items that have no `source` attribute and a sort key without `#`, then for each: writes a new item with sort key `{timestamp}#stormglass` and `source='stormglass'`, then deletes the old item. It processes up to 100 such items per run to avoid timeout.
3. After enough runs (or once all old data is migrated), the migration step no-opts. New data is always written in the new format.

## Source identifiers

- `stormglass` – StormGlass API (default for all spots).
- `imi_swan` – Irish Marine Institute SWAN wave model (Irish shelf spots only).
- `weatherkit` – Apple WeatherKit (weather: wind, precipitation, etc.; all spots when configured).
