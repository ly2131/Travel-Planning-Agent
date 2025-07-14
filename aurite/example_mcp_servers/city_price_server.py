import logging
from typing import Dict
from mcp.server.fastmcp import FastMCP
from spider_runner import run  # 本地同步函数
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP server 实例
mcp = FastMCP("City Price Agent")

# 线程池用于非阻塞运行爬虫
executor = ThreadPoolExecutor(max_workers=1)

@mcp.tool()
async def have_city_prices(city: str) -> Dict:
    """
    获取城市旅游价格信息（线程安全方式运行爬虫）
    """
    logger.info(f"📥 查询城市价格: {city}")
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, run, city)
        return {"success": True, "city": city, "result": result}
    except Exception as e:
        logger.error(f"❌ 出错: {e}")
        return {"success": False, "error": str(e)}

# 启动 MCP server
if __name__ == "__main__":
    print("✅ MCP server 正在启动中")
    mcp.run()
