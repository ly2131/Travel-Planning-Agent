# Part_I_mcp_servers/calculator_server.py

import logging
from mcp.server.fastmcp import FastMCP

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Create the MCP server instance
mcp = FastMCP("Calculator Assistant")

# 2. Define a tool using the @mcp.tool() decorator
@mcp.tool()
async def add(a: int, b: int) -> int:
    """
    Adds two integers together.

    Args:
        a: The first integer.
        b: The second integer.

    Returns:
        The sum of the two integers.
    """
    logger.info(f"Adding {a} + {b}")
    return a + b

@mcp.tool()
async def subtract(a: int, b: int) -> int:
    """
    Subtracts the second integer from the first.

    Args:
        a: The first integer.
        b: The second integer.

    Returns:
        The result of the subtraction.
    """
    logger.info(f"Subtracting {a} - {b}")
    return a - b

# 3. Allow the script to be run directly
if __name__ == "__main__":
    mcp.run()