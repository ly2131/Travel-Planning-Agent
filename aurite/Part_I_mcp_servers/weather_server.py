import anyio
import sys
import logging
from typing import Dict, Any, List
from dateutil import parser as date_parser
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEATHER_ASSISTANT_PROMPT = """You are a helpful weather assistant with access to daily forecast tools.
Use these tools to provide average weather statistics (temperature, precipitation) for each city over a specified date range."""

async def _call_tool_handler(name: str, arguments: dict) -> List[types.TextContent]:
    if name == "multi_city_weather_summary":
        return await multi_city_weather_summary(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def _list_tools_handler() -> List[types.Tool]:
    return [
        types.Tool(
            name="multi_city_weather_summary",
            description="Get average daily weather stats for multiple cities between start_date and end_date",
            inputSchema={
                "type": "object",
                "required": ["cities", "start_date", "end_date"],
                "properties": {
                    "cities": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "start_date": {"type": "string", "format": "date"},
                    "end_date": {"type": "string", "format": "date"}
                }
            },
        )
    ]

async def _list_prompts_handler() -> List[types.Prompt]:
    return [
        types.Prompt(
            name="weather_assistant",
            description="Summarizes average weather data for each city",
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

async def multi_city_weather_summary(args: Dict[str, Any]) -> List[types.TextContent]:
    start = date_parser.isoparse(args["start_date"]).date().isoformat()
    end = date_parser.isoparse(args["end_date"]).date().isoformat()
    output_lines = []

    for city in args["cities"]:
        lat, lon = geocode(city)
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "start_date": start,
                "end_date": end,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto"
            },
            timeout=10
        )
        resp.raise_for_status()
        j = resp.json()
        days = len(j["daily"]["time"])
        avg_max_temp = sum(j["daily"]["temperature_2m_max"]) / days
        avg_min_temp = sum(j["daily"]["temperature_2m_min"]) / days
        avg_precip = sum(j["daily"]["precipitation_sum"]) / days

        output_lines.append(f"{city}: Avg High = {avg_max_temp:.1f}°C, Avg Low = {avg_min_temp:.1f}°C, Avg Precip = {avg_precip:.1f} mm")

    return [types.TextContent(type="text", text="\n".join(output_lines))]

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