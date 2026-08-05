import mimetypes
import xml.etree.ElementTree as ET
from pathlib import Path
from utils.id_generator import IDGenerator


class XMLBuilder:

    MEDIA_NS = "http://search.yahoo.com/mrss/"

    SUPPORTED_IMAGES = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".avif",
        ".bmp",
        ".svg",
        ".gif",
    }

    SUPPORTED_VIDEOS = {
        ".mp4",
        ".webm",
        ".mov",
        ".m4v",
        ".ogv",
    }

    def __init__(self):
        ET.register_namespace("media", self.MEDIA_NS)

    def build(self, items, title: str):

        base_url = (
            "https://htmlpreview.github.io/?"
            "https://raw.githubusercontent.com/"
            "shawnkasaei/news-reader-meli/"
            "refs/heads/main/feeds/view/index.html"
        )

        root = ET.Element(
            "rss",
            {
                "version": "2.0",
                "xmlns:media": self.MEDIA_NS
            }
        )

        channel = ET.SubElement(root, "channel")

        ET.SubElement(channel, "title").text = title

        for item in items:

            anchor_id = IDGenerator.generate(
                item.date + item.title + item.content
            )

            node = ET.SubElement(channel, "item")

            ET.SubElement(node, "pubDate").text = item.date
            ET.SubElement(node, "title").text = item.title
            ET.SubElement(node, "description").text = item.content
            ET.SubElement(node, "link").text = (
                f"{base_url}#{anchor_id}"
            )

            if item.media != []:
                self._add_media(node, item.media[0])

        ET.indent(root, space="    ")

        return ET.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )

    def _add_media(self, node, url: str):

        extension = Path(
            url.split("?")[0]
        ).suffix.lower()

        if extension in self.SUPPORTED_IMAGES:
            medium = "image"

        elif extension in self.SUPPORTED_VIDEOS:
            medium = "video"

        else:
            return

        mime_type, _ = mimetypes.guess_type(url)

        ET.SubElement(
            node,
            f"{{{self.MEDIA_NS}}}content",
            {
                "url": url,
                "medium": medium,
                "type": mime_type or ""
            }
        )

        if medium == "image":
            ET.SubElement(
                node,
                f"{{{self.MEDIA_NS}}}thumbnail",
                {
                    "url": url
                }
            )