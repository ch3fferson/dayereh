from dataclasses import dataclass


@dataclass
class FeedItem:
    title: str
    content: str
    date: str
    link: str
    media: list[str]