import json
from bs4 import BeautifulSoup
from utils.string_utils import StringUtils
from utils.time_utils import TimeUtils
from models.feed_item import FeedItem


class Website:

    def __init__(self, allow_duplicates: bool = True, reverse_items: bool = False):
        
        self.allow_duplicates = allow_duplicates
        self.reverse_items = reverse_items

    def parse(self, html:str, scraping_rules: str, title_char_limit:int = 60):

        rules = json.loads(scraping_rules)

        soup = BeautifulSoup(html, "lxml")

        containers = soup.select(rules.get("container"))

        items = []

        for c in containers:
           
            title_selector = rules.get("title")
            title = c.select_one(title_selector).get_text(strip=True) if title_selector else ""

            description_selector = rules.get("description")
            description = c.select_one(description_selector).get_text(strip=True) if description_selector else "" 

            date_selector = rules.get("date")
            date = c.select_one(date_selector).get_text(strip=True) if date_selector else ""

            date_format = rules.get("date_format")
        
            url_selector = rules.get("url")
            url = c.select_one(url_selector).get("href") if url_selector else ""

            url_base = rules.get("url_base")

            try:
                title = StringUtils.truncate_text_char(title, title_char_limit)
        
                if date and date_format:
                    date = TimeUtils.normalize(date, date_format)
                    date = TimeUtils.to_string(date)

                if url_base and url:
                    url = url_base + url

                if (list(filter(lambda x: x.title == title, items))) and not self.allow_duplicates:
                    continue

                items.append(
                        FeedItem(
                            title=title,
                            content=description,
                            date=date,
                            link=url
                        )
                    )
            except:
                continue

        return items if not self.reverse_items else items[::-1]