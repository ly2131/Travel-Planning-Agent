import asyncio
import logging
import json
import os
from aurite import Aurite
from aurite.config.config_models import AgentConfig, LLMConfig, ClientConfig
import markdown
import pdfkit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def partII():
    from dotenv import load_dotenv

    load_dotenv()

    aurite = Aurite()

    try:
        await aurite.initialize()

        # region Attraction selection
        # 1. Define and register an MCP server configuration
        mcp_server_config = ClientConfig(
            name="Google Places Server",
            # This path is relative to your project root
            server_path="Part_II_mcp_servers/google_place_server.py",
            capabilities=["tools"],
        )
        await aurite.register_client(mcp_server_config)
        # 2. Define a JSON schema for a structured output
        schema = {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "The latitude coordinate of the city"
                },
                "longitude": {
                    "type": "number",
                    "description": "The longitude coordinate of the city"
                },
                "travel_days": {
                    "type": "integer",
                    "description": "The total number of travel days (including start and end dates)"
                }
            },
            "required": [
                "latitude",
                "longitude",
                "travel_days"
            ]
        }
        # 3. Define and register an Agent configuration
        agent_config = AgentConfig(
            name="extract city info Agent",
            system_prompt=(
                "You are a travel planning assistant. Your task is to extract travel information from user queries and return structured data.\n\n"
                "For each user query:\n"
                "1. Extract the city name from the user's input, then output the latitude and longitude of the city\n"
                "2. Extract the start date and end date (in YYYY-MM-DD format)\n"
                "3. Calculate the total number of travel days (including both start and end dates)\n"
                "4. Return ONLY a JSON object in this exact format:\n"
                "{\n"
                '  "latitude": <latitude_value>,\n'
                '  "longitude": <longitude_value>,\n'
                '  "travel_days": <calculated_days>\n'
                "}\n\n"
                "Important rules:\n"
                "- Always return ONLY the JSON object, no additional text or explanations\n"
                "- The JSON must contain exactly these three fields: latitude, longitude, travel_days\n"
                "- Calculate travel_days as (end_date - start_date) + 1\n"
                "- If you cannot extract the information, return a JSON with default values\n\n"
                "Example input: 'I want to travel to Beijing from 2025-07-01 to 2025-07-05'\n"
                "Expected output: {\"latitude\": 39.9042, \"longitude\": 116.4074, \"travel_days\": 5}"
            ),
            # mcp_servers=["Google Places Server"],
            llm_config_id="openai_gpt4_turbo",
            config_validation_schema=schema
        )
        await aurite.register_agent(agent_config)
        # 4. Coustruct input
        with open("agt_msg/preference.json", "r", encoding="utf-8") as f:
            preference = json.load(f)
        with open("agt_msg/recommendation_result.json", "r", encoding="utf-8") as f:
            recommendation = json.load(f)
        travel_info = {
            "start_date": preference["start_date"],
            "end_date": preference["end_date"],
            "city": recommendation["recommended_city"]
        }
        # 5. Run the agent with the user's query. The check for the execution
        # facade is now handled internally by the `aurite.run_agent` method.
        agent_result = await aurite.run_agent(
            agent_name="extract city info Agent",
            user_message=json.dumps(travel_info)
        )
        # 6. parse multi-output results
        results = json.loads(agent_result.primary_text)
        # 7. 配置 推荐agent，来获取Google Place MCP Server的返回， Google place API最多只能返回20个地点
        recommend_agent_config = AgentConfig(
            name="recommend tourist_attraction Agent",
            system_prompt=(
                "You are a tourist attraction recommendation assistant. Your task is to use the provided latitude and longitude coordinates to search for nearby tourist attractions.\n\n"
                "For each request:\n"
                "1. Extract the latitude and longitude from the user's input\n"
                "2. Use the search_nearby tool from Google Places Server to find tourist attractions in that area\n"
                "3. Return ONLY the raw JSON response from the search_nearby tool call\n\n"
                "CRITICAL RULES:\n"
                "- You MUST return ONLY the JSON response from the search_nearby tool\n"
                "- Do NOT modify, format, or add any text to the tool response\n"
                "- Do NOT add explanations, summaries, or any additional content\n"
                "- Return the exact JSON string as returned by the MCP server\n"
                "- If the tool returns an error, return the error JSON as-is\n\n"
                "Example:\n"
                "Input: {\"latitude\": 40.7128, \"longitude\": -74.006, \"travel_days\": 4}\n"
                "Action: Call search_nearby(latitude=40.7128, longitude=-74.006)\n"
                "Output: Return the exact JSON response from the tool call, no modifications"
            ),
            mcp_servers=["Google Places Server"],
            llm_config_id="openai_gpt4_turbo",
            # config_validation_schema=recommend_agent_config_schema
        )
        await aurite.register_agent(recommend_agent_config)
        # 调用推荐 Agent
        mcp_result = await aurite.run_agent(
            agent_name="recommend tourist_attraction Agent",
            user_message=json.dumps(results)  # 传入之前的结果
        )
        # 8. 解析 MCP Server 返回的 JSON 结果，给user选择
        try:
            attractions_data = json.loads(mcp_result.primary_text)
            if "places" in attractions_data and attractions_data["places"]:
                places = attractions_data["places"]
                travel_days = results["travel_days"]
                min_selections = travel_days  # 最少选择天数个
                max_selections = min(travel_days * 2, 20)  # 最多选择 min(天数*2, 20) 个

                print(f"\n🎯 Found {len(places)} tourist attractions")
                print(f"📅 You have {travel_days} travel days")
                print(f"🎯 Please select between {min_selections} and {max_selections} attractions for your trip:")

                # 显示所有景点供用户选择
                for i, place in enumerate(places, 1):
                    name = place.get('name', 'Unknown')
                    address = place.get('address', 'No address')
                    rating = place.get('rating', 'No rating')
                    rating_count = place.get('rating_count', 'No rating')
                    types = place.get('types', [])

                    print(f"\n{i}. {name}")
                    print(f"   📍 Address: {address}")
                    print(f"   ⭐ Rating: {rating}, Rating count: {rating_count}")
                    print(f"   🏷️  Types: {', '.join(types)}")  # 显示全部类型

                # 用户选择
                selected_indices = []
                print(f"\n🎯 Please select between {min_selections} and {max_selections} attractions")
                print("Enter numbers separated by spaces, e.g., 1 3 5")
                print("Type 'done' when finished, 'quit' to cancel:")

                while True:
                    try:
                        user_input = input(
                            f"Selection {len(selected_indices) + 1} (min: {min_selections}, max: {max_selections}): ").strip()

                        if user_input.lower() == 'quit':
                            print("🛑 Selection cancelled.")
                            break

                        if user_input.lower() == 'done':
                            if len(selected_indices) >= min_selections:
                                print(f"✅ Selection completed with {len(selected_indices)} attractions")
                                break
                            else:
                                print(f"❌ You need to select at least {min_selections} attractions")
                                continue

                        # 解析用户输入的数字
                        input_numbers = [int(x) for x in user_input.split() if x.isdigit()]

                        for num in input_numbers:
                            if 1 <= num <= len(places) and num not in selected_indices:
                                if len(selected_indices) < max_selections:
                                    selected_indices.append(num)
                                    print(f"✅ Selected: {places[num - 1].get('name', 'Unknown')}")
                                else:
                                    print(f"❌ Maximum selections ({max_selections}) reached")
                                    break
                            elif num in selected_indices:
                                print(f"⚠️  {num} already selected")
                            else:
                                print(f"❌ Invalid selection: {num}")

                        # 检查是否达到最大选择数
                        if len(selected_indices) >= max_selections:
                            print(f"✅ Maximum selections ({max_selections}) reached")
                            break

                    except ValueError:
                        print("❌ Please enter valid numbers separated by spaces")
                    except KeyboardInterrupt:
                        print("\n🛑 Selection interrupted.")
                        break

                # 检查是否达到最少选择数
                if len(selected_indices) < min_selections:
                    print(
                        f"❌ You only selected {len(selected_indices)} attractions, but need at least {min_selections}")
                    print("🛑 Selection cancelled.")
                    return

                # 构建最终结果
                if selected_indices:
                    selected_places = []
                    for idx in selected_indices:
                        selected_places.append(places[idx - 1])

                    final_result = {
                        "travel_info": {
                            "city": "Extracted from previous step",
                            "start_date": "Extracted from previous step",
                            "end_date": "Extracted from previous step",
                            "travel_days": travel_days,
                            "coordinates": {
                                "latitude": results["latitude"],
                                "longitude": results["longitude"]
                            }
                        },
                        "selected_attractions": selected_places,
                        "total_selected": len(selected_places),
                        "min_selections": min_selections,
                        "max_selections": max_selections,
                        "selection_range": f"{min_selections}-{max_selections}"
                    }

                    print(f"\n🎉 Successfully selected {len(selected_places)} attractions!")
                    print(f"📅 Selection range: {min_selections}-{max_selections} attractions")
                    print("\n📋 Final Selection:")
                    for i, place in enumerate(selected_places, 1):
                        print(f"{i}. {place.get('name', 'Unknown')}")
                        print(f"   📍 {place.get('address', 'No address')}")
                        print(f"   ⭐ {place.get('rating', 'No rating')}")
                        print()

                    # 保存最终结果
                    with open('agt_msg/selected_attractions.json', 'w', encoding='utf-8') as f:
                        json.dump(final_result, f, ensure_ascii=False, indent=2)

                    print("📋 Results saved to 'selected_attractions.json'")

                else:
                    print("❌ No attractions selected")
            else:
                print("❌ No tourist attractions found in the area")
        except json.JSONDecodeError:
            print("❌ Failed to parse attractions data")
            print("Raw response:", mcp_result.primary_text)
        except Exception as e:
            print(f"❌ Error processing attractions: {e}")
        # endregion

        # region Daily itinerary planner
        # 1. Define and register MCP server configurations
        google_maps_config = ClientConfig(
            name="Google Maps MCP Server",
            description="Google Maps MCP server for geocoding and mapping services",
            transport_type="local",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-google-maps"],
            capabilities=["tools"],
            env={"GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY")},
            timeout=30.0
        )
        await aurite.register_client(google_maps_config)
        # 2. Define an Agent configuration (used dynamically)
        agent_config = AgentConfig(
            name="Daily Itinerary Planner Agent",
            system_prompt=(
                "You are a travel itinerary planning specialist.\n\n"

                "TASK: Generate a daily itinerary for EVERY SINGLE DATE based on user requirements.\n\n"

                "WORKFLOW:\n"
                "1. ANALYZE the user's input for:\n"
                "   - Start date and end date\n"
                "   - City\n"
                "   - Preferred attractions (if any)\n\n"

                "2. For each day:\n"
                "   a. SELECT ATTRACTIONS:\n"
                "      - First, use any preferred attractions provided by the user\n"
                "      - Then, use Scrapeless MCP Server to discover additional attractions in the specified city\n"
                "      - Choose exactly ONE morning attraction and ONE afternoon attraction NAME per day\n"
                "      - You MUST NOT repeat any attraction name across different dates\n\n"

                "   b. DESCRIBE ACTIVITY:\n"
                "      - For each selected attraction, generate ONE sentence describing a typical activity a tourist might do there\n"
                "      - Keep the activity line brief\n\n"

                "OUTPUT FORMAT (STRICT):\n"
                "- Markdown format ONLY\n"
                "- Each day's plan must include:\n"
                "  - Morning: [Attraction Name]\n"
                "  - Activity: [One sentence summary]\n"
                "  - Afternoon: [Attraction Name]\n"
                "  - Activity: [One sentence summary]\n\n"

                "EXAMPLE:\n"
                "Date: 2025-06-01\n"
                "- Morning: The Getty Center\n"
                "- Activity: Explore modern and classical art exhibitions.\n"
                "- Afternoon: Griffith Observatory\n"
                "- Activity: View the city skyline through telescopes and exhibits.\n\n"

                "CRITICAL RULES (MANDATORY):\n"
                "- DO NOT include any introductions, summaries, explanations, assumptions, apologies, or closing remarks.\n"
                "- DO NOT write anything like 'Here's your itinerary', 'based on your preferences', or 'I’m unable to access...'.\n"
                "- DO NOT invent activities that are not tied to actual attractions.\n"
                "- DO NOT output anything except Markdown in the above format — no other text is allowed.\n"
                "- Morning and Afternoon lines must ONLY be place names (attraction name only, no verbs or descriptions).\n"
            ),
            mcp_servers=["Scrapeless MCP Server"],
            llm_config_id="openai_gpt4_turbo",
        )
        await aurite.register_agent(agent_config)
        # 3. Define the user's query for the agent using structured JSON input. Save the result
        with open("agt_msg/selected_attractions.json", "r", encoding="utf-8") as f:
            attraction = json.load(f)
        preferred_attractions = [
            item["name"] for item in attraction["selected_attractions"]
        ]
        itinerary_input = {
            "start_date": travel_info["start_date"],
            "end_date": travel_info["end_date"],
            "city": travel_info["city"],
            "activities": preference["activities"],
            "avoid": preference["avoid"],
            "preferred_attractions": preferred_attractions
        }
        agent_result = await aurite.run_agent(
            agent_name="Daily Itinerary Planner Agent",
            user_message=json.dumps(itinerary_input)
        )
        if not agent_result.primary_text.strip():
            raise ValueError("Agent returned empty response.")
        itinerary_output = agent_result.primary_text

        print("\nDaily Itinerary:\n")
        print(itinerary_output)

        with open('agt_msg/daily_itinerary.md', 'w', encoding='utf-8') as f:
            f.write(itinerary_output)
        #endregion

        # region Search Restaurant
        #1. Define an Agent configuration
        agent_config = AgentConfig(
            name="Single-City Restaurant Agent",
            system_prompt=(
                "You are a helpful assistant that receives a list of locations and dates, "
                "and uses a tool to find the highest-rated restaurant within 3km of each location. "
                "Return only valid JSON: a list of dictionaries, each with fields: "
                "`location`, `date`, `name`, `address`, `rating`, `opening_hours` (that day only), and `cuisine`."
                "- If two attractions are close to each other, the lunch and dinner restaurants should not be the same.\n"
                "- Otherwise, avoid repeating the same restaurant more than once a day."
            ),
            mcp_servers=["restaurant_server"],
            llm_config_id="openai_gpt35_turbo"
        )
        await aurite.register_agent(agent_config)
        #2. Define the user's query for the agent using. Save the result.
        with open("agt_msg/daily_itinerary.md", "r", encoding="utf-8") as f:
            restaurant_input = f.read()
        result = await aurite.run_agent(
            agent_name="Single-City Restaurant Agent",
            # user_message=json.dumps(user_message)
            user_message=restaurant_input
        )
        restaurant_output = result.primary_text
        #3. Save the Daily Itinerary.md integrated with restaurant
        md_integrated_prompt = """
        You are a travel itinerary enhancement agent.

        Your task is to combine two inputs:
        
        1. A list of daily travel plans, including dates, morning/afternoon locations, and corresponding activities.
        2. A list of restaurant recommendations, each associated with a location and date, including detailed restaurant info.
        
        ---
        
        Your goal:
        
        For each date and time period (morning or afternoon), do the following:
        - Copy the location and activity from the itinerary.
        - Find the matching restaurant from the list (match by both location and date).
        - Attach a meal recommendation:
          - Morning → 🍽️ Lunch Recommendation
          - Afternoon → 🍽️ Dinner Recommendation
        
        Include the following restaurant details:
        - Name
        - Address
        - Rating
        - Opening Hours
        - Cuisine
        
        ---
        
        Output format:
        
        Use Markdown. For each date, use the following structure:
        
        ### 📅 YYYY-MM-DD
        - Morning: [Location Name]
        - Activity: [Activity Description]
          - 🍽️ Lunch Recommendation:
            - Name: [Restaurant Name]
            - Address: [Restaurant Address]
            - Rating: [Rating]
            - Opening Hours: [Opening Hours]
            - Cuisine: [Cuisine Type]
        - Afternoon: [Location Name]
        - Activity: [Activity Description]
          - 🍽️ Dinner Recommendation:
            - Name: [Restaurant Name]
            - Address: [Restaurant Address]
            - Rating: [Rating]
            - Opening Hours: [Opening Hours]
            - Cuisine: [Cuisine Type]
        
        ---
        
        Constraints:
        - Match locations **exactly** between restaurant and itinerary.
        
        Return only the final Markdown result.
        """
        agent_config = AgentConfig(
            name="Restaurant MD Agent",
            system_prompt=md_integrated_prompt,
            llm_config_id="gpt-4.1",
            include_history=True
        )
        await aurite.register_agent(agent_config)
        md_integrated_input = f"""
                1. Restaurant data (JSON format):
        {json.dumps(restaurant_output, indent=2)}

        2. Daily itinerary (Markdown format):
        {restaurant_input}
        """
        md_integrated_result = await aurite.run_agent(
            agent_name="Restaurant MD Agent",
            user_message=md_integrated_input
        )
        with open('agt_msg/daily_itinerary_with_restaurant.md', 'w', encoding='utf-8') as f:
            f.write(md_integrated_result.primary_text)
        print("\nDaily Itinerary with Restaurant:\n")
        print(md_integrated_result.primary_text)

        agent_config = AgentConfig(
            name="Trip Distance Agent",
            system_prompt="""
                    You are a travel itinerary planning assistant. The user will input a multi-day itinerary in Markdown format, including time segments like "Morning", "Lunch Recommendation", "Afternoon", and "Dinner Recommendation".
                    Sample input：
                    ### 📅 2025-08-02
                    - Morning: Griffith Observatory, Los Angeles
                      - 🍽️ Lunch Recommendation:
                        - Name: Palermo Italian Restaurant
                        - Address: 1858 N Vermont Ave, Los Angeles, CA 90027, USA
                        - Rating: 4.7
                        - Opening Hours: []
                        - Cuisine: Italian
                    - Afternoon: Santa Monica Pier, Los Angeles
                      - 🍽️ Dinner Recommendation:
                        - Name: Fritto Misto
                        - Address: 620 Santa Monica Blvd #A, Santa Monica, CA 90401, USA
                        - Rating: 4.6
                        - Opening Hours: Saturday: 11:30 AM – 9:30 PM
                        - Cuisine: Italian

                    Your tasks:
                    1. Parse the user’s Markdown input and extract the ordered list of places per day.
                    2. Call the MCP tool trip_distance_duration_server with this format:
                    {
                      "daily_routes":
                        {
                          "2025-07-30": [
                            "Griffith Observatory, Los Angeles, CA",
                            "In-N-Out Burger, Sunset Blvd, Los Angeles, CA",
                            "The Getty Center, Los Angeles, CA"
                          ],
                          ...
                        }
                    }
                    3. The MCP tool will return distance and duration between each pair of consecutive locations (by driving and public transport).
                    4. **Preserve the user’s original Markdown input exactly**, and append a clearly formatted route analysis below it, like this:

                    ---

                    #### 🧭 Route Distance & Duration Analysis    

                    2025-07-30（Day 1)    
                    -From Griffith Observatory to Palermo Italian Restaurant：🚗 7.1 km, 13 min；🚆 6.5 km, 22 min  
                    -From Palermo Italian Restaurant to Santa Monica Pier：🚗 12.4 km, 20 min；🚆 11.8 km, 34 min  
                    -From Santa Monica Pier to Fritto Misto：🚗 7.1 km, 13 min；🚆 6.5 km, 22 min  
                     Travel times are estimates. Please choose your preferred mode of transport.

                    Only return Markdown-formatted text as output. Do not include JSON or additional explanations.
                    """,
            mcp_servers=["trip_distance_duration_server"],
            llm_config_id="openai_gpt4_turbo",
        )
        await aurite.register_agent(agent_config)
        # 2. Define the user's query for the agent using. Save the result.
        with open("agt_msg/daily_itinerary_with_restaurant.md", "r", encoding="utf-8") as f:
            transportation_input = f.read()
        agent_result = await aurite.run_agent(
            agent_name="Trip Distance Agent",
            user_message=transportation_input
        )
        transportation_output = agent_result.primary_text
        with open('agt_msg/daily_itinerary_final.md', 'w', encoding='utf-8') as f:
            f.write(transportation_output)
        print("\nDaily Itinerary with Restaurant and Transportation:\n")
        print(transportation_output)
        # endregion



    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(partII())
