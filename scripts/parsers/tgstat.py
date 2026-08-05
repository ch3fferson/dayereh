from bs4 import BeautifulSoup
from datetime import datetime
from utils.string_utils import StringUtils
from utils.time_utils import TimeUtils
from models.feed_item import FeedItem


class TGStat:

    def __init__(self, allow_duplicates: bool = True, reverse_items: bool = False):
        
        self.allow_duplicates = allow_duplicates
        self.reverse_items = reverse_items

    def parse(self, html:str, title_char_limit:int = 60):

        soup = BeautifulSoup(html, "lxml")

        containers = soup.select(".post-container")
        items = []

        for container in containers:
            
            date = container.select_one(".text-muted.m-0").get_text(" ", strip=True)
            text = container.select_one(".post-text").get_text(" ", strip=True)

            url = container.select_one(".btn.btn-light.btn-rounded.p-05.popup_ajax.font-12.font-sm-13.d-sm-inline").get("href")
            url = "https://ir.tgstat.com" + url

            try:
                date = TimeUtils.normalize(
                    f"{datetime.now().year} {date}",
                    fmt="%Y %d %b, %H:%M"
                )
                date = TimeUtils.to_string(date)

                title = StringUtils.truncate_text_char(text, title_char_limit)

                if (list(filter(lambda x: x.title == title, items))) and not self.allow_duplicates:
                    continue

                items.append(
                        FeedItem(
                            title=title,
                            content=text,
                            date=date,
                            link=url
                        )
                    )
            except:
                continue

        return items if not self.reverse_items else items[::-1]