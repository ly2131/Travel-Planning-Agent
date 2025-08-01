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

        # Daily itinerary input
        itinerary = [
            {
                "date": "2025-08-02",
                "morning": "Griffith Observatory, Los Angeles",
                "afternoon": "Santa Monica Pier, Los Angeles"
            },
            {
                "date": "2025-08-03",
                "morning": "The Getty Center, Los Angeles",
                "afternoon": "Grand Central Market, Los Angeles"
            }
        ]

        # Flattened input for restaurant lookup
        locations = []
        for day in itinerary:
            locations.append({"location": day["morning"], "date": day["date"]})
            locations.append({"location": day["afternoon"], "date": day["date"]})

        user_message = {"locations": locations}

        result = await aurite.run_agent(
            agent_name="Single-City Restaurant Agent",
            user_message=json.dumps(user_message)
        )

        print(colored("\n--- Restaurant Agent Raw Output ---", "cyan", attrs=["bold"]))
        print(result.primary_text)

        try:
            parsed = json.loads(result.primary_text)

            with open("restaurant_result.json", "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
            print(colored("\nSaved result to restaurant_result.json", "green", attrs=["bold"]))

            print(colored("\n--- 🍽️ Daily Itinerary with Restaurant Suggestions ---", "magenta", attrs=["bold"]))
            for day in itinerary:
                date = day["date"]
                print(f"\n### 📅 {date}")
                print(f"- Morning: {day['morning']}")
                morning_restaurant = next((r for r in parsed if r["location"] == day["morning"] and r["date"] == date), None)
                if morning_restaurant:
                    print(f"  - 🍽️ Lunch Recommendation:")
                    print(f"    - Name: {morning_restaurant['name']}")
                    print(f"    - Address: {morning_restaurant['address']}")
                    print(f"    - Rating: {morning_restaurant['rating']}")
                    print(f"    - Opening Hours: {morning_restaurant['opening_hours']}")
                    print(f"    - Cuisine: {morning_restaurant['cuisine']}")
                print(f"- Afternoon: {day['afternoon']}")
                afternoon_restaurant = next((r for r in parsed if r["location"] == day["afternoon"] and r["date"] == date), None)
                if afternoon_restaurant:
                    print(f"  - 🍽️ Dinner Recommendation:")
                    print(f"    - Name: {afternoon_restaurant['name']}")
                    print(f"    - Address: {afternoon_restaurant['address']}")
                    print(f"    - Rating: {afternoon_restaurant['rating']}")
                    print(f"    - Opening Hours: {afternoon_restaurant['opening_hours']}")
                    print(f"    - Cuisine: {afternoon_restaurant['cuisine']}")

        except Exception as e:
            raise ValueError(f"Agent did not return valid JSON. Error: {e}")

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
    finally:
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())