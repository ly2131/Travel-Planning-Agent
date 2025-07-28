import scrapy
from scrapy.loader import ItemLoader
from price_spider.price_spider.items import CityDetailItem  # 关键：从 items.py 引入

class CityDetailSpider(scrapy.Spider):
    name = 'city_detail'
    allowed_domains = ['priceoftravel.com']
    def __init__(self, city=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.start_urls = [f'https://www.priceoftravel.com/{self.city}-price-guide']

    def parse(self, response):
        loader = ItemLoader(item=CityDetailItem(), response=response)

        # 城市、国家
        full_title = response.css("h1.intro__title::text").get()
        city = ""
        if full_title:
            # 从标题中提取城市名，假设格式稳定，如 "... Travel to CITY ..."
            import re
            match = re.search(r"travel to ([A-Za-z\s\-]+?)(:|$)", full_title, re.IGNORECASE)
            if match:
                city = match.group(1).strip()
        loader.add_value('city', city)

        published_date = response.css("span.published_date::text").get()
        loader.add_value('last_updated', published_date)


        # 预算
        text = response.css("div.currency__item::text").get()
        index = None

        if text:
            import re
            match = re.search(r"US\$\s*([\d\.]+)", text)
            if match:
                index = float(match.group(1))
        loader.add_value('backpacker_budget', index)

        # 表格：食物、交通、住宿、景点
        loader.add_value('food_prices', self.extract_food_prices(response))
        loader.add_value('accommodation_prices', self.extract_accommodation_prices(response))
        loader.add_value('attraction_prices', self.extract_attraction_prices(response))
        loader.add_value('transport_prices', self.extract_transport_prices(response))

        yield loader.load_item()

    def extract_text_after(self, response, title_keyword):
        para = response.xpath(f'//strong[contains(text(), "{title_keyword}")]/following-sibling::text()[1]').get()
        if para:
            return para.strip()
        return None

    def extract_price_table(self, response, section_title):
        section = response.xpath(f'//h2[contains(text(), "{section_title}")]/following-sibling::table[1]')
        rows = section.css('tr')
        data = {}
        for row in rows:
            cols = row.css('td::text').getall()
            if len(cols) >= 2:
                item = cols[0].strip()
                price = cols[1].strip()
                data[item] = price
        return data

    def extract_accommodation_prices(self, response):
        prices = {}


        hotel_rows = response.css("h3:contains('Hotel Prices') + div table tr")

        for i, row in enumerate(hotel_rows):
            stars = len(row.css("td.rating_td > img.star.active"))
            price_text = row.css("td.price_td::text").get()
            if stars > 0 and price_text:
                prices[f"{stars}-star"] = price_text.strip()

        hostel_rows = response.css("h3:contains('Beijing Hostels Prices') + div table tr")

        for row in hostel_rows:
            label = row.css("td.title_td::text").get()
            price_text = row.css("td.price_td::text").get()
            if label and price_text:
                prices[label.strip()] = price_text.strip()

        return prices

    def extract_attraction_prices(self, response):
        rows = response.css('div.city__attrractions table tr')
        data = []

        for row in rows:
            name = row.css('td.title_td::text').get()
            ticket_type = row.css('td.price_type_td div::text').get()
            price = row.css('td:nth-child(4) div::text').get()

            if name and price:
                data.append({
                    'name': name.strip(),
                    'type': ticket_type.strip() if ticket_type else '',
                    'price': price.strip()
                })

        return data

    def extract_food_prices(self, response):
        rows = response.css("h2#food__section + div + div table tr")
        data = []

        for row in rows:
            food_type = row.css("td.title_td::text").get()
            price = row.css("td.price_td::text").get()

            if food_type and price:
                lower = food_type.lower()
                if any(key in lower for key in ["breakfast", "lunch", "dinner"]):
                    data.append({
                        "type": food_type.strip(),
                        "price": price.strip()
                    })

        return data

    def extract_transport_prices(self, response):
        # 精确锁定交通部分下的表格行
        rows = response.css("h2#transport__section + div table tr")
        data = []

        for row in rows:
            if not row.css("td"):
                continue  # 跳过表头

            transport_type = row.css("td.title_td::text").get()
            price = row.css("td.price_td::text").get()

            if transport_type and price:
                data.append({
                    "type": transport_type.strip(),
                    "price": price.strip()
                })

        return data
