import re
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from bs4 import BeautifulSoup

from models.feed_item import FeedItem
from utils.time_utils import TimeUtils
from utils.string_utils import StringUtils
from net.media_downloader import MediaDownloader


MAX_WORKERS = 4
REPLY_CLASS = "tgme_widget_message_reply"
MEDIA_SELECTOR = ".tgme_widget_message_photo_wrap, video"
MEDIA_BASE_URL = "https://raw.githubusercontent.com/ch3fferson/news-reader-meli/main/feeds/view/media"


class Telegram:

    def __init__(self, media_downloader:MediaDownloader = None, allow_duplicates: bool = True, reverse_items: bool = False):

        self.allow_duplicates = allow_duplicates
        self.reverse_items = reverse_items
        self.media_downloader = media_downloader

    def parse(self, html: str, title_char_limit: int = 60):

        soup = BeautifulSoup(html, "lxml")

        downloaded = {}
        download_lock = Lock()

        seen_titles = set()
        seen_lock = Lock()

        posts = soup.select("div.tgme_widget_message")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = executor.map(
                lambda post: self._process_post(
                    post,
                    title_char_limit,
                    downloaded,
                    download_lock,
                    seen_titles,
                    seen_lock,
                ),
                posts,
            )

        items = [item for item in results if item]

        return items if not self.reverse_items else items[::-1]


    def _process_post(
        self,
        post,
        title_char_limit,
        downloaded,
        download_lock,
        seen_titles,
        seen_lock,
    ):
        try:
            data_post = post["data-post"]

            media_urls = self._find_media_urls(post)

            content = self._extract_content(post, media_urls)

            if not content:
                return None

            title = StringUtils.truncate_text_char(
                content,
                title_char_limit,
            )

            if not self.allow_duplicates:
                with seen_lock:
                    if title in seen_titles:
                        return None
                    seen_titles.add(title)

            time = self._first_own(post, ".time")
            date = ""

            if time and time.has_attr("datetime"):
                date = TimeUtils.to_string(
                    TimeUtils.normalize(time["datetime"])
                )

            media = (
                self._download_media(media_urls, data_post, downloaded, download_lock)
                if media_urls and self.media_downloader
                else []
            )

            return FeedItem(
                title=title,
                content=content,
                date=date,
                link=f"https://t.me/{data_post}",
                media=media,
            )

        except Exception as e:
            print(f"error: {e}")
            return None

    @staticmethod
    def _own_elements(post, selector):
        """
        Returns all elements matching `selector` that belong to the post
        itself, in document order, skipping anything nested inside a
        quoted reply block (`.tgme_widget_message_reply`), since that
        subtree describes the message being replied to, not the post
        being parsed. Grouped albums (galleries) repeat the same media
        markup once per attachment, so returning every match (not just
        the first) is what lets multi-media posts be captured in full.
        """
        return [
            el for el in post.select(selector)
            if el.find_parent(class_=REPLY_CLASS) is None
        ]

    @classmethod
    def _first_own(cls, post, selector):
        elements = cls._own_elements(post, selector)
        return elements[0] if elements else None

    def _extract_content(self, post, media_urls) -> str:
        """
        Builds textual content for any post type. Regular text posts use
        their own caption; media galleries, polls, documents, voice
        notes, and link-preview-only posts fall back to a descriptive
        label so no post is silently dropped just because it lacks a
        text caption.
        """
        text = self._first_own(post, ".tgme_widget_message_text")
        if text:
            content = StringUtils.remove_html_shenanigans(
                text.decode_contents()
            ).strip()
            if content:
                return content

        poll_question = self._first_own(post, ".tgme_widget_message_poll_question")
        if poll_question:
            own_options = [
                option.get_text(" ", strip=True)
                for option in self._own_elements(post, ".tgme_widget_message_poll_option_text")
            ]
            parts = [f"📊 {poll_question.get_text(' ', strip=True)}"]
            parts.extend(f"— {option}" for option in own_options)
            return StringUtils.remove_html_shenanigans(" ".join(parts)).strip()

        document_title = self._first_own(post, ".tgme_widget_message_document_title")
        if document_title:
            return StringUtils.remove_html_shenanigans(
                f"📄 {document_title.get_text(' ', strip=True)}"
            ).strip()

        link_preview = self._first_own(post, ".tgme_widget_message_link_preview")
        if link_preview:
            preview_parts = [
                el.get_text(" ", strip=True)
                for el in (
                    link_preview.select_one(".link_preview_title"),
                    link_preview.select_one(".link_preview_description"),
                )
                if el
            ]
            if preview_parts:
                return StringUtils.remove_html_shenanigans(" — ".join(preview_parts)).strip()

        if self._first_own(post, ".tgme_widget_message_voice"):
            return "🎤 پیام صوتی"

        if len(media_urls) > 1:
            return f"🖼 گالری ({len(media_urls)} رسانه)"

        if self._first_own(post, "video"):
            return "🎬 ویدیو"

        if self._first_own(post, ".tgme_widget_message_photo_wrap"):
            return "🖼 تصویر"

        if self._first_own(post, "img"):
            return "🖼 تصویر"

        return ""

    def _find_media_urls(self, post) -> list[str]:
        """
        Collects every media attachment on the post, in display order:
        photos and videos, whether the post has a single attachment or a
        grouped album (gallery). Falls back to a link-preview thumbnail,
        then a generic image (sticker), for posts with no direct media.
        """
        urls = []
        seen = set()

        def add(url):
            if url and url not in seen:
                seen.add(url)
                urls.append(url)

        for element in self._own_elements(post, MEDIA_SELECTOR):
            if element.name == "video":
                src = element.get("src")
                if not src:
                    source = element.select_one("source")
                    src = source.get("src") if source else None
                add(src)
            else:
                style = element.get("style", "")
                m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                if m:
                    add(m.group(1))

        if urls:
            return urls

        link_preview_image = self._first_own(
            post, ".tgme_widget_message_link_preview .link_preview_image"
        )

        if link_preview_image:
            style = link_preview_image.get("style", "")
            m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
            if m:
                add(m.group(1))

        if urls:
            return urls

        img = self._first_own(post, "img")

        if img:
            src = img.get("src")
            if src and "emoji" not in src:
                add(src)

        if urls:
            return urls

        source = self._first_own(post, "source")

        if source and source.get("src"):
            add(source["src"])

        return urls

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
            f"{MEDIA_BASE_URL}/{file_name}"
            for file_name in file_names
        ]
