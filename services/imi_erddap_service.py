"""
Irish Marine Institute ERDDAP griddap integration for SWAN wave model.
Dataset: IMI_IRISH_SHELF_SWAN_WAVE (Irish Shelf, lat 49-56, lon -15 to -3).
Provides wave-only forecast data; wind/met come from StormGlass.
"""
import json
import urllib.error
import urllib.request
import arrow
from utils.calculations import (
    calculate_surf_size,
    calculate_wave_energy,
    calculateDirectionQuality,
)

BASE_URL = "https://erddap.marine.ie/erddap/griddap/IMI_IRISH_SHELF_SWAN_WAVE"
DATASET_ID = "IMI_IRISH_SHELF_SWAN_WAVE"

# Irish shelf grid bounds (from dataset metadata)
IMI_LAT_MIN = 49.0125
IMI_LAT_MAX = 55.9875
IMI_LON_MIN = -14.9875
IMI_LON_MAX = -3.0125
IMI_GRID_RES = 0.025


def in_imi_bounds(latitude, longitude):
    """Return True if (lat, lon) is inside the IMI Irish Shelf grid."""
    return (
        IMI_LAT_MIN <= latitude <= IMI_LAT_MAX
        and IMI_LON_MIN <= longitude <= IMI_LON_MAX
    )


def _snap_to_grid(lat, lon):
    """Snap (lat, lon) to the dataset grid. Grid starts at IMI_LAT_MIN, IMI_LON_MIN with step 0.025."""
    lat_snapped = IMI_LAT_MIN + round((lat - IMI_LAT_MIN) / IMI_GRID_RES) * IMI_GRID_RES
    lon_snapped = IMI_LON_MIN + round((lon - IMI_LON_MIN) / IMI_GRID_RES) * IMI_GRID_RES
    # Round to 4 decimals for URL to avoid float noise (e.g. 55.175000000000004)
    return round(lat_snapped, 4), round(lon_snapped, 4)


def _build_griddap_url(time_start_iso, time_end_iso, lat, lon):
    """Build griddap request for one grid point and time range. Uses .json."""
    # Subset format: var[(t0):1:(t1)][(lat):1:(lat)][(lon):1:(lon)]
    time_slice = f"[({time_start_iso}):1:({time_end_iso})]"
    lat_slice = f"[({lat}):1:({lat})]"
    lon_slice = f"[({lon}):1:({lon})]"
    vars_ = [
        "significant_wave_height",
        "peak_wave_period",
        "mean_wave_direction_from",
    ]
    # One slice string per variable (same dimensions for all).
    # Do not URL-encode: this ERDDAP server returns 404 when constraints are encoded.
    constraints = ",".join(
        f"{v}{time_slice}{lat_slice}{lon_slice}" for v in vars_
    )
    url = f"{BASE_URL}.json?{constraints}"
    return url


def _parse_erddap_table(response_json):
    """Parse ERDDAP table JSON into list of dicts keyed by column name."""
    table = response_json.get("table", {})
    names = table.get("columnNames", [])
    rows = table.get("rows", [])
    out = []
    for row in rows:
        out.append(dict(zip(names, row)))
    return out


def fetch_imi_forecast(latitude, longitude, beach_direction, ideal_swell_direction):
    """
    Fetch wave forecast from IMI ERDDAP for one grid point.
    Returns list of forecast-like dicts (wave fields only; wind/met are None).
    """
    if not in_imi_bounds(latitude, longitude):
        return []

    lat, lon = _snap_to_grid(latitude, longitude)
    time_start = arrow.utcnow()
    # Dataset coverage is typically ~2 weeks; request up to 10 days to stay within it
    time_end = time_start.shift(days=+10).ceil("hour")
    time_start_iso = time_start.format("YYYY-MM-DDTHH:mm:ss") + "Z"
    time_end_iso = time_end.format("YYYY-MM-DDTHH:mm:ss") + "Z"

    url = _build_griddap_url(time_start_iso, time_end_iso, lat, lon)
    try:
        # Use urllib so the URL is sent as-is; requests.get() encodes [ ] and this server returns 404 for that
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status != 200:
                print(f"IMI ERDDAP request failed: {resp.status} for url: {url[:120]}...")
                return []
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"IMI ERDDAP request failed: {e.code} for url: {url[:120]}...")
        return []
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"IMI ERDDAP request failed: {e}")
        return []

    rows = _parse_erddap_table(data)
    # ERDDAP may return one row per variable per time (long format) or one row per time with all vars
    # Standard griddap returns one row per (time, lat, lon) with all requested variables in columns
    if not rows:
        return []

    # Check structure: expect time, latitude, longitude, significant_wave_height, peak_wave_period, mean_wave_direction_from
    sample = rows[0]
    has_swh = "significant_wave_height" in sample
    has_tp = "peak_wave_period" in sample
    has_dir = "mean_wave_direction_from" in sample

    formatted = []
    for row in rows:
        time_str = row.get("time")
        if not time_str:
            continue
        # Normalize to same datetime format as StormGlass
        dt = arrow.get(time_str)
        date_forecasted = dt.format("YYYY-MM-DD HH:mm:ss")

        swh = row.get("significant_wave_height") if has_swh else None
        tp = row.get("peak_wave_period") if has_tp else None
        swell_dir = row.get("mean_wave_direction_from") if has_dir else None

        # Skip rows where wave height is missing (e.g. future model run not yet available)
        if swh is None and tp is None:
            continue

        # Use float for calculations when present
        swh_f = float(swh) if swh is not None else None
        tp_f = float(tp) if tp is not None else None
        swell_dir_f = float(swell_dir) if swell_dir is not None else None

        surf_size = None
        if swh_f is not None and tp_f is not None and beach_direction is not None:
            surf_size = calculate_surf_size(
                swell_height=swh_f,
                swell_period=tp_f,
                beach_direction=beach_direction,
                swell_direction=swell_dir_f if swell_dir_f is not None else 0,
            )

        wave_energy = None
        if swh_f is not None and tp_f is not None:
            wave_energy = calculate_wave_energy(swh_f, tp_f)

        direction_quality = None
        if swell_dir_f is not None and ideal_swell_direction is not None:
            direction_quality = calculateDirectionQuality(
                swell_dir_f, ideal_swell_direction
            )

        entry = {
            "dateForecastedFor": date_forecasted,
            "temperature": None,
            "humidity": None,
            "pressure": None,
            "windSpeed": None,
            "precipitation": None,
            "windDirection": None,
            "waterTemperature": None,
            "swellHeight": swh_f,
            "swellPeriod": tp_f,
            "swellDirection": swell_dir_f,
            "surfSize": surf_size,
            "waveEnergy": wave_energy,
            "relativeWindDirection": None,
            "surfMessiness": None,
            "directionQuality": direction_quality,
        }
        formatted.append(entry)

    return formatted
