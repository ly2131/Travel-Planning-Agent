import json
import requests

def load_preferences():
    with open("location.json", "r") as f:
        return json.load(f)

def geocode(city: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    resp = requests.get(url, params={"name": city, "count": 1}, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        raise ValueError(f"No geo result for '{city}'")
    loc = results[0]
    return loc["latitude"], loc["longitude"]

def fetch_daily_forecast(lat, lon, start, end):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto"
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def main():
    prefs = load_preferences()
    for entry in prefs:
        city = entry["city"]
        start = entry["start_date"]
        end = entry["end_date"]
        lat, lon = geocode(city)
        data = fetch_daily_forecast(lat, lon, start, end)
        print(f"\n {city}: {start} to {end}")
        for date, tmax, tmin, precip in zip(
            data["daily"]["time"],
            data["daily"]["temperature_2m_max"],
            data["daily"]["temperature_2m_min"],
            data["daily"]["precipitation_sum"]
        ):
            print(f"{date}: High {tmax}°C, Low {tmin}°C, Precip {precip} mm")

if __name__ == "__main__":
    main()