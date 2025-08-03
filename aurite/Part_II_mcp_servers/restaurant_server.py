# import anyio
# import sys
# import logging
# import os
# import requests
# from typing import Dict, Any, List
# from mcp.server.lowlevel import Server
# from mcp.server.stdio import stdio_server
# import mcp.types as types
# from dotenv import load_dotenv
# from datetime import datetime
# from math import radians, cos, sin, sqrt, atan2
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# load_dotenv()
#
# API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
# if not API_KEY:
#     logger.error("Please set GOOGLE_PLACES_API_KEY in .env")
#     sys.exit(1)
#
# # Store previous recommended restaurants and their coordinates
# previous_recommendations = []  # Each item is (lat, lon, place_id)
#
# def haversine(lat1, lon1, lat2, lon2):
#     R = 6371.0
#     dlat = radians(lat2 - lat1)
#     dlon = radians(lon2 - lon1)
#     a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
#     c = 2 * atan2(sqrt(a), sqrt(1 - a))
#     return R * c
#
# def is_nearby(lat, lon, previous_lat, previous_lon, threshold_km=1.0):
#     return haversine(lat, lon, previous_lat, previous_lon) <= threshold_km
#
# async def search_top_restaurant(args: Dict[str, Any]) -> List[types.TextContent]:
#     location_text = args.get("location")
#     date_str = args.get("date")
#
#     if not location_text:
#         return [types.TextContent(type="text", text="ERROR: Please provide a location name.")]
#
#     geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
#     geo_params = {"address": location_text, "key": API_KEY}
#     geo_resp = requests.get(geocode_url, params=geo_params, timeout=5)
#     geo_resp.raise_for_status()
#     geo_data = geo_resp.json()
#     if not geo_data.get("results"):
#         return [types.TextContent(type="text", text="ERROR: Could not find the location.")]
#     location = geo_data["results"][0]["geometry"]["location"]
#     lat = location["lat"]
#     lon = location["lng"]
#
#     nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
#     nearby_params = {
#         "location": f"{lat},{lon}",
#         "radius": 3000,
#         "type": "restaurant",
#         "key": API_KEY
#     }
#     nearby_resp = requests.get(nearby_url, params=nearby_params, timeout=10)
#     nearby_resp.raise_for_status()
#     places = nearby_resp.json().get("results", [])
#     if not places:
#         return [types.TextContent(type="text", text=f"### {location_text} on {date_str}\n- No restaurant found nearby.")]
#
#     # Try to find a restaurant that hasn't been recommended nearby before
#     selected_place = None
#     for place in sorted(places, key=lambda p: p.get("rating", 0), reverse=True):
#         place_lat = place["geometry"]["location"]["lat"]
#         place_lon = place["geometry"]["location"]["lng"]
#         place_id = place.get("place_id")
#
#         is_duplicate = False
#         for prev_lat, prev_lon, prev_id in previous_recommendations:
#             if is_nearby(lat, lon, prev_lat, prev_lon) and place_id == prev_id:
#                 is_duplicate = True
#                 break
#
#         if not is_duplicate:
#             selected_place = place
#             previous_recommendations.append((lat, lon, place_id))
#             break
#
#     if not selected_place:
#         return [types.TextContent(type="text", text=f"### {location_text} on {date_str}\n- All top restaurants already recommended nearby.")]
#
#     place_id = selected_place.get("place_id")
#     name = selected_place.get("name", "Unknown")
#
#     detail_url = "https://maps.googleapis.com/maps/api/place/details/json"
#     detail_params = {
#         "place_id": place_id,
#         "fields": "name,rating,formatted_address,opening_hours,types",
#         "key": API_KEY
#     }
#     detail_resp = requests.get(detail_url, params=detail_params, timeout=10)
#     detail_resp.raise_for_status()
#     det = detail_resp.json().get("result", {})
#     address = det.get("formatted_address")
#     rating = det.get("rating")
#     types_list = [t for t in det.get("types", []) if "restaurant" not in t]
#     opening_text = det.get("opening_hours", {}).get("weekday_text", [])
#
#     if opening_text and date_str:
#         try:
#             weekday_idx = datetime.strptime(date_str, "%Y-%m-%d").weekday()
#             opening_info = opening_text[weekday_idx]
#         except Exception:
#             opening_info = ""
#     else:
#         opening_info = ""
#
#     markdown = f"""
# - **Name**: {name}
# - **Address**: {address}
# - **Rating**: {rating}
# - **Opening Hours**: {opening_info}
# - **Cuisine**: {', '.join(types_list) if types_list else 'Unknown'}
# """
#
#     return [types.TextContent(type="text", text=markdown.strip())]
#
# async def _call_tool_handler(name: str, arguments: dict) -> List[types.TextContent]:
#     if name == "top_restaurant":
#         return await search_top_restaurant(arguments)
#     raise ValueError(f"Unknown tool: {name}")
#
# async def _list_tools_handler() -> List[types.Tool]:
#     return [types.Tool(
#         name="top_restaurant",
#         description="Find highest-rated restaurant near a location on a specific date and return Markdown",
#         inputSchema={
#             "type": "object",
#             "properties": {
#                 "location": {"type": "string", "description": "Name or address of the location"},
#                 "date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
#             },
#             "required": ["location", "date"]
#         }
#     )]
#
# def create_server() -> Server:
#     app = Server("restaurant_server")
#     app.call_tool()(_call_tool_handler)
#     app.list_tools()(_list_tools_handler)
#     return app
#
# def main() -> int:
#     logger.info("Starting Restaurant MCP Server...")
#     app = create_server()
#     async def run():
#         async with stdio_server() as streams:
#             await app.run(streams[0], streams[1], app.create_initialization_options())
#     anyio.run(run)
#     return 0
#
# if __name__ == "__main__":
#     sys.exit(main())
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

# session memory to avoid duplicates
recommended_addresses: Set[str] = set()
recommended_coords: List[Tuple[float, float]] = []

# Haversine distance calculator
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # meters
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

    # Get coordinates
    geo_url = "https://maps.googleapis.com/maps/api/geocode/json"
    geo_params = {"address": location_text, "key": API_KEY}
    geo_resp = requests.get(geo_url, params=geo_params, timeout=5).json()
    if not geo_resp.get("results"):
        return [types.TextContent(type="text", text="ERROR: Could not find the location.")]
    loc = geo_resp["results"][0]["geometry"]["location"]
    lat, lon = loc["lat"], loc["lng"]

    # Get restaurants
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    nearby_params = {
        "location": f"{lat},{lon}",
        "radius": 3000,
        "type": "restaurant",
        "key": API_KEY
    }
    nearby_resp = requests.get(nearby_url, params=nearby_params, timeout=10).json()
    candidates = nearby_resp.get("results", [])

    # Try restaurants one by one based on rating
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

    # Extract and format details
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