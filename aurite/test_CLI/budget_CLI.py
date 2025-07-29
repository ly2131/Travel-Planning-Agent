import asyncio
import json
import logging
from termcolor import colored
from aurite import Aurite
# CHANGE 1: Import ClientConfig
from aurite.config.config_models import AgentConfig, LLMConfig, ClientConfig

# import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """
    A simple example demonstrating how to initialize Aurite, run an agent,
    and print its response.
    """
    from dotenv import load_dotenv
    load_dotenv()

    aurite = Aurite()

    try:
        await aurite.initialize()

        # --- Dynamic Registration Example ---

        # 1. Define and register an LLM configuration
        llm_config = LLMConfig(
            llm_id="gpt-4.1",
            provider="openai",
            model_name="gpt-4.1",
        )
        await aurite.register_llm_config(llm_config)
        #
        # # ✅ 注册你自己的城市价格 MCP Server
        # mcp_city_price_config = ClientConfig(
        #     name="city_price_server",
        #     server_path="Part_I_mcp_servers/city_price_server.py",
        #     capabilities=["tools"],
        # )
        # await aurite.register_client(mcp_city_price_config)
        #
        # mcp_ai_fallback_config = ClientConfig(
        #     name="ai_fallback_server",
        #     server_path="Part_I_mcp_servers/ai_fallback_server.py",
        #     capabilities=["tools"],
        #
        # )
        # await aurite.register_client(mcp_ai_fallback_config)
        #
        # # ✅ 注册代理
        agent_config = AgentConfig(
            name="City Travel Cost Agent",
            system_prompt="""
                        你是一个旅游成本助手，严格按以下规则返回数据：
                        1. **只输出合法的 JSON**，不要包含任何额外文本、Markdown 或注释。
                        2. 示例格式：
                        {               
                            "start_date": "2025-07-28",
                            "end_date": "2025-08-01",
                            "cities": [
                                {
                                    "city": "Paris",
                                    "social media comments": [
                                        "Absolutely magical in springtime!",
                                        "Crowds around the Eiffel Tower were a bit much.",
                                        "Loved the local cafes and boulangeries."
                                    ],
                                    "budget": {},
                                    "weather": 123
                                }
                        }
                        3. do not remove or alter any existing fields
                        """,
            mcp_servers=["city_price_server", "ai_fallback_server"],
            llm_config_id="gpt-4.1",
        )
        await aurite.register_agent(agent_config)

        # ✅ 用户问题
        user_message = {
            "start_date": "2025-07-28",
            "end_date": "2025-08-01",
            "cities": [
                {
                    "city": "Paris",
                    "social media comments": [
                        "Absolutely magical in springtime!",
                        "Crowds around the Eiffel Tower were a bit much.",
                        "Loved the local cafes and boulangeries."
                    ],
                    "weather": 123
                },
                {
                    "city": "Tokyo",
                    "social media comments": [
                        "The subway system is incredibly efficient.",
                        "Such a mix of modern and traditional everywhere.",
                        "Food is amazing, but it can get expensive."
                    ],
                    "weather": 456
                },
                {
                    "city": "Bangkok",
                    "social media comments": [
                        "Street food scene is unbeatable!",
                        "Traffic can be a nightmare during rush hour.",
                        "Temples are stunning—don’t miss the Emerald Buddha."
                    ],
                    "weather": 789
                }
            ]
        }
        agent_result = await aurite.run_agent(
            agent_name="City Travel Cost Agent",
            user_message=json.dumps(user_message)
        )




        # # CHANGE 2: Define and register our new calculator server
        # mcp_server_config = ClientConfig(
        #     name="my_calculator_server",
        #     # This path is relative to your project root
        #     server_path="Part_I_mcp_servers/calculator_server.py",
        #     capabilities=["tools"],
        # )
        # await aurite.register_client(mcp_server_config)
        #
        # # CHANGE 3: Define and register an Agent that uses the server
        # agent_config = AgentConfig(
        #     name="Math Agent",
        #     system_prompt="You are a math assistant. Use the tools you have to solve the user's math problem.",
        #     # Tell the agent to use our new server!
        #     mcp_servers=["my_calculator_server"],
        #     llm_config_id="openai_gpt4_turbo",
        # )
        # await aurite.register_agent(agent_config)
        # # --- End of Dynamic Registration Example ---
        #
        # # CHANGE 4: Update the query and agent name for our test
        # user_query = "What is 123 + 456?"
        #
        # agent_result = await aurite.run_agent(
        #     agent_name="Math Agent", user_message=user_query
        # )

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
