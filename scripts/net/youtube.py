import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import requests
from yt_dlp import YoutubeDL
from ai.gemini import GeminiClient, GenerationConfig


@dataclass(slots=True)
class VideoInfo:
    id: str | None
    title: str | None
    description: str | None
    channel: str | None
    channel_id: str | None
    duration: int | None
    upload_date: datetime | None
    release_date: datetime | None
    published_at: datetime | None
    view_count: int | None
    like_count: int | None
    comment_count: int |None
    is_live: bool
    was_live: bool
    live_status: str | None
    thumbnail: str | None
    tags: list[str]
    categories: list[str]
    subtitles: list[str]
    automatic_subtitles: list[str]
    transcript: str


class YouTube:

    def __init__(self, lang: str = "fa", timeout: int = 15, gemini_key: str = None):
        self.lang = lang
        self.timeout = timeout
        self.gemini_key = gemini_key

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

        self.ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

    def get(self, url: str) -> VideoInfo:
        with YoutubeDL(self.ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        transcript = self._transcript(data)

        return VideoInfo(
            id=data.get("id"),
            title=data.get("title"),
            description=data.get("description"),
            channel=data.get("uploader"),
            channel_id=data.get("channel_id"),
            duration=self._duration(data.get("duration")),
            upload_date=self._date(data.get("upload_date")),
            release_date=self._date(data.get("release_date")),
            published_at=self._timestamp(data.get("timestamp")),
            view_count=data.get("view_count"),
            like_count=data.get("like_count"),
            comment_count=data.get("comment_count"),
            is_live=bool(data.get("is_live")),
            was_live=bool(data.get("was_live")),
            live_status=data.get("live_status"),
            thumbnail=data.get("thumbnail"),
            tags=data.get("tags") or [],
            categories=data.get("categories") or [],
            subtitles=list((data.get("subtitles") or {}).keys()),
            automatic_subtitles=list((data.get("automatic_captions") or {}).keys()),
            transcript=self._transcript_ai(transcript),
        )

    def _transcript(self, data: dict[str, Any]) -> str:
        captions = (data.get("automatic_captions") or {}).get(self.lang)

        if not captions:
            return ""

        subtitle = next(
            (item for item in captions if item.get("ext") == "vtt"),
            None,
        )

        if not subtitle:
            return ""

        response = self.session.get(
            subtitle["url"],
            timeout=self.timeout,
        )
        response.raise_for_status()

        return self._parse_vtt(response.text)
    
    def _transcript_ai(self, transcript: str) -> str:
        if not transcript:
            return ""

        client = GeminiClient(api_key=self.gemini_key,
                            system_instruction="""نقش شما: یک ویراستار حرفه‌ای متن مصاحبه و پاک‌سازی‌کننده رونوشت هستید.

وظیفه:
متن مصاحبه زیر را ویرایش کن تا خواناتر و حرفه‌ای‌تر شود، اما به هیچ عنوان محتوا، مفهوم، نظر، اطلاعات یا ترتیب منطقی صحبت‌ها را تغییر نده.

قوانین سخت‌گیرانه:

1. هیچ اطلاعات جدیدی اضافه نکن.
2. هیچ اطلاعاتی را حذف نکن، به جز موارد زیر:
   - تکرارهای غیرضروری
   - کلمات پرکننده و مکث‌های گفتاری
   - عبارات بی‌معنی ناشی از صحبت طبیعی
   - شروع‌های ناقص جمله که اصلاح آن‌ها معنی را تغییر نمی‌دهد
3. لحن و سبک بیان مصاحبه‌شونده را حفظ کن.
4. جملات را فقط از حالت کاملاً محاوره‌ای به نوشتاری روان تبدیل کن.
5. اصطلاحات تخصصی، اسامی، اعداد، تاریخ‌ها و نقل‌قول‌ها را دقیقاً حفظ کن.
6. هیچ برداشت، تحلیل، تفسیر یا نتیجه‌گیری اضافه نکن.
7. اگر جمله‌ای مبهم است، آن را حدس نزن؛ همان مفهوم مبهم را حفظ کن.
8. ترتیب صحبت‌ها و ساختار پرسش و پاسخ را حفظ کن.
9. پاسخ‌ها را خلاصه نکن؛ فقط متن را تمیز و فشرده کن.
10. خروجی باید فقط متن ویرایش‌شده باشد و هیچ توضیحی درباره تغییرات ارائه نکن.
11. خلاصه تمام متن رو در 3 تا 5 جمله

فرمت خروجی:

[سوال مصاحبه‌گر]
متن پاک‌سازی‌شده پرسش

[پاسخ مصاحبه‌شونده]
متن پاک‌سازی‌شده پاسخ

[خلاصه]
3 تا 5 جمله خلاصه متن
""",
                            generation_config=GenerationConfig(
                                temperature=0.15,
                                top_p=0.8
                            ))

        prompt = f"Summarize the following transcript in Persian:\n\n{transcript}"

        response = client.send(prompt)
        return response

    @staticmethod
    def _parse_vtt(vtt: str) -> str:
        lines = []
        started = False

        for line in vtt.splitlines():
            line = line.strip()

            if "-->" in line:
                started = True
                continue

            if not started:
                continue

            if not line or re.fullmatch(r"\d+", line):
                continue

            line = re.sub(r"<[^>]+>", "", line)

            if not lines:
                lines.append(line)
                continue

            previous = lines[-1]

            if line.startswith(previous):
                lines[-1] = line
            elif previous.startswith(line):
                continue
            else:
                lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _date(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.strptime(value, "%Y%m%d")

    @staticmethod
    def _timestamp(value: int | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromtimestamp(value)
    
    @staticmethod
    def _duration(seconds: int | None) -> str | None:
        if seconds is None:
            return None

        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours:
            return f"{hours:02}:{minutes:02}:{seconds:02}"

        return f"{minutes:02}:{seconds:02}"
