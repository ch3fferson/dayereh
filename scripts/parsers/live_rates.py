from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import requests


@dataclass(frozen=True, slots=True)
class Rate:
    currency: str
    rate: float
    bid: float
    ask: float
    high: Optional[float]
    low: Optional[float]
    open: float
    close: Optional[float]
    timestamp: int

    @property
    def datetime(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp / 1000, tz=timezone.utc)

    @classmethod
    def from_raw(cls, data: dict) -> "Rate":
        def to_float(value: str) -> Optional[float]:
            return None if value == "n/a" else float(value)

        return cls(
            currency=data["currency"],
            rate=to_float(data["rate"]),
            bid=to_float(data["bid"]),
            ask=to_float(data["ask"]),
            high=to_float(data["high"]),
            low=to_float(data["low"]),
            open=to_float(data["open"]),
            close=to_float(data["close"]),
            timestamp=int(data["timestamp"]),
        )


class LiveRates:
    URL = "https://www.live-rates.com/rates"

    def __init__(self, timeout: float = 10.0, session: Optional[requests.Session] = None):
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        )
        self.rates = None
        self._rates_map: Optional[dict[str, Rate]] = None

        print("⟳ getting https://www.live-rates.com/rates")

        try:
            self.rates = self.fetch()
            self._rates_map = {rate.currency: rate for rate in self.rates}
            print("✓ https://www.live-rates.com/rates parsed")

        except Exception as e:
            print("☓ couldn't parse https://www.live-rates.com/rates")
            print(f"error: {e}")


    def fetch(self) -> list[Rate]:
        response = self.session.get(self.URL, timeout=self.timeout)
        response.raise_for_status()
        return [Rate.from_raw(item) for item in response.json()]

    def fetch_map(self) -> dict[str, Rate]:
        if self._rates_map is None:
            self._rates_map = {rate.currency: rate for rate in (self.rates or [])}
        return self._rates_map

    def get(self, currency: str) -> Optional[Rate]:
        return self.fetch_map().get(currency)