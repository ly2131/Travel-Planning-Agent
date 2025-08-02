# import os
# import asyncio
# import logging
# from termcolor import colored
# from dotenv import load_dotenv
# from aurite import Aurite
# from aurite.config.config_models import AgentConfig, LLMConfig
#
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
#
# async def main():
#     load_dotenv()
#     aurite = Aurite()
#
#     try:
#         await aurite.initialize()
#
#         llm_config = LLMConfig(
#             llm_id="openai_gpt35_turbo",
#             provider="openai",
#             model_name="gpt-3.5-turbo"
#         )
#         await aurite.register_llm_config(llm_config)
#
#         agent_config = AgentConfig(
#             name="Single-City Restaurant Agent",
#             system_prompt=(
#                 "You are a helpful assistant that receives a list of locations and dates, "
#                 "and uses a tool to find the highest-rated restaurant within 3km of each location. "
#                 "Return a clean Markdown summary with the following format:\n\n"
#                 "1. <location> on <date>:\n"
#                 "   - Name: <restaurant name>\n"
#                 "   - Address: <address>\n"
#                 "   - Rating: <rating>\n"
#                 "   - Opening Hours: <hours>\n"
#                 "   - Cuisine: <cuisine>\n\n"
#                 "For locations not found, clearly state the error."
#             ),
#             mcp_servers=["restaurant_server"],
#             llm_config_id="openai_gpt35_turbo"
#         )
#         await aurite.register_agent(agent_config)
#
#         itinerary_text = """Date: 2025-06-01
# - Morning: Kurashiki Bikan Historical Quarter
# - Address: Central, Kurashiki, Okayama 710-0046, Japan
# - Afternoon: Ōhara Museum of Art
# - Address: 1 Chome-1-15 Central, Kurashiki, Okayama 710-8575, Japan
#
# Date: 2025-06-02
# - Morning: Achi Shrine
# - Address: 12-1 Honmachi, Kurashiki, Okayama 710-0054, Japan
# - Afternoon: Kurashiki Bikan Historical Quarter
# - Address: Central, Kurashiki, Okayama 710-0046, Japan
#
# Date: 2025-06-03
# - Morning: Ōhara Museum of Art
# - Address: 1 Chome-1-15 Central, Kurashiki, Okayama 710-8575, Japan
# - Afternoon: Achi Shrine
# - Address: 12-1 Honmachi, Kurashiki, Okayama 710-0054, Japan"""
#
#         def parse_itinerary_block(text):
#             itinerary = []
#             blocks = text.strip().split("\n\n")
#             for block in blocks:
#                 lines = block.split("\n")
#                 date = lines[0].split("Date:")[1].strip()
#                 morning_location = lines[1].split(":")[1].strip()
#                 afternoon_location = lines[3].split(":")[1].strip()
#                 itinerary.append(
#                     {"date": date, "locations": [morning_location, afternoon_location]}
#                 )
#             return itinerary
#
#         itinerary = parse_itinerary_block(itinerary_text)
#
#         locations = []
#         for day in itinerary:
#             for loc in day["locations"]:
#                 locations.append({"location": loc, "date": day["date"]})
#
#         user_message = {"locations": locations}
#
#         result = await aurite.run_agent(
#             agent_name="Single-City Restaurant Agent",
#             user_message=str(user_message)
#         )
#
#         markdown = result.primary_text.strip()
#
#         print(colored("\n--- Restaurant Plan (Markdown Output) ---\n", "cyan", attrs=["bold"]))
#         print(markdown)
#
#         with open("restaurant_result.md", "w", encoding="utf-8") as f:
#             f.write(markdown)
#
#         print(colored("\nSaved markdown to restaurant_result.md\n", "green", attrs=["bold"]))
#
#     except Exception as e:
#         logger.error(f"Execution error: {e}", exc_info=True)
#     finally:
#         await aurite.shutdown()
#         logger.info("Aurite shutdown complete.")
#
# if __name__ == "__main__":
#     asyncio.run(main())

import os
import asyncio
import json
import logging
from termcolor import colored
from dotenv import load_dotenv
from aurite import Aurite
from aurite.config.config_models import AgentConfig, LLMConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    aurite = Aurite()

    try:
        await aurite.initialize()

        llm_config = LLMConfig(
            llm_id="openai_gpt35_turbo",
            provider="openai",
            model_name="gpt-3.5-turbo"
        )
        await aurite.register_llm_config(llm_config)

        agent_config = AgentConfig(
            name="Single-City Restaurant Agent",
            system_prompt=(
                "You are a helpful assistant that receives a list of locations and dates, "
                "and uses a tool to find the highest-rated restaurant within 3km of each location. "
                "Return only valid JSON: a list of dictionaries, each with fields: "
                "`location`, `date`, `name`, `address`, `rating`, `opening_hours` (that day only), and `cuisine`."
            ),
            mcp_servers=["restaurant_server"],
            llm_config_id="openai_gpt35_turbo"
        )
        await aurite.register_agent(agent_config)

        itinerary_text = """Date: 2025-06-01
- Morning: Kurashiki Bikan Historical Quarter
- Address: Central, Kurashiki, Okayama 710-0046, Japan
- Afternoon: Ōhara Museum of Art
- Address: 1 Chome-1-15 Central, Kurashiki, Okayama 710-8575, Japan

Date: 2025-06-02
- Morning: Achi Shrine
- Address: 12-1 Honmachi, Kurashiki, Okayama 710-0054, Japan
- Afternoon: Kurashiki Bikan Historical Quarter
- Address: Central, Kurashiki, Okayama 710-0046, Japan

Date: 2025-06-03
- Morning: Ōhara Museum of Art
- Address: 1 Chome-1-15 Central, Kurashiki, Okayama 710-8575, Japan
- Afternoon: Achi Shrine
- Address: 12-1 Honmachi, Kurashiki, Okayama 710-0054, Japan"""

        def parse_itinerary_block(text):
            itinerary = []
            blocks = text.strip().split("\n\n")
            for block in blocks:
                lines = block.split("\n")
                date = lines[0].split("Date:")[1].strip()
                morning_location = lines[1].split(":")[1].strip()
                morning_address = lines[2].split(":")[1].strip()
                afternoon_location = lines[3].split(":")[1].strip()
                afternoon_address = lines[4].split(":")[1].strip()
                itinerary.append({
                    "date": date,
                    "morning": {"location": morning_location, "address": morning_address},
                    "afternoon": {"location": afternoon_location, "address": afternoon_address},
                })
            return itinerary

        itinerary = parse_itinerary_block(itinerary_text)

        locations = []
        for day in itinerary:
            locations.append({"location": day["morning"]["location"], "date": day["date"]})
            locations.append({"location": day["afternoon"]["location"], "date": day["date"]})

        user_message = {"locations": locations}

        result = await aurite.run_agent(
            agent_name="Single-City Restaurant Agent",
            user_message=json.dumps(user_message)
        )

        print(colored("\n--- Restaurant Agent Raw Output ---", "cyan", attrs=["bold"]))
        print(result.primary_text)

        try:
            parsed = json.loads(result.primary_text)

            md_lines = []
            for day in itinerary:
                date = day["date"]
                md_lines.append(f"Date: {date}")

                md_lines.append(f"- Morning: {day['morning']['location']}")
                md_lines.append(f"- Address: {day['morning']['address']}")
                morning_rest = next((r for r in parsed if r["location"] == day["morning"]["location"] and r["date"] == date), None)
                if morning_rest and "address" in morning_rest:
                    md_lines.append(f"- Lunch Restaurant: {morning_rest['name']}")
                    md_lines.append(f"  - Address: {morning_rest['address']}")
                    md_lines.append(f"  - Rating: {morning_rest['rating']}")
                    md_lines.append(f"  - Opening Hours: {morning_rest['opening_hours']}")
                    md_lines.append(f"  - Cuisine: {morning_rest['cuisine']}")

                md_lines.append(f"- Afternoon: {day['afternoon']['location']}")
                md_lines.append(f"- Address: {day['afternoon']['address']}")
                afternoon_rest = next((r for r in parsed if r["location"] == day["afternoon"]["location"] and r["date"] == date), None)
                if afternoon_rest and "address" in afternoon_rest:
                    md_lines.append(f"- Dinner Restaurant: {afternoon_rest['name']}")
                    md_lines.append(f"  - Address: {afternoon_rest['address']}")
                    md_lines.append(f"  - Rating: {afternoon_rest['rating']}")
                    md_lines.append(f"  - Opening Hours: {afternoon_rest['opening_hours']}")
                    md_lines.append(f"  - Cuisine: {afternoon_rest['cuisine']}")
                md_lines.append("")

            print(colored("\n--- Formatted Markdown Output ---", "green", attrs=["bold"]))
            print("\n" + "\n".join(md_lines))

        except Exception as e:
            raise ValueError(f"Agent did not return valid JSON. Error: {e}")

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
    finally:
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())