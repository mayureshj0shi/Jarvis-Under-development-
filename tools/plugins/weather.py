import requests

_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FC_URL = "https://api.open-meteo.com/v1/forecast"

_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "rain",
    65: "heavy rain",
    71: "slight snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    95: "thunderstorm",
}


def get_weather(city):
    try:
        g = requests.get(_GEO_URL, params={"name": city, "count": 1}, timeout=20)
        g.raise_for_status()
        geo = g.json().get("results")
        if not geo:
            return {"error": f"city not found: {city}"}
        lat = geo[0]["latitude"]
        lon = geo[0]["longitude"]
        country = geo[0].get("country", "")
        f = requests.get(
            _FC_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
            },
            timeout=20,
        )
        f.raise_for_status()
        cw = f.json()["current_weather"]
        desc = _CODES.get(cw.get("weathercode"), "unknown")
        return {
            "city": city,
            "country": country,
            "temperature_c": cw.get("temperature"),
            "wind_kph": cw.get("windspeed"),
            "condition": desc,
        }
    except Exception as e:
        return {"error": str(e)}
