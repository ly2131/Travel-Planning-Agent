import asyncio
import logging
import json
# from termcolor import colored  # For colored print statements

from aurite import Aurite
from IPython.display import display, Markdown
from aurite.config.config_models import AgentConfig, LLMConfig, ClientConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def display_agent_response(agent_name: str, query: str, response: str):
  """Formats and displays the agent's response in a structured Markdown block."""

  output = f"""
  <div style=\"border: 1px solid #D1D5DB; border-radius: 8px; margin-top: 20px; font-family: sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.05);\">
    <div style=\"background-color: #F3F4F6; padding: 10px 15px; border-bottom: 1px solid #D1D5DB; border-radius: 8px 8px 0 0;\">
      <h3 style=\"margin: 0; font-size: 16px; color: #1F2937; display: flex; align-items: center;\">
        <span style=\"margin-right: 8px;\">🤖</span>
        Agent Response: <code style=\"background-color: #E5E7EB; color: #374151; padding: 2px 6px; border-radius: 4px; margin-left: 8px;\">{agent_name}</code>
      </h3>
    </div>
    <div style=\"padding: 15px;\">
      <p style=\"margin: 0 0 10px 0; color: #6B7280; font-size: 14px;\">
        <strong>Your Query:</strong>
      </p>
      <p style=\"background-color: #F9FAFB; margin: 0 0 15px 0; color: #1F2937; border: 1px solid #E5E7EB; border-left: 3px solid #9CA3AF; padding: 10px 12px; border-radius: 4px;\">
        <em>\"{query}\"</em>
      </p>
      <hr style=\"border: none; border-top: 1px dashed #D1D5DB; margin-bottom: 15px;\">
      <p style=\"margin: 0 0 10px 0; color: #6B7280; font-size: 14px;\">
        <strong>Result:</strong>
      </p>
      <div style=\"background-color: #FFFFFF; padding: 15px; border-radius: 5px; border: 1px solid #E5E7EB; color: #1F2937; font-size: 15px; line-height: 1.6;\">
        {response}
      </div>
    </div>
  </div>
  """
  display(Markdown(output))

async def main():
    """
    A simple example demonstrating how to initialize Aurite, run an agent,
    and print its response.
    """
    # Initialize the main Aurite application object.
    # This will load configurations based on `old_aurite_config.json` or environment variables.
    # Load environment variables from a .env file if it exists
    from dotenv import load_dotenv

    load_dotenv()

    aurite = Aurite()

    try:
        await aurite.initialize()

        # --- Dynamic Registration Example ---
        # The following section demonstrates how to dynamically register components
        # with Aurite. This is useful for adding or modifying configurations at
        # runtime without changing the project's JSON/YAML files.

        # 1. Define and register an LLM configuration
        llm_config = LLMConfig(
            llm_id="openai_gpt4_turbo",
            provider="openai",
            model_name="gpt-4-turbo-preview",
        )

        await aurite.register_llm_config(llm_config)
        #
        # 2. Define and register an MCP server configuration

        mcp_server_config = ClientConfig(
            name="Scrapeless MCP Server",
            transport_type="local",
            command="npx",
            args=["-y", "scrapeless-mcp-server"],
            capabilities=["tools"],
            timeout=15.0
        )

        # twitter_mcp_config = ClientConfig(
        #     name="twitter-mcp",
        #     transport_type="local",
        #     command="uv",
        #     args=[
        #         "--directory", "mcp-twitter/src",
        #         "run", "--with", "twikit", "--with", "mcp", "tweet_service.py"
        #     ],
        #     capabilities=["tools"],
        #     timeout=20.0
        # )

        await aurite.register_client(mcp_server_config)
        # await aurite.register_client(twitter_mcp_config)

        # 2. Define a JSON schema for a structured output
        schema = {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "recommended_location": {
                        "type": "string",
                        "description": "The city or destination recommended based on user preferences and current travel trends"
                    },
                    "trend_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "How popular the location is currently"
                    },
                    "personalized_reviews": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "user_profile": {
                                    "type": "string",
                                    "description": "Type of traveler, e.g. 'solo backpacker', 'family with kids'"
                                },
                                "comment": {
                                    "type": "string",
                                    "description": "The actual review content"
                                },
                            },
                            "required": ["user_profile", "comment"]
                        },
                        "minItems": 3,
                        "maxItems": 3,
                        "description": "Recent reviews tailored by traveler type"
                    },
                    "trend_summary": {
                        "type": "string",
                        "description": "A concise summary explaining why this destination is currently recommended"
                    },
                    "reference_links": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "format": "uri"
                        },
                        "minItems": 1,
                        "maxItems": 3,
                        "description": "Useful URLs for learning more about the destination"
                    }
                },
                "required": [
                    "recommended_location",
                    "trend_level",
                    "personalized_reviews",
                    "trend_summary",
                    "reference_links"
                ]
            }
        }

        # # 3. Define and register an Agent configuration
        agent_config = AgentConfig(
            name="Search Trends Agent",
            system_prompt=(
                "You are a travel trends expert. Use Scrapeless MCP Server."
                # "For extracting user reviews and trend signals. Use Scrapeless MCP Server only "
                # "For fact-checking or when no Twitter data is found."
                "Return a JSON array of 3 recommendation objects directly, without any wrapping object or response key."
                # "Always call `get_travel_trend_recommendations` with a user keyword (e.g. 'summer vacation', 'family trip') "
            ),
        mcp_servers=["Scrapeless MCP Server"],
            llm_config_id="openai_gpt4_turbo",
            config_validation_schema=schema
        )
        await aurite.register_agent(agent_config)
        # --- End of Dynamic Registration Example ---

        # 4. Define the user's query for the agent using structured JSON input.
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
        # Run the agent with the user's query. The check for the execution
        # facade is now handled internally by the `aurite.run_agent` method.
        agent_result = await aurite.run_agent(
            agent_name="Search Trends Agent",
            user_message=json.dumps(user_query)
        )

        # Print the agent's response in a colored format for better visibility.

        # # print query
        # print("\nYour Query:")
        # print(json.dumps(user_query, indent=2))
        #
        # # print raw output
        # print("\nRaw Result:")
        # print(agent_result.primary_text)

        # display structured output
        # display_agent_response(
        #     agent_name="Search Trends Agent (Structured Output)",
        #     query="Find a destination matching user preferences and trends.",
        #     response=agent_result.primary_text
        # )
        # Print the agent's response in a colored format for better visibility.

        # print query
        print("\nYour Query:")
        print(json.dumps(user_query, indent=2))

        # parse multi-output results
        results = json.loads(agent_result.primary_text)

        # print raw output
        print("\nRaw Result:")
        print(json.dumps(results, indent=2))

        # display each option separately
        for i, result in enumerate(results):
            display_agent_response(
                agent_name=f"Search Trends Agent - Option {i + 1}",
                query="Find a destination matching user preferences and trends.",
                response=json.dumps(result, indent=2)
            )

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())
