import anyio
import sys
import logging
from typing import Dict, Any
from datetime import datetime
from dateutil import parser as date_parser
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEATHER_ASSISTANT_PROMPT = """You are a helpful weather assistant with access to daily forecast tools.
Use these tools to provide accurate 3‑day weather forecasts based on a preferences.json input."""

async def _call_tool_handler(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "daily_forecast":
        return await daily_forecast(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def _list_tools_handler() -> list[types.Tool]:
    return [
        types.Tool(
            name="daily_forecast",
            description="Get daily weather forecast for a city between start_date and end_date",
            inputSchema={
                "type": "object",
                "required": ["city", "start_date", "end_date"],
                "properties": {
                    "city": {"type": "string"},
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"},
                },
            },
        )
    ]

async def _list_prompts_handler() -> list[types.Prompt]:
    return [
        types.Prompt(
            name="weather_assistant",
            description="3‑day weather forecasting agent",
            arguments=[],
        )
    ]

async def _get_prompt_handler(name: str, arguments: dict) -> types.GetPromptResult:
    return types.GetPromptResult(
        messages=[types.PromptMessage(role="system", content=types.TextContent(type="text", text=WEATHER_ASSISTANT_PROMPT))]
    )

def create_server() -> Server:
    app = Server("weather-server")
    app.call_tool()(_call_tool_handler)
    app.list_tools()(_list_tools_handler)
    app.list_prompts()(_list_prompts_handler)
    app.get_prompt()(_get_prompt_handler)
    return app

def geocode(city: str) -> (float, float):
    resp = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": city, "count": 1}, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise ValueError(f"No location found for {city}")
    loc = results[0]
    return loc["latitude"], loc["longitude"]

async def daily_forecast(args: Dict[str, Any]) -> list[types.TextContent]:
    city = args["city"]
    start = date_parser.isoparse(args["start_date"]).date().isoformat()
    end = date_parser.isoparse(args["end_date"]).date().isoformat()
    lat, lon = geocode(city)
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start,
            "end_date": end,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "timezone": "auto"
        },
        timeout=10
    )
    resp.raise_for_status()
    j = resp.json()
    lines = []
    for d, tmax, tmin, prec, wc in zip(j["daily"]["time"], j["daily"]["temperature_2m_max"], j["daily"]["temperature_2m_min"], j["daily"]["precipitation_sum"], j["daily"]["weathercode"]):
        lines.append(f"{d}: high {tmax}°C, low {tmin}°C, precip {prec} mm, code {wc}")
    return [types.TextContent(type="text", text=f"Forecast for {city}:\n" + "\n".join(lines))]

def main() -> int:
    logger.info("Starting Weather MCP Server...")
    app = create_server()
    async def arun():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
    anyio.run(arun)
    return 0

if __name__ == "__main__":
    sys.exit(main())