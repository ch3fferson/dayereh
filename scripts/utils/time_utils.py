from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional, Union

TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))


class TimeUtils:

    @staticmethod
    def normalize(
        value: Union[str, int, float, datetime],
        to_tz: timezone = TEHRAN_TZ,
        fmt: Optional[str] = None
    ) -> datetime:

        dt = TimeUtils._to_datetime(value, fmt)
        dt_utc = TimeUtils._to_utc(dt)
        return dt_utc.astimezone(to_tz)

    @staticmethod
    def _to_datetime(
        value: Union[str, int, float, datetime],
        fmt: Optional[str] = None
    ) -> datetime:

        if isinstance(value, datetime):
            return value

        if isinstance(value, (int, float)):
            # Auto-detect milliseconds timestamp
            if value > 10_000_000_000:
                value /= 1000

            return datetime.fromtimestamp(value, tz=timezone.utc)

        if isinstance(value, str):
            value = value.strip()

            if fmt:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    pass

            try:
                return datetime.fromisoformat(value)
            except ValueError:
                pass

            try:
                return parsedate_to_datetime(value)
            except Exception:
                pass

        raise ValueError(f"Unsupported time format: {value}")

    @staticmethod
    def _to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def to_string(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        return dt.strftime(fmt)

    @staticmethod
    def now(to_tz: timezone = TEHRAN_TZ) -> datetime:
        return datetime.now(timezone.utc).astimezone(to_tz)

    @staticmethod
    def from_timestamp(
        timestamp: Union[int, float],
        to_tz: timezone = TEHRAN_TZ,
        fmt: Optional[str] = None
    ) -> Union[datetime, str]:
        """
        Convert Unix timestamp (seconds or milliseconds) to target timezone.
        """
        dt = TimeUtils.normalize(timestamp, to_tz)

        return TimeUtils.to_string(dt, fmt) if fmt else dt

    @staticmethod
    def parse_persian_time(value: str, to_tz: timezone = TEHRAN_TZ) -> datetime:
        value = value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

        today = datetime.now(to_tz).strftime("%Y-%m-%d")

        dt = datetime.strptime(
            f"{today} {value}",
            "%Y-%m-%d %H:%M:%S"
        )

        return dt.replace(tzinfo=to_tz)