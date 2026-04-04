# Backend changes for multi-source forecast data

The forecaster writes **StormGlass** for all spots (on full runs) and **`imi_swan+weatherkit`** (pre-merged) for Irish shelf spots. The backend must read and expose multi-source items correctly (including any legacy `imi_swan` / `weatherkit` rows).

## Quick checklist

- [ ] Update forecast read path to Query with `forecast_timestamp BETWEEN :t0 AND :t1` (inclusive of `#source` suffixes).
- [ ] Parse `forecast_timestamp` as `{ts}#{source}`; group by `ts`, keep `source` per item.
- [ ] Include `source` (and/or a grouped-by-source shape) in the API response.
- [ ] Optionally support `?sources=all` or a primary source + alternates for backward compatibility.

---

## Table and key schema

- **Table**: Forecast table (env `FORECAST_TABLE`, e.g. `FORECAST_DATA`).
- **Partition key**: `spot_id` (String), format `country#region#spot`.
- **Sort key**: `forecast_timestamp` (String), format `{unix_timestamp}#{source}` (e.g. `1705312800#stormglass`, `1705312800#imi_swan+weatherkit`; legacy keys may include `imi_swan` or `weatherkit`).

**Item attributes:**
- `spot_id`, `forecast_timestamp`
- `generated_at` (String): When the forecast was generated (epoch seconds).
- `source` (String): e.g. `stormglass`, `imi_swan+weatherkit` (and optionally legacy `imi_swan`, `weatherkit`).
- `data` (Map): The forecast payload (same structure as before).

## Querying for a spot and time range

Use **one Query** (no Scan):

- **Partition key**: `spot_id = :sid`.
- **Sort key condition**: `forecast_timestamp BETWEEN :t0 AND :t1`.

Use `:t0 = "{start_ts}"` and `:t1 = "{end_ts}\uffff"` (or `"{end_ts}~"`) so every `{timestamp}#{source}` in the range is included. Lexicographic order depends on the `#source` suffix (e.g. `1705312800#stormglass` vs `1705312800#imi_swan+weatherkit`). Ensure timestamps are fixed-width (e.g. 10-digit Unix).

**Example (pseudo):**
```
Query(
  KeyConditionExpression: "spot_id = :sid AND forecast_timestamp BETWEEN :t0 AND :t1",
  ExpressionAttributeValues: {
    ":sid": "ireland#connacht#easkey",
    ":t0": "1705312800",
    ":t1": "1706122800~"
  }
)
```

## Response shape

Each returned item has: `spot_id`, `forecast_timestamp`, `generated_at`, `source`, `data`.

**Backend should:**
1. Group items by forecast time (strip `#source` from `forecast_timestamp`).
2. Per timestamp, return either:
   - **Option A**: `{ "time": ts, "sources": { "stormglass": { ...data }, "imi_swan+weatherkit": { ...data } } }` (plus any legacy keys)
   - **Option B**: `{ "time": ts, "forecasts": [ { "source": "stormglass", "data": {...} }, ... ] }`

## Backward compatibility

- If the API currently returns a single `data` per time, add a query param (e.g. `?sources=all`) or default to one primary source and expose others under `sources` / `alternates`.

## Source preference

Clients may prefer one source (e.g. IMI for Irish spots, StormGlass elsewhere). The backend can implement a “primary source per region” rule and expose it (e.g. `primary_source` plus `sources`).
