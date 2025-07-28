# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class CityDetailItem(scrapy.Item):
    city = scrapy.Field()
    last_updated = scrapy.Field()
    backpacker_budget = scrapy.Field()
    food_prices = scrapy.Field()
    attraction_prices = scrapy.Field()
    accommodation_prices = scrapy.Field()
    transport_prices = scrapy.Field()
    pass
