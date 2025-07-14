import json
import os
from scrapy.crawler import CrawlerProcess
from price_spider.price_spider.spiders.city_detail import CityDetailSpider


def run(city: str):
    output_file = "result.json"

    # 若文件已存在，先删除，避免读取到旧数据
    if os.path.exists(output_file):
        os.remove(output_file)

    process = CrawlerProcess(settings={
        "FEEDS": {
            output_file: {
                "format": "json",
                "encoding": "utf8",
                "indent": 4,
            },
        },
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/",
        }
    })

    # 启动爬虫（阻塞执行）
    process.crawl(CityDetailSpider, city=city)
    process.start()

    # 爬虫结束后读取 JSON 文件
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf8") as f:
            data = json.load(f)
        return data
    else:
        return []


# 示例调用
if __name__ == "__main__":
    result = run("beijing")
    print("=== 爬取结果 ===")
    for i, item in enumerate(result, 1):
        print(f"\n--- Item {i} ---")
        print(item)
