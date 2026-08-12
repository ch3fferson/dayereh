from pathlib import Path


class PathUtils:

    def __init__(self, base_path):
        self.base = Path(base_path)

        self.feeds = self.base / "feeds"

        self.view = self.feeds / "view"

        self.media = self.view / "media"

    def save_xml(self, name: str, data: bytes):
        self.feeds.mkdir(parents=True, exist_ok=True)
        (self.feeds / f"{name}.xml").write_bytes(data)

    def save_json(self, name: str, data: str):
        self.feeds.mkdir(parents=True, exist_ok=True)
        (self.feeds / f"{name}.json").write_text(data, encoding="utf-8")

    def save_html(self, html: str):
        self.view.mkdir(parents=True, exist_ok=True)
        (self.view / "index.html").write_text(html, encoding="utf-8")
