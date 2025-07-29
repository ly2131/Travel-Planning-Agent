import asyncio, re, json, uuid
from dotenv import load_dotenv
from aurite import Aurite, AgentConfig
from termcolor import colored
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
system_prompt  = """
You are a travel planning agent. Your job is to:

1. Ingest the user’s travel preferences (dates, budget, interests, must‑see activities, things to avoid).
2. Review the provided list of candidate cities along with their key data (cost of living, climate, main attractions, safety, transportation).
3. Weigh all relevant factors—seasonality, budget alignment, activity match, travel constraints, and avoidances.
4. Choose one city that best meets the user’s needs.
5. Present your recommendation with:
   - A clear statement of the chosen city.
   - A concise explanation (3–5 bullet points) highlighting the top reasons why this city is the ideal pick.

Always focus on matching the user’s stated priorities and be explicit about how each factor influenced your decision.
"""

async def main():
    load_dotenv()
    aurite = Aurite()
    try:
        await aurite.initialize()

        agent_config = AgentConfig(
            name="Destination Recommendation Agent",
            system_prompt=system_prompt,
            llm_config_id="my_openai_gpt4_turbo",
            include_history=True
        )

        # Register the agent with Aurite so the framework knows about it.
        await aurite.register_agent(agent_config)

        user_query = """{
        "preferences": {
            "start_date": "2025-06-01",
            "end_date": "2025-06-06",
            "region": "Asia",
            "activities": "nature lover",
            "budget": "5k dollars",
            "avoid": "no"
                },
        "cities": [
            {
            "city": "Paris",
            "social media comments": [
            "Absolutely magical in springtime!",
            "Crowds around the Eiffel Tower were a bit much.",
            "Loved the local cafes and boulangeries."
                ],
            "budget": {
            "currency": "EUR",
            "average_daily_per_person": 150
    },
    "weather": {
      "season": "Spring",
      "average_temperature_c": 16,
      "conditions": "Sunny with occasional showers"
    }
  },
  {
    "city": "Tokyo",
    "social media comments": [
      "The subway system is incredibly efficient.",
      "Such a mix of modern and traditional everywhere.",
      "Food is amazing, but it can get expensive."
    ],
    "budget": {
      "currency": "JPY",
      "average_daily_per_person": 18000
    },
    "weather": {
      "season": "Summer",
      "average_temperature_c": 27,
      "conditions": "Hot and humid"
    }
  },
  {
    "city": "Bangkok",
    "social media comments": [
      "Street food scene is unbeatable!",
      "Traffic can be a nightmare during rush hour.",
      "Temples are stunning—don’t miss the Emerald Buddha."
    ],
    "budget": {
      "currency": "THB",
      "average_daily_per_person": 2000
    },
    "weather": {
      "season": "Winter",
      "average_temperature_c": 29,
      "conditions": "Warm and dry"
    }
        }
        ]
    }
        """
        agent_result = await aurite.run_agent(
            agent_name="Destination Recommendation Agent",
            user_message=user_query
        )
        print(colored("\n--- Agent Result ---", "yellow", attrs=["bold"]))
        response_text = agent_result.primary_text
        print(colored(f"Agent's response: {response_text}", "cyan", attrs=["bold"]))
    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
    finally:
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())