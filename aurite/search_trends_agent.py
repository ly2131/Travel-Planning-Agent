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
            name="search_trend_server",
            transport_type="local",
            command="npx",
            args=["-y", "scrapeless-mcp-server"],
            env={"SCRAPELESS_KEY": "SCRAPELESS_KEY"},
            capabilities=["tools"],
            timeout=15.0
        )
        await aurite.register_client(mcp_server_config)

        # 2. Define a JSON schema for a structured output
        schema = {
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
                "trend_change": {
                    "type": "string",
                    "enum": ["increasing", "stable", "decreasing"],
                    "description": "Recent change in travel interest"
                },
                "related_reviews": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Snippets of recent user comments or feedback related to the location"
                },
                "concerns_or_warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 3,
                    "description": "Potential concerns about the destination, such as crowds or closures"
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
                "trend_change",
                "related_reviews",
                "trend_summary"
            ]
        }

        # # 3. Define and register an Agent configuration
        agent_config = AgentConfig(
            name="Search Trends Agent",
            system_prompt= (
                "You are a travel trends expert. Use the available tools to identify a travel destination that matches the user's preferences. "
                "CRITICAL: Your output must be structured according to the predefined JSON schema."
            ),
            mcp_servers=["Scrapeless MCP Server"],
            llm_config_id="openai_gpt4_turbo",
            config_validation_schema=schema
        )
        await aurite.register_agent(agent_config)
        # --- End of Dynamic Registration Example ---

        # 4. Define the user's query for the agent using structured JSON input.
        # user_query = {
        #     "start_date": "2025-07-13",
        #     "end_date": "2025-07-16",
        #     "region": "Kyoto",
        #     "activity_preferences": "temple visits",
        #     "budget_level": "medium",
        #     "things_to_avoid": "crowds"
        # }
        # user_query= {
        #     "start_date": "2025-08-20",
        #     "end_date": "2025-08-23",
        #     "region": "Shaanxi",
        #     "activity_preferences": "historical places",
        #     "budget_level": "low",
        #     "things_to_avoid": "crowds"
        # }
        user_query = {
            "start_date": "2025-12-20",
            "end_date": "2025-12-25",
            "region": "Shanghai",
            "activity_preferences": "fancy shopping mall",
            "budget_level": "high",
            "things_to_avoid": "small places"
        }
        # Run the agent with the user's query. The check for the execution
        # facade is now handled internally by the `aurite.run_agent` method.
        agent_result = await aurite.run_agent(
            agent_name="Search Trends Agent",
            user_message=json.dumps(user_query)
        )

        # Print the agent's response in a colored format for better visibility.

        # print query
        print("\nYour Query:")
        print(json.dumps(user_query, indent=2))

        # print raw output
        print("\nRaw Result:")
        print(agent_result.primary_text)

        # display structured output
        display_agent_response(
            agent_name="Search Trends Agent (Structured Output)",
            query="Find a destination matching user preferences and trends.",
            response=agent_result.primary_text
        )


    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}", exc_info=True)
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")


if __name__ == "__main__":
    # Run the asynchronous main function.
    asyncio.run(main())
