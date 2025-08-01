import anyio
import sys
import logging
import os
import requests
from typing import Dict, Any, List
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from dotenv import load_dotenv
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
if not API_KEY:
    logger.error("Please set GOOGLE_PLACES_API_KEY in .env")
    sys.exit(1)

async def search_top_restaurant(args: Dict[str, Any]) -> List[types.TextContent]:
    location_text = args.get("location")
    date_str = args.get("date")

    if not location_text:
        return [types.TextContent(type="text", text="ERROR: Please provide a location name.")]

    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_params = {"address": location_text, "key": API_KEY}
    geo_resp = requests.get(geocode_url, params=geo_params, timeout=5)
    geo_resp.raise_for_status()
    geo_data = geo_resp.json()
    if not geo_data.get("results"):
        return [types.TextContent(type="text", text="ERROR: Could not find the location.")]
    location = geo_data["results"][0]["geometry"]["location"]
    lat = location["lat"]
    lon = location["lng"]

    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    nearby_params = {
        "location": f"{lat},{lon}",
        "radius": 3000,
        "type": "restaurant",
        "key": API_KEY
    }
    nearby_resp = requests.get(nearby_url, params=nearby_params, timeout=10)
    nearby_resp.raise_for_status()
    places = nearby_resp.json().get("results", [])
    if not places:
        return [types.TextContent(type="text", text="No restaurant found nearby.")]

    best = max(places, key=lambda p: p.get("rating", 0) or 0)
    place_id = best.get("place_id")
    name = best.get("name", "Unknown")

    detail_url = "https://maps.googleapis.com/maps/api/place/details/json"
    detail_params = {
        "place_id": place_id,
        "fields": "name,rating,formatted_address,opening_hours,types",
        "key": API_KEY
    }
    detail_resp = requests.get(detail_url, params=detail_params, timeout=10)
    detail_resp.raise_for_status()
    det = detail_resp.json().get("result", {})
    address = det.get("formatted_address")
    rating = det.get("rating")
    types_list = [t for t in det.get("types", []) if "restaurant" not in t]
    opening_text = det.get("opening_hours", {}).get("weekday_text", [])

    if opening_text and date_str:
        try:
            weekday_idx = datetime.strptime(date_str, "%Y-%m-%d").weekday()
            opening_info = opening_text[weekday_idx]
        except Exception:
            opening_info = opening_text
    else:
        opening_info = opening_text

    result = {
        "name": name,
        "address": address,
        "rating": rating,
        "opening_hours": opening_info,
        "category": types_list
    }
    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

async def _call_tool_handler(name: str, arguments: dict) -> List[types.TextContent]:
    if name == "top_restaurant":
        return await search_top_restaurant(arguments)
    raise ValueError(f"Unknown tool: {name}")

async def _list_tools_handler() -> List[types.Tool]:
    return [types.Tool(
        name="top_restaurant",
        description="Find highest-rated restaurant near a location on a specific date",
        inputSchema={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Name or address of the location"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
            },
            "required": ["location", "date"]
        }
    )]

def create_server() -> Server:
    app = Server("restaurant_server")
    app.call_tool()(_call_tool_handler)
    app.list_tools()(_list_tools_handler)
    return app

def main() -> int:
    logger.info("Starting Restaurant MCP Server...")
    app = create_server()
    async def run():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
    anyio.run(run)
    return 0

if __name__ == "__main__":
    sys.exit(main())