import sys
import asyncio
import logging
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor

import anyio
from mcp.types import Tool, TextContent, Prompt, PromptArgument, GetPromptResult, PromptMessage
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from spider_runner import run_sequential  # 支持多城市的同步爬虫函数

# 初始化日志
ogging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=1)

# ------------------------
# 工具实现
# ------------------------

async def have_city_prices(arguments: Dict) -> List[TextContent]:
    cities = arguments.get("cities", [])
    if not cities:
        return [TextContent(type="text", text="⚠️ 参数缺失：请提供至少一个城市名称")]

    logger.info(f"📥 查询城市价格: {cities}")
    try:
        loop = asyncio.get_event_loop()
        result_list = await loop.run_in_executor(executor, run_sequential, cities)

        results = []
        for item in result_list:
            city = item.get("city", ["未知城市"])[0]
            results.append(
                TextContent(
                    type="text",
                    text=f"🌍 城市: {city}\n预算信息如下：\n"
                         f"🕓 数据更新日期：{item.get('last_updated')}\n"
                         f"🎒 背包客预算：{item.get('backpacker_budget')}\n"
                         f"🍽️ 餐饮价格：{item.get('food_prices')}\n"
                         f"🛏️ 住宿价格：{item.get('accommodation_prices')}\n"
                         f"🚇 交通价格：{item.get('transport_prices')}\n"
                         f"🎯 景点价格：{item.get('attraction_prices')}"
                )
            )

        return results

    except Exception as e:
        logger.error(f"❌ 爬虫运行出错: {e}")
        return [TextContent(type="text", text=f"❌ 获取失败：{str(e)}")]

# ------------------------
# Prompt（可选支持）
# ------------------------

CITY_PRICE_PROMPT = (
    "你是一个聪明的城市旅游花费助手，请帮助用户查询多个城市的旅行预算信息。"
)

async def _list_prompts_handler() -> List[Prompt]:
    return [
        Prompt(
            name="city_price_assistant",
            description="城市旅游花费助手",
            arguments=[
                PromptArgument(name="user_name", description="用户名字", required=False),
                PromptArgument(name="preferred_city", description="感兴趣的城市", required=False),
            ],
        )
    ]

async def _get_prompt_handler(name: str, arguments: dict) -> GetPromptResult:
    if name != "city_price_assistant":
        raise ValueError(f"Unknown prompt: {name}")

    prompt = CITY_PRICE_PROMPT
    if "user_name" in arguments:
        prompt = f"你好，{arguments['user_name']}！" + prompt
    if "preferred_city" in arguments:
        prompt += f"\n你当前感兴趣的城市是：{arguments['preferred_city']}。"

    return GetPromptResult(
        messages=[PromptMessage(role="user", content=TextContent(type="text", text=prompt))]
    )

# ------------------------
# Handler 注册
# ------------------------

async def _call_tool_handler(name: str, arguments: dict) -> List[TextContent]:
    if name == "have_city_prices":
        return await have_city_prices(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def _list_tools_handler() -> List[Tool]:
    return [
        Tool(
            name="have_city_prices",
            description="获取一个或多个城市的旅游价格信息",
            inputSchema={
                "type": "object",
                "required": ["cities"],
                "properties": {
                    "cities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "目标城市名称列表（英文）",
                    }
                },
            },
        )
    ]

# ------------------------
# MCP Server 创建函数
# ------------------------

def create_server() -> Server:
    app = Server("city-price-server")
    app.call_tool()(_call_tool_handler)
    app.list_tools()(_list_tools_handler)
    app.list_prompts()(_list_prompts_handler)
    app.get_prompt()(_get_prompt_handler)
    return app

# ------------------------
# 启动 stdio 模式
# ------------------------

def main() -> int:
    logger.info("🚀 启动 City Price MCP Server（stdio 模式）")
    app = create_server()

    async def arun():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)
    return 0

if __name__ == "__main__":
    sys.exit(main())

