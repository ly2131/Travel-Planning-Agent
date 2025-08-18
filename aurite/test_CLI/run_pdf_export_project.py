import os
import asyncio
import json
import logging
from termcolor import colored
from dotenv import load_dotenv
from aurite import Aurite
from aurite.config.config_models import AgentConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    load_dotenv()
    aurite = Aurite()

    try:
        await aurite.initialize()

        agent_config = AgentConfig(
            name="Markdown to PDF Agent",
            system_prompt="You are a PDF export assistant. Use the tool 'markdown_to_pdf' to convert Markdown files to PDF.",
            mcp_servers=["pdf_export_server"]
        )
        await aurite.register_agent(agent_config)

        user_message = json.dumps({
            "input_path": "/Users/xx-g/Desktop/TPA/aurite/agt_msg/daily_itinerary_final.md",
            "output_path": "/Users/xx-g/Desktop/TPA/aurite/agt_msg/daily_itinerary_final.pdf"
        })

        result = await aurite.run_agent(
            agent_name="Markdown to PDF Agent",
            user_message=user_message
        )

        print(colored("\n--- PDF Export Result ---\n", "cyan", attrs=["bold"]))
        print(result.primary_text)

    except Exception as e:
        logger.error(f"Agent execution error: {e}", exc_info=True)
    finally:
        await aurite.shutdown()
        logger.info("Aurite shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
