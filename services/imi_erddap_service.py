"""
Irish Marine Institute ERDDAP griddap integration for SWAN wave model.
Dataset: IMI_IRISH_SHELF_SWAN_WAVE (Irish Shelf, lat 49-56, lon -15 to -3).
Provides wave-only forecast data; wind/met come from StormGlass.
"""
import json
import math
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


def _build_griddap_url(time_start_iso, time_end_iso, lat_min, lat_max, lon_min, lon_max):
    """Build griddap request for a lat/lon box and time range. Uses .json."""
    # Subset format: var[(t0):1:(t1)][(lat0):1:(lat1)][(lon0):1:(lon1)]
    time_slice = f"[({time_start_iso}):1:({time_end_iso})]"
    lat_slice = f"[({lat_min}):1:({lat_max})]"
    lon_slice = f"[({lon_min}):1:({lon_max})]"
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


def _fetch_erddap_rows(url):
    try:
        # Use urllib so the URL is sent as-is; requests.get() encodes [ ] and this server returns 404 for that
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            if resp.status != 200:
                print(f"IMI ERDDAP request failed: {resp.status} for url: {url[:120]}...")
                return []
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()[:500]
        except Exception:
            pass
        msg = f"IMI ERDDAP request failed: {e.code} for url: {url[:120]}..."
        if body:
            msg += f" {body}"
        print(msg)
        return []
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"IMI ERDDAP request failed: {e}")
        return []

    return _parse_erddap_table(data)


def _to_float_or_none(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _looks_like_land_or_mask(rows):
    """
    Heuristic: if the query returns only 0/None for Hs, it's likely a land/masked grid cell.
    """
    if not rows:
        return True
    any_nonzero = False
    any_present = False
    for row in rows:
        swh_f = _to_float_or_none(row.get("significant_wave_height"))
        if swh_f is None:
            continue
        any_present = True
        if swh_f > 0:
            any_nonzero = True
            break
    return (not any_present) or (not any_nonzero)


def _choose_best_cell(rows, target_lat, target_lon):
    """
    Pick the nearest (lat, lon) cell that has non-zero, finite Hs at least once.
    """
    candidates = {}
    for row in rows:
        lat = _to_float_or_none(row.get("latitude"))
        lon = _to_float_or_none(row.get("longitude"))
        if lat is None or lon is None:
            continue
        key = (round(lat, 4), round(lon, 4))
        cand = candidates.get(key)
        if cand is None:
            candidates[key] = {"has_nonzero": False}
            cand = candidates[key]
        swh_f = _to_float_or_none(row.get("significant_wave_height"))
        if swh_f is not None and swh_f > 0:
            cand["has_nonzero"] = True

    best = None
    best_dist2 = None
    for (lat, lon), meta in candidates.items():
        if not meta.get("has_nonzero"):
            continue
        dist2 = (lat - target_lat) ** 2 + (lon - target_lon) ** 2
        if best is None or dist2 < best_dist2:
            best = (lat, lon)
            best_dist2 = dist2

    return best


# Request at most this many days ahead; dataset coverage is ~15 days and ERDDAP
# returns 404 "Your query produced no matching results" when time is outside actual_range.
IMI_MAX_FORECAST_DAYS = 5


def fetch_imi_forecast(latitude, longitude, beach_direction, ideal_swell_direction):
    """
    Fetch wave forecast from IMI ERDDAP for one grid point.
    Returns list of forecast-like dicts (wave fields only; wind/met are None).
    """
    if not in_imi_bounds(latitude, longitude):
        return []

    lat, lon = _snap_to_grid(latitude, longitude)
    time_start = arrow.utcnow()
    # Keep request within dataset's rolling window to avoid 404 (time outside actual_range).
    time_end = time_start.shift(days=+IMI_MAX_FORECAST_DAYS).ceil("hour")
    time_start_iso = time_start.format("YYYY-MM-DDTHH:mm:ss") + "Z"
    time_end_iso = time_end.format("YYYY-MM-DDTHH:mm:ss") + "Z"

    # First try: exact snapped point. In inlets/nearshore this can land on a masked (land) cell and return 0.
    url = _build_griddap_url(time_start_iso, time_end_iso, lat, lat, lon, lon)
    rows = _fetch_erddap_rows(url)

    # Fallback: if it looks like land/mask, query a small surrounding box and pick the nearest wet cell.
    if _looks_like_land_or_mask(rows):
        radius_cells = 2  # 2 * 0.025° ~= 5.5 km; small enough to stay nearshore but usually finds ocean
        lat_min = max(IMI_LAT_MIN, round(lat - radius_cells * IMI_GRID_RES, 4))
        lat_max = min(IMI_LAT_MAX, round(lat + radius_cells * IMI_GRID_RES, 4))
        lon_min = max(IMI_LON_MIN, round(lon - radius_cells * IMI_GRID_RES, 4))
        lon_max = min(IMI_LON_MAX, round(lon + radius_cells * IMI_GRID_RES, 4))
        url_box = _build_griddap_url(time_start_iso, time_end_iso, lat_min, lat_max, lon_min, lon_max)
        box_rows = _fetch_erddap_rows(url_box)
        best = _choose_best_cell(box_rows, latitude, longitude)
        if best is not None:
            best_lat, best_lon = best
            rows = [r for r in box_rows if round(_to_float_or_none(r.get("latitude")) or -999, 4) == best_lat
                    and round(_to_float_or_none(r.get("longitude")) or -999, 4) == best_lon]
        # If we couldn't find a better wet cell, keep the original point result (likely 0/masked).

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
