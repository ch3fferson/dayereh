import re
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from utils.string_utils import StringUtils
from utils.time_utils import TimeUtils
from utils.id_generator import IDGenerator
from models.feed_item import FeedItem
from net.media_downloader import MediaDownloader


MAX_WORKERS = 4


class RSS:

    def __init__(self, media_downloader: MediaDownloader, allow_duplicates: bool = True, reverse_items: bool = False):

        self.allow_duplicates = allow_duplicates
        self.reverse_items = reverse_items
        self.media_downloader = media_downloader

    def parse(self, xml: str, title_char_limit: int = 60):

        downloaded = {}
        download_lock = Lock()

        seen_titles = set()
        seen_lock = Lock()

        raw_items = re.findall(r"<item>([\s\S]*?)</item>", xml)

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = executor.map(
                lambda item: self._process_item(
                    item,
                    title_char_limit,
                    downloaded,
                    download_lock,
                    seen_titles,
                    seen_lock,
                ),
                raw_items,
            )

        items = [item for item in results if item]

        return (
            items
            if not self.reverse_items
            else items[::-1]
        )

    def _process_item(
        self,
        item,
        title_char_limit,
        downloaded,
        download_lock,
        seen_titles,
        seen_lock,
    ):
        try:
            title_match = re.search(
                r"<title>([\s\S]*?)</title>",
                item
            )

            content_match = re.search(
                r"<description>([\s\S]*?)</description>",
                item
            )

            date_match = re.search(
                r"<pubDate>([\s\S]*?)</pubDate>",
                item
            )

            link_match = re.search(
                r"<link>([\s\S]*?)</link>",
                item
            )

            if not all([
                title_match,
                content_match,
                date_match,
                link_match
            ]):
                return None

            content = StringUtils.remove_html_shenanigans(
                            content_match.group(1).strip()
                        )

            title = StringUtils.truncate_text_char(
                content,
                title_char_limit,
            )

            date = TimeUtils.to_string(
                TimeUtils.normalize(
                    date_match.group(1).strip()
                )
            )

            link = link_match.group(1).strip()

            if not self.allow_duplicates:
                with seen_lock:
                    if title in seen_titles:
                        return None
                    seen_titles.add(title)

            domain_match = re.search(
                r'^(?:https?://)?(?:www\.)?([^/?#:]+)',
                link,
            )

            if not domain_match:
                return None

            domain = domain_match.group(1)

            item_id = IDGenerator.generate(
                date + title + content
            )

            file_name = f"{domain}-{item_id}"

            media_urls = self._parse_media(item)

            media = self._download_media(
                media_urls,
                file_name,
                downloaded,
                download_lock,
            )

            return FeedItem(
                title=title,
                content=content,
                date=date,
                link=link,
                media=media,
            )

        except Exception:
            return None

    def _download_media(
        self,
        media_urls,
        post_id,
        downloaded,
        download_lock,
    ):

        file_names = []

        for index, url in enumerate(media_urls):

            with download_lock:
                cached = downloaded.get(url)

            if cached:
                file_name = cached
            else:
                item_id = (
                    post_id
                    if index == 0
                    else f"{post_id}_{index}"
                )

                file_name = self.media_downloader.download(
                    url,
                    item_id,
                )

                with download_lock:
                    file_name = downloaded.setdefault(
                        url,
                        file_name,
                    )

            if file_name:
                file_names.append(file_name)

        return [
            f"https://raw.githubusercontent.com/ch3fferson/news-reader-meli/main/feeds/view/media/{file_name}"
            for file_name in file_names
        ]

    def _parse_media(self, item: str):

        medias = []

        medias.extend(
            re.findall(
                r'<media:content[^>]+url=["\'](.*?)["\']',
                item
            )
        )

        medias.extend(
            re.findall(
                r'<media:thumbnail[^>]+url=["\'](.*?)["\']',
                item
            )
        )

        medias.extend(
            re.findall(
                r'<enclosure[^>]+url=["\'](.*?)["\']',
                item
            )
        )

        return list(dict.fromkeys(medias))