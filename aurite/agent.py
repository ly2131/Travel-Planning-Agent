import os
import json
import asyncio
import logging
from termcolor import colored
from aurite import Aurite
from aurite.config.config_models import AgentConfig, LLMConfig
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_preferences():
    base = os.path.dirname(__file__)
    path = os.path.join(base, "location.json")
    with open(path, "r") as f:
        return json.load(f)

def geocode(city: str):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    resp = requests.get(url, params={"name": city, "count": 1}, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        raise ValueError(f"No results for {city}")
    loc = results[0]
    return loc["latitude"], loc["longitude"]

def get_daily_forecast(lat, lon, start, end):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto"
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

async def main():
    from dotenv import load_dotenv
    load_dotenv()
    aurite = Aurite()
    await aurite.initialize()

    llm = LLMConfig(
        llm_id="my_openai_gpt4_turbo",
        provider="openai",
        model_name="gpt-4-turbo-preview",
    )
    await aurite.register_llm_config(llm)

    agent_cfg = AgentConfig(
        name="My Weather Agent",
        system_prompt="Use the tools to fetch weather for each location in preferences.",
        mcp_servers=["weather_server"],
        llm_config_id=llm.llm_id
    )
    await aurite.register_agent(agent_cfg)

    prefs_list = load_preferences()
    for prefs in prefs_list:
        city = prefs["city"]
        start = prefs["start_date"]
        end = prefs["end_date"]

        lat, lon = geocode(city)
        forecast = get_daily_forecast(lat, lon, start, end)
        print(colored(f"\n Weather forecast for {city} ({start} to {end}):", "green"))
        for date, tmax, tmin, precip in zip(
                forecast["daily"]["time"],
                forecast["daily"]["temperature_2m_max"],
                forecast["daily"]["temperature_2m_min"],
                forecast["daily"]["precipitation_sum"]):
            print(f"{date}: High {tmax}°C, Low {tmin}°C, Precip {precip} mm")

    await aurite.shutdown()

if __name__ == "__main__":
    asyncio.run(main())