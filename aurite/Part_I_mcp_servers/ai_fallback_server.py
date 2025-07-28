import logging
import json
import os
import sys
import requests
import asyncio  # ✅ 替代 anyio.gather
import anyio

from openai import OpenAI
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ------------------------
# 配置日志
# ------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------
# OpenAI / SerpAPI 设置
# ------------------------
client = OpenAI(api_key='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')
SERP_API_KEY = '48f928ec180db3a16c78c2223b225a4e90737770fd50e30ebb9b25e33edad06b'

# ------------------------
# 补全逻辑核心（异步）
# ------------------------
async def ai_generate_fallback(city: str) -> dict:
    def search_snippets(city):
        params = {
            "engine": "google",
            "q": f"{city} travel cost site:budgetyourtrip.com OR site:nomadlist.com OR site:wikivoyage.org",
            "api_key": SERP_API_KEY,
        }
        try:
            res = requests.get("https://serpapi.com/search", params=params).json()
            snippets = [r.get("snippet", "") for r in res.get("organic_results", []) if r.get("snippet")]
            return "\n".join(snippets[:5])
        except Exception as e:
            logger.error(f"SerpAPI 错误: {e}")
            return ""

    def summarize(snippets, city: str):
        prompt = f"For a trip to {city}, estimate the average daily travel budget per person, including accommodation, food, transport, and activities. Provide a single number in USD. Respond with just the number."

        try:
            res = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
            )
            content = res.choices[0].message.content.strip()
            budget = float("".join([c for c in content if c.isdigit() or c == "."]))
            return {"city": city, "daily_budget_usd": budget}
        except Exception as e:
            logger.error(f"GPT 补全失败: {e}")
            return {"city": city, "note": f"⚠️ AI 补全失败：{e}"}

    logger.info(f"🔍 正在 AI 补全: {city}")
    summary_input = search_snippets(city)
    if not summary_input:
        return {"city": city, "note": "⚠️ 没有找到摘要"}

    data = summarize(summary_input, city)
    data.setdefault("note", "✅ 此数据由 AI 自动生成")
    return data

# ------------------------
# MCP Tool Handler
# ------------------------
async def _call_tool_handler(name: str, arguments: dict) -> list[TextContent]:
    if name == "ai_fallback":
        cities = arguments.get("cities")
        if not cities or not isinstance(cities, list):
            return [TextContent(type="text", text="⚠️ 参数缺失：请提供城市名称列表")]

        # ✅ 修复这里的 anyio.gather 问题
        results = await asyncio.gather(*[ai_generate_fallback(city) for city in cities])
        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

    else:
        raise ValueError(f"Unknown tool: {name}")

# ------------------------
# MCP Tool 定义
# ------------------------
async def _list_tools_handler() -> list[Tool]:
    return [
        Tool(
            name="ai_fallback",
            description="使用 AI 补全多个城市的旅游预算",
            inputSchema={
                "type": "object",
                "required": ["cities"],
                "properties": {
                    "cities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "城市名称列表"
                    }
                },
            },
        )
    ]

# ------------------------
# MCP Server 创建函数
# ------------------------
def create_server() -> Server:
    app = Server("ai-fallback-server")
    app.call_tool()(_call_tool_handler)
    app.list_tools()(_list_tools_handler)
    return app

# ------------------------
# 启动 stdio 模式
# ------------------------
def main() -> int:
    logger.info("🚀 启动 AI Fallback MCP Server（stdio 模式）")
    app = create_server()

    async def arun():
        async with stdio_server() as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    anyio.run(arun)
    return 0

if __name__ == "__main__":
    sys.exit(main())
