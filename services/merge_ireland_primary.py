"""
Pre-merge Ireland primary forecast: swell from IMI SWAN, weather from WeatherKit.

Matches backend compose rules (treblesurf-backend internal/service/forecast_service.go
weatherDataKeys + surfMessiness from WeatherKit).
"""

import arrow

# Overlay from WeatherKit onto SWAN row (align with Go weatherDataKeys + surfMessiness).
WEATHER_OVERLAY_KEYS = (
    "temperature",
    "humidity",
    "pressure",
    "windSpeed",
    "windDirection",
    "precipitation",
    "relativeWindDirection",
    "surfMessiness",
)


def _time_key(row):
    ts = row.get("dateForecastedFor")
    if not ts:
        return None
    return arrow.get(ts.replace("Z", "+00:00")).int_timestamp


def merge_ireland_swan_weatherkit(imi_rows, weatherkit_rows):
    """
    Join IMI SWAN and WeatherKit hourly rows by forecast instant.

    Returns rows in the same dict shape as imi_rows, with weather fields replaced
    from WeatherKit where present. Only hours with both sources are included.
    Caller saves with source='imi_swan+weatherkit'.
    """
    if not imi_rows or not weatherkit_rows:
        return []

    wk_by_ts = {}
    for row in weatherkit_rows:
        k = _time_key(row)
        if k is not None:
            wk_by_ts[k] = row

    out = []
    for swan in imi_rows:
        k = _time_key(swan)
        if k is None:
            continue
        wk = wk_by_ts.get(k)
        if wk is None:
            continue
        merged = dict(swan)
        for key in WEATHER_OVERLAY_KEYS:
            val = wk.get(key)
            if val is not None:
                merged[key] = val
        out.append(merged)
    return out
