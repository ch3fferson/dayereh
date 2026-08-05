import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional
import requests
from bs4 import BeautifulSoup

_NUM_RE = re.compile(r"-?[\d,]+\.?\d*")
_CHANGE_RE = re.compile(r"([\d,]+\.?\d*)\s*\(([-\d.]+)%\)")


@dataclass(slots=True)
class TGJUItem:
    slug: str
    title: str
    price: Optional[float]
    change_value: Optional[float]
    change_percent: Optional[float]
    direction: str
    low: Optional[float]
    high: Optional[float]
    time: str
    unit: str
    category: str

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "title": self.title,
            "price": self.price,
            "change_value": self.change_value,
            "change_percent": self.change_percent,
            "direction": self.direction,
            "low": self.low,
            "high": self.high,
            "time": self.time,
            "unit": self.unit,
            "category": self.category,
        }


class TGJU:
    BASE_URL = "https://www.tgju.org"
    ENDPOINTS = {
        "currency": "/currency",
        "coin": "/coin",
        "gold": "/gold-chart",
    }

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        max_workers: int = 3,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_workers = max_workers
        self.session = session or self._build_session()
        self.everything = None

        print("⟳ getting https://www.tgju.org")

        try:
            self.everything = self.get_all()
            print("✓ https://www.tgju.org parsed")

        except Exception as e:
            print("☓ couldn't parse https://www.tgju.org")
            print(f"error: {e}")

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fa,en-US;q=0.9,en;q=0.8",
                "Connection": "keep-alive",
            }
        )
        return session

    def _fetch(self, path: str) -> str:
        url = f"{self.BASE_URL}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                response.encoding = "utf-8"
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(self.backoff_factor * (2**attempt))
        raise ConnectionError(f"Failed to fetch {url}: {last_error}") from last_error

    @staticmethod
    def _to_float(text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        match = _NUM_RE.search(text.replace(",", ""))
        if not match:
            return None
        try:
            return float(match.group())
        except ValueError:
            return None

    @staticmethod
    def _direction(row) -> str:
        classes = row.get("class") or []
        if "high" in classes:
            return "up"
        if "low" in classes:
            return "down"
        change_cell = row.find(class_=re.compile(r"^(high|low)$"))
        if change_cell:
            cell_classes = change_cell.get("class") or []
            if "high" in cell_classes:
                return "up"
            if "low" in cell_classes:
                return "down"
        return "unchanged"

    def _parse_change(self, cell) -> tuple[Optional[float], Optional[float]]:
        if cell is None:
            return None, None
        text = cell.get_text(strip=True)
        match = _CHANGE_RE.search(text)
        if not match:
            return 0.0, self._to_float(text)
        value = self._to_float(match.group(1))
        percent = self._to_float(match.group(2))
        if value is not None and self._direction_from_text(text) == "down":
            value = -abs(value)
        return value, percent

    @staticmethod
    def _direction_from_text(text: str) -> str:
        return "down" if text.strip().startswith("-") else "up"

    def _parse_table_row(self, row, category: str, unit: str) -> Optional[TGJUItem]:
        slug = row.get("data-market-nameslug")
        if not slug:
            return None
        slug = slug.replace("disabled_", "")

        title_cell = row.find("th")
        title = title_cell.get_text(strip=True) if title_cell else slug

        cells = row.find_all("td")
        if len(cells) < 5:
            return None

        price = self._to_float(row.get("data-price")) or self._to_float(cells[0].get_text())
        change_value, change_percent = self._parse_change(cells[1])
        direction = self._direction(row)
        if direction == "unchanged" and change_value:
            direction = "up" if change_value > 0 else "down"

        low = self._to_float(cells[2].get_text())
        high = self._to_float(cells[3].get_text())

        row_time = re.match(r"\d{4}-\d{2}-\d{2}", cells[4].get_text(strip=True))
        if not row_time: row_time = ""

        return TGJUItem(
            slug=slug,
            title=title,
            price=price,
            change_value=change_value,
            change_percent=change_percent,
            direction=direction,
            low=low,
            high=high,
            time=row_time,
            unit=unit,
            category=category,
        )

    def _parse_market_tables(self, html: str, category: str, unit: str = "IRR") -> list[TGJUItem]:
        soup = BeautifulSoup(html, "lxml")
        items: list[TGJUItem] = []
        seen: set[str] = set()
        for table in soup.select("table.market-table"):
            for row in table.select("tbody tr[data-market-nameslug]"):
                item = self._parse_table_row(row, category, unit)
                if item and item.slug not in seen:
                    seen.add(item.slug)
                    items.append(item)
        return items

    def _parse_summary_ticker(self, html: str) -> list[TGJUItem]:
        soup = BeautifulSoup(html, "lxml")
        items: list[TGJUItem] = []
        for li in soup.select("ul.info-bar > li[id^='l-']"):
            slug = li.get("id", "").replace("l-", "")
            title_tag = li.find("strong")
            title = title_tag.get_text(strip=True) if title_tag else slug
            price_tag = li.find(class_="info-price")
            change_tag = li.find(class_="info-change")
            price = self._to_float(price_tag.get_text()) if price_tag else None
            change_value, change_percent = self._parse_change(change_tag)
            classes = li.get("class") or []
            direction = "up" if "high" in classes else "down" if "low" in classes else "unchanged"
            items.append(
                TGJUItem(
                    slug=slug,
                    title=title,
                    price=price,
                    change_value=change_value,
                    change_percent=change_percent,
                    direction=direction,
                    low=None,
                    high=None,
                    time="",
                    unit="",
                    category="summary",
                )
            )
        return items

    def get_currencies(self) -> list[TGJUItem]:
        html = self._fetch(self.ENDPOINTS["currency"])
        return self._parse_market_tables(html, category="currency", unit="IRR")

    def get_coins(self) -> list[TGJUItem]:
        html = self._fetch(self.ENDPOINTS["coin"])
        return self._parse_market_tables(html, category="coin", unit="IRR")

    def get_gold(self) -> list[TGJUItem]:
        html = self._fetch(self.ENDPOINTS["gold"])
        return self._parse_market_tables(html, category="gold", unit="IRR")

    def get_summary(self) -> list[TGJUItem]:
        html = self._fetch(self.ENDPOINTS["currency"])
        return self._parse_summary_ticker(html)

    def get_all(self) -> dict[str, list[TGJUItem]]:
        results: dict[str, list[TGJUItem]] = {}
        fetchers = {
            "currency": self.get_currencies,
            "coin": self.get_coins,
            "gold": self.get_gold,
        }
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(fn): name for name, fn in fetchers.items()}
            for future in as_completed(futures):
                name = futures[future]
                results[name] = future.result()
        return results

    def find(self, slug: str) -> Optional[TGJUItem]:
        for items in self.everything.values():
            for item in items:
                if item.slug == slug:
                    return item
        return None

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "TGJUScraper":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
