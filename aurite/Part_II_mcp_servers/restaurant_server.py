import anyio
import sys
import logging
import os
import requests
import json
from typing import Dict, Any, List, Set, Tuple
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from dotenv import load_dotenv
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
if not API_KEY:
    logger.error("Please set GOOGLE_PLACES_API_KEY in .env")
    sys.exit(1)

recommended_addresses: Set[str] = set()
recommended_coords: List[Tuple[float, float]] = []

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = radians(lat2 - lat1)
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))

def is_near_duplicate(lat: float, lon: float, address: str) -> bool:
    for prev_lat, prev_lon in recommended_coords:
        if haversine(lat, lon, prev_lat, prev_lon) < 300:
            return True
    return address in recommended_addresses

async def search_top_restaurant(args: Dict[str, Any]) -> List[types.TextContent]:
    location_text = args.get("location")
    date_str = args.get("date")

    if not location_text:
        return [types.TextContent(type="text", text="ERROR: Please provide a location name.")]

    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_params = {"address": location_text, "key": API_KEY}
    geo_resp = requests.get(geo_url, params=geo_params, timeout=5).json()
    if not geo_resp.get("results"):
        return [types.TextContent(type="text", text="ERROR: Could not find the location.")]
    loc = geo_resp["results"][0]["geometry"]["location"]
    lat, lon = loc["lat"], loc["lng"]

    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    nearby_params = {
        "location": f"{lat},{lon}",
        "radius": 3000,
        "type": "restaurant",
        "key": API_KEY
    }
    nearby_resp = requests.get(nearby_url, params=nearby_params, timeout=10).json()
    candidates = nearby_resp.get("results", [])

    sorted_places = sorted(candidates, key=lambda p: p.get("rating", 0), reverse=True)
    selected_place = None
    for place in sorted_places:
        place_id = place.get("place_id")
        detail_url = "https://maps.googleapis.com/maps/api/place/details/json"
        detail_params = {
            "place_id": place_id,
            "fields": "name,rating,formatted_address,geometry,opening_hours,types",
            "key": API_KEY
        }
        detail_resp = requests.get(detail_url, params=detail_params, timeout=10).json()
        det = detail_resp.get("result", {})
        rest_lat = det.get("geometry", {}).get("location", {}).get("lat")
        rest_lon = det.get("geometry", {}).get("location", {}).get("lng")
        address = det.get("formatted_address", "")
        if not is_near_duplicate(rest_lat, rest_lon, address):
            selected_place = det
            recommended_addresses.add(address)
            recommended_coords.append((rest_lat, rest_lon))
            break

    if not selected_place:
        return [types.TextContent(type="text", text="*Restaurant information not available*")]

    name = selected_place.get("name", "Unknown")
    address = selected_place.get("formatted_address")
    rating = selected_place.get("rating")
    types_list = [t for t in selected_place.get("types", []) if "restaurant" not in t]
    opening_text = selected_place.get("opening_hours", {}).get("weekday_text", [])
    opening_info = ""
    if opening_text and date_str:
        try:
            weekday_idx = datetime.strptime(date_str, "%Y-%m-%d").weekday()
            opening_info = opening_text[weekday_idx]
        except Exception:
            pass

    markdown = f"""- **Name:** {name}
- **Address:** {address}
- **Rating:** {rating}
- **Opening Hours:** {opening_info}
- **Cuisine:** {', '.join(types_list) if types_list else 'Unknown'}"""

    return [types.TextContent(type="text", text=markdown)]

async def _call_tool_handler(name: str, arguments: dict) -> List[types.TextContent]:
    if name == "top_restaurant":
        return await search_top_restaurant(arguments)
    raise ValueError(f"Unknown tool: {name}")

async def _list_tools_handler() -> List[types.Tool]:
    return [types.Tool(
        name="top_restaurant",
        description="Find top-rated restaurant near a location with Markdown output (no duplicates nearby)",
        inputSchema={
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "date": {"type": "string"}
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
    logger.info("Starting Restaurant MCP Server with deduplication...")
    app = create_server()
    async def run():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())
    anyio.run(run)
    return 0

if __name__ == "__main__":
    sys.exit(main())