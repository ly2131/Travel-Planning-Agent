import asyncio
import logging
import json
import re
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
            llm_id="openai_gpt4_turbo",
            provider="openai",
            model_name="gpt-4-turbo-preview",
        )
        await aurite.register_llm_config(llm_config)

        agent_config = AgentConfig(
            name="Multi-City Weather Agent",
            system_prompt="You are a helpful assistant that receives a list of cities with metadata and fills in the average high/low temperature and precipitation in the 'weather' field for a given time period. Only return valid JSON, no extra text or markdown formatting.",
            mcp_servers=["weather_server"],
            llm_config_id="openai_gpt4_turbo",
        )
        await aurite.register_agent(agent_config)
        a = {
            "start_date": "2025-06-01",
            "end_date": "2025-06-06",
            "region": "beijing",
            "activities": "no",
            "budget": "no",
            "avoid": "no"
        }
        subset = {k: a[k] for k in ('start_date', 'end_date')}
        b = [
            {
                "city": "Beijing, China",
                "trend_level": "medium",
                "comments": [
                    "Beijing offers a mix of modern and traditional university campuses, a must-visit for educational tours.",
                    "Tsinghua and Peking University have beautiful campuses and less crowded in the summer.",
                    "Exploring universities in Beijing was insightful, offering a glance into China's educational prestige."
                ],
                "trend_summary": "Beijing, with its renowned universities and historical significance, offers a balanced educational visit experience, avoiding the busiest tourist spots."
            },
            {
                "city": "Xi'an, China",
                "trend_level": "low",
                "comments": [
                    "Xi'an Jiaotong University has a rich history and the city is less crowded compared to other educational hubs.",
                    "The Terracotta Army is a bonus visit after exploring the educational institutions in Xi'an.",
                    "Xi'an provides a unique blend of education and culture, perfect for quieter, more reflective educational trips."
                ],
                "trend_summary": "Xi'an offers educational visits with a historical twist, ideal for those looking to combine learning with cultural exploration in a less crowded setting."
            },
            {
                "city": "Hangzhou, China",
                "trend_level": "medium",
                "comments": [
                    "Zhejiang University in Hangzhou is not only prestigious but also located in one of China's most beautiful cities.",
                    "Hangzhou offers serene landscapes around West Lake, making university visits more relaxing and enjoyable.",
                    "Visiting Hangzhou's universities offered a peaceful educational experience away from the urban frenzy."
                ],
                "trend_summary": "Hangzhou's blend of scenic beauty and academic prowess provides a tranquil setting for educational visits, away from the hustle and bustle."
            }
        ]
        b.append(subset)
        # user_message = {
        #     "start_date": "2025-07-28",
        #     "end_date": "2025-08-01",
        #     "cities": [
        #         {
        #             "city": "Paris",
        #             "social media comments": [
        #                 "Absolutely magical in springtime!",
        #                 "Crowds around the Eiffel Tower were a bit much.",
        #                 "Loved the local cafes and boulangeries."
        #             ],
        #             "budget": {"average_daily_per_person": 150},
        #             "weather": {}
        #         },
        #         {
        #             "city": "Tokyo",
        #             "social media comments": [
        #                 "The subway system is incredibly efficient.",
        #                 "Such a mix of modern and traditional everywhere.",
        #                 "Food is amazing, but it can get expensive."
        #             ],
        #             "budget": {"average_daily_per_person": 18000},
        #             "weather": {}
        #         },
        #         {
        #             "city": "Bangkok",
        #             "social media comments": [
        #                 "Street food scene is unbeatable!",
        #                 "Traffic can be a nightmare during rush hour.",
        #                 "Temples are stunning—don’t miss the Emerald Buddha."
        #             ],
        #             "budget": {"average_daily_per_person": 2000},
        #             "weather": {}
        #         }
        #     ]
        # }

        result = await aurite.run_agent(
            agent_name="Multi-City Weather Agent",
            user_message= json.dumps(b)
        )

        print(colored("\n---Weather Agent Output ---", "yellow", attrs=["bold"]))
        print(result.primary_text)

        match = re.search(r"\{.*\}", result.primary_text, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON object found in agent result.")

        raw_data = json.loads(match.group(0))

        with open("../agt_msg/weather_result.json", "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

        print(colored("\nSaved result to weather_result.json", "green", attrs=["bold"]))

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
    finally:
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())