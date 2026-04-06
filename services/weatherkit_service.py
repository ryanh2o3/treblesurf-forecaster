"""
Apple WeatherKit REST API integration for weather forecast (wind, precipitation, etc.).
Provides weather-only forecast data; wave data comes from StormGlass or IMI SWAN.
Uses JWT auth with Apple credentials (Team ID, Service ID, Key ID, P8 private key).
"""
import os
import time
import requests
import arrow
from utils.calculations import (
    calculateRelativeWindDirection,
    calculateSurfMessiness,
)

BASE_URL = "https://weatherkit.apple.com/api/v1/weather"
# Hourly forecast window for REST API (default response without range is ~24h).
# IMI SWAN uses ~5 days; 6 days covers that with a small buffer for merge alignment.
WEATHERKIT_HOURLY_FORECAST_DAYS = 6
JWT_EXPIRATION_SECONDS = 86400 * 7  # 7 days
# REST forecastHourly windSpeed is km/h; StormGlass and calculateSurfMessiness use m/s.
_KMH_TO_MS = 1.0 / 3.6


def _get_jwt():
    """
    Build a JWT for WeatherKit. Uses env: APPLE_TEAM_ID, APPLE_SERVICE_ID,
    APPLE_KEY_ID, APPLE_PRIVATE_KEY (PEM string; newlines as \\n or literal).
    Alternatively WEATHERKIT_JWT can be set to a pre-generated token (short-lived).
    """
    token = os.environ.get("WEATHERKIT_JWT")
    if token:
        return token

    try:
        import jwt as pyjwt
    except ImportError:
        raise RuntimeError("PyJWT and cryptography are required for WeatherKit: pip install pyjwt cryptography")

    team_id = os.environ.get("APPLE_TEAM_ID")
    service_id = os.environ.get("APPLE_SERVICE_ID")
    key_id = os.environ.get("APPLE_KEY_ID")
    private_key = os.environ.get("APPLE_PRIVATE_KEY")

    if not all((team_id, service_id, key_id, private_key)):
        return None

    # Restore newlines if stored as \n in env
    if isinstance(private_key, str) and "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")

    now = int(time.time())
    payload = {
        "iss": team_id,
        "iat": now,
        "exp": now + JWT_EXPIRATION_SECONDS,
        "sub": service_id,
    }
    headers = {
        "alg": "ES256",
        "kid": key_id,
        "id": f"{team_id}.{service_id}",
    }
    token = pyjwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers=headers,
    )
    return token if isinstance(token, str) else token.decode("utf-8")


def fetch_weatherkit_forecast(latitude, longitude, beach_direction):
    """
    Fetch hourly weather forecast from Apple WeatherKit (wind, precipitation, etc.).
    Returns list of forecast-like dicts with weather fields set; wave/surf fields are None.
    """
    jwt_token = _get_jwt()
    if not jwt_token:
        print("WeatherKit: no WEATHERKIT_JWT or Apple credentials (APPLE_*), skipping")
        return []

    url = f"{BASE_URL}/en_US/{latitude}/{longitude}"
    hourly_start = arrow.utcnow().floor("hour")
    hourly_end = hourly_start.shift(days=+WEATHERKIT_HOURLY_FORECAST_DAYS).ceil("hour")
    iso_start = hourly_start.format("YYYY-MM-DDTHH:mm:ss") + "Z"
    iso_end = hourly_end.format("YYYY-MM-DDTHH:mm:ss") + "Z"
    params = {
        "dataSets": "forecastHourly",
        "hourlyStart": iso_start,
        "hourlyEnd": iso_end,
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=60)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"WeatherKit request failed: {e}")
        return []

    try:
        data = r.json()
    except ValueError as e:
        print(f"WeatherKit JSON parse failed: {e}")
        return []

    # Response has forecastHourly.hours (array of hourly forecasts)
    forecast = data.get("forecastHourly")
    if not forecast:
        forecast = data.get("hourlyForecast") or data.get("hourly")
    if not forecast:
        print("WeatherKit: no forecastHourly in response")
        return []

    hours = forecast.get("hours") or forecast.get("hourly") or []
    if not hours:
        return []

    formatted = []
    for h in hours:
        # Apple uses forecastStartTime (ISO 8601)
        start = h.get("forecastStartTime") or h.get("time") or h.get("forecastStart")
        if not start:
            continue
        dt = arrow.get(start)
        date_forecasted = dt.format("YYYY-MM-DD HH:mm:ss")

        temp = h.get("temperature")
        humidity = h.get("humidity")
        pressure = h.get("pressure")
        wind_speed_raw = h.get("windSpeed")
        wind_speed = (
            float(wind_speed_raw) * _KMH_TO_MS if wind_speed_raw is not None else None
        )
        wind_dir = h.get("windDirection")
        precip = h.get("precipitationAmount") or h.get("precipitation") or 0.0
        if precip is None:
            precip = 0.0

        relative_wind = None
        surf_messiness = None
        if wind_dir is not None and beach_direction is not None:
            relative_wind = calculateRelativeWindDirection(wind_dir, beach_direction)
        if wind_dir is not None and wind_speed is not None and beach_direction is not None:
            surf_messiness = calculateSurfMessiness(wind_dir, wind_speed, beach_direction)

        entry = {
            "dateForecastedFor": date_forecasted,
            "temperature": float(temp) if temp is not None else None,
            "humidity": float(humidity) if humidity is not None else None,
            "pressure": float(pressure) if pressure is not None else None,
            "windSpeed": wind_speed,
            "precipitation": float(precip) if precip is not None else None,
            "windDirection": float(wind_dir) if wind_dir is not None else None,
            "waterTemperature": None,
            "swellHeight": None,
            "swellPeriod": None,
            "swellDirection": None,
            "surfSize": None,
            "waveEnergy": None,
            "relativeWindDirection": relative_wind,
            "surfMessiness": surf_messiness,
            "directionQuality": None,
        }
        formatted.append(entry)

    return formatted
