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
            name="Single-City Restaurant Markdown Agent",
            system_prompt=(
                "You are a helpful travel assistant.\n"
                "Given a list of locations and dates, for each location, call the tool to find the top-rated nearby restaurant.\n"
                "Then, return a Markdown-formatted itinerary grouped by date.\n"
                "For each date:\n"
                "- Show the morning and afternoon destination (with address)\n"
                "- For the morning location, provide a restaurant and label it as 'Lunch Restaurant'\n"
                "- For the afternoon location, provide a restaurant and label it as 'Dinner Restaurant'\n"
                "- If two attractions are close to each other, the lunch and dinner restaurants should not be the same.\n"
                "- Otherwise, avoid repeating the same restaurant more than once a day."
            ),
            mcp_servers=["restaurant_server"],
            llm_config_id="openai_gpt35_turbo"
        )
        await aurite.register_agent(agent_config)

        itinerary_text = """Date: 2025-06-01
- Morning: Fremont Street Experience
- Address: 425 Fremont St, Las Vegas, NV 89101, USA
- Afternoon: Gold & Silver Pawn Shop
- Address: 713 Las Vegas Blvd N, Las Vegas, NV 89101, USA

Date: 2025-06-02
- Morning: The Neon Museum Las Vegas
- Address: 770 Las Vegas Blvd N, Las Vegas, NV 89101, USA
- Afternoon: Fashion Show Mall
- Address: 3200 S Las Vegas Blvd, Las Vegas, NV 89109, USA"""

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
            agent_name="Single-City Restaurant Markdown Agent",
            user_message=json.dumps(user_message)
        )

        print(colored("\n--- Restaurant Markdown Itinerary ---\n", "cyan", attrs=["bold"]))
        print(result.primary_text)

        with open("restaurant_result.md", "w", encoding="utf-8") as f:
            f.write(result.primary_text)
        print(colored("\nSaved markdown to restaurant_result.md\n", "green", attrs=["bold"]))

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
    finally:
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())