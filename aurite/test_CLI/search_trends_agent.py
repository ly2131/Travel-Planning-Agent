import asyncio
import logging
import json

from aurite import Aurite
from aurite.config.config_models import AgentConfig, LLMConfig, ClientConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():

    from dotenv import load_dotenv

    load_dotenv()

    aurite = Aurite()

    try:
        await aurite.initialize()

        # 1. Define and register an LLM configuration
        llm_config = LLMConfig(
            llm_id="openai_gpt4_turbo",
            provider="openai",
            model_name="gpt-4-turbo-preview",
        )

        await aurite.register_llm_config(llm_config)

        # 2. Define and register an MCP server configuration

        mcp_server_config = ClientConfig(
            name="Scrapeless MCP Server",
            transport_type="local",
            command="npx",
            args=["-y", "scrapeless-mcp-server"],
            capabilities=["tools"],
            timeout=15.0
        )

        await aurite.register_client(mcp_server_config)

        # 3. Define a JSON schema for a structured output
        schema = {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name recommended based on user preferences and current travel trends"
                    },
                    "trend_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "How popular the location is currently"
                    },
                    "comments": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "A user comment about the destination"
                        },
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Three recent user comments about the destination"
                    },
                    "trend_summary": {
                        "type": "string",
                        "description": "A concise summary explaining why this destination is currently recommended"
                    },
                },
                "required": [
                    "city",
                    "trend_level",
                    "comments",
                    "trend_summary"
                ]
            }
        }

        # 4. Define and register an Agent configuration
        agent_config = AgentConfig(
            name="Search Trends Agent",
            system_prompt=(
                "You are a travel trends expert using Scrapeless MCP Server to analyze travel patterns and user preferences. "
                "Your task is to recommend exactly 3 travel destinations based on the user's input. "
                "You MUST return ONLY a raw JSON array with exactly 3 objects. Do NOT include markdown, explanations, or any wrapping objects.\n\n"
                "Each object must strictly follow this structure:\n"
                "{\n"
                '  "city": string,                    // e.g. "Kyoto, Japan"\n'
                '  "trend_level": one of "high", "medium", or "low", // popularity level of the location\n'
                '  "comments": [                          // exactly 3 user comments as strings\n'
                '    "string",\n'
                '    "string",\n'
                '    "string"\n'
                '  ],\n'
                '  "trend_summary": string                            // concise explanation of the destination’s trend\n'
                "}\n\n"
                "Output must be a valid JSON array of 3 such objects. No other text or formatting is allowed."
            ),
            mcp_servers=["Scrapeless MCP Server"],
            llm_config_id="openai_gpt4_turbo",
            config_validation_schema=schema
            )
        await aurite.register_agent(agent_config)

        # 5. Define the user's query for the agent using structured JSON input.
        user_query = {
            "start_date": "2025-07-13",
            "end_date": "2025-07-16",
            "region": "China",
            "activity_preferences": "university visits",
            "budget_level": "medium",
            "things_to_avoid": "crowds"
        }
        # user_query= {
        #     "start_date": "2025-08-20",
        #     "end_date": "2025-08-23",
        #     "region": "not sure",
        #     "activity_preferences": "historical places",
        #     "budget_level": "low",
        #     "things_to_avoid": "crowds"
        # }
        # user_query = {
        #     "start_date": "2025-12-20",
        #     "end_date": "2025-12-25",
        #     "region": "not sure",
        #     "activity_preferences": "summer vacation",
        #     "budget_level": "high",
        #     "things_to_avoid": "indoor"
        # }

        # 6. Run the agent with the user's query. The check for the execution
        # facade is now handled internally by the `aurite.run_agent` method.
        agent_result = await aurite.run_agent(
            agent_name="Search Trends Agent",
            user_message=json.dumps(user_query)
        )

        # 7. print query
        print("\nYour Query:")
        print(json.dumps(user_query, indent=2))

        # 8. parse multi-output results
        results = json.loads(agent_result.primary_text)

        # 9. print raw output
        print("\nRaw Result:")
        print(json.dumps(results, indent=2))

        with open('../search_trends.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())
