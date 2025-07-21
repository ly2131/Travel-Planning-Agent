from scrapy.crawler import CrawlerProcess
from price_spider.price_spider.spiders.city_detail import CityDetailSpider
import os
import json


def run_sequential(city_list):
    output_file = "result.json"

    # 删除旧文件，避免内容冲突
    if os.path.exists(output_file):
        os.remove(output_file)

    # 初始化 Scrapy CrawlerProcess
    process = CrawlerProcess(settings={
        "FEEDS": {
            output_file: {
                "format": "jsonlines",  # 每行一个 JSON 对象
                "encoding": "utf8",
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

    for city in city_list:
        print(f"\n🌐 正在爬取城市: {city}")
        process.crawl(CityDetailSpider, city=city)

    process.start()

    return load_jsonlines(output_file)


def load_jsonlines(filepath: str):
    data = []
    with open(filepath, "r", encoding="utf8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析失败 (line {i}): {e}")
                print(f"🔎 内容: {repr(line)}")
    return data


# 主程序入口
if __name__ == "__main__":
    cities = ["beijing", "bangkok", "paris"]
    result = run_sequential(cities)

    print("\n✅ 所有城市爬取完成，共", len(result), "条数据")
    for item in result:
        print(f"\n🌍 城市: {item.get('city', ['Unknown'])[0]}")
        print(json.dumps(item, indent=2, ensure_ascii=False))
